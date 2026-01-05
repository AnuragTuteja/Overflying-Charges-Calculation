import pandas as pd
import numpy as np
import os
import re

# File paths
vendor_file = "1900373598.csv"
iata_mapping_file = "IATA ICAO Mapping.xlsx - Sheet1.csv"
mtow_master_file = "MTOW Master.xlsx - Sheet1.csv"
rate_master_file = "Rate Master.csv"

# Read files
print("Loading files...")
df_vendor = pd.read_csv(vendor_file)
df_iata = pd.read_csv(iata_mapping_file)
df_mtow_master = pd.read_csv(mtow_master_file)
df_rate_master = pd.read_csv(rate_master_file)

print(f"Vendor data loaded: {len(df_vendor)} records")
print(f"IATA-ICAO Mapping loaded: {len(df_iata)} airports")
print(f"MTOW Master loaded: {len(df_mtow_master)} aircraft")
print(f"Rate Master loaded: {len(df_rate_master)} rate entries")

# Clean column names
df_vendor.columns = df_vendor.columns.str.strip()
df_iata.columns = df_iata.columns.str.strip()
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
print("STEP 1: IATA CODE EXTRACTION AND AIRPORT MAPPING")
print("="*100)

# Extract IATA codes from From and To columns
from_col = 'From'
to_col = 'To'

# Extract From IATA code - take first 4 characters or until space
def extract_iata(val):
    if pd.isna(val):
        return None
    iata_str = str(val).strip().upper()
    # Take first part (before space if exists)
    if ' ' in iata_str:
        return iata_str.split()[0][:4]
    return iata_str[:4]

df_working['FROM_IATA'] = df_working[from_col].apply(extract_iata)
df_working['TO_IATA'] = df_working[to_col].apply(extract_iata)

# Create IATA to Airport name lookup
iata_lookup = dict(zip(df_iata['IATA'], df_iata['Airport']))
iata_to_icao = dict(zip(df_iata['IATA'], df_iata['ICAO']))

df_working['FROM_AIRPORT'] = df_working['FROM_IATA'].map(iata_lookup)
df_working['TO_AIRPORT'] = df_working['TO_IATA'].map(iata_lookup)
df_working['TO_ICAO'] = df_working['TO_IATA'].map(iata_to_icao)

print(f"IATA mapping completed:")
print(f"  From airport mapped: {df_working['FROM_AIRPORT'].notna().sum()}/{len(df_working)}")
print(f"  To airport mapped: {df_working['TO_AIRPORT'].notna().sum()}/{len(df_working)}")

# STEP 2: Landing Detection - Check if landed in AUH
print("\n" + "="*100)
print("STEP 2: LANDING DETECTION")
print("="*100)

# Landing in AUH if destination is AUH
df_working['LANDED_IN_AUH'] = df_working['TO_IATA'].str.upper() == 'AUH'
df_working['FLIGHT_TYPE'] = df_working['LANDED_IN_AUH'].apply(
    lambda x: 'With landing' if x else 'Without landing (Overflight)'
)

landing_count = df_working['LANDED_IN_AUH'].sum()
overflight_count = len(df_working) - landing_count

print(f"Flight Type Distribution:")
print(f"  With landing (to AUH): {landing_count}")
print(f"  Without landing (Overflight): {overflight_count}")
print(f"  Total: {len(df_working)}")

# STEP 3: MTOW Lookup from Master
print("\n" + "="*100)
print("STEP 3: MTOW LOOKUP FROM MASTER")
print("="*100)

# Extract aircraft registration from Info column
info_col = 'Info'
df_working['AIRCRAFT_REG'] = df_working[info_col].apply(lambda x: str(x).strip() if pd.notna(x) else None)

# Lookup MTOW from master file
def get_mtow_from_master(reg):
    """Get MTOW from master file using aircraft registration"""
    if pd.isna(reg) or reg is None:
        return np.nan
    matches = df_mtow_master[df_mtow_master['Aircraft'].str.strip() == str(reg).strip()]
    if len(matches) > 0:
        return matches.iloc[0]['MTOW_in_KGs']
    return np.nan

df_working['MTOW_tonnes'] = df_working['AIRCRAFT_REG'].apply(get_mtow_from_master)
# Convert to tonnes (divide by 1000) only if numeric
df_working['MTOW_tonnes'] = pd.to_numeric(df_working['MTOW_tonnes'], errors='coerce') / 1000

print(f"MTOW lookup results:")
print(f"  Valid MTOW values: {df_working['MTOW_tonnes'].notna().sum()}/{len(df_working)}")

