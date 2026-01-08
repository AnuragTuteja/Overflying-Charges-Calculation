import pandas as pd
import numpy as np

def verify_jed_charges():
    # 1. Load Data
    print("Loading files...")
    vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\Vendor Master.csv"

    df_vendor = pd.read_csv(vendor_file)

    # Clean column names
    df_vendor.columns = df_vendor.columns.str.replace('\n', ' ').str.strip()

    # 2. Prepare Data
    df_working = df_vendor.copy()

    # Convert required columns to numeric
    df_working['Weight Factor'] = pd.to_numeric(df_working['Weight Factor'], errors='coerce')
    df_working['Distance Factor'] = pd.to_numeric(df_working['Distance Factor'], errors='coerce')
    df_working['En-Route Charge'] = pd.to_numeric(df_working['En-Route Charge'], errors='coerce')

    # 3. Calculate Charge
    UNIT_RATE = 118.0

    def calculate_formula(row):
        if pd.isna(row['Weight Factor']) or pd.isna(row['Distance Factor']):
            return np.nan
        charge = row['Weight Factor'] * row['Distance Factor'] * UNIT_RATE
        return round(charge, 2)

    df_working['Calculated_Charge'] = df_working.apply(calculate_formula, axis=1)

    # 4. Compare with Vendor En-Route Charge
    df_working['Vendor_Charge'] = df_working['En-Route Charge']

    df_working['Status'] = np.where(
        abs(df_working['Calculated_Charge'] - df_working['Vendor_Charge']) <= 0.5,
        'Matched',
        'Not Matched'
    )

    # 5. Save Output
    output_cols = [
        'Invoice No', 'Flight Number', 'Aircraft ID', 'Origin Code', 'Dest. Code',
        'Weight Factor', 'Distance Factor',
        'Calculated_Charge', 'Vendor_Charge', 'Status'
    ]

    output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\Vendor_Data_Verified.csv"
    df_working[output_cols].to_csv(output_file, index=False)

    print(f"Verification Complete. Results saved to {output_file}")
    print(df_working[output_cols].head())

if __name__ == "__main__":
    verify_jed_charges()
