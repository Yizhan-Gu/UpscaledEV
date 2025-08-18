# -*- coding: utf-8 -*-
"""
Created on Tue Oct 15 18:46:01 2024

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

Data1= pd.read_csv(dir_Input + 'UCSD_AllSites_Sessions_wCarInfo_20210501_20231231.csv')
columns1 = Data1.columns


Data2= pd.read_csv(dir_Input + 'UCSD_AllSites_Sessions_wCarInfo_20240101_20240930.csv')
columns2 = Data2.columns
unwanted = columns2[28:35]
Data2_ = Data2.drop(columns = unwanted)



Data2_.columns =columns1


Data12 = Data1.append(Data2_) #97,056
Data12 = Data12.drop_duplicates(subset=['Session start','10-digit UID'], keep='first', inplace=False, ignore_index=True) #97,056



filepath = Path(dir_Input + 'UCSD_AllSites_Sessions_wCarInfo_20210501_20240930.csv')  
filepath.parent.mkdir(parents=True, exist_ok=True)  
Data12.to_csv(filepath,index=False)




#################################################################################
# Report the processing time
#################################################################################


Time_Run_End = process_time() 
Time_Process = time.strftime('%H:%M:%S', time.gmtime(Time_Run_End-Time_Run_Start))