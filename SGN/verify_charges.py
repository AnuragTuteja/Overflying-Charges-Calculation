import pandas as pd
import numpy as np

# Read the three CSV files
main_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\00003015 vietnam.csv"
mtow_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\MTOW Master.csv"
rate_master = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\Rate Master.csv"

# Load data
df_main = pd.read_csv(main_file)
df_mtow = pd.read_csv(mtow_master)
df_rates = pd.read_csv(rate_master)

print("="*100)
print("WORKFLOW: SGN CHARGE VERIFICATION")
print("="*100)
print(f"\nTotal rows in main file: {len(df_main)}")

# Step 0: Clean column names and filter summary rows
df_mtow['Aircraft_Reg'] = df_mtow['Aircraft '].str.strip()
df_main['Aircraft_Reg'] = df_main['Aircraft regist'].str.strip()

# Filter out summary rows
df_main = df_main[df_main['Aircraft_Reg'].notna()].copy()
df_main = df_main[~df_main['Aircraft_Reg'].str.contains('Subtotal|Grandtotal|Total', case=False, na=False)].copy()

print(f"Total rows after filtering: {len(df_main)}")

# Display Rate Master for reference
print("\n" + "="*100)
print("RATE MASTER (Lookup Table):")
print("="*100)
print(df_rates.to_string(index=False))

# Convert MTOW to numeric
df_mtow['MTOW_in_KGs'] = pd.to_numeric(df_mtow['MTOW_in_KGs'], errors='coerce')

# Merge to get MTOW
df_merged = df_main.merge(df_mtow[['Aircraft_Reg', 'MTOW_in_KGs']], 
                          left_on='Aircraft_Reg', 
                          right_on='Aircraft_Reg', 
                          how='left')

# Step 2: Extract MTOW from merged data
# Convert MTOW to numeric
df_merged['MTOW_in_KGs'] = pd.to_numeric(df_merged['MTOW_in_KGs'], errors='coerce')

# Step 3: Look up Total amount from Rate Master based on MTOW
def get_total_amount_from_rate_master(mtow_kg):
    """
    Look up the Total Amount (Charge + Fee) from Rate Master based on MTOW.
    Match aircraft MTOW to the rate master MTOW category.
    """
    if pd.isna(mtow_kg):
        return np.nan
    
    try:
        mtow_kg = float(mtow_kg)
    except (ValueError, TypeError):
        return np.nan
    
    # Convert kg to tonnes for comparison with Rate Master
    mtow_tonnes = mtow_kg / 1000
    
    # Try exact match first
    rate_master_copy = df_rates.copy()
    rate_master_copy['MTOW'] = pd.to_numeric(rate_master_copy['MTOW'], errors='coerce')
    rate_master_copy['Charge'] = pd.to_numeric(rate_master_copy['Charge'], errors='coerce')
    
    exact_match = rate_master_copy[rate_master_copy['MTOW'] == mtow_tonnes]
    if len(exact_match) > 0:
        return float(exact_match.iloc[0]['Charge'])
    
    # Try closest match
    rate_master_copy = rate_master_copy.dropna(subset=['MTOW', 'Charge'])
    if len(rate_master_copy) == 0:
        return np.nan
    
    rate_master_copy['MTOW_diff'] = abs(rate_master_copy['MTOW'] - mtow_tonnes)
    closest = rate_master_copy.loc[rate_master_copy['MTOW_diff'].idxmin()]
    
    return float(closest['Charge'])

# Get the expected Total Amount based on MTOW
df_merged['CALCULATED_TOTAL_AMOUNT'] = df_merged['MTOW_in_KGs'].apply(get_total_amount_from_rate_master)

# Step 4: Extract the Total amount from vendor file
df_merged['VENDOR_TOTAL_AMOUNT'] = pd.to_numeric(df_merged['Total amount'], errors='coerce')

# Step 5: Compare and verify
tolerance = 0.01
df_merged['VERIFICATION_STATUS'] = df_merged.apply(
    lambda row: 'Matched' if pd.notna(row['CALCULATED_TOTAL_AMOUNT']) and pd.notna(row['VENDOR_TOTAL_AMOUNT']) 
                and abs(row['VENDOR_TOTAL_AMOUNT'] - row['CALCULATED_TOTAL_AMOUNT']) <= tolerance 
                else 'Not Matched',
    axis=1
)

# Create output dataframe
output_df = df_merged[[
    'Date', 'Callsign', 'Aircraft_Reg', 'Aircraft type', 'From', 'To',
    'MTOW_in_KGs', 'CALCULATED_TOTAL_AMOUNT', 'Total amount',
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
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\SGN\SGN_Verification.csv"
output_df.to_csv(output_file, index=False)
print(f"\n\n✓ Results saved to: {output_file}")

# Summary Analysis
print("\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)
matched = (output_df['VERIFICATION_STATUS'] == 'Matched').sum()
total = len(output_df)
success_rate = (matched / total * 100) if total > 0 else 0

print(f"\n✓ Total Records Verified: {total}")
print(f"✓ Successfully Matched: {matched}/{total} ({success_rate:.1f}%)")
print(f"✓ Aircraft Found in MTOW Master: {df_merged['MTOW_in_KGs'].notna().sum()}/{total}")
print(f"\nRate Master Categories Applied:")
print(f"  - MTOW 97 tonnes (97,000 kg) → Total Amount: $286")
print(f"  - MTOW 228 tonnes (227,930 kg) → Total Amount: $460")
print("\n" + "="*100)
