import pandas as pd
import numpy as np
import re

# Read the main data file
main_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\MCT\MDETLST-0320860591.csv"
mtow_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\MCT\MTOW Master.xlsx - Sheet1.csv"
rate_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\MCT\Rate Master.csv"

# Load data
df_main = pd.read_csv(main_file)
df_mtow = pd.read_csv(mtow_master_file)
df_rates = pd.read_csv(rate_master_file)

print("="*120)
print("MCT AIRPORT CHARGE VERIFICATION WORKFLOW")
print("="*120)
print(f"\nMain Data Records: {len(df_main)}")
print(f"MTOW Master Records: {len(df_mtow)}")
print(f"Rate Master Records: {len(df_rates)}")

# Display column names to understand structure
print("\n" + "-"*120)
print("Main Data Columns:")
print("-"*120)
print(df_main.columns.tolist())

# Display Rate Master
print("\n" + "="*120)
print("RATE MASTER (Pricing Structure):")
print("="*120)
print(df_rates.to_string(index=False))

# Create working copy
df_working = df_main.copy()

# Step 1: Extract and clean MTOW (already in numeric format with @ UOM)
print("\n" + "="*120)
print("STEP 1: Extracting MTOW")
print("="*120)

def extract_numeric_value(val):
    """Extract numeric value from string like '280.0000  @ TON' or multiline formats"""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip()
    # Remove newlines and extra spaces
    val_str = val_str.replace('\n', ' ').replace('\r', ' ')
    # Extract first complete number (decimal or integer)
    match = re.search(r'(\d+\.?\d*)', val_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return np.nan
    return np.nan

# Extract MTOW
df_working['MTOW_numeric'] = df_working['Max. Take Off Weight @UOM'].apply(extract_numeric_value)

# Convert MTOW from TON to KG for matching with Rate Master
df_working['MTOW_kg'] = df_working['MTOW_numeric'] * 1000

print(f"MTOW extracted successfully for {df_working['MTOW_numeric'].notna().sum()}/{len(df_working)} records")

# Step 2: Extract Distance
print("\n" + "="*120)
print("STEP 2: Extracting Distance")
print("="*120)

# Distance column appears to be "Distance @ UOM" with format like "774.000  @  KM"
distance_col = [col for col in df_main.columns if 'Distance' in col][0]
print(f"Found distance column: '{distance_col}'")

df_working['Distance_numeric'] = df_working[distance_col].apply(extract_numeric_value)
print(f"Distance extracted successfully for {df_working['Distance_numeric'].notna().sum()}/{len(df_working)} records")

# Step 3: Calculate Distance Factor
print("\n" + "="*120)
print("STEP 3: Calculating Distance Factor (Distance / 100)")
print("="*120)

df_working['Distance_Factor'] = df_working['Distance_numeric'] / 100
print(f"Distance Factor calculated for {df_working['Distance_Factor'].notna().sum()}/{len(df_working)} records")

# Step 4: Map Rate Master to get Unit Rate and Weight Factor
print("\n" + "="*120)
print("STEP 4: Mapping Unit Rate and Weight Factor from Rate Master")
print("="*120)

# Clean rate master data
df_rates['Mtow'] = pd.to_numeric(df_rates['Mtow'], errors='coerce')
df_rates['Unit Rate'] = pd.to_numeric(df_rates['Unit Rate'], errors='coerce')
df_rates['Weight Factor'] = pd.to_numeric(df_rates['Weight Factor'], errors='coerce')

def find_rate_master_match(mtow_kg):
    """Find matching rate master entry based on MTOW"""
    if pd.isna(mtow_kg):
        return np.nan, np.nan
    
    # Find exact match in Rate Master
    matches = df_rates[df_rates['Mtow'] == mtow_kg]
    
    if len(matches) > 0:
        return float(matches.iloc[0]['Unit Rate']), float(matches.iloc[0]['Weight Factor'])
    else:
        # If no exact match, find closest
        df_rates['MTOW_diff'] = abs(df_rates['Mtow'] - mtow_kg)
        closest = df_rates.loc[df_rates['MTOW_diff'].idxmin()]
        return float(closest['Unit Rate']), float(closest['Weight Factor'])

# Map rate and weight factors
df_working[['Unit_Rate_mapped', 'Weight_Factor_mapped']] = df_working['MTOW_kg'].apply(
    lambda x: pd.Series(find_rate_master_match(x))
)

matched_rates = df_working['Unit_Rate_mapped'].notna().sum()
print(f"Rate Master matches found for {matched_rates}/{len(df_working)} records")

# Step 5: Calculate Charges
print("\n" + "="*120)
print("STEP 5: Calculating Charges (Unit rate × Distance factor × Weight factor)")
print("="*120)

df_working['Calculated_Charge'] = (
    df_working['Unit_Rate_mapped'] * 
    df_working['Distance_Factor'] * 
    df_working['Weight_Factor_mapped']
)

# Round to 2 decimal places
df_working['Calculated_Charge'] = df_working['Calculated_Charge'].round(2)

print(f"Charges calculated for {df_working['Calculated_Charge'].notna().sum()}/{len(df_working)} records")

# Step 6: Extract and compare with existing Charge Amount
print("\n" + "="*120)
print("STEP 6: Comparing with Existing Charges")
print("="*120)

df_working['Existing_Charge'] = pd.to_numeric(df_working['Charge Amount'], errors='coerce')

# Verify
tolerance = 0.01
df_working['Verification_Status'] = df_working.apply(
    lambda row: 'Matched' if pd.notna(row['Calculated_Charge']) and pd.notna(row['Existing_Charge'])
                and abs(row['Calculated_Charge'] - row['Existing_Charge']) <= tolerance
                else 'Not Matched',
    axis=1
)

# Create output dataframe
output_df = df_working[[
    'Flight Date Time',
    'Flt. #',
    'Acft. Reg.',
    'Acft. Type Code',
    'MTOW_numeric',
    'MTOW_kg',
    'Distance_numeric',
    'Distance_Factor',
    'Unit_Rate_mapped',
    'Weight_Factor_mapped',
    'Calculated_Charge',
    'Existing_Charge',
    'Verification_Status'
]]

# Rename columns for clarity
output_df.columns = [
    'Flight_DateTime',
    'Flight_No',
    'Aircraft_Reg',
    'Aircraft_Type',
    'MTOW_Tonnes',
    'MTOW_kg',
    'Distance_km',
    'Distance_Factor',
    'Unit_Rate',
    'Weight_Factor',
    'Calculated_Charge',
    'Vendor_Charge',
    'Status'
]

# Display summary
print("\nVERIFICATION SUMMARY")
print("="*120)
matched = (output_df['Status'] == 'Matched').sum()
not_matched = (output_df['Status'] == 'Not Matched').sum()

print(f"[MATCHED]     {matched}")
print(f"[NOT MATCHED] {not_matched}")
print(f"Total Records: {len(output_df)}")
print(f"Success Rate:  {(matched/len(output_df)*100):.1f}%")

# Display sample results
print("\n" + "="*120)
print("DETAILED VERIFICATION RESULTS (First 30 rows):")
print("="*120)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
print(output_df.head(30).to_string(index=False))

# Save results
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\MCT\MDETLST_Verified.csv"
output_df.to_csv(output_file, index=False)
print(f"\n\nResults saved to: {output_file}")

# Show summary statistics
print("\n" + "="*120)
print("SUMMARY STATISTICS")
print("="*120)

# Data quality
valid_mtow = df_working['MTOW_numeric'].notna().sum()
valid_distance = df_working['Distance_numeric'].notna().sum()
valid_rates = df_working['Unit_Rate_mapped'].notna().sum()
valid_charges = df_working['Existing_Charge'].notna().sum()

print(f"Records with valid MTOW:             {valid_mtow}/{len(df_working)}")
print(f"Records with valid Distance:         {valid_distance}/{len(df_working)}")
print(f"Records with Rate Master matches:    {valid_rates}/{len(df_working)}")
print(f"Records with existing charges:       {valid_charges}/{len(df_working)}")

# Charge analysis
if matched > 0:
    matched_df = output_df[output_df['Status'] == 'Matched']
    print(f"\nMatched Charges:")
    print(f"  Count: {len(matched_df)}")
    print(f"  Min: {matched_df['Calculated_Charge'].min():.2f}")
    print(f"  Max: {matched_df['Calculated_Charge'].max():.2f}")
    print(f"  Mean: {matched_df['Calculated_Charge'].mean():.2f}")
    print(f"  Total: {matched_df['Calculated_Charge'].sum():.2f}")

if not_matched > 0:
    print(f"\n[FOUND {not_matched} MISMATCHES]")
    mismatches = output_df[output_df['Status'] == 'Not Matched']
    
    # Filter out NaN rows
    mismatches_valid = mismatches[mismatches['Flight_No'].notna() & mismatches['Aircraft_Reg'].notna()]
    
    if len(mismatches_valid) > 0:
        print(f"\nValid Mismatch Analysis (first 15):")
        print(mismatches_valid.head(15)[['Flight_No', 'Aircraft_Reg', 'MTOW_Tonnes', 'Distance_km', 
                                    'Unit_Rate', 'Weight_Factor', 'Calculated_Charge', 'Vendor_Charge']].to_string(index=False))
        
        # Calculate difference
        mismatches_valid_copy = mismatches_valid.copy()
        mismatches_valid_copy['Difference'] = abs(mismatches_valid_copy['Calculated_Charge'] - mismatches_valid_copy['Vendor_Charge'])
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(mismatches_valid_copy)}")
        print(f"  Min difference: {mismatches_valid_copy['Difference'].min():.2f}")
        print(f"  Max difference: {mismatches_valid_copy['Difference'].max():.2f}")
        print(f"  Mean difference: {mismatches_valid_copy['Difference'].mean():.2f}")
        print(f"  Total vendor difference: {mismatches_valid_copy['Difference'].sum():.2f}")
    
    # Count header/footer rows
    invalid_rows = len(mismatches) - len(mismatches_valid)
    print(f"\nInvalid/Header/Footer rows: {invalid_rows}")
