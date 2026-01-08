import pandas as pd
import numpy as np

# Load data
vendor_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Vendor Data.csv"
iata_mapping_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\IATA ICAO Mapping.xlsx - Sheet1.csv"
mtow_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\MTOW Master.csv"
rate_master_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Rate Master.csv"

df_vendor = pd.read_csv(vendor_file)
df_iata = pd.read_csv(iata_mapping_file)
df_mtow = pd.read_csv(mtow_master_file)
df_rates = pd.read_csv(rate_master_file)

#Map flight type based on DOH presence in Dep or Arr
def determine_flight_type(row):
    dep = str(row['IATA']).upper().strip()
    arr = str(row['IATA.1']).upper().strip()
    # Logic: If DOH is involved in either end, it's a landing charge
    if dep == 'DOH' or arr == 'DOH':
        return 'With landing'
    else:
        return 'Without landing rate'

df_vendor['FLIGHT_TYPE'] = df_vendor.apply(determine_flight_type, axis=1)

#Clean
df_vendor = df_vendor.dropna(subset=['Invoice number']).reset_index(drop=True)
df_vendor = df_vendor.loc[:, ~df_vendor.columns.str.contains('^Unnamed')]

#Get MTOW and convert to Tonnes
df_mtow['Reg_Clean'] = df_mtow['Aircraft '].str.strip()
df_vendor['Reg_Clean'] = df_vendor['Registration'].str.strip()
df_working = df_vendor.merge(df_mtow[['Reg_Clean', 'MTOW_in_KGs']], on='Reg_Clean', how='left')

ac_type_mtow = {'A20N': 77000.0, 'A21N': 97000.0, 'B77W': 351534.0, 'B788': 227930.0}
df_working['MTOW_in_KGs'] = df_working.apply(
    lambda r: ac_type_mtow.get(r['AC Type'], r['MTOW_in_KGs']) if pd.isna(r['MTOW_in_KGs']) else r['MTOW_in_KGs'], axis=1
)
df_working['MTOW_Tonnes'] = pd.to_numeric(df_working['MTOW_in_KGs'], errors='coerce') / 1000

# Rate Master Lookup
def get_charge(mtow, f_type):
    if pd.isna(mtow): return np.nan
    # Clean rate master and filter by exact flight type
    rates = df_rates.copy()
    rates['Landing/takeoff'] = rates['Landing/takeoff'].str.strip()
    match = rates[rates['Landing/takeoff'] == f_type].copy()
    # Find closest MTOW match
    match['diff'] = abs(pd.to_numeric(match['MTOW']) - mtow)
    return float(match.loc[match['diff'].idxmin()]['Charge'])

df_working['CALCULATED_CHARGE'] = df_working.apply(
    lambda r: get_charge(r['MTOW_Tonnes'], r['FLIGHT_TYPE']), axis=1
)

# 4. Compare and Save
df_working['TOTAL_BILL_NUM'] = pd.to_numeric(df_working['Total Bill'], errors='coerce')
df_working['STATUS'] = np.where(abs(df_working['CALCULATED_CHARGE'] - df_working['TOTAL_BILL_NUM']) <= 0.01, 'Matched', 'Not Matched')

output_file = r"c:\Users\Anurag\Downloads\Assignment\Assignment\DOH\Vendor_Data_Verified.csv"
df_working.to_csv(output_file, index=False)
print("Verification complete. Results saved.")