# STEP 4: Rate Master Lookup
print("\n" + "="*100)
print("STEP 4: RATE MASTER LOOKUP")
print("="*100)

# For each flight, find the matching rate based on MTOW
def get_rate_from_master(mtow_tonnes):
    """Find the charge rate for a given MTOW"""
    if pd.isna(mtow_tonnes):
        return np.nan
    
    mtow_kg = mtow_tonnes * 1000
    
    # Try exact match first
    matching_rates = df_rate_master[df_rate_master['Mtow'] == mtow_kg]
    
    if len(matching_rates) > 0:
        return matching_rates.iloc[0]['Charge']
    
    # If no exact match, use closest match
    rate_master_copy = df_rate_master.copy()
    rate_master_copy['MTOW_diff'] = abs(rate_master_copy['Mtow'] - mtow_kg)
    best_match = rate_master_copy.loc[rate_master_copy['MTOW_diff'].idxmin()]
    
    return best_match['Charge']

df_working['Unit_Rate_mapped'] = df_working['MTOW_tonnes'].apply(get_rate_from_master)

print(f"Rate master matching results:")
print(f"  Matched rates: {df_working['Unit_Rate_mapped'].notna().sum()}/{len(df_working)}")

# STEP 5: Extract Vendor Charge
print("\n" + "="*100)
print("STEP 5: VENDOR CHARGE EXTRACTION")
print("="*100)

charge_col = 'Charge'
df_working['Vendor_Charge'] = df_working[charge_col].apply(extract_numeric_value)

print(f"Vendor charge extraction:")
print(f"  Valid charges: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 6: Verification
print("\n" + "="*100)
print("STEP 6: CHARGE VERIFICATION")
print("="*100)

# Calculated charge equals mapped unit rate for flat rate verification
df_working['Calculated_Charge'] = df_working['Unit_Rate_mapped']

# Compare charges
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

print("\n" + "="*100)
print("VERIFICATION SUMMARY")
print("="*100)
print(f"[MATCHED]     {matched_count}")
print(f"[NOT MATCHED] {not_matched_count}")
print(f"Total Records: {total_records}")
print(f"Success Rate:  {success_rate:.1f}%")

# Data quality metrics
print("\nData Quality:")
print(f"- Records with valid MTOW: {df_working['MTOW_tonnes'].notna().sum()}/{total_records} ({(df_working['MTOW_tonnes'].notna().sum()/total_records)*100:.1f}%)")
print(f"- Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{total_records}")
print(f"- Records with Rate Master matches: {df_working['Unit_Rate_mapped'].notna().sum()}/{total_records}")

# Matched charges statistics
matched_data = df_working[df_working['Status'] == 'Matched']
if len(matched_data) > 0:
    print("\nMatched Charges:")
    print(f"  Count: {len(matched_data)}")
    print(f"  Min: {matched_data['Vendor_Charge'].min():.2f}")
    print(f"  Max: {matched_data['Vendor_Charge'].max():.2f}")
    print(f"  Mean: {matched_data['Vendor_Charge'].mean():.2f}")
    print(f"  Total: {matched_data['Vendor_Charge'].sum():.2f}")

# Results by flight type
print("\nResults by Flight Type:")
for flight_type in df_working['FLIGHT_TYPE'].unique():
    if pd.notna(flight_type):
        type_data = df_working[df_working['FLIGHT_TYPE'] == flight_type]
        type_matched = (type_data['Status'] == 'Matched').sum()
        type_total = len(type_data)
        type_rate = (type_matched / type_total) * 100 if type_total > 0 else 0
        print(f"  {flight_type:30} {type_matched:>4}/{type_total:<4} ({type_rate:>5.1f}%)")

# Detailed verification results
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS (First 30 rows):")
print("="*100)
display_cols = ['AIRCRAFT_REG', 'MTOW_tonnes', 'FLIGHT_TYPE', 'Unit_Rate_mapped', 'Vendor_Charge', 'Difference', 'Status']
print(df_working[display_cols].head(30).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Unit_Rate_mapped'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[['AIRCRAFT_REG', 'MTOW_tonnes', 'FLIGHT_TYPE', 'Unit_Rate_mapped', 'Vendor_Charge', 'Difference']].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: {valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: {valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: {valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results
output_file = "1900373598_Verified.csv"

output_cols = ['AIRCRAFT_REG', 'FROM_IATA', 'TO_IATA', 'MTOW_tonnes', 'FLIGHT_TYPE', 
               'Unit_Rate_mapped', 'Vendor_Charge', 'Difference', 'Status']
df_output = df_working[output_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
