#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Store sessions data driver wise

@author: avikghosh
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
from sklearn import preprocessing


from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.linear_model import LinearRegression


import joblib

"""""""""""""""""""""""""""""""""""""""READ SESSIONS DATA HERE"""""""""""""""""""""""""""""""""
#%%

Sessions_Table = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Past_Data/PF_UCSD_20210504_20230129_Sessions.csv');

User_Data = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Driver Table and Sessions/Driver_Table.csv');
User_Data=User_Data[User_Data['TotSession']>100]

Prediction_Table = pd.DataFrame()
Error_Table = pd.DataFrame()

N=100
M=100
k=0

for i in range(len(User_Data)):
    
    User = User_Data['driver_id'].iloc[i]   
    Data_User = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Driver_sessions_100/Driver_Sessions/Sessions_Data_'+str(int(User))+'.csv');
    Data_User['Session start'] = pd.to_datetime(Data_User['Session start']);

    for j in range(N,len(Data_User)):
        
        train_sessions_data = Data_User.head(j)
        train_sessions_data = train_sessions_data[['Session start','Arrival Hour','Session duration (minutes)', 'kWh delivered']]
        mean_PD_train = train_sessions_data['Session duration (minutes)'].mean()
        mean_ED_train = train_sessions_data['kWh delivered'].mean()
        
        test_sessions_data = Data_User.filter(items=[j], axis=0)
        test_sessions_data = test_sessions_data[['Session start','Arrival Hour','Session duration (minutes)', 'kWh delivered']]
        test_AT = test_sessions_data['Session start'].iloc[0]
        test_PD = test_sessions_data['Session duration (minutes)']
        test_ED = test_sessions_data['kWh delivered']
        test_arrival = test_sessions_data['Arrival Hour'].iloc[0]
        
        train_sessions_data["Net AT distance"] =  (test_AT-train_sessions_data['Session start']).dt.total_seconds()
        train_sessions_data["Intraday AT distance"] = abs(test_arrival-train_sessions_data['Arrival Hour'])
        Scaler = preprocessing.MinMaxScaler()
        
        train_sessions_data[["Net AT distance", "Intraday AT distance"]] = Scaler.fit_transform(train_sessions_data[["Net AT distance", "Intraday AT distance"]])
        
        w_netAT = 0.5
        w_intraAT = 0.5
        train_sessions_data["Weighted Sum"]= w_netAT * train_sessions_data["Net AT distance"]+ w_intraAT * train_sessions_data["Intraday AT distance"]
        train_sessions_data=train_sessions_data.sort_values(by='Weighted Sum', ascending=True,ignore_index=True)
        
        p_denom = 0 #denominator of p 
        for l in range(M):
            p_denom = p_denom + 1/(l+1)
        #proportionality constant p 
        p = 1/p_denom
        
        train_sessions_data["Weights"] = p/(train_sessions_data.index+1)
        train_sessions_data.loc[train_sessions_data['Weights'] < p/M, 'Weights'] = 0

        
        plug_duration_prediction = sum(train_sessions_data['Session duration (minutes)'] * train_sessions_data["Weights"])
        energy_demand_prediction = sum(train_sessions_data['kWh delivered'] * train_sessions_data["Weights"])
        
        PD_RBM_Loss = mean_squared_error(test_PD, [plug_duration_prediction])
        ED_RBM_Loss = mean_squared_error(test_ED, [energy_demand_prediction])
        PD_Naive_Loss = mean_squared_error(test_PD, [mean_PD_train])
        ED_Naive_Loss = mean_squared_error(test_ED, [mean_ED_train])

                                         
        
        temp_d = {'User': User, 'Training': j, 'Actual Arrival Hr': round(test_arrival,2), 'Actual PD': test_PD.iloc[0],'Predicted PD RBM': plug_duration_prediction, 'Predicted PD Naive': mean_PD_train, 
                  'Actual ED': test_ED.iloc[0],'Predicted ED RBM': energy_demand_prediction, 'Predicted ED Naive': mean_ED_train, 
                  'PD RBM Loss':PD_RBM_Loss, 'PD Naive Loss':PD_Naive_Loss, 'ED RBM Loss':ED_RBM_Loss, 'ED Naive Loss':ED_Naive_Loss}
        
        temp = pd.DataFrame(temp_d,index=[k]) 
        Prediction_Table = pd.concat([Prediction_Table, temp], axis=0);
        k=k+1
        
    print(i)
    
