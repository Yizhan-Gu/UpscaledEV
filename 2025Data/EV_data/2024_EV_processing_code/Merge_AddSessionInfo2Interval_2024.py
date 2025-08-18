# -*- coding: utf-8 -*-
"""
Created on Wed Sep  7 15:35:16 2022

@author: Anne
"""
from datetime import datetime
import time
from time import process_time

import os.path
import pandas as pd
import numpy as np
from pathlib import Path 
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


#################################################################################
# Choose the 'Site' you want to analyze
#################################################################################
MySite_str = "AllSites" #choices: "AllSites", "Athena", "Gilman"




#################################################################################
# Choose the 'start date' and 'end date' you want to analyze
#################################################################################


TheDate_Start = datetime(2021, 5, 4)
TheDate_End = datetime(2024, 10, 1)

TheDate_Start_str = TheDate_Start.strftime("%Y%m%d")
TheDate_End_str = TheDate_End.strftime("%Y%m%d")




#################################################################################
# Measure the processing time with wall clock time
#################################################################################


Time_Run_Start = process_time()  




#################################################################################
# Read/Import the PowerFlex Data from the folder
#################################################################################


dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")
#"C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download"


PowerFlexData_Site = "AllSites" #'Athena', 'Gilman'
#filename_Input = r'C:\Users\Anne\Downloads\UCSD_AllSites_Interval_20220906_20220908.csv'




# Read Interval Data
#PowerFlexData_Type = "Interval" #'Sessions', 'Stations'
#PowerFlexData_DateRangeStart = "20230128"
#PowerFlexData_DateRangeEnd = "20230302"
#filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
#data_Interval= pd.read_csv(filename_Input)
data_Interval= pd.read_csv(dir_Input+'UCSD_AllSites_Interval_20210504_20240930.csv')

# Read Sessions Data
#PowerFlexData_Type = "Sessions" 
#PowerFlexData_DateRangeStart = "20230128"
#PowerFlexData_DateRangeEnd = "20230302"
#filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
#data_Sessions= pd.read_csv(filename_Input)
data_Sessions= pd.read_csv(dir_Input+'UCSD_AllSites_Sessions_wCarInfo_20210501_20240930.csv')



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

SessionStart_datetime = pd.to_datetime(data_Sessions_MySite['Session start'])
SessionEnd_datetime = pd.to_datetime(data_Sessions_MySite['Session end']) 




data_Interval_MySite_MyDates = data_Interval_MySite[(TheDate_Start <= IntervalStart_datetime) & (IntervalStart_datetime <= TheDate_End) \
                                                & (TheDate_Start <= IntervalEnd_datetime) & (IntervalEnd_datetime <= TheDate_End) ]
    
   

data_Sessions_MySite_MyDates = data_Sessions_MySite[(TheDate_Start <= SessionStart_datetime) & (SessionStart_datetime <= TheDate_End) \
                                                & (TheDate_Start <= SessionEnd_datetime) & (SessionEnd_datetime <= TheDate_End) ]
    
    
# =============================================================================
# test =pd.concat([data_Sessions_MySite_MyDates,data_Sessions_MySite]).drop_duplicates(keep=False)   
# # check the discarded data: there are session start before 2021/05/04 but since Interval data starts after 2021/05/04, all previous Session data are discarded
# test = pd.to_datetime(data_Sessions_MySite['Session start']).sort_values(ascending=True)  # 97,056 events: 2021/05/01 - 2024/09/30
# test1 = pd.to_datetime(data_Sessions_MySite_MyDates['Session start']).sort_values(ascending=True) # 97,013 events: 2021/05/04 = 2024/09/30
# =============================================================================

 
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



#ind_new = np.arange(0,count_row_Interval_MySite)
data_Interval_MySite_MyDates_NewInd = data_Interval_MySite_MyDates.copy()
#data_Interval_MySite_MyDates_NewInd = data_Interval_MySite_MyDates_NewInd.set_index(ind_new)   

#ind_new = np.arange(0,count_row_Sessions_MySite)
data_Sessions_MySite_MyDates_NewInd = data_Sessions_MySite_MyDates.copy()
#data_Sessions_MySite_MyDates_NewInd = data_Sessions_MySite_MyDates_NewInd.set_index(ind_new)


UID_list_Interval = data_Interval_MySite_MyDates_NewInd["10-digit UID"].unique() #events: 70,844
UID_list_Sessions = data_Sessions_MySite_MyDates_NewInd["10-digit UID"].unique() #events: 97,013

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
    "Cost to site", "Cost to driver", "Fleet", "Vehicle barcode", "Minutes available", "Miles needed", "Energy needed", "Energy unit", "Wh per mile",\
    'Car Year', 'Car Make', 'Car Model', 'Car Battery']    
    
data_Sessions_appen = data_Sessions_MySite_MyDates_NewInd.filter(ColumnNames_appen)




#################################################################################
# Identify the same "10-digit UID" of both Interval and Session data, and merge the Sessions and the Interval data
#################################################################################


