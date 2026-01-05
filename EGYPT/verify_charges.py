import pandas as pd
import numpy as np
import os
import re

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

# Clean column names
df_vendor.columns = df_vendor.columns.str.strip()
print(f"\nVendor columns: {list(df_vendor.columns)}")

# Create working dataframe
df_working = df_vendor.copy()

# Helper function to extract numeric values
def extract_numeric_value(val):
    """Extract first numeric value from a cell, handling various formats"""
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

# Helper function to extract aircraft registration
def extract_aircraft_reg(flight_info):
    """Extract registration number from flight info"""
    if pd.isna(flight_info):
        return None
    flight_str = str(flight_info).strip()
    # Format is typically "FLIGHTNUMBER REGISTRATION"
    parts = flight_str.split()
    if len(parts) >= 2:
        return parts[1]  # Second part is registration
    return None

print("\n" + "="*80)
print("DATA EXTRACTION AND PREPARATION")
print("="*80)

# Extract aircraft registration from flight column
df_working['Aircraft_Reg'] = df_working.iloc[:, 2].apply(extract_aircraft_reg)

# Extract MTOW from vendor data or lookup from master
# Note: MTOW might be in the vendor data directly or needs lookup
# Try to extract from flight details first
def extract_mtow_from_flight(flight_info):
    """Try to extract MTOW from flight info or use master file"""
    if pd.isna(flight_info):
        return np.nan
    # Aircraft type is typically after the departure/arrival airports
    flight_str = str(flight_info).strip()
    parts = flight_str.split()
    if len(parts) >= 4:
        aircraft_type = parts[-1]  # Last part is aircraft type code
        # This will be used to lookup in MTOW master
        return aircraft_type
    return None

# Extract aircraft type from flight column
df_working['Aircraft_Type'] = df_working.iloc[:, 2].apply(extract_mtow_from_flight)

# Lookup MTOW from master file using registration
print("\nLooking up MTOW from master file...")

def get_mtow_from_master(reg):
    """Get MTOW from master file using aircraft registration"""
    if pd.isna(reg) or reg is None:
        return np.nan
    matches = df_mtow_master[df_mtow_master['Aircraft'].str.strip() == str(reg).strip()]
    if len(matches) > 0:
        return matches.iloc[0]['MTOW_in_KGs']
    return np.nan

df_working['MTOW_numeric'] = df_working['Aircraft_Reg'].apply(get_mtow_from_master)

# Extract distance
distance_col = None
for col in df_working.columns:
    if 'DIST' in col.upper() or 'KM' in col.upper():
        distance_col = col
        break

if distance_col:
    print(f"Distance column identified: {distance_col}")
    df_working['Distance_numeric'] = df_working[distance_col].apply(extract_numeric_value)
else:
    print("WARNING: Distance column not found, attempting to extract from first numeric column")
    df_working['Distance_numeric'] = df_working.iloc[:, -3].apply(extract_numeric_value)

# Extract vendor charge - looking for currency values
vendor_charge_col = None
for col in df_working.columns:
    if 'CHARGE' in col.upper() or 'COST' in col.upper() or 'PRICE' in col.upper():
        vendor_charge_col = col
        break

if vendor_charge_col:
    print(f"Vendor charge column identified: {vendor_charge_col}")
    df_working['Vendor_Charge'] = df_working[vendor_charge_col].apply(extract_numeric_value)
else:
    print("WARNING: Vendor charge column not found")
    df_working['Vendor_Charge'] = np.nan

print(f"\nData Quality Check:")
print(f"  Records with valid MTOW: {df_working['MTOW_numeric'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid Distance: {df_working['Distance_numeric'].notna().sum()}/{len(df_working)}")
print(f"  Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# CALCULATION WORKFLOW
print("\n" + "="*80)
print("CALCULATION WORKFLOW")
print("="*80)

# Step 1: Calculate Weight Factor = SQRT(MTOW) / 50
print("\nStep 1: Calculate Weight Factor = SQRT(MTOW) / 50")
df_working['Weight_Factor'] = (np.sqrt(df_working['MTOW_numeric']) / 50).round(6)

# Step 2: Calculate Distance Factor = Distance / 100
print("Step 2: Calculate Distance Factor = Distance / 100")
df_working['Distance_Factor'] = (df_working['Distance_numeric'] / 100).round(4)

# Step 3: Apply constant Unit Rate = 21.38
print("Step 3: Apply constant Unit Rate = 21.38")
UNIT_RATE = 21.38
df_working['Unit_Rate'] = UNIT_RATE

# Step 4: Calculate Final Charges = Unit Rate * Distance Factor * Weight Factor
print("Step 4: Calculate Final Charges = Unit Rate * Distance Factor * Weight Factor")
df_working['Calculated_Charge'] = (
    df_working['Unit_Rate'] * 
    df_working['Distance_Factor'] * 
    df_working['Weight_Factor']
).round(2)

print("\nFormula Verification (Sample Calculation):")
if len(df_working[df_working['Calculated_Charge'].notna()]) > 0:
    sample = df_working[df_working['Calculated_Charge'].notna()].iloc[0]
    print(f"  MTOW: {sample['MTOW_numeric']} kg")
    print(f"  Weight Factor (SQRT({sample['MTOW_numeric']})/50): {sample['Weight_Factor']:.6f}")
    print(f"  Distance: {sample['Distance_numeric']} km")
    print(f"  Distance Factor ({sample['Distance_numeric']}/100): {sample['Distance_Factor']:.4f}")
    print(f"  Unit Rate: {UNIT_RATE}")
    print(f"  Final Charge: {UNIT_RATE} × {sample['Distance_Factor']:.4f} × {sample['Weight_Factor']:.6f} = {sample['Calculated_Charge']:.2f}")

# VERIFICATION
print("\n" + "="*80)
print("CHARGE VERIFICATION")
print("="*80)

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
print(f"- Records with valid MTOW: {df_working['MTOW_numeric'].notna().sum()}/{total_records}")
print(f"- Records with valid Distance: {df_working['Distance_numeric'].notna().sum()}/{total_records}")
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
print("\n" + "="*80)
print("DETAILED VERIFICATION RESULTS (First 20 rows):")
print("="*80)
display_cols = ['Aircraft_Reg', 'MTOW_numeric', 'Distance_numeric', 'Weight_Factor', 
                'Distance_Factor', 'Unit_Rate', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
print(df_working[display_cols].head(20).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[['Aircraft_Reg', 'MTOW_numeric', 'Distance_numeric', 
                                'Calculated_Charge', 'Vendor_Charge', 'Difference']].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: {valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: {valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: {valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {valid_mismatches['Vendor_Charge'].sum():.2f}")
        
        # Grouped by difference ranges
        print(f"\nMismatch Distribution:")
        ranges = [(0, 10), (10, 50), (50, 100), (100, 500), (500, 10000)]
        for low, high in ranges:
            count = len(valid_mismatches[(valid_mismatches['Difference'] >= low) & (valid_mismatches['Difference'] < high)])
            if count > 0:
                print(f"  Difference {low:>4} - {high:>5}: {count:>4} records")

# Save results
output_file = "Vendor_Data_Verified.csv"
output_cols = ['Aircraft_Reg', 'MTOW_numeric', 'Distance_numeric', 'Weight_Factor', 
               'Distance_Factor', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status']
df_output = df_working[output_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*80)
