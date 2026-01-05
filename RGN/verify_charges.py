import pandas as pd
import numpy as np
import os
import re
import glob

# File paths - detect files automatically
vendor_files = glob.glob("*.csv")
vendor_file = None
mtow_master_file = None
rate_master_file = None

# Identify files
for f in vendor_files:
    f_lower = f.lower()
    if 'mtow' in f_lower and 'master' in f_lower:
        mtow_master_file = f
    elif 'rate' in f_lower and 'master' in f_lower:
        rate_master_file = f
    elif 'vendor' in f_lower and 'master' in f_lower:
        vendor_file = f

# If vendor master not found, use the remaining CSV file
if vendor_file is None and len(vendor_files) >= 3:
    for f in vendor_files:
        f_lower = f.lower()
        if 'mtow' not in f_lower and 'rate' not in f_lower:
            vendor_file = f
            break

print(f"Detected files:")
print(f"  Vendor: {vendor_file}")
print(f"  MTOW Master: {mtow_master_file}")
print(f"  Rate Master: {rate_master_file}")

if not all([vendor_file, mtow_master_file, rate_master_file]):
    print("ERROR: Could not detect all required files")
    exit(1)

# Read files
print("\nLoading files...")
df_vendor = pd.read_csv(vendor_file)
df_mtow_master = pd.read_csv(mtow_master_file)
df_rate_master = pd.read_csv(rate_master_file)

print(f"Vendor data loaded: {len(df_vendor)} records")
print(f"MTOW Master loaded: {len(df_mtow_master)} aircraft")
print(f"Rate Master loaded: {len(df_rate_master)} rate entries")

# Clean column names - remove special characters and non-breaking spaces
df_vendor.columns = df_vendor.columns.str.replace('\xa0', ' ').str.strip()
df_mtow_master.columns = df_mtow_master.columns.str.strip()
df_rate_master.columns = df_rate_master.columns.str.strip()

print(f"\nVendor columns: {list(df_vendor.columns)}")

# Create working dataframe
df_working = df_vendor.copy()

