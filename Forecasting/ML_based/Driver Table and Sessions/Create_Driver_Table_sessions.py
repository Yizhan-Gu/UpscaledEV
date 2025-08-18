# -*- coding: utf-8 -*-
"""
Created on Tue Feb 13 13:56:43 2024

@author: Avik Ghosh
"""
from IPython import get_ipython
get_ipython().magic('reset -sf')

import os
os.system('clear')

import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns

import math
import time
from time import process_time
from datetime import datetime, timedelta                           #pip install dill --user
import pytz

from sklearn.cluster import KMeans
from sklearn import preprocessing
from sklearn.decomposition import PCA
from kneed import KneeLocator

from scipy.stats import norm
import statistics

start_time = time.time()

"""""""""""""""""""""""""""""""""""""""READ SESSIONS DATA HERE"""""""""""""""""""""""""""""""""
#%%

Sessions_Table = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Past_Data/PF_UCSD_20210504_20230129_Sessions.csv');

Sessions_Table['Session start'] = pd.to_datetime(Sessions_Table['Session start']);
Sessions_Table['Session end'] = pd.to_datetime(Sessions_Table['Session end']);
Sessions_Table=Sessions_Table[Sessions_Table['Session start'].dt.date == Sessions_Table['Session end'].dt.date]
Sessions_Table['Session duration (minutes)']=(Sessions_Table['Session end'] - Sessions_Table['Session start']).dt.total_seconds()/60


Sessions_Table['Session duration (minutes)'] = Sessions_Table['Session duration (minutes)'].astype("float");
Sessions_Table['kWh delivered'] = Sessions_Table['kWh delivered'].astype("float");
Sessions_Table = Sessions_Table[~((Sessions_Table["Session duration (minutes)"] < 30) & (Sessions_Table["kWh delivered"] < 1))]
Sessions_Table = Sessions_Table[~((Sessions_Table["Charging duration (minutes)"] == 0) & (Sessions_Table["kWh delivered"] > 0))]

Sessions_Table.loc[Sessions_Table['Battery (kWh)'] == 'no data', 'Battery (kWh)'] = float("nan") ## has nan
Sessions_Table['Battery (kWh)'] = Sessions_Table['Battery (kWh)'].astype("float");

Sessions_Table = Sessions_Table[~Sessions_Table['Battery (kWh)'].isnull()]
Sessions_Table = Sessions_Table[Sessions_Table['Battery (kWh)']>0]

Sessions_Table = Sessions_Table[~Sessions_Table['EVSE type'].isnull()]
Sessions_Table["Max Charging Power"] = 0
Sessions_Table.loc[Sessions_Table['EVSE type'] == 'Tesla', 'Max Charging Power'] = 4.16*4 ## has nan
Sessions_Table.loc[Sessions_Table['EVSE type'] != 'Tesla', 'Max Charging Power'] = 1.664*4 ## has nan
Sessions_Table = Sessions_Table[Sessions_Table['Max Charging Power']>0]

Sessions_Table = Sessions_Table[~Sessions_Table['User'].isnull()]

Sessions_Table = Sessions_Table[~Sessions_Table['Session start'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Session end'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Session duration (minutes)'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Charging duration (minutes)'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['kWh delivered'].isnull()]

Sessions_Table = Sessions_Table[Sessions_Table['kWh delivered']>=0.5]
Sessions_Table = Sessions_Table[Sessions_Table['Session duration (minutes)']>=15]
#%% Setting up Data

Sessions_Table_clean = Sessions_Table;

Sessions_Table_clean['Charging duration (minutes)'] = Sessions_Table_clean['Charging duration (minutes)'].astype("float");
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session duration (minutes)']-Sessions_Table_clean['Charging duration (minutes)']          
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session idle (minutes)'].astype("float");

#%%  Sorting out by drivers

Unique_user = pd.unique(Sessions_Table_clean["User"])
Driver_Table = pd.DataFrame()

for i in range(len(Unique_user)):

    driver_id = Unique_user[i];
    Session_Past_User = Sessions_Table_clean[Sessions_Table_clean["User"]==driver_id];
    Session_Past_User=Session_Past_User.sort_values(by='Session start', ascending=False,ignore_index=True)
    
    First_arrival = Session_Past_User['Session start'][len(Session_Past_User)-1]
    Last_arrival = Session_Past_User['Session start'][0]
    TotSession = len(Session_Past_User)
    Weeks = max((Last_arrival-First_arrival).days/7,1)
    
    vehicle_battery_capacity = Session_Past_User['Battery (kWh)'].mean()
    TotEnergy =  Session_Past_User['kWh delivered'].sum()
    TotCharDuration = Session_Past_User['Charging duration (minutes)'].sum()/60
    SessionPerWeek = TotSession/Weeks;
    EnergyPerSession = Session_Past_User['kWh delivered'].mean()
    EnergyPerSessionOverBattery =  (Session_Past_User['kWh delivered']/Session_Past_User['Battery (kWh)']).mean()
    AvgArrivalHr = (Session_Past_User['Session start'].dt.hour+Session_Past_User['Session start'].dt.minute/60).mean()
    AvgDepartureHr = (Session_Past_User['Session end'].dt.hour+Session_Past_User['Session end'].dt.minute/60).mean()
    AvgLayoverHr = Session_Past_User['Session duration (minutes)'].mean()/60
    AvgCharHour = Session_Past_User['Charging duration (minutes)'].mean()/60
    AvgIdleHour =  Session_Past_User['Session idle (minutes)'].mean()/60
    AvgCharPow = Session_Past_User['Max Charging Power'].mean()
    
    temp_d = {'driver_id': driver_id, 'vehicle_battery_capacity': vehicle_battery_capacity, 'TotSession': TotSession,
              'TotEnergy': TotEnergy,'TotCharDuration': TotCharDuration, 'SessionPerWeek': SessionPerWeek, 
              'EnergyPerSession':  EnergyPerSession, 'EnergyPerSessionOverBattery': EnergyPerSessionOverBattery, 
              'AvgCharPow': AvgCharPow, 
              'AvgArrivalHr': AvgArrivalHr,'AvgDepartureHr': AvgDepartureHr, 'AvgLayoverHr': AvgLayoverHr, 'AvgCharHour': AvgCharHour, 
              'AvgIdleHour': AvgIdleHour}
    
    temp = pd.DataFrame(temp_d,index=[i]) 
    Driver_Table = pd.concat([Driver_Table, temp], axis=0); 
    
Driver_Table.to_csv("Driver_Table.csv", index=False); # export as csv
