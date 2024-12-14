# -*- coding: utf-8 -*-
"""
ML Forecasting Known Driver

@author: avghosh
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
from datetime import datetime, timedelta,date                           #pip install dill --user
import pytz

from sklearn.cluster import KMeans
from sklearn import preprocessing
from sklearn.decomposition import PCA
from kneed import KneeLocator

from scipy.stats import norm
import statistics
from sklearn.metrics import mean_absolute_error, mean_squared_error


# from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import LSTM, Dense

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

Sessions_Table = Sessions_Table[~Sessions_Table['Session start'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Session end'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Session duration (minutes)'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['Charging duration (minutes)'].isnull()]
Sessions_Table = Sessions_Table[~Sessions_Table['kWh delivered'].isnull()]

Sessions_Table = Sessions_Table[Sessions_Table['kWh delivered']>=0.5]
Sessions_Table = Sessions_Table[Sessions_Table['Session duration (minutes)']>=15]

Sessions_Table = Sessions_Table[~Sessions_Table['User'].isnull()]

#%% Setting up Data

Sessions_Table_clean = Sessions_Table[:];

Sessions_Table_clean['Charging duration (minutes)'] = Sessions_Table_clean['Charging duration (minutes)'].astype("float");
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session duration (minutes)']-Sessions_Table_clean['Charging duration (minutes)']          
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session idle (minutes)'].astype("float");

Sessions_Table_clean['Arrival Hour'] =  Sessions_Table_clean['Session start'].dt.hour+Sessions_Table_clean['Session start'].dt.minute/60;
Sessions_Table_clean["Weekday"] = Sessions_Table_clean['Session start'].dt.dayofweek


df=Sessions_Table_clean

df = df.sample(frac=1, random_state=42).reset_index(drop=True)

# Define the percentage of data to be used for testing
test_size = 0  # 20% of the data for testing

# Calculate the number of rows for testing
num_test_rows = int(len(df) * test_size)

# Split the DataFrame into training and testing sets
train_df = df.iloc[:-num_test_rows]
#test_df = df.iloc[-num_test_rows:]

train_df.to_csv("Train_Data.csv", index=False); # export as csv
#test_df.to_csv("Test_Data.csv", index=False); # export as csv
