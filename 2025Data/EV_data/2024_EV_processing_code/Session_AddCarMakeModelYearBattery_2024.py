# -*- coding: utf-8 -*-
"""
Created on Tue Nov  1 15:34:43 2022

@author: Anne
"""


#################################################################################
# Measure the processing time with wall clock time
#################################################################################


import time
from time import process_time
import pandas as pd
import os.path
from pathlib import Path 


Time_Run_Start = process_time()  




#################################################################################
# Read/Import the Session Data and the Car Make/Model/Year/DoeID file from the folder
#################################################################################


dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")
    #C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download
PowerFlexData_Site = "AllSites" #'Athena', 'Gilman'
PowerFlexData_Type = "Sessions" 
PowerFlexData_DateRangeStart = "20210501" #20210501
PowerFlexData_DateRangeEnd = "20231231" #20231231
filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
data_Sessions= pd.read_csv(filename_Input)

#data_Sessions= pd.read_csv(dir_Input+"UCSD_AllSites_Sessions_20210501_20231231.csv")
    #UCSD_AllSites_Sessions_20210501_20231231.csv
    #UCSD-AllSites_Sessions_20240101_20240930.csv


# Read Car Make/Model/Year/DoeID file
dir_Input_2 = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")
data_CarInfo= pd.read_csv(dir_Input_2 + 'PowerFlex input for EV statistics to be plugged into master sheet_2024.csv' )





#################################################################################
# Create extra columns of Car Year, Car Make, and Car Model for Session data
#################################################################################





#data_CarInfo['YearMakeModel'] = data_CarInfo['Year'].astype(str)+' '+data_CarInfo['Make'].astype(str)+' '+data_CarInfo['Model'].astype(str)
Vehicle_session = data_Sessions['Vehicle']

data_CarInfo['Year'] = data_CarInfo['Year'].astype(str)


Year = []
Make = []
Model = []
BESS = []

# if the Type of data is 'str', its the new data, if its 'int64', its the old data
if type(Vehicle_session[0]) is str:
    
    for i in range(len(Vehicle_session)):
        #i = 4
        Vehicle_ThisSession = Vehicle_session[i]
        
        # the 'Vehicle' is NOT 0.000 in the PF session data
        if len(Vehicle_ThisSession)>6:
            Year_ThisSession = Vehicle_ThisSession.split(' ')[0]
            Make_ThisSession = Vehicle_ThisSession.split(' ')[1]
            Model_ThisSession = Vehicle_ThisSession.split(Year_ThisSession + ' ' +Make_ThisSession+' ')[1]
            BESS_ThisSession = data_CarInfo['Battery (kWh)'][(data_CarInfo['Make']==Make_ThisSession)&\
                                                                (data_CarInfo['Model']==Model_ThisSession)&\
                                                                (data_CarInfo['Year']==Year_ThisSession) ]
           
            if len(pd.Series(BESS_ThisSession))>=1:
               BESS_ThisSession = BESS_ThisSession.iloc[0] 
                
            #if no match, give up one matching the Year, as long as the Make and Model match, asign the BES capacity
            elif len(pd.Series(BESS_ThisSession))==0:
                BESS_ThisSession = data_CarInfo['Battery (kWh)'][(data_CarInfo['Make']==Make_ThisSession)&\
                                                                    (data_CarInfo['Model']==Model_ThisSession)]
            
                if len(pd.Series(BESS_ThisSession))>=1:
                   BESS_ThisSession = BESS_ThisSession.iloc[0]
                   
                #if STILL no match, the BESS capacity is unknown
                elif len(pd.Series(BESS_ThisSession))==0:
                    BESS_ThisSession = 'nan'

       
        
        # if the 'Vehicle' is 0.000 in the PF session data
        else:
            Year_ThisSession = 'nan'
            Make_ThisSession = 'nan'
            Model_ThisSession = 'nan'
            BESS_ThisSession = 'nan'
            
            
                    
        Year = Year + [Year_ThisSession]
        Make = Make + [Make_ThisSession]
        Model = Model + [Model_ThisSession]
        BESS = BESS + [BESS_ThisSession]            
            
            

        

else:
    
    for i in range(len(Vehicle_session)):
        #i = 12
        Vehicle_ThisSession = Vehicle_session[i]
        data_CarInfo_ThisSession = data_CarInfo[data_CarInfo['Doe Id']==Vehicle_ThisSession]

        if len(data_CarInfo_ThisSession)==0:
            Year = Year + ['nan']
            Make = Make + ['nan']
            Model = Model + ['nan']
            BESS = BESS + ['nan']
            
        else:
            Year = Year + [data_CarInfo_ThisSession['Year'].iloc[0]]
            Make = Make + [data_CarInfo_ThisSession['Make'].iloc[0]]
            Model = Model + [data_CarInfo_ThisSession['Model'].iloc[0]]
            BESS = BESS + [data_CarInfo_ThisSession['Battery (kWh)'].iloc[0]]




data_Sessions['Car Year'] = Year
data_Sessions['Car Make'] = Make
data_Sessions['Car Model'] = Model
data_Sessions['Car Battery'] = BESS




#################################################################################
# Write the Session_wCarInfo data to .csv file
#################################################################################


 

#filepath = Path('C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Interval_aux/out.csv')  
#dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download")
filepath = Path(dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_wCarInfo_'+ PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
data_Sessions.to_csv(filepath,index=False)




#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))

# sessions: 53679+43377