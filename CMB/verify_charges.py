import pandas as pd
import numpy as np
import os
import re

# File paths
mtow_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\CMB\MTOW Master.csv"
rate_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\CMB\Rate Master.csv"
vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\CMB\Vendor Data.csv"

# Read files
print("Loading files...")
df_vendor = pd.read_csv(vendor_file)
df_mtow_master = pd.read_csv(mtow_master)
df_rate_master = pd.read_csv(rate_master)

print(f"Vendor data loaded: {len(df_vendor)} records")
print(f"MTOW Master loaded: {len(df_mtow_master)} aircraft")
print(f"Rate Master loaded: {len(df_rate_master)} rate entries")

# Clean column names
df_vendor.columns = df_vendor.columns.str.strip()
df_mtow_master.columns = df_mtow_master.columns.str.strip()
df_rate_master.columns = df_rate_master.columns.str.strip()

print(f"\nVendor columns: {list(df_vendor.columns)}")

# Create working dataframe
df_working = df_vendor.copy()

# Helper function to extract numeric values
def extract_numeric_value(val):
    """Extract first numeric value from a cell"""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace('\n', ' ').replace('\r', ' ')
    match = re.search(r'(\d+\.?\d*)', val_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return np.nan
    return np.nan

print("\n" + "="*100)
print("STEP 1: DATA EXTRACTION")
print("="*100)

# Extract registration number
reg_col = 'Registration No'
df_working['Aircraft_Reg'] = df_working[reg_col].apply(lambda x: str(x).strip() if pd.notna(x) else None)

# Extract distance (in NM - Nautical Miles)
distance_col = None
for col in df_working.columns:
    if 'Distance' in col and 'NM' in col:
        distance_col = col
        break

if distance_col is None:
    # Try to find distance column by checking for numeric column with large values
    for col in df_working.columns:
        if 'Distance' in col or 'distance' in col:
            distance_col = col
            break

print(f"Distance column identified: {distance_col}")
df_working['Distance_NM'] = df_working[distance_col].apply(extract_numeric_value)

# Extract MTOW (in M.Ton or tonnes)
mtow_col = None
for col in df_working.columns:
    if 'MTOW' in col and 'Ton' in col:
        mtow_col = col
        break

print(f"MTOW column identified: {mtow_col}")
df_working['MTOW_tonnes'] = df_working[mtow_col].apply(extract_numeric_value)

# Extract vendor charge
charge_col = 'Charge'
df_working['Vendor_Charge'] = df_working[charge_col].apply(extract_numeric_value)

print(f"\nData Quality Check:")
print(f"  Records with valid Distance: {df_working['Distance_NM'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid MTOW: {df_working['MTOW_tonnes'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 2: DISTANCE CAPPING
print("\n" + "="*100)
print("STEP 2: DISTANCE CAPPING LOGIC")
print("="*100)

# Apply distance capping rules:
# - If distance < 300, use 300
# - If distance > 600, use 600
# - Otherwise use actual distance
def cap_distance(distance):
    """Apply distance capping rules"""
    if pd.isna(distance):
        return np.nan
    if distance < 300:
        return 300
    elif distance > 600:
        return 600
    else:
        return distance

df_working['Distance_Capped'] = df_working['Distance_NM'].apply(cap_distance)

print(f"\nDistance Capping Results:")
below_300 = (df_working['Distance_NM'] < 300).sum()
above_600 = (df_working['Distance_NM'] > 600).sum()
between = ((df_working['Distance_NM'] >= 300) & (df_working['Distance_NM'] <= 600)).sum()
print(f"  Distance < 300 (capped to 300): {below_300}")
print(f"  Distance between 300-600 (unchanged): {between}")
print(f"  Distance > 600 (capped to 600): {above_600}")

# STEP 3: CHARGE CALCULATION
print("\n" + "="*100)
print("STEP 3: CHARGE CALCULATION: (Capped Distance + MTOW) / 3")
print("="*100)

# Calculate charge: (Capped Distance + MTOW) / 3
df_working['Calculated_Charge'] = (
    (df_working['Distance_Capped'] + df_working['MTOW_tonnes']) / 3
).round(2)

print(f"\nFormula Verification (Sample Calculation):")
if len(df_working[df_working['Calculated_Charge'].notna()]) > 0:
    sample = df_working[df_working['Calculated_Charge'].notna()].iloc[0]
    print(f"  Original Distance (NM): {sample['Distance_NM']}")
    print(f"  Capped Distance: {sample['Distance_Capped']}")
    print(f"  MTOW (M.Ton): {sample['MTOW_tonnes']}")
    print(f"  Calculation: ({sample['Distance_Capped']} + {sample['MTOW_tonnes']}) / 3 = {sample['Calculated_Charge']:.2f}")

# STEP 4: VERIFICATION
print("\n" + "="*100)
print("STEP 4: CHARGE VERIFICATION")
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
print(f"- Records with valid Distance: {df_working['Distance_NM'].notna().sum()}/{total_records}")
print(f"- Records with valid MTOW: {df_working['MTOW_tonnes'].notna().sum()}/{total_records}")
print(f"- Records with existing charges: {df_working['Vendor_Charge'].notna().sum()}/{total_records}")
print(f"- Records with calculated charges: {df_working['Calculated_Charge'].notna().sum()}/{total_records}")

# Matched charges statistics
matched_data = df_working[df_working['Status'] == 'Matched']
if len(matched_data) > 0:
    print("\nMatched Charges:")
    print(f"  Count: {len(matched_data)}")
    print(f"  Min: {matched_data['Vendor_Charge'].min():.2f}")
    print(f"  Max: {matched_data['Vendor_Charge'].max():.2f}")
    print(f"  Mean: {matched_data['Vendor_Charge'].mean():.2f}")
    print(f"  Total: {matched_data['Vendor_Charge'].sum():.2f}")

# Detailed verification results
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS (First 20 rows):")
print("="*100)
display_cols = ['Aircraft_Reg', 'Distance_NM', 'Distance_Capped', 'MTOW_tonnes', 
                'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
print(df_working[display_cols].head(20).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[['Aircraft_Reg', 'Distance_NM', 'Distance_Capped', 'MTOW_tonnes',
                                'Calculated_Charge', 'Vendor_Charge', 'Difference']].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: {valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: {valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: {valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results

output_cols = ['Aircraft_Reg', 'Distance_NM', 'Distance_Capped', 'MTOW_tonnes', 
               'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
df_output = df_working[output_cols].copy()
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\CMB\Vendor_Data_Verified.csv"
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
