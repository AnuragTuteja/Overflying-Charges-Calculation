import pandas as pd
import numpy as np
import os
import re

# File paths
vendor_file = "Vendor Master.csv"
mtow_master_file = "MTOW Master.xlsx - Sheet1.csv"
rate_master_file = "Rate Master.csv"

# Read files
print("Loading files...")
df_vendor = pd.read_csv(vendor_file)
df_mtow_master = pd.read_csv(mtow_master_file)
df_rate_master = pd.read_csv(rate_master_file)

print(f"Vendor data loaded: {len(df_vendor)} records")
print(f"MTOW Master loaded: {len(df_mtow_master)} aircraft")
print(f"Rate Master loaded: {len(df_rate_master)} rate entries")

# Clean column names - remove non-breaking spaces and extra whitespace
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
    # Remove currency symbols
    val_str = val_str.replace('$', '').replace(',', '')
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

# Extract aircraft registration
reg_col = 'Reg No. Dept'
df_working['Aircraft_Reg'] = df_working[reg_col].apply(lambda x: str(x).strip() if pd.notna(x) else None)

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

# Extract vendor charges from A/N Charge column
total_col = 'A/N Charge'
df_working['Vendor_Charge'] = df_working[total_col].apply(extract_numeric_value)

print(f"  Valid vendor charges: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 2: RATE MASTER LOOKUP
print("\n" + "="*100)
print("STEP 2: FLAT RATE LOOKUP FROM RATE MASTER")
print("="*100)

# Create MTOW to Charge mapping from rate master
print(f"\nRate Master MTOW-to-Charge Mapping:")
print(f"{'MTOW (KG)':<15} {'Charge (USD)':<15}")
print("-" * 30)
for idx, row in df_rate_master.iterrows():
    print(f"{row['MTOW']:<15} {row['Charge']:<15}")

# Lookup charge based on MTOW
def get_charge_from_master(mtow):
    """Get flat rate charge from rate master based on MTOW"""
    if pd.isna(mtow):
        return np.nan
    
    # Convert to numeric
    try:
        mtow = float(mtow)
    except (ValueError, TypeError):
        return np.nan
    
    # Try exact match first
    matching_rates = df_rate_master[df_rate_master['MTOW'] == mtow]
    
    if len(matching_rates) > 0:
        return matching_rates.iloc[0]['Charge']
    
    # Try closest match
    rate_master_copy = df_rate_master.copy()
    # Ensure MTOW is numeric in rate master too
    rate_master_copy['MTOW'] = pd.to_numeric(rate_master_copy['MTOW'], errors='coerce')
    rate_master_copy = rate_master_copy[rate_master_copy['MTOW'].notna()]
    
    if len(rate_master_copy) == 0:
        return np.nan
    
    rate_master_copy['MTOW_diff'] = abs(rate_master_copy['MTOW'] - mtow)
    best_match = rate_master_copy.loc[rate_master_copy['MTOW_diff'].idxmin()]
    
    return best_match['Charge']

df_working['Calculated_Charge'] = df_working['MTOW'].apply(get_charge_from_master)

print(f"\nCharge Mapping Results:")
print(f"  Successfully mapped: {df_working['Calculated_Charge'].notna().sum()}/{len(df_working)}")

# STEP 3: VERIFICATION
print("\n" + "="*100)
print("STEP 3: CHARGE VERIFICATION")
print("="*100)

# Compare calculated vs vendor charges with tolerance
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

# Summary statistics
matched_count = (df_working['Status'] == 'Matched').sum()
not_matched_count = (df_working['Status'] == 'Not Matched').sum()
total_records = len(df_working)
success_rate = (matched_count / total_records) * 100 if total_records > 0 else 0

print(f"\n[MATCHED]     {matched_count}")
print(f"[NOT MATCHED] {not_matched_count}")
print(f"Total Records: {total_records}")
print(f"Success Rate:  {success_rate:.1f}%")

# Data quality metrics
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

# Detailed verification results
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS (First 30 rows):")
print("="*100)
display_cols = ['Aircraft_Reg', 'MTOW', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
print(df_working[display_cols].head(30).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 20):")
        print(valid_mismatches[['Aircraft_Reg', 'MTOW', 'Calculated_Charge', 'Vendor_Charge', 'Difference']].head(20).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: ${valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: ${valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: ${valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: ${valid_mismatches['Vendor_Charge'].sum():.2f}")
        
        # Group by difference ranges
        print(f"\nMismatch Distribution:")
        ranges = [(0, 10), (10, 50), (50, 100), (100, 500)]
        for low, high in ranges:
            count = len(valid_mismatches[(valid_mismatches['Difference'] >= low) & (valid_mismatches['Difference'] < high)])
            if count > 0:
                print(f"  Difference ${low:>3} - ${high:>3}: {count:>4} records")

# Save results
output_file = "Vendor_Master_Verified.csv"

output_cols = ['Aircraft_Reg', 'MTOW', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
df_output = df_working[output_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
