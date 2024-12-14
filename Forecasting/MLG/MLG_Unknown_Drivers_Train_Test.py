# -*- coding: utf-8 -*-
"""
MLG Forecasting Train Unknown Driver

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


from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.ensemble import RandomForestRegressor
from keras.models import load_model 
from sklearn.linear_model import LinearRegression

import joblib

start_time = time.time()

"""""""""""""""""""""""""""""""""""""""TRAINING"""""""""""""""""""""""""""""""""
#%%

Train_Data = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Train and Test Data_Unknown_Drivers/Train_Data.csv');

# Train_Data=df2 = Train_Data.head(10)
#%% MLG

# Load all features
# train_sessions_data = Train_Data[['Arrival Hour', 'Battery (kWh)', 'Max Charging Power', 'Weekday','Session duration (minutes)', 'kWh delivered']]

# Leave out weekday
# train_sessions_data = Train_Data[['Arrival Hour', 'Battery (kWh)', 'Max Charging Power','Session duration (minutes)', 'kWh delivered']]

# Leave out weekday, Max Char
# train_sessions_data = Train_Data[['Arrival Hour', 'Battery (kWh)','Session duration (minutes)', 'kWh delivered']]

# Leave out weekday, Max Char, Battery
train_sessions_data = Train_Data[['Weekday','Session duration (minutes)', 'kWh delivered']]


# One-hot encode the 'DayOfWeek' column
onehot_encoder = OneHotEncoder(sparse=False)
onehot_encoded = onehot_encoder.fit_transform(train_sessions_data['Weekday'].values.reshape(-1, 1))
Encoded_Weekday = (pd.DataFrame(onehot_encoded, columns=onehot_encoder.get_feature_names_out(['Weekday'])))
train_sessions_data_encoded = train_sessions_data.join(Encoded_Weekday)
train_sessions_data_encoded.drop(['Weekday'], axis=1, inplace=True)
            
# train_sessions_data_encoded = train_sessions_data
# X_train = past_sessions_data_encoded.drop(columns=['Weekday', 'Session start', 'Battery (kWh)', 'Max Charging Power','Session duration (minutes)', 'kWh delivered'])
X_train = train_sessions_data_encoded.drop(columns=['Session duration (minutes)', 'kWh delivered'])
y_duration_train = train_sessions_data_encoded['Session duration (minutes)']
y_energy_train = train_sessions_data_encoded['kWh delivered']

# Train Random Forest models for energy demand and plug duration
PD_Unknown_MLG_model = LinearRegression()
ED_Unknown_MLG_model = LinearRegression()

PD_Unknown_MLG_model.fit(X_train, y_duration_train)
# PD_Unknown_MLG_model.save('PD_Unknown_MLG_model.h5') 

ED_Unknown_MLG_model.fit(X_train, y_energy_train)
# ED_Unknown_MLG_model.save('ED_Unknown_MLG_model.h5') 

PD_train_loss = mean_squared_error(y_duration_train, PD_Unknown_MLG_model.predict(X_train))
ED_train_loss = mean_squared_error(y_energy_train, ED_Unknown_MLG_model.predict(X_train))

        
"""""""""""""""""""""""""""""""""""""""TESTING"""""""""""""""""""""""""""""""""
         
Test_Data = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Train and Test Data_Unknown_Drivers/Test_Data.csv');

# Load the requisite columns of test data
# test_sessions_data = Test_Data[['Arrival Hour', 'Battery (kWh)', 'Max Charging Power', 'Weekday','Session duration (minutes)', 'kWh delivered','User']]

# Leave out weekday
# test_sessions_data = Test_Data[['Arrival Hour', 'Battery (kWh)', 'Max Charging Power','Session duration (minutes)', 'kWh delivered','User']]

# Leave out weekday, Max Char
# test_sessions_data = Test_Data[['Arrival Hour', 'Battery (kWh)','Session duration (minutes)', 'kWh delivered','User']]

# Leave out weekday, Max Char, Battery
test_sessions_data = Test_Data[['Weekday','Session duration (minutes)', 'kWh delivered','User']]

onehot_encoder = OneHotEncoder(sparse=False)
onehot_encoded = onehot_encoder.fit_transform(test_sessions_data['Weekday'].values.reshape(-1, 1))

Encoded_Weekday = (pd.DataFrame(onehot_encoded, columns=onehot_encoder.get_feature_names_out(['Weekday'])))
test_sessions_data_encoded = test_sessions_data.join(Encoded_Weekday)
test_sessions_data_encoded.drop(['Weekday'], axis=1, inplace=True)
  
# test_sessions_data_encoded =  test_sessions_data         
# X_train = past_sessions_data_encoded.drop(columns=['Weekday', 'Session start', 'Battery (kWh)', 'Max Charging Power','Session duration (minutes)', 'kWh delivered'])
X_test = test_sessions_data_encoded.drop(columns=['Session duration (minutes)', 'kWh delivered','User'])
y_duration_test = test_sessions_data_encoded['Session duration (minutes)']
y_energy_test = test_sessions_data_encoded['kWh delivered']

plug_duration_prediction = PD_Unknown_MLG_model.predict(X_test)
energy_demand_prediction = ED_Unknown_MLG_model.predict(X_test)

PD_test_loss = mean_squared_error(y_duration_test, PD_Unknown_MLG_model.predict(X_test))
ED_test_loss = mean_squared_error(y_energy_test, ED_Unknown_MLG_model.predict(X_test))


"""""""""""""""""""""""""""""""""""""""PRINTING"""""""""""""""""""""""""""""""""

# print(f'\nPD Training Loss: {PD_train_loss:.0f}')
# print(f'\nED Training Loss: {ED_train_loss:.0f}')
# print(f'\nPD Test Loss: {PD_test_loss:.0f}')
# print(f'\nED Test Loss: {ED_test_loss:.0f}')
# print(f'\nPD Naive Loss: {MSE_PD_Naive:.0f}')
# print(f'\nED Naive Loss: {MSE_ED_Naive:.0f}')

from prettytable import PrettyTable
 
# These 3 are the columns of the tables
t = PrettyTable(['PD Training Loss', 'ED Training Loss', 'PD Test Loss','ED Test Loss'])
 
# To insert rows:
t.add_row([round(PD_train_loss), round(ED_train_loss), round(PD_test_loss), round(ED_test_loss)])

print(t)

