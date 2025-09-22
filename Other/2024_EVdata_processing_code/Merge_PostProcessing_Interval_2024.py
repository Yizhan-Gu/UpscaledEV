# -*- coding: utf-8 -*-
"""
Created on Mon Oct 24 21:50:38 2022

@author: Anne
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
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
dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")




#################################################################################
# Enter the folder path of you output file
#################################################################################


from pathlib import Path   
dir_Output = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")




#################################################################################
# Enter "site", the "start date" and the "end date" of your input data file
#################################################################################


PowerFlexData_Site = "AllSites" # "AllSites", 'Athena', 'Gilman'
PowerFlexData_DateRangeStart = "20210504"
PowerFlexData_DateRangeEnd = "20240930" #"20220928"




#################################################################################
# Read/Import the PowerFlex 'Merge' Data from the folder
#################################################################################


PowerFlexData_Type = "Merge" #'Sessions', 'Stations'

import pandas as pd
filename_Input = dir_Input + '/UCSD_' + PowerFlexData_Site + '_' + PowerFlexData_Type + '_' + PowerFlexData_DateRangeStart + '_' + PowerFlexData_DateRangeEnd + '.csv'
data_Merge= pd.read_csv(filename_Input)

data_Merge_flip = data_Merge.iloc[::-1]



#################################################################################
# Report all the events with "No data available"
#################################################################################


data_Merge_NoDataAvailable = data_Merge_flip[data_Merge_flip["Interval kWh"]=="No data available"]
Events_NoDataAvailable = data_Merge_NoDataAvailable["10-digit UID"].unique() #695




#################################################################################
# Interval data of all the events with "No data available"
#################################################################################


data_Merge_NoDataAvailable_ = data_Merge_flip[data_Merge_flip["10-digit UID"].isin(Events_NoDataAvailable)]




#################################################################################
# Case 1: For column "Interval kWh", a series of "No data available" is followed by a positive value
# Solution:
# In the for loop (for each event with "No data available"), 
# count the number of "No data available" in column "Interval kWh"
# and if the next "Interval kWh" after the last "No data available" is positive, 
# redistribute that "Interval kWh" thru all time slots with "No data available" and that "Interval kWh"
#################################################################################


data_Merge_NoDataAvailable_new = []
numb_FollowedByPos = 0  #497
Event_FollowedByPos = [] 

for i in range(len(Events_NoDataAvailable)):
    #i = 1
    ThisEvent = Events_NoDataAvailable[i]
    data_Merge_NoDataAvailable_ThisEvent = data_Merge_NoDataAvailable_[data_Merge_NoDataAvailable_["10-digit UID"]==ThisEvent]
    numb_row_ThisEvent = data_Merge_NoDataAvailable_ThisEvent.shape[0]  # Gives number of rows
    count = 0
    for j in range(numb_row_ThisEvent-1):
        # j = 0
        if data_Merge_NoDataAvailable_ThisEvent["Interval kWh"].iloc[j] == "No data available":
            if data_Merge_NoDataAvailable_ThisEvent["Interval kWh"].iloc[j+1] == "No data available":
                count = count + 1
            elif float((data_Merge_NoDataAvailable_ThisEvent["Interval kWh"].iloc[j+1])) >= 0:
                numb_FollowedByPos = numb_FollowedByPos + 1
                Event_FollowedByPos = Event_FollowedByPos + [ThisEvent]
                numb_NoDataAvailable = count+2
                numb_Accumulated_kWh = float(data_Merge_NoDataAvailable_ThisEvent["Interval kWh"].iloc[j+1])
                data_Merge_NoDataAvailable_ThisEvent["Interval kWh"].iloc[j-count : j+1] = numb_Accumulated_kWh/numb_NoDataAvailable
                count_final = count
                count = 0

    data_Merge_NoDataAvailable_new = data_Merge_NoDataAvailable_ThisEvent.append(data_Merge_NoDataAvailable_new, ignore_index=True)

import numpy as np
Event_FollowedByPos_unique = np.unique(np.array(Event_FollowedByPos)) #393

#################################################################################
# Case 2: For column "Interval kWh", a series of "No data available" is followed by a non positive value
#         or the charging event ends with "No data available"
# Solution: Replace all "No data available" with zero
#################################################################################

data_Merge_NoDataAvailable_new_ = data_Merge_NoDataAvailable_new[data_Merge_NoDataAvailable_new["Interval kWh"]=="No data available"]
Event_FollowedByNoData = data_Merge_NoDataAvailable_new_['10-digit UID'].unique() #323


data_Merge_NoDataAvailable_new["Interval kWh"][data_Merge_NoDataAvailable_new["Interval kWh"]=="No data available"] = 0
data_Merge_NoDataAvailable_new["Interval kWh"] = data_Merge_NoDataAvailable_new["Interval kWh"].astype(float)


Event_FollowedByNeg = data_Merge_NoDataAvailable_new['10-digit UID'][data_Merge_NoDataAvailable_new["Interval kWh"] <0] #62
Event_FollowedByNeg_unique = np.unique(np.array(Event_FollowedByNeg)) #181
data_Merge_NoDataAvailable_new["Interval kWh"][data_Merge_NoDataAvailable_new["Interval kWh"]<0] = 0



#################################################################################
#Combine the processed interval data with "No data available" with the rest interval data
# i.e., the interval data with events not containing "No data available"
#################################################################################


data_Merge_Rest = data_Merge_flip[~data_Merge_flip["10-digit UID"].isin(Events_NoDataAvailable)]
data_Merged_Processed = data_Merge_Rest.append(data_Merge_NoDataAvailable_new, ignore_index=True)





# Discard intervals with 'Interval kWh'=='-'
data_Merged_Processed = data_Merged_Processed[data_Merged_Processed['Interval kWh']!='-']           #1,797,873 --> #1,713,105


# Replace negative values with zeros
data_Merged_Processed["Interval kWh"] = data_Merged_Processed["Interval kWh"].to_numpy(dtype=float)


#test =data_Merged_Processed["Interval kWh"][data_Merged_Processed["Interval kWh"] <0]
#test1 =  data_Merged_Processed['10-digit UID'][data_Merged_Processed["Interval kWh"] <0]
Event_Processed_below0_unique = np.unique(np.array(data_Merged_Processed['10-digit UID'][data_Merged_Processed["Interval kWh"] <0])) #4,905

data_Merged_Processed["Interval kWh"] = data_Merged_Processed["Interval kWh"].clip(lower=0)





# Cap values under 3 kWh ---> changed to 4.16. 2023/01/29
# Tesla station: 80 A * 208 V = 16.64 kW ---> 4.16 kWh per 15 mins
#test =data_Merged_Processed["Interval kWh"][data_Merged_Processed["Interval kWh"] >3]
#test1 =  data_Merged_Processed['10-digit UID'][data_Merged_Processed["Interval kWh"] >3] #458
Event_Processed_above3_unique = np.unique(np.array(data_Merged_Processed['10-digit UID'][data_Merged_Processed["Interval kWh"] > 4.16])) #697

data_Merged_Processed["Interval kWh"] = data_Merged_Processed["Interval kWh"].clip(upper=4.16)




#################################################################################
# What are the discarded data?
#################################################################################


UID_old = data_Merge['10-digit UID'].unique() #70,808
UID_new = data_Merged_Processed['10-digit UID'].unique() #69,844

UID_discard = pd.Series(UID_old)[~(pd.Series(UID_old).isin(list(UID_new)))] #964

data_disgard = data_Merge[data_Merge['10-digit UID'].isin(list(UID_discard))]

UID_discard_time = []
for i in UID_discard:
    IntervalStart_ThisEvent = data_disgard['Interval start'][data_disgard['10-digit UID']==i]
    UID_discard_time = UID_discard_time + [IntervalStart_ThisEvent.iloc[0]]

UID_discard_time = pd.to_datetime(UID_discard_time)
discard_time = plt.hist(UID_discard_time) #, bins = list(np.linspace(0, 70, 71)))

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
# Write the post processed Merge data to .csv file
#################################################################################


filepath = Path(dir_Output + 'UCSD_AllSites_Merge_PostProcessedInterval_20210504_20240930.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
data_Merged_Processed.to_csv(filepath,index=False)










#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))