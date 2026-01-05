import pandas as pd
import numpy as np

# Read the CSV file
csv_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\IKA\1900357153.csv"
df = pd.read_csv(csv_file)

print(f"Total rows in file: {len(df)}")
print("\n" + "="*100)

# Define constants
UNIT_RATE = 0.00286
ADDITIONAL_CHARGE = 0.18
MTOW_THRESHOLD = 150
NM_TO_KM = 1.852

# Create a working copy
result_df = df.copy()

# Step 1: Convert Distance from Nautical Miles to KMs
result_df['DISTANCE_KM'] = result_df['Distance(NM)'] * NM_TO_KM

# Step 2: Calculate Final Unit Rate based on MTOW
# If MTOW > 150: Final_unit_rate = (MTOW * 0.00286) + 0.18
# Otherwise: Final_unit_rate = MTOW * 0.00286
result_df['FINAL_UNIT_RATE'] = result_df['MTOW'].apply(
    lambda mtow: (mtow * UNIT_RATE) + ADDITIONAL_CHARGE if mtow > MTOW_THRESHOLD else mtow * UNIT_RATE
)

# Step 3: Calculate Charges
result_df['CALCULATED_CHARGE'] = result_df['FINAL_UNIT_RATE'] * result_df['DISTANCE_KM']

# Round to 2 decimal places for comparison
result_df['CALCULATED_CHARGE'] = result_df['CALCULATED_CHARGE'].round(2)

# Step 4: Compare with existing Charge column
tolerance = 0.01
result_df['VERIFICATION_STATUS'] = result_df.apply(
    lambda row: 'Matched' if abs(row['Charge'] - row['CALCULATED_CHARGE']) <= tolerance else 'Not Matched',
    axis=1
)

# Create output dataframe with relevant columns
output_df = result_df[['No.', 'Type', 'MTOW', 'Flight No.', 'REG', 'Distance(NM)', 'DISTANCE_KM', 
                       'FINAL_UNIT_RATE', 'Charge', 'CALCULATED_CHARGE', 'VERIFICATION_STATUS']]

# Display summary statistics
print("\nVERIFICATION SUMMARY")
print("="*100)
matched = (output_df['VERIFICATION_STATUS'] == 'Matched').sum()
not_matched = (output_df['VERIFICATION_STATUS'] == 'Not Matched').sum()

print(f"Matched:     {matched}")
print(f"Not Matched: {not_matched}")
print(f"Total:       {len(output_df)}")
print("\n" + "="*100)

# Display detailed results
print("\nDETAILED VERIFICATION RESULTS:")
print("="*100)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(output_df.to_string(index=False))

# Save the results to a new CSV file
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\IKA\1900357153_Verified.csv"
output_df.to_csv(output_file, index=False)
print(f"\n\nResults saved to: {output_file}")

# Display mismatches if any
print("\n" + "="*100)
if not_matched > 0:
    print(f"\n⚠️  FOUND {not_matched} MISMATCHES:")
    print("="*100)
    mismatches = output_df[output_df['VERIFICATION_STATUS'] == 'Not Matched']
    print(mismatches.to_string(index=False))
else:
    print("\n✓ All charges matched successfully!")
