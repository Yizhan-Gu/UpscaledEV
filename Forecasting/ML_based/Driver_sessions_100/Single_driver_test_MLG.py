#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for a single driver
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
from sklearn.linear_model import LinearRegression


import joblib

User_Data = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Driver Table and Sessions/Driver_Table.csv');
User_Data=User_Data[User_Data['TotSession']>=100]

Prediction_Table = pd.read_csv ('/Users/avikghosh/Desktop/EV_Forecast_MPC/Forecasting/ML_based/Driver_sessions_100/Prediction_Table.csv');

User = User_Data['driver_id'].iloc[0]

Prediction_User = Prediction_Table[Prediction_Table["User"]==User]

print(f'\nMean PD MLG Training Loss: {Prediction_User["PD MLG Loss"].mean():.0f}')
print(f'\nMean ED MLG Training Loss: {Prediction_User["ED MLG Loss"].mean():.0f}')
print(f'\nMean PD Naive Training Loss: {Prediction_User["PD Naive Loss"].mean():.0f}')
print(f'\nMean ED Naive Training Loss: {Prediction_User["ED Naive Loss"].mean():.0f}')

    
fig = plt.figure(1)

plt.plot(Prediction_User["Training"],Prediction_User["PD MLG Loss"],color='green', linestyle = 'solid')
plt.plot(Prediction_User["Training"],Prediction_User["PD Naive Loss"],color='red', linestyle = 'solid')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
plt.legend(["PD MLG Loss", "PD Naive Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  

fig = plt.figure(2)

plt.plot(Prediction_User["Training"],Prediction_User["ED MLG Loss"],color='green', linestyle = 'dashed')
plt.plot(Prediction_User["Training"],Prediction_User["ED Naive Loss"],color='red', linestyle = 'dashed')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
plt.legend(["ED MLG Loss", "ED Naive Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  

fig = plt.figure(3)

plt.plot(Prediction_User["Training"],np.cumsum(Prediction_User["PD MLG Loss"])/(Prediction_User["Training"]-9),color='green', linestyle = 'solid')
plt.plot(Prediction_User["Training"],np.cumsum(Prediction_User["PD Naive Loss"])/(Prediction_User["Training"]-9),color='red', linestyle = 'solid')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
plt.legend(["PD MLG CMA Loss", "PD Naive CMA Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  

fig = plt.figure(4)

plt.plot(Prediction_User["Training"],np.cumsum(Prediction_User["ED MLG Loss"])/(Prediction_User["Training"]-9),color='green', linestyle = 'dashed')
plt.plot(Prediction_User["Training"],np.cumsum(Prediction_User["ED Naive Loss"])/(Prediction_User["Training"]-9),color='red', linestyle = 'dashed')
plt.xlabel('# Training sessions')
plt.ylabel('Loss')
plt.legend(["ED MLG CMA Loss", "ED Naive CMA Loss"],bbox_to_anchor=(1.05, 1.0), loc='best', borderaxespad=0)
plt.show()  