data_Interval_MySite_aux = []
UID_missing = list()

#UID_list = data_Interval_MySite_MyDates_NewInd["10-digit UID"].unique()
     
for ind in range(len(UID_list_Interval)):       
#ind = 0    #test with one iteration
    
    UID = UID_list_Interval[ind]    
    data_Sessions_ThisUID = data_Sessions_appen[data_Sessions_appen['10-digit UID'] == UID]
    
    if data_Sessions_ThisUID.empty is True:        
        UID_missing.append(UID) 
            
    data_Interval_ThisUID = data_Interval_MySite_MyDates_NewInd[data_Interval_MySite_MyDates_NewInd["10-digit UID"] == UID]    
    data_Interval_MySite_merge = pd.merge(data_Interval_ThisUID, data_Sessions_ThisUID, on='10-digit UID')    
    data_Interval_MySite_aux = data_Interval_MySite_merge.append(data_Interval_MySite_aux, ignore_index=True)    
    
#data_Interval_MySite_aux_flip = data_Interval_MySite_aux.iloc[::-1]
data_Interval_MySite_aux_flip = data_Interval_MySite_aux.copy()





Event_Interval = data_Interval_MySite_MyDates_NewInd['10-digit UID'].unique() 
Event_Sessions = data_Sessions_MySite_MyDates_NewInd['10-digit UID'].unique()
Event_Merge = data_Interval_MySite_aux_flip['10-digit UID'].unique()
# Interval: 70,844; Sessions: 97,013; Merge: 70,808
# len(UID_missing) = 36

Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))

#################################################################################
# When did those 'UID_missing' happen?
#################################################################################


# Events in Interval data that cannot be found in Session data
Missing_Interval = data_Interval_MySite_MyDates_NewInd[data_Interval_MySite_MyDates_NewInd['10-digit UID'].isin(UID_missing)] #4,662
UID_missing_Interval = Missing_Interval['10-digit UID'].unique() #36

#only pick one time slot for each event
Missing_Interval_time = []
for i in UID_missing_Interval:
    IntervalStart_ThisEvent = Missing_Interval['Interval start'][Missing_Interval['10-digit UID']==i]
    Missing_Interval_time = Missing_Interval_time + [IntervalStart_ThisEvent.iloc[0]]

Missing_Interval_time = pd.to_datetime(Missing_Interval_time)
Missing_time = plt.hist(Missing_Interval_time) #, bins = list(np.linspace(0, 70, 71)))

# beautify the x-labels
plt.gcf().autofmt_xdate()
myFmt = mdates.DateFormatter('%Y/%m/%d')
plt.gca().xaxis.set_major_formatter(myFmt)
plt.xticks(rotation=45)
#plt.xlim(xmin, xmax)
#plt.ylim(ymin, ymax_pw)
plt.xlabel('Time [-]')
plt.ylabel('Number [-]' )





# Events in Session data that cannot be found in Interval data
Missing_Session = data_Sessions_appen[~(data_Sessions_appen['10-digit UID'].isin(list(Event_Merge)))] #26,205
UID_missing_Session = Missing_Session['10-digit UID'].unique() #26,205

Missing_Session_time = pd.to_datetime(Missing_Session['Session start'])

Missing_time = plt.hist(Missing_Session_time) #, bins = list(np.linspace(0, 70, 71)))

# beautify the x-labels
plt.gcf().autofmt_xdate()
myFmt = mdates.DateFormatter('%Y/%m/%d')
plt.gca().xaxis.set_major_formatter(myFmt)
plt.xticks(rotation=45)
#plt.xlim(xmin, xmax)
#plt.ylim(ymin, ymax_pw)
plt.xlabel('Time [-]')
plt.ylabel('Number [-]' )




#################################################################################
#################################################################################
# Write the merged data to .csv file
#################################################################################


 
#filepath = Path('C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Interval_aux/out.csv')  
dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024")
#filepath = Path(dir_Output + '/UCSD_' + MySite_str + '_Merge'+ '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '_v3.csv')  
filepath = Path(dir_Output + '/UCSD_AllSites_Merge_20210504_20240930.csv')  
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


# =============================================================================
# filename_Input =dir_Output + '/UCSD_AllSites_Merge_20210504_20220928.csv'
# Merge1= pd.read_csv(filename_Input)
# Merge1 = Merge1.rename(columns={'Space #': 'Parking Space'}) # PF decided to chance the column name... 2019/01/29
# 
# Merge2 = data_Interval_MySite_aux_flip
# 
# Merge3 = Merge1.append(Merge2, ignore_index=True) 
# 
# Merge4 = Merge3.drop_duplicates(subset=['10-digit UID','Interval start'])
# 
# filepath = Path(dir_Output + '/UCSD_AllSites_Merge_20210504_20230129.csv')  
# filepath.parent.mkdir(parents=True, exist_ok=True)  
# Merge4.to_csv(filepath,index=False)
# =============================================================================


#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))

