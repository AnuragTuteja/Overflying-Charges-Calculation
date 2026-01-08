import pandas as pd
import numpy as np

def verify_charges():
    # 1. Load Data
    vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\ASB\Vendor Master.csv"
    rate_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\ASB\Rate Master.csv"

    df_vendor = pd.read_csv(vendor_file)
    df_rates = pd.read_csv(rate_master_file)

    # 2. Clean Column Names
    df_vendor.columns = df_vendor.columns.str.strip().str.replace('\n', '')
    df_rates.columns = df_rates.columns.str.strip().str.replace('\n', '')

    # 3. Prepare Rate Master
    # Select relevant columns and convert to numeric
    rate_cols = ['MTOW', 'Unit Rate']
    df_rates_clean = df_rates[rate_cols].dropna().copy()
    df_rates_clean['MTOW'] = pd.to_numeric(df_rates_clean['MTOW'], errors='coerce')
    df_rates_clean['Unit Rate'] = pd.to_numeric(df_rates_clean['Unit Rate'], errors='coerce')

    # 4. Define Lookup Function (Finds closest MTOW)
    def get_unit_rate(tonn):
        if pd.isna(tonn):
            return np.nan
        
        # Try exact match first
        match = df_rates_clean[df_rates_clean['MTOW'] == tonn]
        if not match.empty:
            return float(match.iloc[0]['Unit Rate'])
        
        # If no exact match, find the closest MTOW
        df_rates_clean['diff'] = abs(df_rates_clean['MTOW'] - tonn)
        closest_idx = df_rates_clean['diff'].idxmin()
        return float(df_rates_clean.loc[closest_idx, 'Unit Rate'])

    # 5. Apply Logic
    # Map Unit Rate
    df_vendor['Mapped_Unit_Rate'] = df_vendor['tonn'].apply(get_unit_rate)
    
    # Calculate Charge: Unit Rate * (Distance / 100)
    df_vendor['Calculated_Amount'] = df_vendor['Mapped_Unit_Rate'] * (df_vendor['Dist.'] / 100)
    df_vendor['Calculated_Amount'] = df_vendor['Calculated_Amount'].round(2)
    
    # 6. Verify
    df_vendor['Status'] = np.where(
        abs(df_vendor['Calculated_Amount'] - df_vendor['Amount']) <= 0.5,
        'Matched',
        'Not Matched'
    )
    
    # 7. Save Results
    output_cols = ['Invoice Number', 'Ident', 'Reg', 'Dist.', 'tonn', 'Amount', 
                   'Mapped_Unit_Rate', 'Calculated_Amount', 'Status']
    
    output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\ASB\Vendor_Data_Verified.csv"
    df_vendor[output_cols].to_csv(output_file, index=False)
    print("Verification complete. Results saved.")

if __name__ == "__main__":
    verify_charges()