Prediction_Table.to_csv("Prediction_Table.csv", index=False); # export as csv

#%%                   PRINTING
        
unique_training = pd.unique(Prediction_Table["Training"])    

minimum_training = min(unique_training)
maximum_training = max(unique_training)    
k=0
for j in range(minimum_training,maximum_training):
    
    Training_Data = Prediction_Table[Prediction_Table["Training"] == j]
    
    Mean_RBM_PD_Loss = round(Training_Data["PD RBM Loss"].mean())
    Mean_RBM_ED_Loss = round(Training_Data["ED RBM Loss"].mean(),2)
    Mean_Naive_PD_Loss = round(Training_Data["PD Naive Loss"].mean())
    Mean_Naive_ED_Loss = round(Training_Data["ED Naive Loss"].mean(),2)

    temp_d = {'Training': j, 'Mean PD RBM Loss':Mean_RBM_PD_Loss, 'Mean PD Naive Loss':Mean_Naive_PD_Loss, 'Mean ED RBM Loss':Mean_RBM_ED_Loss, 'Mean ED Naive Loss':Mean_Naive_ED_Loss}
     
    temp = pd.DataFrame(temp_d,index=[k]) 
    Error_Table = pd.concat([Error_Table, temp], axis=0);
    k=k+1
    
Error_Table.to_csv("Error_Table.csv", index=False); # export as csv

print(f'\nMean of mean PD RBM Training Loss: {Error_Table["Mean PD RBM Loss"].mean():.0f}')
print(f'\nMean of mean ED RBM Training Loss: {Error_Table["Mean ED RBM Loss"].mean():.0f}')
print(f'\nMean of mean PD Naive Training Loss: {Error_Table["Mean PD Naive Loss"].mean():.0f}')
print(f'\nMean of mean ED Naive Training Loss: {Error_Table["Mean ED Naive Loss"].mean():.0f}')

# fig = plt.figure(1)

# plt.plot(Error_Table["Training"],Error_Table["Mean PD RBM Loss"],color='green', linestyle = 'solid')
# plt.plot(Error_Table["Training"],Error_Table["Mean PD Naive Loss"],color='red', linestyle = 'solid')
# plt.xlabel('# Training sessions')
# plt.ylabel('Loss')
# plt.legend(["PD RBM Loss", "PD Naive Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
# plt.show()  

# fig = plt.figure(2)

# plt.plot(Error_Table["Training"],Error_Table["Mean ED RBM Loss"],color='green', linestyle = 'dashed')
# plt.plot(Error_Table["Training"],Error_Table["Mean ED Naive Loss"],color='red', linestyle = 'dashed')
# plt.xlabel('# Training sessions')
# plt.ylabel('Loss')
# plt.ylim((-5,140))
# plt.legend(["ED RBM Loss", "ED Naive Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
# plt.show()  

fig = plt.figure(3)

plt.plot(Error_Table["Training"],np.cumsum(Error_Table["Mean PD RBM Loss"])/(Error_Table["Training"]-9),color='green', linestyle = 'solid')
plt.plot(Error_Table["Training"],np.cumsum(Error_Table["Mean PD Naive Loss"])/(Error_Table["Training"]-9),color='red', linestyle = 'solid')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
plt.legend(["PD RBM CMA Loss", "PD Naive CMA Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  

fig = plt.figure(4)

plt.plot(Error_Table["Training"],np.cumsum(Error_Table["Mean ED RBM Loss"])/(Error_Table["Training"]-9),color='green', linestyle = 'dashed')
plt.plot(Error_Table["Training"],np.cumsum(Error_Table["Mean ED Naive Loss"])/(Error_Table["Training"]-9),color='red', linestyle = 'dashed')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
# plt.ylim((-5,400))
plt.legend(["ED RBM CMA Loss", "ED Naive CMA Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  