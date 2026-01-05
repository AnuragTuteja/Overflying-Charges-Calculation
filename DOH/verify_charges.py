import pandas as pd
import numpy as np

# Read all files
vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Vendor Data.csv"
iata_mapping_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\IATA ICAO Mapping.xlsx - Sheet1.csv"
mtow_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\MTOW Master.xlsx - Sheet1.csv"
rate_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Rate Master.csv"

# Load data
df_vendor = pd.read_csv(vendor_file)
df_iata = pd.read_csv(iata_mapping_file)
df_mtow = pd.read_csv(mtow_master_file)
df_rates = pd.read_csv(rate_master_file)

print("="*120)
print("DOH AIRPORT CHARGE VERIFICATION WORKFLOW")
print("="*120)
print(f"\nVendor Data Records: {len(df_vendor)}")
print(f"IATA-ICAO Mapping Records: {len(df_iata)}")
print(f"MTOW Master Records: {len(df_mtow)}")
print(f"Rate Master Records: {len(df_rates)}")

# Display Rate Master for reference
print("\n" + "="*120)
print("RATE MASTER (Pricing Structure):")
print("="*120)
print(df_rates.to_string(index=False))

# Step 1: Create working copy
df_working = df_vendor.copy()

# Step 2: Create IATA lookup dictionary (IATA -> Airport Name)
iata_lookup = dict(zip(df_iata['IATA'], df_iata['Airport']))

# Step 3: Map departure and arrival IATA codes to airport names
df_working['DEP_AIRPORT'] = df_working['IATA'].map(iata_lookup)
df_working['ARR_AIRPORT'] = df_working['IATA.1'].map(iata_lookup)

# Also add ICAO codes for reference
icao_lookup = dict(zip(df_iata['IATA'], df_iata['ICAO']))
df_working['DEP_ICAO'] = df_working['IATA'].map(icao_lookup)
df_working['ARR_ICAO'] = df_working['IATA.1'].map(icao_lookup)

# Step 4: Identify if flight landed in DOH
# Check if Arrival IATA matches "DOH" (indicating the flight landed at Doha)
df_working['LANDED_IN_DOH'] = df_working['IATA.1'].str.upper() == 'DOH'
df_working['FLIGHT_TYPE'] = df_working['LANDED_IN_DOH'].apply(
    lambda x: 'With landing' if x else 'Without landing (Overflight)'
)

# Step 5: Get MTOW from Master using Registration
df_mtow['Registration_Clean'] = df_mtow['Aircraft '].str.strip()
df_working['Registration_Clean'] = df_working['Registration'].str.strip()

df_working = df_working.merge(
    df_mtow[['Registration_Clean', 'MTOW_in_KGs', 'Aircraft_Type']], 
    left_on='Registration_Clean', 
    right_on='Registration_Clean',
    how='left'
)

# Convert MTOW to numeric
df_working['MTOW_in_KGs'] = pd.to_numeric(df_working['MTOW_in_KGs'], errors='coerce')

# For missing MTOW, use a standard mapping for aircraft types
aircraft_type_mtow = {
    'A20N': 77.0,  # Airbus A220
    'A21N': 97.0,  # Airbus A220-100 variant
    'B77W': 351.534,  # Boeing 777-300ER
    'B788': 227.93,  # Boeing 787-8
    'B789': 254.011,  # Boeing 787-9
    'A359': 280.0,  # Airbus A350-900
}

# Fill missing MTOW values using AC Type
df_working['MTOW_in_KGs'] = df_working.apply(
    lambda row: aircraft_type_mtow.get(row['AC Type'], row['MTOW_in_KGs']) 
    if pd.isna(row['MTOW_in_KGs']) else row['MTOW_in_KGs'],
    axis=1
)

df_working['MTOW_in_Tonnes'] = df_working['MTOW_in_KGs'] / 1000

# Step 6: Create lookup function for Rate Master
def get_charge_from_rate_master(mtow_tonnes, flight_type):
    """
    Look up charge based on MTOW and Landing/Overflight status.
    """
    if pd.isna(mtow_tonnes):
        return np.nan
    
    # Clean and convert rate master data
    df_rates_clean = df_rates.copy()
    df_rates_clean['MTOW'] = pd.to_numeric(df_rates_clean['MTOW'], errors='coerce')
    df_rates_clean['Charge'] = pd.to_numeric(df_rates_clean['Charge'], errors='coerce')
    df_rates_clean['Landing/takeoff'] = df_rates_clean['Landing/takeoff'].str.strip()
    
    # Filter by flight type (handle both "With landing" and "Without landing rate")
    if 'With landing' in flight_type.lower() or 'landing' in flight_type.lower():
        search_type = 'With landing'
    else:
        search_type = 'Without landing rate'
    
    matching_rates = df_rates_clean[
        df_rates_clean['Landing/takeoff'].str.lower() == search_type.lower()
    ]
    
    # Find best match (closest MTOW)
    if len(matching_rates) == 0:
        return np.nan
    
    # Calculate difference and find closest
    matching_rates_copy = matching_rates.copy()
    matching_rates_copy['MTOW_diff'] = abs(matching_rates_copy['MTOW'] - mtow_tonnes)
    best_match = matching_rates_copy.loc[matching_rates_copy['MTOW_diff'].idxmin()]
    
    return float(best_match['Charge'])

