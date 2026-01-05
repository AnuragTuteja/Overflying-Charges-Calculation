import pandas as pd
import numpy as np
import os
import re
import glob

# File paths - detect files automatically
vendor_files = glob.glob("*.csv")
vendor_file = None

# Look for specific vendor file first
if os.path.exists("1900374945.csv"):
    vendor_file = "1900374945.csv"
else:
    # Identify vendor file (should be the main data file, not master files)
    for f in vendor_files:
        f_lower = f.lower()
        if 'mtow' not in f_lower and 'rate' not in f_lower:
            vendor_file = f
            break

print(f"Detected files:")
print(f"  Vendor: {vendor_file}")

if not vendor_file:
    print("ERROR: Could not detect vendor file")
    exit(1)

# Read files
print("\nLoading files...")
df_vendor = pd.read_csv(vendor_file)

print(f"Vendor data loaded: {len(df_vendor)} records")

# Clean column names - remove special characters and non-breaking spaces
df_vendor.columns = df_vendor.columns.str.replace('\xa0', ' ').str.strip()

print(f"\nVendor columns: {list(df_vendor.columns)}")

# Create working dataframe
df_working = df_vendor.copy()

# Helper function to extract numeric values
def extract_numeric_value(val):
    """Extract numeric value from a cell, handling currency formats"""
    if pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace('\n', ' ').replace('\r', ' ')
    # Remove currency symbols and commas
    val_str = val_str.replace('$', '').replace(',', '').replace('USD', '')
    match = re.search(r'(\d+\.?\d*)', val_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return np.nan
    return np.nan

print("\n" + "="*100)
print("LHR CHARGE VERIFICATION - FLAT RATE SUM")
print("="*100)

# LHR Charge Formula
NATS_CHARGE = 57.6
SATELLITE_DATA_CHARGE = 38.89
FLAT_RATE = NATS_CHARGE + SATELLITE_DATA_CHARGE

print(f"\nCharge Components:")
print(f"  NATS Charge: {NATS_CHARGE}")
print(f"  Satellite Data Charge: {SATELLITE_DATA_CHARGE}")
print(f"  Total Flat Rate = {FLAT_RATE}")
print(f"\nFormula: Total Charge = NATS Charge + Satellite Data Charge")

# Find Core NATS Charge column
nats_col = None
for col in df_working.columns:
    col_lower = col.lower()
    if 'nats' in col_lower and 'core' in col_lower:
        nats_col = col
        break

print(f"\nCore NATS Charge column: {nats_col}")

if nats_col:
    df_working['NATS_Charge_Value'] = df_working[nats_col].apply(extract_numeric_value)
else:
    print("ERROR: Could not find NATS charge column")
    df_working['NATS_Charge_Value'] = np.nan

# Find Satellite Data Charge column
sat_col = None
for col in df_working.columns:
    col_lower = col.lower()
    if 'satellite' in col_lower and 'data' in col_lower:
        sat_col = col
        break

print(f"Satellite Data Charge column: {sat_col}")

if sat_col:
    df_working['Satellite_Charge_Value'] = df_working[sat_col].apply(extract_numeric_value)
else:
    print("ERROR: Could not find Satellite Data charge column")
    df_working['Satellite_Charge_Value'] = np.nan

print(f"  Valid NATS charges: {df_working['NATS_Charge_Value'].notna().sum()}/{len(df_working)}")
print(f"  Valid Satellite charges: {df_working['Satellite_Charge_Value'].notna().sum()}/{len(df_working)}")

# Find vendor charge column (Total charge)
charge_col = None
for col in df_working.columns:
    col_lower = col.lower()
    if 'total' in col_lower and 'charge' in col_lower:
        charge_col = col
        break

print(f"Vendor charge column: {charge_col}")

if charge_col:
    df_working['Vendor_Charge'] = df_working[charge_col].apply(extract_numeric_value)
else:
    df_working['Vendor_Charge'] = np.nan

print(f"  Valid vendor charges: {df_working['Vendor_Charge'].notna().sum()}/{len(df_working)}")

# STEP 2: CHARGE CALCULATION
print("\n" + "="*100)
print("STEP 2: CHARGE CALCULATION")
print("="*100)

def calculate_charge(nats_val, sat_val):
    """Calculate total charge = NATS Charge + Satellite Data Charge"""
    if pd.isna(nats_val) or pd.isna(sat_val):
        return np.nan
    try:
        return float(nats_val) + float(sat_val)
    except (ValueError, TypeError):
        return np.nan

df_working['Calculated_Charge'] = df_working.apply(
    lambda row: calculate_charge(row['NATS_Charge_Value'], row['Satellite_Charge_Value']),
    axis=1
)

print(f"\nCharge Calculation Results:")
print(f"  Successfully calculated: {df_working['Calculated_Charge'].notna().sum()}/{len(df_working)}")

# STEP 3: VERIFICATION
print("\n" + "="*100)
print("STEP 3: CHARGE VERIFICATION")
print("="*100)

tolerance = 0.01

def check_match(calculated, vendor):
    """Check if calculated charge matches vendor charge within tolerance"""
    if pd.isna(calculated) or pd.isna(vendor):
        return "Not Matched"
    diff = abs(calculated - vendor)
    if diff <= tolerance:
        return "Matched"
    else:
        return "Not Matched"

df_working['Difference'] = abs(df_working['Calculated_Charge'] - df_working['Vendor_Charge'])
df_working['Status'] = df_working.apply(
    lambda row: check_match(row['Calculated_Charge'], row['Vendor_Charge']),
    axis=1
)

# Summary
matched_count = (df_working['Status'] == 'Matched').sum()
not_matched_count = (df_working['Status'] == 'Not Matched').sum()
total_records = len(df_working)
success_rate = (matched_count / total_records) * 100 if total_records > 0 else 0

print(f"\n[MATCHED]     {matched_count}")
print(f"[NOT MATCHED] {not_matched_count}")
print(f"Total Records: {total_records}")
print(f"Success Rate:  {success_rate:.1f}%")

print("\nData Quality:")
print(f"- Records with valid NATS Charge: {df_working['NATS_Charge_Value'].notna().sum()}/{total_records} ({(df_working['NATS_Charge_Value'].notna().sum()/total_records)*100:.1f}%)")
print(f"- Records with valid Satellite Charge: {df_working['Satellite_Charge_Value'].notna().sum()}/{total_records} ({(df_working['Satellite_Charge_Value'].notna().sum()/total_records)*100:.1f}%)")
print(f"- Records with valid Vendor Charge: {df_working['Vendor_Charge'].notna().sum()}/{total_records}")
print(f"- Records with Calculated Charges: {df_working['Calculated_Charge'].notna().sum()}/{total_records}")

# Matched charges statistics
matched_data = df_working[df_working['Status'] == 'Matched']
if len(matched_data) > 0:
    print("\nMatched Charges:")
    print(f"  Count: {len(matched_data)}")
    print(f"  Min: ${matched_data['Vendor_Charge'].min():.2f}")
    print(f"  Max: ${matched_data['Vendor_Charge'].max():.2f}")
    print(f"  Mean: ${matched_data['Vendor_Charge'].mean():.2f}")
    print(f"  Total: ${matched_data['Vendor_Charge'].sum():.2f}")

# Detailed results (first 20)
print("\n" + "="*100)
print("DETAILED VERIFICATION RESULTS (First 20 rows):")
print("="*100)
display_cols = [col for col in ['NATS_Charge_Value', 'Satellite_Charge_Value', 'Calculated_Charge', 'Vendor_Charge', 'Difference', 'Status'] 
                if col in df_working.columns]
print(df_working[display_cols].head(20).to_string())

# Mismatch analysis
mismatches = df_working[df_working['Status'] == 'Not Matched'].copy()
if len(mismatches) > 0:
    valid_mismatches = mismatches[mismatches['Calculated_Charge'].notna()].copy()
    if len(valid_mismatches) > 0:
        print(f"\n[FOUND {len(valid_mismatches)} MISMATCHES]")
        print(f"\nMismatch Details (first 15):")
        print(valid_mismatches[display_cols].head(15).to_string())
        
        print(f"\nDifference Analysis (valid mismatches):")
        print(f"  Total valid mismatches: {len(valid_mismatches)}")
        print(f"  Min difference: ${valid_mismatches['Difference'].min():.2f}")
        print(f"  Max difference: ${valid_mismatches['Difference'].max():.2f}")
        print(f"  Mean difference: ${valid_mismatches['Difference'].mean():.2f}")
        print(f"  Total vendor difference: ${valid_mismatches['Vendor_Charge'].sum():.2f}")

# Save results
output_file = "Verification_Results.csv"
df_output = df_working[display_cols].copy()
df_output.to_csv(output_file, index=False)

print(f"\n\nResults saved to: {os.path.abspath(output_file)}")
print("="*100)
