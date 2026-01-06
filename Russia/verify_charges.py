import pandas as pd
import numpy as np
import os
import re
import math

# File paths
vendor_file = "1900374834.csv"
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

# Clean column names - remove newlines and extra spaces
df_vendor.columns = df_vendor.columns.str.strip().str.replace('\n', ' ').str.replace('\r', ' ')
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
    # Remove spaces within numbers (e.g., "4 779.40" -> "4779.40")
    val_str = val_str.replace(' ', '')
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

# Find the correct columns
distance_col = None
mtow_col = None
charge_col = None
reg_col = None

for col in df_working.columns:
    col_lower = col.lower()
    if 'distance' in col_lower and 'km' in col_lower:
        distance_col = col
    if 'mtow' in col_lower and ('tons' in col_lower or 'ton' in col_lower):
        mtow_col = col
    if 'en-route' in col_lower and 'amount' in col_lower and 'usd' in col_lower:
        charge_col = col
    if 'registration' in col_lower or 'registr' in col_lower:
        reg_col = col

print(f"Identified columns:")
print(f"  Distance: {distance_col}")
print(f"  MTOW: {mtow_col}")
print(f"  Registration: {reg_col}")
print(f"  Vendor Charge: {charge_col}")

# Extract registration number
if reg_col is None:
    # Fallback to a column that likely contains registration
    for col in df_working.columns:
        if 'registr' in col.lower():
            reg_col = col
            break

df_working['Aircraft_Reg'] = df_working[reg_col].apply(lambda x: str(x).strip() if pd.notna(x) else None)

# Extract distance (in km)
df_working['Distance_km'] = df_working[distance_col].apply(extract_numeric_value)

# Extract MTOW (in tons)
mtow_found = False
for col in df_working.columns:
    col_lower = col.lower()
    # Check for MT OM pattern (common in poorly formatted CSV)
    if ('mtom' in col_lower or 'mt om' in col_lower or 'mtow' in col_lower):
        if ('tons' in col_lower or 'ton' in col_lower):
            mtow_col = col
            df_working['MTOW_tons'] = df_working[col].apply(extract_numeric_value)
            mtow_found = True
            print(f"Found MTOW column: {mtow_col}")
            break

if not mtow_found:
    print("ERROR: Could not find MTOW column")
    print(f"Searched columns: {[col for col in df_working.columns if 'mtow' in col.lower() or 'mt om' in col.lower()]}")
    df_working['MTOW_tons'] = np.nan

# Extract vendor charge
df_working['Vendor_Charge'] = df_working[charge_col].apply(extract_numeric_value)

print(f"\nData Quality Check:")
print(f"  Records with valid Distance: {df_working['Distance_km'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid MTOW: {df_working['MTOW_tons'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 2: DISTANCE ROUNDING
print("\n" + "="*100)
print("STEP 2: DISTANCE ROUNDING (To Nearest Highest Hundred)")
print("="*100)

# Round distance to nearest highest hundred
def round_to_nearest_highest_hundred(distance):
    """Round distance to nearest highest value in hundreds"""
    if pd.isna(distance):
        return np.nan
    # If distance is already a multiple of 100, keep it
    if distance % 100 == 0:
        return distance
    # Otherwise round up to next hundred
    return math.ceil(distance / 100) * 100

df_working['Distance_Rounded'] = df_working['Distance_km'].apply(round_to_nearest_highest_hundred)

print(f"\nDistance Rounding Examples:")
sample_distances = df_working[df_working['Distance_km'].notna()].head(10)
for idx, row in sample_distances.iterrows():
    print(f"  {row['Distance_km']:>8.1f} km -> {row['Distance_Rounded']:>8.1f} km")

# STEP 3: UNIT RATE LOOKUP
print("\n" + "="*100)
print("STEP 3: UNIT RATE LOOKUP FROM RATE MASTER")
print("="*100)

# Create MTOW to Unit Rate mapping from rate master
mtow_to_rate = dict(zip(df_rate_master['MTOW'], df_rate_master['Unit Rate']))

print(f"Rate Master MTOW-to-UnitRate Mapping:")
for mtow, rate in mtow_to_rate.items():
    if pd.notna(mtow) and pd.notna(rate):
        print(f"  MTOW {mtow:>10} -> Unit Rate {rate:>8.1f}")

# Lookup unit rate based on MTOW
def get_unit_rate(mtow):
    """Get unit rate from rate master based on MTOW (convert tonnes to kg for matching)"""
    if pd.isna(mtow):
        return np.nan
    
    # Vendor MTOW is in tonnes, convert to kg for matching with rate master
    mtow_kg = mtow * 1000
    
    # Try exact match first
    if mtow_kg in mtow_to_rate:
        return mtow_to_rate[mtow_kg]
    
    # Try closest match
    closest_mtow = min(mtow_to_rate.keys(), 
                       key=lambda x: abs(x - mtow_kg) if pd.notna(x) else float('inf'))
    if pd.notna(closest_mtow):
        return mtow_to_rate[closest_mtow]
    
    return np.nan

df_working['Unit_Rate_mapped'] = df_working['MTOW_tons'].apply(get_unit_rate)

print(f"\nUnit Rate Lookup Results:")
print(f"  Matched rates: {df_working['Unit_Rate_mapped'].notna().sum()}/{len(df_working)}")

# STEP 4: CHARGE CALCULATION
print("\n" + "="*100)
print("STEP 4: CHARGE CALCULATION: Unit Rate * (Rounded Distance / 100)")
print("="*100)

# Calculate charge: Unit Rate * (Distance / 100)
df_working['Calculated_Charge'] = (
    df_working['Unit_Rate_mapped'] * 
    (df_working['Distance_Rounded'] / 100)
).round(2)

print(f"\nFormula Verification (Sample Calculation):")
if len(df_working[df_working['Calculated_Charge'].notna()]) > 0:
    sample = df_working[df_working['Calculated_Charge'].notna()].iloc[0]
    print(f"  Original Distance: {sample['Distance_km']} km")
    print(f"  Rounded Distance: {sample['Distance_Rounded']} km")
    print(f"  MTOW: {sample['MTOW_tons']} tons")
    print(f"  Unit Rate: {sample['Unit_Rate_mapped']}")
    print(f"  Calculation: {sample['Unit_Rate_mapped']} * ({sample['Distance_Rounded']}/100) = {sample['Calculated_Charge']:.2f}")

# STEP 5: VERIFICATION
print("\n" + "="*100)
print("STEP 5: CHARGE VERIFICATION")
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
print(f"- Records with valid Distance: {df_working['Distance_km'].notna().sum()}/{total_records}")
print(f"- Records with valid MTOW: {df_working['MTOW_tons'].notna().sum()}/{total_records}")
print(f"- Records with valid Unit Rate: {df_working['Unit_Rate_mapped'].notna().sum()}/{total_records}")
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
display_cols = ['Aircraft_Reg', 'Distance_km', 'Distance_Rounded', 'MTOW_tons', 
                'Unit_Rate_mapped', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
print(df_working[display_cols].head(20).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[['Aircraft_Reg', 'Distance_Rounded', 'MTOW_tons', 'Unit_Rate_mapped',
                                'Calculated_Charge', 'Vendor_Charge', 'Difference']].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: {valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: {valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: {valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results
output_file = "1900374834_Verified.csv"

output_cols = ['Aircraft_Reg', 'Distance_km', 'Distance_Rounded', 'MTOW_tons', 
               'Unit_Rate_mapped', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
df_output = df_working[output_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
