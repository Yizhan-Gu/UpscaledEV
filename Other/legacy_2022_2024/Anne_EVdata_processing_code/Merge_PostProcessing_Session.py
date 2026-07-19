# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 13:56:13 2022

@author: Anne
"""


#################################################################################
# Measure the processing time with wall clock time
#################################################################################


import time
from time import process_time

Time_Run_Start = process_time()  




#################################################################################
# Enter the folder path of your input file
#################################################################################


import os.path
dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Merge_aux")




#################################################################################
# Enter the folder path of you output file
#################################################################################


from pathlib import Path   
dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Merge_aux")




#################################################################################
# Enter "site", the "start date" and the "end date" of your input data file
#################################################################################


PowerFlexData_Site = "AllSites" # "AllSites", 'Athena', 'Gilman'
PowerFlexData_DateRangeStart = "20210504"
PowerFlexData_DateRangeEnd = "20230129" #"20220928"




#################################################################################
# Read/Import the PowerFlex 'Merge' Data from the folder
#################################################################################


PowerFlexData_Type = "Merge_PostProcessed" #'Sessions', 'Stations'

import pandas as pd
filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
data_Merge= pd.read_csv(filename_Input)

#data_Merge_flip = data_Merge.iloc[::-1]

EventNumb_dataMerge = data_Merge["10-digit UID"].unique()


#################################################################################
# For each event, calaulate the difference between the sum of Interval kWh and Session kWh 
# Here, assume EnergyDemand_Difference_ThisEvent > 1 be the "abnormal events"
#################################################################################


EnergyDemand_IntervalSum_list = []
EnergyDemand_Difference_list = []
AbnormalEvent_list = []
AbnormalSessionStart_list = []
data_Merge_abnormal_list = []

Events = data_Merge["10-digit UID"].unique() 
for ind_event in range(len(Events)):
    #ind_event = 0 
    EventName = Events[ind_event]
    data_Merge_ThisEvent = data_Merge[data_Merge["10-digit UID"] == Events[ind_event]] 
    EnergyDemand_Session_ThisEvent = data_Merge_ThisEvent["kWh delivered"].iloc[0]
    EnergyDemand_IntervalSum_ThisEvent = data_Merge_ThisEvent["Interval kWh"].sum()
    EnergyDemand_IntervalSum_list = EnergyDemand_IntervalSum_list + [EnergyDemand_IntervalSum_ThisEvent]
    EnergyDemand_Difference_ThisEvent = EnergyDemand_IntervalSum_ThisEvent - EnergyDemand_Session_ThisEvent 
    EnergyDemand_Difference_list = EnergyDemand_Difference_list + [EnergyDemand_Difference_ThisEvent]
    if EnergyDemand_Difference_ThisEvent > 1:
        AbnormalEvent_list = AbnormalEvent_list + [[EventName,EnergyDemand_Difference_ThisEvent]]
        AbnormalSessionStart_list = AbnormalSessionStart_list + [data_Merge_ThisEvent['Session start'].iloc[0]]
        data_Merge_ThisEvent['_Interval kWh'] = data_Merge_ThisEvent['Interval kWh']
        data_Merge_ThisEvent['_Sum Interval kWh'] = EnergyDemand_IntervalSum_ThisEvent
        data_Merge_ThisEvent['_Session kWh'] = data_Merge_ThisEvent["kWh delivered"]
        data_Merge_ThisEvent['_Difference kWh'] = EnergyDemand_Difference_ThisEvent
        
        
        data_Merge_abnormal_list = data_Merge_ThisEvent.append(data_Merge_abnormal_list, ignore_index=True) 


Abnormal_Events = data_Merge_abnormal_list["10-digit UID"].unique() 

# Take the start of the session for each charging event
data_Merge_abnormal_list_UniqueEvent = data_Merge_abnormal_list[data_Merge_abnormal_list['Interval ID']==1]

Abnormal_Session_kWh_list = data_Merge_abnormal_list_UniqueEvent["_Session kWh"]





#################################################################################
# Plot histogram of EnergyDemand_Difference_list
#################################################################################


import matplotlib.pyplot as plt
import numpy as np
#import matplotlib.ticker as ticker


ax1 = plt.hist(EnergyDemand_Difference_list, bins = list(np.linspace(-10, 10, 21)), density=True)
#plt.title('Discrepency of Session Energy Demand', fontsize = 12)
plt.xlabel('Discrepancy of Energy Demand [kWh]')
plt.ylabel('Probability [-]' )




#################################################################################
# Plot histogram of EnergyDemand_Difference_list within [-1,1]
#################################################################################


ax1_2 = plt.hist(EnergyDemand_Difference_list, bins = list(np.linspace(-0.02, 0.02, 21)))
#plt.title('Discrepency of Session Energy Demand', fontsize = 12)
plt.xlabel('Discrepancy of Energy Demand [kWh]')
plt.ylabel('Number [-]' )


    

#################################################################################
#################################################################################
# Analysis of "Abnormal data"
#################################################################################
#################################################################################


    #################################################################################
    # Plot histogram of "Session start" from AbnormalSessionStart_list
    #################################################################################


TimeList = pd.to_datetime(AbnormalSessionStart_list).sort_values(ascending=True)
t_start = pd.datetime(TimeList[0].year,TimeList[0].month,1)
t_end = pd.datetime(TimeList[-1].year,TimeList[-1].month,30)
numb_month = (TimeList[-1].year - TimeList[0].year)*12 + (TimeList[-1].month - TimeList[0].month) + 1

from dateutil.relativedelta import relativedelta

t_list = []
for i in range(numb_month+1):
    # i = 0
    t_list = t_list + [t_start + relativedelta(months=i)]



#ax2 = plt.hist( pd.to_datetime(AbnormalSessionStart_list), density=True)
#ax2 = plt.hist( pd.to_datetime(AbnormalSessionStart_list))
ax2 = plt.hist( pd.to_datetime(AbnormalSessionStart_list), bins = t_list)
plt.xlabel('Session start of abnormal data [kWh]')
#plt.ylabel('Probability [-]' )
plt.ylabel('Number [-]' )


import matplotlib.dates as mdates
# beautify the x-labels
plt.gcf().autofmt_xdate()
myFmt = mdates.DateFormatter('%Y/%m')
plt.gca().xaxis.set_major_formatter(myFmt)
plt.xticks(rotation=45)
        



    #################################################################################
    # Plot histogram of "Session kWh" from AbnormalSessionStart_list
    #################################################################################


import numpy as np
import matplotlib.pyplot as plt
#ax1_abnormal = plt.hist(EnergyDemand_Difference_list, bins = list(np.linspace(-0.02, 0.02, 21)))
ax1_abnormal = plt.hist(Abnormal_Session_kWh_list, bins = list(np.linspace(0, 70, 71)))

plt.xlabel('Session Energy Demand [kWh]')
plt.ylabel('Number [-]' )




    #################################################################################
    # Plot the ratio of # abnormal events / # total events for each month
    #################################################################################
    
    
# total events for each month
TimeList =  pd.to_datetime(data_Merge['Session start']).sort_values(ascending=True)
t_start = pd.datetime(TimeList.iloc[0].year,TimeList.iloc[0].month,1)
t_end = pd.datetime(TimeList.iloc[-1].year,TimeList.iloc[-1].month,30)

numb_month = (TimeList.iloc[-1].year - TimeList.iloc[0].year)*12 + (TimeList.iloc[-1].month - TimeList.iloc[0].month) + 1

from dateutil.relativedelta import relativedelta

t_list = []
Numb_Events_list = []  
Numb_Events_abnormal_list = []  

for i in range(numb_month):
    # i = 0   
    t_list = t_list + [t_start + relativedelta(months=i)]
    Start_ThisMonth = t_start + relativedelta(months=i)
    End_ThisMonth = Start_ThisMonth + relativedelta(months=1)
    data_Merge_ThisMonth = data_Merge[(Start_ThisMonth <= pd.to_datetime(data_Merge['Session start'])) & \
                                       (pd.to_datetime(data_Merge['Session start'])< End_ThisMonth)]
    Numb_Events = len(data_Merge_ThisMonth["10-digit UID"].unique())
    Numb_Events_list = Numb_Events_list + [Numb_Events]
        
    # abnormal events  for each month  
    data_Merge_abnormal_ThisMonth = data_Merge_abnormal_list[(Start_ThisMonth <= pd.to_datetime(data_Merge_abnormal_list['Session start'])) & \
                                       (pd.to_datetime(data_Merge_abnormal_list['Session start'])< End_ThisMonth)]
    Numb_Events_abnormal = len(data_Merge_abnormal_ThisMonth["10-digit UID"].unique())
    Numb_Events_abnormal_list = Numb_Events_abnormal_list + [Numb_Events_abnormal]
    
    
Numb_Events_abnormal_ratio_list = np.array(Numb_Events_abnormal_list)/np.array(Numb_Events_list)

import matplotlib.pyplot as plt
AbnormalEventRatio, = plt.plot(t_list, Numb_Events_abnormal_ratio_list,   linestyle='-', linewidth=2)
plt.xlabel('Time [-]')
plt.ylabel('# Abnormal Events / # All Events [-]')


import matplotlib.dates as mdates
# beautify the x-labels
plt.gcf().autofmt_xdate()
myFmt = mdates.DateFormatter('%Y/%m')
plt.gca().xaxis.set_major_formatter(myFmt)
plt.xticks(rotation=45)

plt.show()

 
    
    
#################################################################################
#################################################################################
# Further analysis of different groups in "Abnormal data"
#################################################################################
#################################################################################


    #################################################################################
    # Seperate data_Merge_abnormal_list into different catagories (could overlap)
    #################################################################################    
    

# Catagory 1: Abnormal events including No data available
data_Merge_abnormal_NoDataAvailable = data_Merge_abnormal_list[data_Merge_abnormal_list["Interval max demand kW"] =="No data available"]
Abnormal_Events_NoDataAvailable = data_Merge_abnormal_NoDataAvailable["10-digit UID"].unique()



# Catagory 2: Abnormal events including Session energy demand < 1 kWh
data_Merge_abnormal_Session_kWh_Below1 = data_Merge_abnormal_list[data_Merge_abnormal_list["_Session kWh"] < 1]
Abnormal_Events_Session_kWh_Below1 = data_Merge_abnormal_Session_kWh_Below1["10-digit UID"].unique()

Abnormal_Events_Not1 =  [x for x in Abnormal_Events if x not in Abnormal_Events_NoDataAvailable]
Abnormal_Events_Not1Not2 = [x for x in Abnormal_Events_Not1 if x not in Abnormal_Events_Session_kWh_Below1]


data_Merge_abnormal_list_Not1Not2 = data_Merge_abnormal_list[data_Merge_abnormal_list["10-digit UID"].isin(Abnormal_Events_Not1Not2)]


# Catagory 3: Not in above two catagories, (sum of interval kWh - Session kWh) > 5 kWh
data_Merge_abnormal_list_Not1Not2_DiffAbove5 = data_Merge_abnormal_list_Not1Not2[data_Merge_abnormal_list_Not1Not2["_Difference kWh"] > 5]

Abnormal_Events_Not1Not2_DiffAbove5 = data_Merge_abnormal_list_Not1Not2_DiffAbove5["10-digit UID"].unique()


    #################################################################################
    # Histogram of data_Merge_abnormal_list_Not1Not2_DiffAbove5 (Catagory 3)
    # Session start
    #################################################################################


TimeList = pd.to_datetime(data_Merge_abnormal_list_Not1Not2_DiffAbove5['Session start']).sort_values(ascending=True)
t_start = pd.datetime(TimeList.iloc[0].year,TimeList.iloc[0].month,1)
t_end = pd.datetime(TimeList.iloc[-1].year,TimeList.iloc[-1].month,30)
numb_month = (TimeList.iloc[-1].year - TimeList.iloc[0].year)*12 + (TimeList.iloc[-1].month - TimeList.iloc[0].month) + 1




import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta

t_list = []
for i in range(numb_month+1):
    # i = 0
    t_list = t_list + [t_start + relativedelta(months=i)]

ax2 = plt.hist( pd.to_datetime(data_Merge_abnormal_list_Not1Not2_DiffAbove5['Session start']), bins = t_list)
plt.xlabel('Session start of abnormal data, Not1Not2_DiffAbove5 [kWh]')
plt.ylabel('Number [-]' )


import matplotlib.dates as mdates
# beautify the x-labels
plt.gcf().autofmt_xdate()
myFmt = mdates.DateFormatter('%Y/%m')
plt.gca().xaxis.set_major_formatter(myFmt)
plt.xticks(rotation=45)



    #################################################################################
    # Histogram of data_Merge_abnormal_list_Not1Not2_DiffAbove5
    # Chargers (XB address)
    # Not finished---- 2022/11/15
    #################################################################################


# =============================================================================
# # Create a charger list with shorter names
# ChargerAndSite = data_Merge_abnormal_list_Not1Not2_DiffAbove5[['XB Address','Site']]
# ChargerAndSite = ChargerAndSite.replace('Athena Garage','Athena')
# ChargerAndSite = ChargerAndSite.replace('UCSD Gilman Parking Structure','Gilman')
# 
# 
# StationName_list = []
# for ind in range(len(ChargerAndSite)):
#     # ind = 7687
#     StationName = ChargerAndSite['Site'].iloc[ind] + '_' + str(ChargerAndSite['XB Address'].iloc[ind])
#     StationName_list = StationName_list +   [StationName]
# 
# 
# import numpy as np
# StationName_list_uni = np.unique(np.array(StationName_list))
# Chargers_ind = list(range(1,len(StationName_list_uni)+1))
# 
# 
# 
# ax2 = plt.hist( data_Merge_abnormal_list_Not1Not2_DiffAbove5['XB Address'])
# plt.xlabel('SXB Address, Not1Not2_DiffAbove5 [-]')
# plt.ylabel('Number [-]' )
# 
# =============================================================================




#################################################################################
#################################################################################
# Results of all analysis:
    # # Abnormal data / # all data = 1,436 / 19,860
    # Within all abnormal data, 
    # event in group 1 (event include "No data available"): 195
    # event in group 2 (Session kWh < 1 kWh): 119
    # event in group 3 (Discrepancy > 5 kWh): 353
    # event not group 1 or 2: 1,127
    # event in group 4 (not group 1, 2, or 3): 774 
# group 4 is the majority of the abnormal data, 
# conclusion: cannot find the reason causing the discrepancy for most abnormal data
# action: revise the session data based on the interval data (for all data)
# input: Merge_PostProcessed; output: Merge_PostProcessed2
#################################################################################
#################################################################################


data_Merge_2 = data_Merge
AbnormalSessionStart_list = []
data_Merge_abnormal_list = []

Event_DontMatch = []

Events = data_Merge_2["10-digit UID"].unique() 
for ind_event in range(len(Events)):
    #ind_event = 0 
         
    data_Merge_2_ThisEvent = data_Merge_2[data_Merge_2["10-digit UID"] == Events[ind_event]] 
    #teste = data_Merge_2_ThisEvent["Interval kWh"].sum() 
    #test1 = data_Merge_2_ThisEvent["kWh delivered"].iloc[0]
    if data_Merge_2_ThisEvent["Interval kWh"].sum() - data_Merge_2_ThisEvent["kWh delivered"].iloc[0] != 0:
        Event_DontMatch = Event_DontMatch + [Events[ind_event]]        
        data_Merge_2["kWh delivered"][data_Merge_2["10-digit UID"]== Events[ind_event]] = data_Merge_2_ThisEvent["Interval kWh"].sum()
    
    
Event_DontMatch_unique =  np.unique(np.array(Event_DontMatch)) #13,619

#################################################################################
# Write the Merge_PostProcessed2 data to .csv file
#################################################################################


filepath = Path(dir_Output + '/UCSD_' + PowerFlexData_Site + '_Merge'+ '_PostProcessed2_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
data_Merge_2.to_csv(filepath,index=False)




#################################################################################
# Read/Import the Session Data, fix the session kWh, and output the Session2 Data
# Notes:
    # Events_data_Sessions = 20,178
    # Events_data_Interval = 19,867
    # Events (Merge) = 19,860
#################################################################################


dir_Input2 = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download/")
filename_Input2 = dir_Input2 + 'UCSD_AllSites_Sessions_20220627_20230129.csv'
data_Sessions= pd.read_csv(filename_Input2)

dir_Input3 = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download/")
filename_Input3 = dir_Input2 + 'UCSD_AllSites_Interval_20220925_20230129.csv'
data_Interval= pd.read_csv(filename_Input3)


Events_data_Sessions = data_Sessions["10-digit UID"].unique() 
Events_data_Interval = data_Interval["10-digit UID"].unique() 

data_Sessions2 = data_Sessions[data_Sessions["10-digit UID"].isin(Events)]


for ind_event in range(len(Events)):
    #ind_event = 0 
    EnergyDemand_ThisSession =  data_Merge_2["kWh delivered"][data_Merge_2["10-digit UID"] == Events[ind_event]]
    data_Sessions2["kWh delivered"][data_Sessions2["10-digit UID"] == Events[ind_event]]  = EnergyDemand_ThisSession.iloc[0]




#################################################################################
# Write the data_Sessions2 data to .csv file
#################################################################################


dir_Output2 = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Download/")
filepath2 = Path(dir_Output2 + 'UCSD_AllSites_Sessions2_20220925_20230129.csv')         #20928.csv')  
filepath2.parent.mkdir(parents=True, exist_ok=True)  
data_Sessions2.to_csv(filepath2,index=False)




#################################################################################
# Concate two Session2 data 
#################################################################################


filename_Input =dir_Output2 + '/UCSD_AllSites_Sessions2_20210504_20220928.csv'
Session2_1= pd.read_csv(filename_Input)
Session2_1 = Session2_1.rename(columns={'Space #': 'Parking Space'}) # PF decided to chance the column name... 2029/01/29

#Session2_2 = data_Sessions2

filename_Input =dir_Output2 + '/UCSD_AllSites_Sessions2_20220925_20230129.csv'
Session2_2= pd.read_csv(filename_Input)


Session2_3 = Session2_1.append(Session2_2, ignore_index=True) 

Session2_4 = Session2_3.drop_duplicates(subset=['10-digit UID'])
Session2_4['Session start']= pd.to_datetime(Session2_4['Session start']) # Convert to datetime 
Session2_4 = Session2_4.sort_values(by=['Session start'])

filepath = Path(dir_Output2 + '/UCSD_AllSites_Sessions2_20210504_20230129.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Session2_4.to_csv(filepath,index=False)



#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))



