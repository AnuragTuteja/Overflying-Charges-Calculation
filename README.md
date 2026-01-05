# Overflight Charges Validation Documentation

This project focuses on auditing and validating the overflight charges applied by multiple countries.  
Whenever an aircraft overflies or passes through the airspace of a particular country or airport, a navigation or overflight fee is charged. This fee primarily depends on the **MTOW (Maximum Takeoff Weight)** of the aircraft, along with other country-specific parameters.

Each country follows its own calculation methodology or formula to determine the final charge.

The source data for validation is obtained from multiple vendor invoices, which are initially available in **PDF format** and are later converted into **Excel/CSV format** for processing and analysis.

For the purpose of validation, we consider the **distance provided by the vendor** as the base reference.  
We also maintain two supporting master files for each country:

- **MTOW Master File** — contains aircraft details and their corresponding MTOW values  
- **Rate Master File** — defines the pricing structure and calculation formula used by the country

Although the final charges may appear in different currencies or units depending on the country, our primary objective is to **validate the calculated charge against the amount charged by the vendor**, ensuring correctness and consistency in billing.

---

## Country / Airport Specific Validation Steps

### YYZ

Net Charges have to be calculated:

\[
\text{Charges} = \text{Weight Factor} \times \text{Unit Rate} \times \text{Distance (BILLDIST)}
\]

Where:
- **Weight Factor** is the square root of MTOW  
- **Unit Rate** is constant **0.03524**

---

### DPS

1. **Weight Factor** is available in the Rate Master for different MTOWs  
2. **Distance Factor** is also available  
3. **Route Unit** is calculated as:

\[
\text{Route Unit} = \text{Weight Factor} \times \text{Distance Factor}
\]

4. **Charges** are then calculated:

\[
\text{Charges} = \text{Route Unit} \times \text{Unit Rate}
\]

- **Unit Rate** is constant **0.65**

---

### IKA

1. Convert distance from Nautical Miles to KM:

\[
\text{KM} = \text{Miles} \times 1.852
\]

2. Calculate **Final Unit Rate**:

\[
\text{Final Unit Rate} = (\text{MTOW} \times \text{Unit Rate}) + \text{Additional Charge (if above 150 Tonnes)}
\]

- **Unit Rate** = **0.00286**  
- **Additional Charge** = **0.18** (applied only if MTOW > 150T)

3. Calculate **Charges**:

\[
\text{Charges} = \text{Final Unit Rate} \times \text{Distance}
\]

---

### LHR

Two components apply: **NATS Charge** and **Satellite Data Charge**

1. **Flat Rate**:

\[
\text{Flat Rate} = \text{NATS Charge} + \text{Satellite Data Charge}
\]

- **NATS Charge** = 57.6  
- **Satellite Data Charge** = 38.89  
- **Total Flat Rate** = **96.49**

2. **Charges**:

\[
\text{Charges} = \text{Flat Rate} \times \text{Distance}
\]

---

### SGN

Flat rate based on MTOW:
- MTOW **97** → Charges **286**  
- MTOW **228** → Charges **460**

---

### DOH

1. Additional file required  
2. Map **IATA codes** for arrival and departure from master file  
3. Verify whether the flight has landed in Doha  
4. Refer to Rate Master for MTOW-based pricing and landing condition

---

### MCT

1. Extract **Distance** from the given column  
2. Calculate **Distance Factor**:

\[
\text{Distance Factor} = \text{Distance} / 100
\]

3. Map **Weight Factor** and **Unit Rate** from Rate Master  
4. Final calculation:

\[
\text{Charges} = \text{Unit Rate} \times \text{Distance Factor} \times \text{Weight Factor}
\]

---

### DAC

Flat rate per MTOW.  
Map the value and check for mismatches.

---

### Egypt (Irregular Data)

1. Weight Factor:

\[
\text{Weight Factor} = \sqrt{\text{MTOW}} / 50
\]

2. Distance Factor:

\[
\text{Distance Factor} = \text{Distance} / 100
\]

3. Final Charges:

\[
\text{Final Charges} = \text{Unit Rate} \times \text{Distance Factor} \times \text{Weight Factor}
\]

- **Unit Rate** is constant **21.38**

---

### AUH

Same process as **DOH**:
1. Verify landing  
2. Map IATA codes  
3. Confirm landing status  
4. Refer to Rate Master for MTOW-based pricing

---

### CMB

1. Cap distance:
   - Below **300** → **300**
   - Above **600** → **600**

2. Final Charges:

\[
\text{Charges} = (\text{Capped Distance} + \text{MTOW}) / 3
\]

---

### RUSSIA

1. Round distance up to nearest hundred  
2. Map MTOW and Unit Rate  
3. Calculate:

\[
\text{Charges} = \text{Unit Rate} \times (\text{Distance} / 100)
\]

---

### PNH

Flat rate per MTOW.  
Map and verify.

---

### Kazakhstan

Flat rate based on MTOW.  
Map and validate.

---

### RGN / MGQ / LHE / KAZ

All follow a flat-rate structure based on fixed unit rates derived from the data.
