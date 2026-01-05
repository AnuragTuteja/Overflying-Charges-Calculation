We are auditing and validating the overflight charges applied by multiple countries. Whenever an aircraft overflies or passes through the airspace of a particular country or airport, a navigation or overflight fee is charged. This fee primarily depends on the MTOW (Maximum Takeoff Weight) of the aircraft, along with other country-specific parameters.
Each country follows its own calculation methodology or formula to determine the final charge.
The source data for validation is obtained from multiple vendor invoices, which are initially available in PDF format and are later converted into Excel/CSV format for processing and analysis.
For the purpose of validation, we consider the distance provided by the vendor as the base reference. We also maintain two supporting master files for each country:
MTOW Master File — contains aircraft details and their corresponding MTOW values
Rate Master File — defines the pricing structure and calculation formula used by the country
Although the final charges may appear in different currencies or units depending on the country, our primary objective is to validate the calculated charge against the amount charged by the vendor, ensuring correctness and consistency in billing.
YYZ
Net Charges have to be calculated
Charges = Weight Factor * Unit Rate * Distance(BILLDIST)
Where Weight Factor is Square Root of MTOW and Unit Rate is constant 0.03524
DPS
Weight Factor available in the Rate Master for different MTOWs and Similarly Distance Factor also.
Route Unit has to be Calculated which is Weight Factor * Distance Factor
And then, Charges = Route Unit * Unit Rate, here Unit rate is constant 0.65.
IKA
Firstly the distance has to be converted from Nautical Miles to Kms. by multiplying Miles with 1.852
Then we have to calculate a Final unit rate which is derived by the below formula
 Final unit rate =  (MTOW * Unit Rate) + Additional Charge if above 150 Tonnes
Here, Unit Rate is constant 0.00286 and Additional charge is 0.18 which only needs to be added if the weight exceeds 150 Tonnes, Otherwise it is only MTOW * Unit Rate.
Now, Charges = Final unit rate * Distance 
LHR
Two Components of charges, NATS Charge & Satellite Data Charge.
Flat Rate = NATS Charge + Satellite Data Charge                             	
Where, NATS Charge = 57.6 & Satellite Data Charge = 38.89   
So it has a Flat rate of 96.49 and charges can be directly calculated by multiplying it with the Distance
Charges = Flat Rate * Distance
SGN
It has a flat rate on the basis of MTOW, if MTOW is 97 then charges are 286 and if MTOW is 228 then charges are 460.
DOH
There would be one extra file/step for this airport. We have to map IATA code for both arrival and departure locations from a separate master file. Once the IATA codes are mapped now we have to confirm whether the flight has landed in Doha or not by checking the fields Arrival/Departure.
 Once this is confirmed, we have to refer to the Rate master for different pricing on the basis of MTOW as well as if the flight has landed or not.
MCT
Firstly we have to delimit and extract Distance from a particular column, once that is done we will calculate the distance factor.
Distance Factor = Distance/100
Then we have to map Weight factor and unit rate from the rate master on the basis of MTOW to calculate the final charges.
Charges = Unit rate * Distance factor * weight factor
DAC
There is a flat rate for each MTOW, we have to just map it with the flight in the master charges file and check for any mismatch or differences.
Egypt Irregular Data
Here the formula for calculating the weight factor is a bit different ,
Weight factor = SQRT(MTOW)/50
Distance Factor = Distance/100
Final Charges = Unit rate*Distance Factor*Weight Factor
Now Unit Rate is constant 21.38 across all MTOWs.
AUH
The steps are similar to DOH and we have to verify if the flight has landed or not. Then we have to map IATA code for both arrival and departure locations from a separate master file. Once the IATA codes are mapped now we have to confirm whether the flight has landed or not by checking the fields Arrival/Departure. Once this is confirmed, we have to refer to the Rate master for different pricing on the basis of MTOW as well as if the flight has landed or not.
CMB
For this location we have to cap the distance on the basis:
If distance is below 300 then it is always 300 only and if distance Above 600 then it is always 600, therefore only two values to be considered while deriving out the calculations.
For calculating the final charges,
Charges = (Capped Distance + MTOW)/3
RUSSIA
For this location we have to round off the distance to the nearest highest value in hundreds i.e. if 148 then 200.
Now we have to map MTOW and their particular Unit rate from the master file and derive the charges.
 Charges = Unit Rate * (Distance/100)
PNH
We have to map MTOW from the master file. Once mapped there is a flat rate for each MTOW and we just have to verify the same from the vendor charges.
Kazakhstan
There is a flat rate for charges, we just have to map the MTOW and check for differences.
RGN/MGQ/LHE/KAZ
All of the above locations have a flat rate based on my analysis of the file, even though not explained in the meeting. They all have a fixed unit rate on the basis that charges can be calculated and verified.
 

