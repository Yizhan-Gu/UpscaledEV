# -*- coding: utf-8 -*-
"""
Created on Mon Oct 14 09:32:18 2024

@author: Anne
"""


import os.path
import pandas as pd
from datetime import datetime
from pathlib import Path  

dir_Input = os.path.join('C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/')

CarInfo_2024 = pd.read_csv(dir_Input +'model_year_2024_vehicles_clean.csv')


#data_Sessions = pd.read_csv(dir_Input +'UCSD_AllSites_Sessions_wCarInfo_20210501_20240930.csv')
data_Sessions = pd.read_csv(dir_Input +'UCSD_AllSites_Sessions_20240101_20240930.csv')
data_Sessions = data_Sessions.rename(columns={'Session Start': 'Session start', \
                              'Session End': 'Session end' })


SessionStart_datetime = pd.to_datetime(data_Sessions['Session start'])
SessionEnd_datetime = pd.to_datetime(data_Sessions['Session end']) 

TheDate_Start = datetime(2024, 1, 1)
TheDate_End = datetime(2024, 10, 1)


data_Sessions_2024 = data_Sessions[(TheDate_Start <= SessionStart_datetime) & (SessionStart_datetime <= TheDate_End) \
                                                & (TheDate_Start <= SessionEnd_datetime) & (SessionEnd_datetime <= TheDate_End) ]
    
    
Vehicle_session_unique = data_Sessions_2024['Vehicle'].unique()
Vehicle_session_unique = Vehicle_session_unique[1:]


Vehicle_year = []
Vehicle_Make = []
Vehicle_Model = []

for i in range(len(Vehicle_session_unique)):
    Vehicle_year = Vehicle_year + [Vehicle_session_unique[i][0:4]]
    
    Vehicle_Make_ThisCar = Vehicle_session_unique[i][4:].split(' ')[1]
    Vehicle_Make = Vehicle_Make + [Vehicle_Make_ThisCar]
    
    Vehicle_Model = Vehicle_Model + [Vehicle_session_unique[i][4:].split(Vehicle_Make_ThisCar)[1]]



Car_Table_Session = pd.DataFrame({'Make':Vehicle_Make,'Model':Vehicle_Model,'Year':Vehicle_year})

Car_Table_Session = Car_Table_Session.sort_values(by=['Make','Model','Year'])
Car_Table_Session_2024 = Car_Table_Session[Car_Table_Session['Year']=='2024']

Car_Table_Web = CarInfo_2024[['Make','Model','Battery Capacity (kWh)']].sort_values(by=['Make','Model'])

filepath = Path(dir_Input + '/EV_MakeModelYear_2024_Session.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Car_Table_Session_2024.to_csv(filepath,index=False)

filepath = Path(dir_Input + '/EV_MakeModelYear_2024_Web.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Car_Table_Web.to_csv(filepath,index=False)  