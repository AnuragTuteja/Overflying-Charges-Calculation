import pandas as pd
import numpy as np
import os

# Read the CSV file
csv_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\YYZ\CS434278DE.csv"
df = pd.read_csv(csv_file)

# Filter for Overflight rows only
overflight_df = df[df['SERVDESC'].str.contains('Overflight', case=False, na=False)].copy()

print(f"Total rows in file: {len(df)}")
print(f"Overflight rows found: {len(overflight_df)}")
print("\n" + "="*80)

# Define constants
UNIT_RATE = 0.03524

# Calculate expected charges using formula: BILLDIST × Weight Factor × 0.03524
# The formula uses billing distance (distance flown) × weight factor × unit rate
overflight_df['CALCULATED_CHARGE'] = overflight_df['BILLDIST'] * overflight_df['WEIGHT FACTOR'] * UNIT_RATE

# Round to 2 decimal places for comparison
overflight_df['CALCULATED_CHARGE'] = overflight_df['CALCULATED_CHARGE'].round(2)

# Allow for small rounding differences (tolerance of 0.01)
tolerance = 0.01
overflight_df['VERIFICATION_STATUS'] = overflight_df.apply(
    lambda row: 'Matched' if abs(row['TOTAL'] - row['CALCULATED_CHARGE']) <= tolerance else 'Not Matched',
    axis=1
)

# Create a verification report
result_df = overflight_df[['UTC_DATE', 'FLIGHT_ID', 'AC_IDENT', 'MTOW', 'WEIGHT FACTOR', 
                            'BILLDIST', 'AMOUNT', 'TOTAL', 'CALCULATED_CHARGE', 'VERIFICATION_STATUS']]

# Display summary statistics
print("\nVERIFICATION SUMMARY")
print("="*80)
matched = (result_df['VERIFICATION_STATUS'] == 'Matched').sum()
not_matched = (result_df['VERIFICATION_STATUS'] == 'Not Matched').sum()

print(f"Matched:     {matched}")
print(f"Not Matched: {not_matched}")
print(f"Total:       {len(result_df)}")
print("\n" + "="*80)

# Display detailed results
print("\nDETAILED VERIFICATION RESULTS:")
print("="*80)
print(result_df.to_string(index=False))

# Save the results to a new CSV file
output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\YYZ\Overflight_Verification_Results.csv"
result_df.to_csv(output_file, index=False)
print(f"\n\nResults saved to: {output_file}")

# Display mismatches if any
print("\n" + "="*80)
if not_matched > 0:
    print(f"\n FOUND {not_matched} MISMATCHES:")
    print("="*80)
    mismatches = result_df[result_df['VERIFICATION_STATUS'] == 'Not Matched']
    print(mismatches.to_string(index=False))
else:
    print("\n All charges matched successfully!")
