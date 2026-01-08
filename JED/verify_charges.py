import pandas as pd
import numpy as np

def verify_jed_charges():
    # 1. Load Data
    print("Loading files...")
    vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\Vendor Master.csv"
    mtow_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\MTOW Master.csv"
    rate_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\Rate Master.csv"

    # Load data
    df_vendor = pd.read_csv(vendor_file)
    df_mtow = pd.read_csv(mtow_master_file)
    df_rates = pd.read_csv(rate_master_file)


    # Clean column names (remove newlines and spaces)
    df_vendor.columns = df_vendor.columns.str.replace('\n', ' ').str.strip()
    df_rates.columns = df_rates.columns.str.replace('\n', ' ').str.strip()
    df_mtow.columns = df_mtow.columns.str.replace('\n', ' ').str.strip()

    # 2. Prepare Data
    # Clean up strings for merging
    df_mtow['Aircraft'] = df_mtow['Aircraft'].astype(str).str.strip()
    df_vendor['Aircraft ID'] = df_vendor['Aircraft ID'].astype(str).str.strip()
    
    # Merge Vendor Data with MTOW Master
    df_working = df_vendor.merge(
        df_mtow[['Aircraft', 'MTOW_in_KGs']], 
        left_on='Aircraft ID', 
        right_on='Aircraft', 
        how='left'
    )

    # Convert MTOW to Tonnes
    df_working['MTOW_Tonnes'] = pd.to_numeric(df_working['MTOW_in_KGs'], errors='coerce') / 1000

    # 3. Determine Weight Factor
    # The Rate Master defines Weight Factors for specific MTOWs.
    # We need to find the closest MTOW match in the Rate Master for each flight.
    
    # Clean Rate Master
    df_rates['MTOW_Target'] = pd.to_numeric(df_rates['MTOW.1'], errors='coerce')
    df_rates['Weight Factor'] = pd.to_numeric(df_rates['Weight Factor'], errors='coerce')
    
    def get_weight_factor(mtow):
        if pd.isna(mtow): return np.nan
        # Find absolute difference between flight MTOW and Rate Master MTOWs
        df_rates['diff'] = abs(df_rates['MTOW_Target'] - mtow)
        # Get the Weight Factor of the closest match
        closest_match = df_rates.loc[df_rates['diff'].idxmin()]
        return float(closest_match['Weight Factor'])

    df_working['Calc_Weight_Factor'] = df_working['MTOW_Tonnes'].apply(get_weight_factor)

    # 4. Calculate Charge
    # Formula: Weight Factor * (Distance / 100) * Unit Rate
    # Note: Unit Rate is 118 according to the Rate Master snippet
    UNIT_RATE = 118.0
    
    # Clean Distance
    df_working['Distance Km'] = pd.to_numeric(df_working['Distance Km'], errors='coerce')

    def calculate_formula(row):
        if pd.isna(row['Calc_Weight_Factor']) or pd.isna(row['Distance Km']):
            return np.nan
        
        distance_factor = row['Distance Km'] / 100
        charge = row['Calc_Weight_Factor'] * distance_factor * UNIT_RATE
        return round(charge, 2)

    df_working['Calculated_Charge'] = df_working.apply(calculate_formula, axis=1)

    # 5. Compare Results
    # Vendor uses 'Flight Total Charge'
    df_working['Vendor_Charge'] = pd.to_numeric(df_working['Flight Total Charge'], errors='coerce')
    
    df_working['Status'] = np.where(
        abs(df_working['Calculated_Charge'] - df_working['Vendor_Charge']) <= 0.5, # 0.5 tolerance for rounding
        'Matched', 
        'Not Matched'
    )

    # 6. Save Output
    output_cols = [
        'Invoice No', 'Flight Number', 'Aircraft ID', 'Origin Code', 'Dest. Code',
        'Distance Km', 'MTOW_Tonnes', 'Calc_Weight_Factor', 
        'Calculated_Charge', 'Vendor_Charge', 'Status'
    ]
    
    output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\JED\Vendor_Data_Verified.csv"
    df_working[output_cols].to_csv(output_file, index=False)
    
    print(f"Verification Complete. Results saved to {output_file}")
    print(df_working[output_cols].head())

if __name__ == "__main__":
    verify_jed_charges()