# Helper function to extract numeric values
def extract_numeric_value(val):
    """Extract numeric value from a cell, handling currency formats"""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace('\n', ' ').replace('\r', ' ')
    # Remove currency symbols and commas
    val_str = val_str.replace('$', '').replace(',', '').replace('USD', '')
    match = re.search(r'(\d+\.?\d*)', val_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return np.nan
    return np.nan

print("\n" + "="*100)
print("STEP 1: DATA EXTRACTION AND MTOW LOOKUP")
print("="*100)

# Find registration column
reg_col = None
for col in df_working.columns:
    col_lower = col.lower()
    if 'reg' in col_lower and 'no' in col_lower:
        reg_col = col
        break

if reg_col is None:
    # Try alternate patterns
    for col in df_working.columns:
        col_lower = col.lower()
        if 'reg' in col_lower or 'aircraft' in col_lower:
            reg_col = col
            break

print(f"Registration column: {reg_col}")

if reg_col:
    df_working['Aircraft_Reg'] = df_working[reg_col].apply(lambda x: str(x).strip() if pd.notna(x) else None)
else:
    print("ERROR: Could not find registration column")
    df_working['Aircraft_Reg'] = None

# Lookup MTOW from master file
def get_mtow_from_master(reg):
    """Get MTOW from master file using aircraft registration"""
    if pd.isna(reg) or reg is None:
        return np.nan
    matches = df_mtow_master[df_mtow_master['Aircraft'].str.strip() == str(reg).strip()]
    if len(matches) > 0:
        return matches.iloc[0]['MTOW_in_KGs']
    return np.nan

df_working['MTOW'] = df_working['Aircraft_Reg'].apply(get_mtow_from_master)

print(f"\nMTOW Lookup Results:")
print(f"  Successfully mapped: {df_working['MTOW'].notna().sum()}/{len(df_working)}")

# Find vendor charge column
charge_col = None
for col in df_working.columns:
    col_lower = col.lower()
    if any(term in col_lower for term in ['charge', 'cost', 'amount', 'total']):
        if 'holiday' not in col_lower and 'ot' not in col_lower and 'vat' not in col_lower:
            charge_col = col
            break

if charge_col is None:
    # Use last numeric column if not found
    for col in reversed(df_working.columns):
        if df_working[col].dtype in ['float64', 'int64']:
            charge_col = col
            break

print(f"Vendor charge column: {charge_col}")

if charge_col:
    df_working['Vendor_Charge'] = df_working[charge_col].apply(extract_numeric_value)
else:
    df_working['Vendor_Charge'] = np.nan

print(f"  Valid vendor charges: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 2: RATE MASTER LOOKUP
print("\n" + "="*100)
print("STEP 2: FLAT RATE LOOKUP FROM RATE MASTER")
print("="*100)

# Display rate master mapping
print(f"\nRate Master MTOW-to-Charge Mapping:")
mtow_col = None
charge_rate_col = None
for col in df_rate_master.columns:
    if 'mtow' in col.lower():
        mtow_col = col
    if 'charge' in col.lower() and 'rate' not in col.lower():
        charge_rate_col = col

if mtow_col and charge_rate_col:
    for idx, row in df_rate_master.iterrows():
        print(f"  MTOW {row[mtow_col]:<15} -> Charge {row[charge_rate_col]}")

# Lookup charge based on MTOW (converting to tonnes if needed)
def get_charge_from_master(mtow):
    """Get flat rate charge from rate master based on MTOW"""
    if pd.isna(mtow):
        return np.nan
    
    try:
        mtow = float(mtow)
    except (ValueError, TypeError):
        return np.nan
    
    # Find numeric columns in rate master
    numeric_cols = df_rate_master.select_dtypes(include=[np.number]).columns
    
    if len(numeric_cols) < 2:
        return np.nan
    
    # First numeric column is usually MTOW, second is Charge
    mtow_col = numeric_cols[0]
    charge_col = numeric_cols[1]
    
    # Convert MTOW to tonnes (from kg)
    mtow_tonnes = mtow / 1000.0
    
    # Try exact match with kg
    matching_rates = df_rate_master[df_rate_master[mtow_col] == mtow]
    if len(matching_rates) > 0:
        return matching_rates.iloc[0][charge_col]
    
    # Try exact match with tonnes
    matching_rates = df_rate_master[df_rate_master[mtow_col] == mtow_tonnes]
    if len(matching_rates) > 0:
        return matching_rates.iloc[0][charge_col]
    
    # Try closest match with tonnes
    rate_copy = df_rate_master.copy()
    rate_copy[mtow_col] = pd.to_numeric(rate_copy[mtow_col], errors='coerce')
    rate_copy = rate_copy[rate_copy[mtow_col].notna()]
    
    if len(rate_copy) == 0:
        return np.nan
    
    # Check if rate master uses tonnes or kg
    # If max value is < 500, likely tonnes; if > 50000, likely kg
    max_mtow = rate_copy[mtow_col].max()
    if max_mtow < 500:  # Using tonnes
        rate_copy['MTOW_diff'] = abs(rate_copy[mtow_col] - mtow_tonnes)
    else:  # Using kg
        rate_copy['MTOW_diff'] = abs(rate_copy[mtow_col] - mtow)
    
    best_match = rate_copy.loc[rate_copy['MTOW_diff'].idxmin()]
    
    return best_match[charge_col]

df_working['Calculated_Charge'] = df_working['MTOW'].apply(get_charge_from_master)

print(f"\nCharge Mapping Results:")
print(f"  Successfully mapped: {df_working['Calculated_Charge'].notna().sum()}/{len(df_working)}")

# STEP 3: VERIFICATION
print("\n" + "="*100)
print("STEP 3: CHARGE VERIFICATION")
print("="*100)

tolerance = 0.01

def check_match(calculated, vendor):
    """Check if calculated charge matches vendor charge within tolerance"""
    if pd.isna(calculated) or pd.isna(vendor):
        return "Not Matched"
    diff = abs(calculated - vendor)
    if diff <= tolerance:
        return "Matched"
    else:
        return "Not Matched"

df_working['Difference'] = abs(df_working['Calculated_Charge'] - df_working['Vendor_Charge'])
df_working['Status'] = df_working.apply(
    lambda row: check_match(row['Calculated_Charge'], row['Vendor_Charge']),
    axis=1
)

# Summary
matched_count = (df_working['Status'] == 'Matched').sum()
not_matched_count = (df_working['Status'] == 'Not Matched').sum()
total_records = len(df_working)
success_rate = (matched_count / total_records) * 100 if total_records > 0 else 0

print(f"\n[MATCHED]     {matched_count}")
print(f"[NOT MATCHED] {not_matched_count}")
print(f"Total Records: {total_records}")
print(f"Success Rate:  {success_rate:.1f}%")

print("\nData Quality:")
print(f"- Records with valid MTOW: {df_working['MTOW'].notna().sum()}/{total_records} ({(df_working['MTOW'].notna().sum()/total_records)*100:.1f}%)")
print(f"- Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{total_records}")
print(f"- Records with Rate Master matches: {df_working['Calculated_Charge'].notna().sum()}/{total_records}")

# Matched charges statistics
matched_data = df_working[df_working['Status'] == 'Matched']
if len(matched_data) > 0:
    print("\nMatched Charges:")
    print(f"  Count: {len(matched_data)}")
    print(f"  Min: ${matched_data['Vendor_Charge'].min():.2f}")
    print(f"  Max: ${matched_data['Vendor_Charge'].max():.2f}")
    print(f"  Mean: ${matched_data['Vendor_Charge'].mean():.2f}")
    print(f"  Total: ${matched_data['Vendor_Charge'].sum():.2f}")

# Detailed results (first 20)
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS (First 20 rows):")
print("="*100)
display_cols = [col for col in ['Aircraft_Reg', 'MTOW', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status'] 
                if col in df_working.columns]
print(df_working[display_cols].head(20).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[display_cols].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: ${valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: ${valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: ${valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: ${valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results
output_file = "Verification_Results.csv"
df_output = df_working[display_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
