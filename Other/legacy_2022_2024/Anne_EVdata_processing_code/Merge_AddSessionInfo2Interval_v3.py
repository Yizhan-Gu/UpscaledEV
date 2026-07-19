# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 15:35:16 2022

@author: Anne
"""

#################################################################################
# Choose the 'Site' you want to analyze
#################################################################################
MySite_str = "AllSites" #choices: "AllSites", "Athena", "Gilman"




#################################################################################
# Choose the 'start date' and 'end date' you want to analyze
#################################################################################


from datetime import datetime
TheDate_Start = datetime(2022, 9, 25)
TheDate_End = datetime(2023, 1, 29)

TheDate_Start_str = TheDate_Start.strftime("%Y%m%d")
TheDate_End_str = TheDate_End.strftime("%Y%m%d")


#################################################################################
# Measure the processing time with wall clock time
#################################################################################


import time
from time import process_time

Time_Run_Start = process_time()  




#################################################################################
# Read/Import the PowerFlex Data from the folder
#################################################################################


import os.path
dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download")
#C:\Users\Anne\Desktop\Total\Data\EV_PF_UCSD\Download
#C:/Users/Anne/Downloads

PowerFlexData_Site = "AllSites" #'Athena', 'Gilman'
#filename_Input = r'C:\Users\Anne\Downloads\UCSD_AllSites_Interval_20220906_20220908.csv'


import pandas as pd

# Read Interval Data
PowerFlexData_Type = "Interval" #'Sessions', 'Stations'
PowerFlexData_DateRangeStart = "20230128"
PowerFlexData_DateRangeEnd = "20230302"
filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
data_Interval= pd.read_csv(filename_Input)

# Read Sessions Data
PowerFlexData_Type = "Sessions" 
PowerFlexData_DateRangeStart = "20230128"
PowerFlexData_DateRangeEnd = "20230302"
filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
data_Sessions= pd.read_csv(filename_Input)




#################################################################################
# Filter the data based on the site location you choose
#################################################################################


if MySite_str == "AllSites":    
    data_Interval_MySite = data_Interval
    data_Sessions_MySite = data_Sessions
else:    
    
    if MySite_str == "Athena":
        MySite_address = "3960 Health Sciences Dr., La Jolla, CA 93027"
    else: 
        MySite_address = "3100 Gilman Dr La Jolla, CA 92093"       
    
    data_Interval_MySite = data_Interval[data_Interval['Site Location'] == MySite_address]
    data_Sessions_MySite = data_Sessions[data_Sessions['Site Location'] == MySite_address] 
        



#################################################################################
# Filter the data based on the duration you choose
#################################################################################


IntervalStart_datetime = pd.to_datetime(data_Interval_MySite['Interval start'])
IntervalEnd_datetime = pd.to_datetime(data_Interval_MySite['Interval end'])

data_Interval_MySite_MyDates = data_Interval_MySite[(TheDate_Start <= IntervalStart_datetime) & (IntervalStart_datetime <= TheDate_End) \
                                                & (TheDate_Start <= IntervalEnd_datetime) & (IntervalEnd_datetime <= TheDate_End) ]
    
SessionStart_datetime = pd.to_datetime(data_Sessions_MySite['Session start'])
SessionEnd_datetime = pd.to_datetime(data_Sessions_MySite['Session end'])    

data_Sessions_MySite_MyDates = data_Sessions_MySite[(TheDate_Start <= SessionStart_datetime) & (SessionStart_datetime <= TheDate_End) \
                                                & (TheDate_Start <= SessionEnd_datetime) & (SessionEnd_datetime <= TheDate_End) ]
    
    
    
    
#################################################################################
# Count the # of rows/columns of the Interval_MySite data
#################################################################################


count_row_Interval_MySite = data_Interval_MySite_MyDates.shape[0]  # Gives number of rows
count_col_Interval_MySite = data_Interval_MySite_MyDates.shape[1]  # Gives number of columns

count_row_Sessions_MySite = data_Sessions_MySite_MyDates.shape[0]  # Gives number of rows
count_col_Sessions_MySite = data_Sessions_MySite_MyDates.shape[1]  # Gives number of columns




#################################################################################
# Re asign index to the filtered Interval/Session data
#################################################################################


import numpy as np
ind_new = np.arange(0,count_row_Interval_MySite)
data_Interval_MySite_MyDates_NewInd = data_Interval_MySite_MyDates
data_Interval_MySite_MyDates_NewInd = data_Interval_MySite_MyDates_NewInd.set_index(ind_new)   

ind_new = np.arange(0,count_row_Sessions_MySite)
data_Sessions_MySite_MyDates_NewInd = data_Sessions_MySite_MyDates
data_Sessions_MySite_MyDates_NewInd = data_Sessions_MySite_MyDates_NewInd.set_index(ind_new)




#################################################################################
# What columns from the Sessions data you want to add to the Interval data?
# Added columns include: 
    # column C, D, E, F, G, I:
        # "Session start", "Session end", "Session duration (minutes)", "Charging duration (minutes)", Session idle (minutes), kWh delivered
    # column L, M, N, O, P: 
        # "SoC Start", "SoC End", "User", "Vehicle", "EVSE Status", 
    # column T: 
        # "Serial #", 
    # column V, W: 
        # "Space #", "Site", 
    # column Y, Z, AA, AB, AC, AD, AE, AF, AG:
        #"Cost to site", "Cost to driver", "Fleet", "Vehicle barcode", "Minutes available", "Miles needed", "Energy needed", "Energy unit", "Wh per mile".
#################################################################################


#ColumnNames_appen = [\
    # "10-digit session UID", \
    # "Session start", "Session end", "Session duration (minutes)", "Charging duration (minutes)"," Session idle (minutes)", "kWh delivered"
    # "SoC Start","SoC End","User", "Vehicle", "EVSE Status", \
    # "Serial #", \
    # "Space #", "Site", \
    # "Cost to site", "Cost to driver", "Fleet", "Vehicle barcode", "Minutes available", "Miles needed", "Energy needed", "Energy unit", "Wh per mile"]
# =============================================================================
# ColumnNames_appen = [\
#     "10-digit UID", \
#     "Session start", "Session end", "Session duration (minutes)", "Charging duration (minutes)","Session idle (minutes)", "kWh delivered",\
#     "SoC Start","SoC End","User", "Vehicle", "EVSE Status", \
#     "Serial #", \
#     "Space #", "Site", \
#     "Cost to site", "Cost to driver", "Fleet", "Vehicle barcode", "Minutes available", "Miles needed", "Energy needed", "Energy unit", "Wh per mile"]
# =============================================================================
    
ColumnNames_appen = [\
    "10-digit UID", \
    "Session start", "Session end", "Session duration (minutes)", "Charging duration (minutes)","Session idle (minutes)", "kWh delivered",\
    "SoC Start","SoC End","User", "Vehicle", "EVSE Status", \
    "Serial #", \
    "Parking Space", "Site", \
    "Cost to site", "Cost to driver", "Fleet", "Vehicle barcode", "Minutes available", "Miles needed", "Energy needed", "Energy unit", "Wh per mile"]    
    
data_Sessions_appen = data_Sessions_MySite_MyDates_NewInd.filter(ColumnNames_appen)




#################################################################################
# Identify the same "10-digit UID" of both Interval and Session data, and merge the Sessions and the Interval data
#################################################################################


data_Interval_MySite_aux = []
UID_missing = list()

UID_list = data_Interval_MySite_MyDates_NewInd["10-digit UID"].unique()
     
for ind in range(len(UID_list)):       
#ind = 0    #test with one iteration
    
    UID = UID_list[ind]    
    data_Sessions_ThisUID = data_Sessions_appen[data_Sessions_appen['10-digit UID'] == UID]
    
    if data_Sessions_ThisUID.empty is True:        
        UID_missing.append(UID) 
            
    data_Interval_ThisUID = data_Interval_MySite_MyDates_NewInd[data_Interval_MySite_MyDates_NewInd["10-digit UID"] == UID]    
    data_Interval_MySite_merge = pd.merge(data_Interval_ThisUID, data_Sessions_ThisUID, on='10-digit UID')    
    data_Interval_MySite_aux = data_Interval_MySite_merge.append(data_Interval_MySite_aux, ignore_index=True)    
    
data_Interval_MySite_aux_flip = data_Interval_MySite_aux.iloc[::-1]






EventNumb_Interval = data_Interval['10-digit UID'].unique() 
EventNumb_Sessions = data_Sessions['10-digit UID'].unique()
EventNumb_Merge = data_Interval_MySite_aux_flip['10-digit UID'].unique()
# Interval: 19, 867; Sessions: 20,178; Merge: 19,860
#################################################################################
#################################################################################
# Write the merged data to .csv file
#################################################################################


from pathlib import Path  
#filepath = Path('C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Interval_aux/out.csv')  
dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Merge_aux")
filepath = Path(dir_Output + '/UCSD_' + MySite_str + '_Merge'+ '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '_v3.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
data_Interval_MySite_aux_flip.to_csv(filepath,index=False)


# =============================================================================
# from pathlib import Path  
# 
# #filepath = Path('C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Interval_aux/out.csv')  
# dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_Pr4F_UCSD/Merge_aux")
# filepath = Path(dir_Output + '/UCSD_' + MySite_str + '_Merge'+ '_' + TheDate_Start_str + '_' + TheDate_End_str + '.csv')  
# filepath.parent.mkdir(parents=True, exist_ok=True)  
# data_Interval_MySite_aux_flip.to_csv(filepath,index=False)
# =============================================================================




#################################################################################
# Concate two Merge data 
#################################################################################


filename_Input =dir_Output + '/UCSD_AllSites_Merge_20210504_20220928.csv'
Merge1= pd.read_csv(filename_Input)
Merge1 = Merge1.rename(columns={'Space #': 'Parking Space'}) # PF decided to chance the column name... 2019/01/29

Merge2 = data_Interval_MySite_aux_flip

Merge3 = Merge1.append(Merge2, ignore_index=True) 

Merge4 = Merge3.drop_duplicates(subset=['10-digit UID','Interval start'])

filepath = Path(dir_Output + '/UCSD_AllSites_Merge_20210504_20230129.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Merge4.to_csv(filepath,index=False)


#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))

