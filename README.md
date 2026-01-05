# Overflight Charges Validation Documentation

We are auditing and validating the overflight charges applied by multiple countries. Whenever an aircraft overflies or passes through the airspace of a particular country or airport, a navigation or overflight fee is charged. This fee primarily depends on the **MTOW (Maximum Takeoff Weight)** of the aircraft, along with other country-specific parameters.

Each country follows its own calculation methodology or formula to determine the final charge.

The source data for validation is obtained from multiple vendor invoices, which are initially available in PDF format and are later converted into Excel/CSV format for processing and analysis.

For the purpose of validation, we consider the distance provided by the vendor as the base reference. We also maintain two supporting master files for each country:

  * **MTOW Master File** — contains aircraft details and their corresponding MTOW values
  * **Rate Master File** — defines the pricing structure and calculation formula used by the country

Although the final charges may appear in different currencies or units depending on the country, our primary objective is to validate the calculated charge against the amount charged by the vendor, ensuring correctness and consistency in billing.

-----

## Country/Airport Specific Validation Steps

### **YYZ**

Net Charges have to be calculated:
$$
\\text{Charges} = \\text{Weight Factor} \\times \\text{Unit Rate} \\times \\text{Distance (BILLDIST)}
$$
Where:

  * **Weight Factor** is Square Root of MTOW
  * **Unit Rate** is constant 0.03524

### **DPS**

1.  **Weight Factor** is available in the Rate Master for different MTOWs.
2.  **Distance Factor** is also available.
3.  **Route Unit** has to be Calculated:
    $$
    \\text{Route Unit} = \\text{Weight Factor} \\times \\text{Distance Factor}
    $$
4.  Then, **Charges** are calculated:
    $$
    \\text{Charges} = \\text{Route Unit} \\times \\text{Unit Rate}
    $$
      * Here, **Unit Rate** is constant 0.65.

### **IKA**

1.  Firstly, the distance has to be converted from Nautical Miles to Kms. by multiplying Miles with **1.852**.
2.  Then, calculate the **Final unit rate** derived by the below formula:
    $$
    \\text{Final unit rate} = (\\text{MTOW} \\times \\text{Unit Rate}) + \\text{Additional Charge (if above 150 Tonnes)}
    $$
      * Here, **Unit Rate** is constant **0.00286** and **Additional charge** is **0.18** which only needs to be added if the weight exceeds 150 Tonnes. Otherwise, it is only $\\text{MTOW} \\times \\text{Unit Rate}$.
3.  Now, **Charges** are calculated:
    $$
    \\text{Charges} = \\text{Final unit rate} \\times \\text{Distance}
    $$

### **LHR**

There are two components of charges: NATS Charge & Satellite Data Charge.

1.  **Flat Rate** is calculated:
    $$
    \\text{Flat Rate} = \\text{NATS Charge} + \\text{Satellite Data Charge}
    $$
      * Where, **NATS Charge** = 57.6 & **Satellite Data Charge** = 38.89
      * So it has a **Flat rate of 96.49**.
2.  **Charges** can be directly calculated by multiplying it with the Distance:
    $$
    \\text{Charges} = \\text{Flat Rate} \\times \\text{Distance}
    $$

### **SGN**

It has a flat rate on the basis of MTOW:

  * If **MTOW** is **97** then charges are **286**.
  * If **MTOW** is **228** then charges are **460**.

### **DOH**

1.  There would be one extra file/step for this airport.
2.  Map **IATA code** for both arrival and departure locations from a separate master file.
3.  Confirm whether the flight has landed in Doha or not by checking the fields Arrival/Departure.
4.  Once this is confirmed, refer to the **Rate master** for different pricing on the basis of **MTOW** as well as if the flight has landed or not.

### **MCT**

1.  Firstly, delimit and extract **Distance** from a particular column.
2.  Calculate the **Distance Factor**:
    $$
    \\text{Distance Factor} = \\text{Distance} / 100
    $$
3.  Map **Weight factor** and **unit rate** from the rate master on the basis of MTOW to calculate the final charges.
4.  **Charges** are calculated:
    $$
    \\text{Charges} = \\text{Unit rate} \\times \\text{Distance factor} \\times \\text{weight factor}
    $$

### **DAC**

There is a **flat rate** for each **MTOW**. We have to just map it with the flight in the master charges file and check for any mismatch or differences.

### **Egypt Irregular Data**

1.  The formula for calculating the **Weight factor** is a bit different:
    $$
    \\text{Weight factor} = \\text{SQRT}(\\text{MTOW}) / 50
    $$
2.  **Distance Factor** is calculated:
    $$
    \\text{Distance Factor} = \\text{Distance} / 100
    $$
3.  **Final Charges** are calculated:
    $$
    \\text{Final Charges} = \\text{Unit rate} \\times \\text{Distance Factor} \\times \\text{Weight Factor}
    $$
      * **Unit Rate** is constant **21.38** across all MTOWs.

### **AUH**

The steps are similar to **DOH**:

1.  Verify if the flight has landed or not.
2.  Map **IATA code** for both arrival and departure locations from a separate master file.
3.  Once the IATA codes are mapped, confirm whether the flight has landed or not by checking the fields Arrival/Departure.
4.  Refer to the **Rate master** for different pricing on the basis of **MTOW** as well as if the flight has landed or not.

### **CMB**

1.  Cap the **distance** on the basis:
      * If distance is **below 300** then it is always **300**.
      * If distance is **above 600** then it is always **600**.
      * Therefore, only two values (300 and 600) are to be considered while deriving out the calculations.
2.  For calculating the **final charges**:
    $$
    \\text{Charges} = (\\text{Capped Distance} + \\text{MTOW}) / 3
    $$

### **RUSSIA**

1.  Round off the **distance** to the nearest highest value in hundreds (i.e., if 148 then 200).
2.  Map **MTOW** and their particular **Unit rate** from the master file and derive the charges.
3.  **Charges** are calculated:
    $$
    \\text{Charges} = \\text{Unit Rate} \\times (\\text{Distance} / 100)
    $$

### **PNH**

1.  Map **MTOW** from the master file.
2.  Once mapped, there is a **flat rate** for each MTOW.
3.  Verify the same from the vendor charges.

### **Kazakhstan**

There is a **flat rate** for charges. We just have to map the **MTOW** and check for differences.

### **RGN/MGQ/LHE/KAZ**

All of the above locations have a **flat rate** based on my analysis of the file, even though not explained in the meeting. They all have a **fixed unit rate** on the basis that charges can be calculated and verified.
