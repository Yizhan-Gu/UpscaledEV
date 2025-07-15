# -*- coding: utf-8 -*-
"""
Created on Mon May 13 13:09:45 2024

@author: Anne
"""

# from IPython import get_ipython
# get_ipython().magic('reset -sf')
globals().clear()

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



# Take the known user threshold, User ID, and the current session arrival time of the user for whom we want to predict the current session plug duration and energy demand
def KnownUser(known_thres,User,test_sessions_data):
    
    #Use the current user's ID to import the user's saved data
    Data_User = pd.read_csv ('/Users/admin/Desktop/EV_program/Total Transfer/Forecasting/Driver_sessions_x/Driver_Sessions_'+str(known_thres)+'/Sessions_Data_'+str(int(User))+'.csv');
    Data_User['Session start'] = pd.to_datetime(Data_User['Session start']);
    
    
    #read the current session arrival time
    ThisSessionStart = test_sessions_data['Session start'].iloc[0]
    
    # based on arrival time, select the user data BEFORE this arrival time
    train_sessions_data = Data_User[Data_User['Session start']<ThisSessionStart]
    train_sessions_data = train_sessions_data[['Session start','Arrival Hour','Session duration (minutes)', 'kWh delivered']]

    #convert the current session arrival time to arrival hour
    test_AT = test_sessions_data['Session start'].iloc[0]
    test_arrival = test_sessions_data['Arrival Hour'].iloc[0]
    
    #setup columns of intra day and inter day distance between AT of sessions of the current user for training
    train_sessions_data["Net AT distance"] =  (test_AT-train_sessions_data['Session start']).dt.total_seconds()
    train_sessions_data["Intraday AT distance"] = abs(test_arrival-train_sessions_data['Arrival Hour'])
    Scaler = preprocessing.MinMaxScaler()
    
    train_sessions_data[["Net AT distance", "Intraday AT distance"]] = Scaler.fit_transform(train_sessions_data[["Net AT distance", "Intraday AT distance"]])
    
    #select weights to prioritize intra day and inter day distance between past sessions arrival time and current session arrival time
    w_netAT = 0.5
    w_intraAT = 0.5
    train_sessions_data["Weighted Sum"]= w_netAT * train_sessions_data["Net AT distance"]+ w_intraAT * train_sessions_data["Intraday AT distance"]
    #sort the past sessions based on their intra day and inter day distance from the current session AT
    train_sessions_data=train_sessions_data.sort_values(by='Weighted Sum', ascending=True,ignore_index=True)
    
    p_denom = 0 #denominator of p 
    for l in range(len(train_sessions_data)):
        p_denom = p_denom + 1/(l+1)
    #proportionality constant p 
    p = 1/p_denom
    
    #Assign proportionally decreasing weights to past sessions
    train_sessions_data["Weights"] = p/(train_sessions_data.index+1)
    
    #find the weighted average of the past sessions plug duration and energy demand to predict the current EV sessions's plug duration and energy demand
    plug_duration_prediction = sum(train_sessions_data['Session duration (minutes)'] * train_sessions_data["Weights"])
    energy_demand_prediction = sum(train_sessions_data['kWh delivered'] * train_sessions_data["Weights"])
    
    return [plug_duration_prediction,energy_demand_prediction]

    


# Take the unknown user current session features to predict the current session plug duration and energy demand    
def UnKnownUser(test_sessions_data):
    
    #read all sessions data from all users for all time
    Train_Data = pd.read_csv ('/Users/admin/Desktop/EV_program/Total Transfer/Forecasting/Train and Test Data_Unknown_Drivers/Train_Data.csv')
    Train_Data['Session start'] = pd.to_datetime(Train_Data['Session start'])
    
    #read the current session arrival time
    ThisSessionStart = test_sessions_data['Session start'].iloc[0]
    
    # based on current session arrival time, select the data BEFORE this arrival time
    Train_Data = Train_Data[Train_Data['Session start']<ThisSessionStart]
    
    # Choose all relevant features and labels of past session data to train the multilinear regression model        
    train_sessions_data = Train_Data[['Arrival Hour', 'Battery (kWh)','Weekday', 'Max Charging Power','Session duration (minutes)', 'kWh delivered']]    
    train_sessions_data = train_sessions_data.reset_index(drop=True)
    
    # One-hot encode the 'DayOfWeek' column
    onehot_encoder = OneHotEncoder(sparse=False)
    onehot_encoded = onehot_encoder.fit_transform(train_sessions_data['Weekday'].values.reshape(-1, 1))
    Encoded_Weekday = (pd.DataFrame(onehot_encoded, columns=onehot_encoder.get_feature_names_out(['Weekday'])))
    train_sessions_data_encoded = train_sessions_data.join(Encoded_Weekday)
    train_sessions_data_encoded.drop(['Weekday'], axis=1, inplace=True)
                
    # Labels that we want to predict: plug duration and energy demand of sessions
    y_duration_train = train_sessions_data_encoded['Session duration (minutes)']
    y_energy_train = train_sessions_data_encoded['kWh delivered']
    
    # Features that we want to use to predict the plug duration and energy demand of sessions
    X_train = train_sessions_data_encoded.drop(columns=['Session duration (minutes)', 'kWh delivered'])

    
    # Train MLG models for energy demand and plug duration
    PD_Unknown_MLG_model = LinearRegression()
    ED_Unknown_MLG_model = LinearRegression()

    PD_Unknown_MLG_model.fit(X_train, y_duration_train)
    ED_Unknown_MLG_model.fit(X_train, y_energy_train)
    

    # Set up the unknown user current session features to use the MLG model             
    test_sessions_data = test_sessions_data[['Arrival Hour', 'Battery (kWh)','Weekday', 'Max Charging Power']]
    test_sessions_data = test_sessions_data.reset_index(drop=True)
    
    # One-hot encode the 'DayOfWeek' column
    WeekdayLogic =  pd.DataFrame((pd.Series(range(7)) == test_sessions_data['Weekday'].iloc[0]).astype(int)).T
    WeekdayLogic=WeekdayLogic.rename({0: 'Weekday_0', 1: 'Weekday_1', 2: 'Weekday_2', 3: 'Weekday_3', 4: 'Weekday_4', 5: 'Weekday_5', 6: 'Weekday_6'},axis='columns')
    
    test_sessions_data_encoded = pd.concat([test_sessions_data,WeekdayLogic],axis=1)


    test_sessions_data_encoded.drop(['Weekday'], axis=1, inplace=True)
      
    X_test = test_sessions_data_encoded #.drop(columns=['Session duration (minutes)', 'kWh delivered','User'])
    
    #find the current EV sessions's plug duration and energy demand based on the MLG model
    plug_duration_prediction = PD_Unknown_MLG_model.predict(X_test)
    energy_demand_prediction = ED_Unknown_MLG_model.predict(X_test)
    
    return [plug_duration_prediction[0],energy_demand_prediction[0]]


