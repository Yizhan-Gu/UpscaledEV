#import libraries
import IPython
#from IPython import get_ipython
#get_ipython().magic('reset -sf')
import os
os.system('clear')
import pathlib
from pathlib import Path
import csv
import time 
import datetime
from datetime import datetime, timedelta   
import re
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns

import math
import time
from time import process_time
#pip install dill --user
import pytz

from sklearn.cluster import KMeans
from sklearn import preprocessing
from sklearn.decomposition import PCA
from kneed import KneeLocator

from scipy.stats import norm
import statistics

#select path, file 
data_folder = Path("/Users/isabelmartinez/SCALeDEV/") #change path name for different user 
file_to_open = data_folder / "PF_UCSD_20210504_20230129_Sessions.csv"

"""""""""""""""""""""""""""""""""""""""USER INPUTS""""""""""""""""""""""""""""""""" 
User_ID  = '0051010108'
AT_ref = '2023-03-01 08:00:00' #AT time for which we are trying to predict PD, ED 

'''To be optimized as necessay
weights given to the repsective AT distances. Must always sum to 1.'''
w_netAT = 0.50
w_intraAT = 0.50

#spilt reference AT into strings, convert to integers -> datetime object
AT_ref_split = re.split(r':|-| ', AT_ref)  
AT_ref_int = [int(j) for j in AT_ref_split]
reference_dt = datetime(AT_ref_int[0],AT_ref_int[1], AT_ref_int[2], AT_ref_int[3], AT_ref_int[4], AT_ref_int[5])
reference_time = datetime(1,1,1, AT_ref_int[3], AT_ref_int[4], AT_ref_int[5]) #datetime object only accounting for intra day distance

 


#select path, file 
data_folder = Path("/Users/isabelmartinez/SCALeDEV/") #change path name for different user 
file_to_open = data_folder / "PF_UCSD_20210504_20230129_Sessions.csv"
start_time = time.time()

"""""""""""""""""""""""""""""""""""""""READ SESSIONS DATA HERE"""""""""""""""""""""""""""""""""

"""""""""""""""""""""""""""""""""""""""Clean Session Data """""""""""""""""""""""""""""""""

Sessions_Table = pd.read_csv ('/Users/isabelmartinez/SCALeDEV/PF_UCSD_20210504_20230129_Sessions.csv');
#low_memory = False

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
#%% Setting up Data

Sessions_Table_clean = Sessions_Table[:];

Sessions_Table_clean['Charging duration (minutes)'] = Sessions_Table_clean['Charging duration (minutes)'].astype("float");
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session duration (minutes)']-Sessions_Table_clean['Charging duration (minutes)']          
Sessions_Table_clean['Session idle (minutes)'] = Sessions_Table_clean['Session idle (minutes)'].astype("float");
#Use Sessions_table_clean for further analysis




#Filter the dataframe for the specifc User ID
filtered_lines = Sessions_Table_clean[Sessions_Table_clean["Session ID"].str.contains(User_ID)]
row_index = filtered_lines.index

#assign  PD, and ED, convert to arrays for future use
PD =  filtered_lines['Charging duration (minutes)']
ED = filtered_lines['kWh delivered']


#convert PD and ED to numpy arrays for future use 
PD_array = np.array(PD)
ED_array = np.array(ED)

'''read-cell function returns the AT from the original csv file based upon the filtered indices from the cleaned-up file '''
def read_cell(row_index, x1): 
    with open(file_to_open, 'r') as f:
        reader = csv.reader(f)
        y_count = 0
        AT = []
        y_count = 0
        for n in reader:
            if y_count in  row_index:
                AT.append(n[x1])
            y_count += 1
        return AT

AT = read_cell(row_index,2)

''' weighted_values function defines a weighted PD and ED based on a weighted sum of historical PDs and EDs respectfully, as a function of arrival time.
The weights are based on the normalized sum of  arrival time distance  and the  intra-day arrival time distance, where a smaller difference in these distances
correponds to a higher weight given to that particular PD and ED.
'''
def weighted_values(AT,PD, ED, reference_dt, reference_time):
    Net = np.array([]) #create an empty array to store net distances 
    Intra = np.array([]) #create an empty array to store intra day distances 
    
    #spilt AT into strings, convert to integers
    for i in range(len(AT)):
        #spilt AT into strings, convert to integers
        AT_split = re.split(r':|-| ', AT[i])  
        AT_int = [int(j) for j in AT_split]
        
        #define net AT distance
        dt = datetime(AT_int[0],AT_int[1], AT_int[2], AT_int[3], AT_int[4], AT_int[5])
        delta_dt =  abs(dt - reference_dt)
        net = delta_dt.total_seconds() #net AT distance in seconds 
        Net = np.append(Net,net) #append to array
        
        #define intra day AT distance 
        dt_time = datetime( 1,1,1,AT_int[3], AT_int[4], AT_int[5]) #datetime object only accounting for intra day distance
        delta_t = abs(dt_time-reference_time)
        intra = delta_t.total_seconds() # intra day distance in seconds
        Intra = np.append(Intra, intra) #append to array 
        

        
    #normalize intra-day and net distance arrays
    net2 = (Net- Net.min()) / (Net.max() - Net.min())
    norm_net = net2 / net2.sum()
    intra2 = (Intra - Intra.min()) / (Intra.max() - Intra.min())
    norm_intra = intra2 / intra2.sum()

    '''Define Q; Q is the set of weights that takes the norm of intra day and net arrival time distances and reorders the PD and ED arrays such that PD_1 and ED_1 correspond 
 to the smallest difference in arrival time distances. '''
    Q = w_netAT*norm_net + w_intraAT*norm_intra
    sorted_indices = np.argsort(Q)
    #Q = np.sort(q)
   

    #reorder PD, ED
    reordered_PD = PD_array[sorted_indices]
    reordered_ED = ED_array[sorted_indices]


    #define proportionality constant p
    p_denom = 0 #denominator of p 
    for j in range(len(norm_net)):
        p_denom += 1/(j+1)
    #proportionality constant p 
    p = 1/p_denom

    #define weights W 
    #create empty arrays   
    PD_weight= 0
    ED_weight= 0
    for i in range(len(reordered_PD)):
        W = p/(i+1)
        PD_i = reordered_PD[i]*W
        PD_weight += PD_i
        ED_i = reordered_ED[i]*W
        ED_weight += ED_i
   
    return PD_weight, ED_weight

PD_weight, ED_weight = weighted_values(AT,PD, ED, reference_dt, reference_time)

print('The weighted average PD is', PD_weight, 'and the weighted average ED is', ED_weight, '.')
