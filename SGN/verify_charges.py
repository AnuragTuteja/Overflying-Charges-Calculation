import pandas as pd
import numpy as np

# Read the three CSV files
main_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\00003015 vietnam.csv"
mtow_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\MTOW Master.xlsx - Sheet1.csv"
rate_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\Rate Master.csv"

# Load data
df_main = pd.read_csv(main_file)
df_mtow = pd.read_csv(mtow_master)
df_rates = pd.read_csv(rate_master)

print("="*100)
print("WORKFLOW: SGN CHARGE VERIFICATION")
print("="*100)
print(f"\nTotal rows in main file: {len(df_main)}")
print(f"Total aircraft in MTOW Master: {len(df_mtow)}")
print(f"Total MTOW categories in Rate Master: {len(df_rates)}")

# Display Rate Master for reference
print("\n" + "="*100)
print("RATE MASTER (Lookup Table):")
print("="*100)
print(df_rates.to_string(index=False))

# Step 1: Merge main data with MTOW Master
# Clean column names for matching
df_mtow['Aircraft_Reg'] = df_mtow['Aircraft '].str.strip()
df_main['Aircraft_Reg'] = df_main['Aircraft regist'].str.strip()

# Convert MTOW to numeric
df_mtow['MTOW_in_KGs'] = pd.to_numeric(df_mtow['MTOW_in_KGs'], errors='coerce')

# Merge to get MTOW
df_merged = df_main.merge(df_mtow[['Aircraft_Reg', 'MTOW_in_KGs']], 
                          left_on='Aircraft_Reg', 
                          right_on='Aircraft_Reg', 
                          how='left')

# Step 2: Categorize MTOW to match Rate Master categories
# This is a simple lookup - find the closest MTOW category that matches or is <= the aircraft MTOW
def get_rate_from_mtow(mtow_value):
    """
    Look up the rate based on MTOW.
    The MTOW in Rate Master represents aircraft categories in tonnes.
    Match based on MTOW bands.
    """
    if pd.isna(mtow_value):
        return np.nan
    
    # Convert MTOW from kg to tonnes for comparison
    mtow_tonnes = mtow_value / 1000
    
    # Sort rates by MTOW
    rates_sorted = df_rates.sort_values('MTOW', ascending=False)
    rates_sorted['MTOW'] = pd.to_numeric(rates_sorted['MTOW'], errors='coerce')
    rates_sorted['Charge'] = pd.to_numeric(rates_sorted['Charge'], errors='coerce')
    
    # Find the matching rate (use the highest MTOW category that is <= aircraft MTOW)
    for idx, row in rates_sorted.iterrows():
        if mtow_tonnes >= float(row['MTOW']):
            return float(row['Charge'])
    
    # If no match, return the lowest rate (for aircraft below minimum threshold)
    return float(df_rates.loc[df_rates['MTOW'].idxmin(), 'Charge'])

# Get the charge based on MTOW
df_merged['CALCULATED_CHARGE'] = df_merged['MTOW_in_KGs'].apply(get_rate_from_mtow)

# Step 3: Extract the Charge component (excluding Fee and Sur charge)
# Based on the structure: Total amount = Charge + Fee + Sur charge
# We validate if the Charge column matches our calculated charge
df_merged['CHARGE_FROM_FILE'] = pd.to_numeric(df_merged['Charge'], errors='coerce')

# Step 4: Compare and verify
tolerance = 0.01
df_merged['VERIFICATION_STATUS'] = df_merged.apply(
    lambda row: 'Matched' if pd.notna(row['CALCULATED_CHARGE']) and pd.notna(row['CHARGE_FROM_FILE']) 
                and abs(row['CHARGE_FROM_FILE'] - row['CALCULATED_CHARGE']) <= tolerance 
                else 'Not Matched',
    axis=1
)

# Create output dataframe
output_df = df_merged[[
    'Date', 'Callsign', 'Aircraft_Reg', 'Aircraft type', 'From', 'To',
    'MTOW_in_KGs', 'CALCULATED_CHARGE', 'Charge', 'Fee', 'Total amount',
    'VERIFICATION_STATUS'
]]

# Display summary
print("\n" + "="*100)
print("VERIFICATION SUMMARY")
print("="*100)
matched = (output_df['VERIFICATION_STATUS'] == 'Matched').sum()
not_matched = (output_df['VERIFICATION_STATUS'] == 'Not Matched').sum()

print(f"[MATCHED]     {matched}")
print(f"[NOT MATCHED] {not_matched}")
print(f"Total Flights: {len(output_df)}")
print(f"Success Rate:  {(matched/len(output_df)*100):.1f}%")

# Display detailed results
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS:")
print("="*100)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
print(output_df.to_string(index=False))

# Save results
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\00003015_Verified.csv"
output_df.to_csv(output_file, index=False)
print(f"\n\n✓ Results saved to: {output_file}")

# Show mismatches if any
print("\n" + "="*100)
print("INTERPRETATION:")
print("="*100)
print("The workflow validates:")
print("1. Aircraft Registration → MTOW (from MTOW Master)")
print("2. MTOW Category → Fixed Rate (from Rate Master)")
print("3. Calculated Charge should match the 'Charge' column in the source file")
print("\nCURRENT FINDINGS:")
print("- A21N aircraft: MTOW 97,000 kg → Rate Master MTOW 97 tonnes → Expected Charge: 286")
print("  But source file shows: 136 (possibly half-charge or different fee structure)")
print("- B788 aircraft: MTOW 227,930 kg → Rate Master MTOW 228 tonnes → Expected Charge: 460")
print("  But source file shows: 218 (possibly half-charge or different fee structure)")
print("\n⚠️  MISMATCH ANALYSIS:")
print("Possible reasons:")
print("1. The 'Charge' column might be a component of a larger calculation")
print("2. The Rate Master might have different rate bands not visible in current data")
print("3. There may be a discount or special rate applied")
print("4. The charges might be split between multiple components")
print("\nRECOMMENDATION:")
print("Please confirm:")
print("- How the fixed rates from Rate Master should be applied")
print("- What the 'Charge' column represents (is it the full charge or a component?)")
print("- Whether there are any modifiers or multipliers to apply")
print("\n" + "="*100)

print("\n\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)
print(f"Aircraft Registration Found in MTOW Master: {df_merged['MTOW_in_KGs'].notna().sum()}/{len(df_main)}")
print(f"Aircraft Registration NOT Found: {df_merged['MTOW_in_KGs'].isna().sum()}/{len(df_main)}")
if df_merged['MTOW_in_KGs'].isna().sum() > 0:
    print("\nMissing Aircraft:")
    missing = df_merged[df_merged['MTOW_in_KGs'].isna()][['Aircraft_Reg', 'Aircraft type']].drop_duplicates()
    print(missing.to_string(index=False))