# Step 7: Calculate expected charge
df_working['CALCULATED_CHARGE'] = df_working.apply(
    lambda row: get_charge_from_rate_master(row['MTOW_in_Tonnes'], row['FLIGHT_TYPE']),
    axis=1
)

# Step 8: Compare with vendor charges
df_working['TOTAL_BILL_NUM'] = pd.to_numeric(df_working['Total Bill'], errors='coerce')
tolerance = 0.01

df_working['VERIFICATION_STATUS'] = df_working.apply(
    lambda row: 'Matched' if pd.notna(row['CALCULATED_CHARGE']) and pd.notna(row['TOTAL_BILL_NUM'])
                and abs(row['TOTAL_BILL_NUM'] - row['CALCULATED_CHARGE']) <= tolerance
                else 'Not Matched',
    axis=1
)

# Step 9: Create output dataframe
output_df = df_working[[
    'Invoice number', 'Callsign', 'Departure', 'IATA', 'Arrival', 'IATA.1',
    'DEP_AIRPORT', 'ARR_AIRPORT', 'FLIGHT_TYPE', 'LANDED_IN_DOH',
    'Registration', 'AC Type', 'MTOW_in_Tonnes', 'Aircraft_Type',
    'CALCULATED_CHARGE', 'Total Bill', 'VERIFICATION_STATUS'
]]

# Rename columns for clarity
output_df.columns = [
    'Invoice', 'Callsign', 'Dep_ICAO', 'Dep_IATA', 'Arr_ICAO', 'Arr_IATA',
    'Dep_Airport', 'Arr_Airport', 'Flight_Type', 'Landed_In_DOH',
    'Aircraft_Reg', 'AC_Type', 'MTOW_Tonnes', 'Aircraft_Type',
    'Calculated_Charge', 'Vendor_Charge', 'Status'
]

# Display Summary
print("\n" + "="*120)
print("VERIFICATION SUMMARY")
print("="*120)
matched = (output_df['Status'] == 'Matched').sum()
not_matched = (output_df['Status'] == 'Not Matched').sum()

print(f"[MATCHED]     {matched}")
print(f"[NOT MATCHED] {not_matched}")
print(f"Total Records: {len(output_df)}")
print(f"Success Rate:  {(matched/len(output_df)*100):.1f}%")

# Breakdown by Flight Type
print("\n" + "-"*120)
print("Breakdown by Flight Type:")
print("-"*120)
flight_type_summary = output_df.groupby('Flight_Type').agg({
    'Status': ['count', lambda x: (x == 'Matched').sum()],
    'Calculated_Charge': 'sum',
    'Vendor_Charge': 'sum'
})
print(flight_type_summary)

# Display detailed results (first 50 rows)
print("\n" + "="*120)
print("DETAILED VERIFICATION RESULTS (First 50 rows):")
print("="*120)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
print(output_df.head(50).to_string(index=False))

# Save results
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Vendor_Data_Verified.csv"
output_df.to_csv(output_file, index=False)
print(f"\n\nResults saved to: {output_file}")

# Show mismatches
print("\n" + "="*120)
if not_matched > 0:
    print(f"FOUND {not_matched} MISMATCHES")
    print("="*120)
    mismatches = output_df[output_df['Status'] == 'Not Matched']
    print(f"\nSample of mismatches (first 20):")
    print(mismatches.head(20).to_string(index=False))
    
    # Detailed mismatch analysis
    print("\n" + "-"*120)
    print("Mismatch Analysis by Flight Type:")
    print("-"*120)
    for flight_type in output_df['Flight_Type'].unique():
        subset = mismatches[mismatches['Flight_Type'] == flight_type]
        if len(subset) > 0:
            print(f"\n{flight_type}:")
            print(f"  Count: {len(subset)}")
            print(f"  Sample:")
            print(subset.head(5)[['Callsign', 'Aircraft_Reg', 'MTOW_Tonnes', 'Calculated_Charge', 'Vendor_Charge']].to_string(index=False))
else:
    print("\nAll charges verified successfully!")

# Aircraft registration mapping issues
print("\n" + "="*120)
print("DATA QUALITY CHECK")
print("="*120)
unmatched_mtow = df_working['MTOW_in_KGs'].isna().sum()
print(f"Aircraft registrations found in MTOW Master: {len(df_working) - unmatched_mtow}/{len(df_working)}")
print(f"Aircraft registrations NOT found: {unmatched_mtow}/{len(df_working)}")

if unmatched_mtow > 0:
    print("\nMissing Aircraft Registrations:")
    missing_reg = df_working[df_working['MTOW_in_KGs'].isna()][['Registration', 'AC Type']].drop_duplicates()
    print(missing_reg.to_string(index=False))

# Landing vs Overflight summary
print("\n" + "-"*120)
print("Flight Categories:")
print("-"*120)
landing_summary = output_df.groupby('Flight_Type').size()
print(landing_summary)
