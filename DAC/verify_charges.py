import pandas as pd
import numpy as np
import os

# File paths
vendor_file = "Vendor data.csv"
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

# Clean column names (remove extra spaces and newlines)
df_vendor.columns = df_vendor.columns.str.strip().str.replace('\n', ' ')
df_vendor.columns = [col.replace(' ', '_') for col in df_vendor.columns]

print(f"\nVendor columns: {list(df_vendor.columns)}")

# Identify the columns
vendor_charge_col = None
for col in df_vendor.columns:
    if 'RNC' in col.upper() or 'USD' in col.upper():
        vendor_charge_col = col
        break

if vendor_charge_col is None:
    print("ERROR: Could not find RNC(USD) column")
    print(f"Available columns: {list(df_vendor.columns)}")
    exit(1)

print(f"Vendor charge column identified: {vendor_charge_col}")

# Create working dataframe
df_working = df_vendor.copy()

# Column mappings - find the actual column names
regn_col = None
mtow_col = None
for col in df_working.columns:
    if 'Regn' in col or 'Registration' in col or 'Acft_Reg' in col:
        regn_col = col
    if 'MTOW' in col and 'KG' in col:
        mtow_col = col

print(f"\nIdentified columns:")
print(f"  Registration: {regn_col}")
print(f"  MTOW: {mtow_col}")

# Parse MTOW if in KG format
if mtow_col:
    df_working['MTOW_numeric'] = pd.to_numeric(df_working[mtow_col], errors='coerce')
else:
    print("WARNING: MTOW column not found, will try to extract from vendor data")
    df_working['MTOW_numeric'] = pd.to_numeric(df_working.iloc[:, -2], errors='coerce')

# Parse vendor charge
df_working['Vendor_Charge'] = pd.to_numeric(df_working[vendor_charge_col], errors='coerce')

print(f"\nData preparation:")
print(f"  Valid MTOW values: {df_working['MTOW_numeric'].notna().sum()}/{len(df_working)}")
print(f"  Valid Vendor charges: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# Map MTOW to rate master - direct lookup
def get_rate_for_mtow(mtow_value):
    """Find the charge for a given MTOW value"""
    if pd.isna(mtow_value):
        return np.nan
    
    # Try exact match first
    matching_rates = df_rate_master[df_rate_master['MTOW (KG)'] == mtow_value]
    
    if len(matching_rates) > 0:
        return matching_rates.iloc[0]['Charge']
    
    # If no exact match, try closest match
    rate_master_copy = df_rate_master.copy()
    rate_master_copy['MTOW_diff'] = abs(rate_master_copy['MTOW (KG)'] - mtow_value)
    closest = rate_master_copy.loc[rate_master_copy['MTOW_diff'].idxmin()]
    
    return closest['Charge']

print("\nMapping MTOW to rates...")
df_working['Rate_Master_Charge'] = df_working['MTOW_numeric'].apply(get_rate_for_mtow)

print(f"  Rate master matches: {df_working['Rate_Master_Charge'].notna().sum()}/{len(df_working)}")

# Verification: Compare calculated charge with vendor charge
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

df_working['Difference'] = abs(df_working['Rate_Master_Charge'] - df_working['Vendor_Charge'])
df_working['Status'] = df_working.apply(
    lambda row: check_match(row['Rate_Master_Charge'], row['Vendor_Charge']),
    axis=1
)

# Summary statistics
matched_count = (df_working['Status'] == 'Matched').sum()
not_matched_count = (df_working['Status'] == 'Not Matched').sum()
total_records = len(df_working)
success_rate = (matched_count / total_records) * 100 if total_records > 0 else 0

print("\n" + "="*80)
print("VERIFICATION SUMMARY")
print("="*80)
print(f"[MATCHED]     {matched_count}")
print(f"[NOT MATCHED] {not_matched_count}")
print(f"Total Records: {total_records}")
print(f"Success Rate:  {success_rate:.1f}%")

# Data quality metrics
print("\nData Quality:")
print(f"- Records with valid MTOW: {df_working['MTOW_numeric'].notna().sum()}/{total_records} ({(df_working['MTOW_numeric'].notna().sum()/total_records)*100:.1f}%)")
print(f"- Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{total_records}")
print(f"- Records with Rate Master matches: {df_working['Rate_Master_Charge'].notna().sum()}/{total_records}")

# Matched charges statistics
matched_data = df_working[df_working['Status'] == 'Matched']
if len(matched_data) > 0:
    print("\nMatched Charges:")
    print(f"  Count: {len(matched_data)}")
    print(f"  Min: {matched_data['Vendor_Charge'].min():.2f}")
    print(f"  Max: {matched_data['Vendor_Charge'].max():.2f}")
    print(f"  Mean: {matched_data['Vendor_Charge'].mean():.2f}")
    print(f"  Total: {matched_data['Vendor_Charge'].sum():.2f}")

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Rate_Master_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 20):")
        print(valid_mismatches[[regn_col, 'MTOW_numeric', 'Rate_Master_Charge', 'Vendor_Charge', 'Difference']].head(20).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: {valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: {valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: {valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results
output_file = "Vendor_Data_Verified.csv"

# Select relevant columns for output
output_cols = []
if regn_col:
    output_cols.append(regn_col)
output_cols.extend(['MTOW_numeric', 'Rate_Master_Charge', 'Vendor_Charge', 'Difference', 'Status'])

df_output = df_working[output_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*80)
