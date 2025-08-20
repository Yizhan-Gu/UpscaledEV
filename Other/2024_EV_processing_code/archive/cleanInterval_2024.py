# -*- coding: utf-8 -*-
"""
Created on Mon Oct  7 13:17:07 2024

@author: Anne
"""
import time
from time import process_time
import pandas as pd
import os.path
from pathlib import Path 
from datetime import datetime

Time_Run_Start = process_time()  




#################################################################################
# Enter the folder path of your input file
#################################################################################



dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")

Data1= pd.read_csv(dir_Input + 'UCSD_AllSites_Interval_20210504_20230118.csv')

Data2= pd.read_csv(dir_Input + 'UCSD_AllSites_Interval_20230128_20230301.csv')

Data3= pd.read_csv(dir_Input + 'UCSD_AllSites_Interval_20240101-20240930.csv')
Data3 = Data3.rename(columns={'Interval Start': 'Interval start', \
                              'Interval End': 'Interval end', \
                              'Interval KWh': 'Interval kWh', \
                              'Interval Max Demand KW': 'Interval max demand kW',\
                              'Interval Average Demand KW': 'Interval average demand kW'   })


Data12 = Data1.append(Data2)
Data123 = Data12.append(Data3)
Data123['Interval start'] = pd.to_datetime(Data123['Interval start'])


Data123_ = Data123.drop_duplicates(subset=['Interval start','10-digit UID'], keep='first', inplace=False, ignore_index=True)

#test = Data123_[(Data123_['Interval start']>=datetime(2023, 1, 1))&(Data123_['Interval start']<=datetime(2023, 1, 18))]



filepath = Path(dir_Input + 'UCSD_AllSites_Interval_20210504_20240930.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Data123_.to_csv(filepath,index=False)




#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))