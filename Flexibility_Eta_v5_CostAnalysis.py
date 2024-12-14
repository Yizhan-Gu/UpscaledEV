# -*- coding: utf-8 -*-
"""
Created on Wed May 22 07:18:50 2024

@author: Anne
"""
           

import os.path
import pandas as pd
#import matplotlib.dates as mdates
#import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta
from datetime import datetime
import time
from time import process_time
import calendar
import holidays
from pathlib import Path
from random import choices
import cvxpy as cp
import scs
#import sys
#sys.path.insert(0, 'C:/Users/Anne/Desktop/Total/Code\Python/')
#from forecast_ED_PD import KnownUser, UnKnownUser
#from forecast_ED_PD import UnKnownUser


#%%
#################################################################################
# Monthly Costs Analysis ( from the dispatch file)
################################################################################# 

# =============================================================================
# Y_tot = np.ones([4, 1]) 
# Y_TotkWh = np.ones([4, 1]) 
# =============================================================================

dt_m_EV = 15
dt_h = dt_m_EV/60
c_e_TOU_AL = np.ones((96, 1))*0.10679
c_e_TOU_AL[16*4:21*4] = 0.12628
c_NCD = 24.48
c_PD = 19.14 + 9.78

# Tax
c_tax_DWR = 0.00580                               # x Total kWh
c_tax_oEESbo_Franchise = 0.0688 * c_tax_DWR       # x Total kWh
c_tax_CA_Surcharge = 0.00030                      # x Total kWh
c_tax_CA_Regulatory = 0.00058                     # x Total kWh
# x Total Bill (UDC+Commodity)
c_tax_SD_Franchise = 0.0578
c_tax_all = c_tax_DWR + c_tax_oEESbo_Franchise + c_tax_CA_Surcharge + c_tax_CA_Regulatory


Fc_SessionkWh = 'PersistenceSessionkWh'  # 'PerfectSessionkWh' #'PersistenceSessionkWh'
Fc_NumbEV = 'PersistenceNumbEV'          # 'PerfectNumbEV'     #'PersistenceNumbEV'
Fc_AtArrival = 'PerfectatArrival'    # 'PerfectatArrival'  #'MLatArrival'


#kWh data
dir_Input = os.path.join( 'C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/Flexibility/Dispatch' )
filename_Input = dir_Input + '/2022_'+Fc_SessionkWh+'_'+Fc_NumbEV+'_'+Fc_AtArrival +'_MonthlyTh_Eta_v5_test4.csv'
Dispatch_2022 = pd.read_csv(filename_Input)

Dispatch_2022['Interval start'] = pd.to_datetime(Dispatch_2022['Interval start'])
Dispatch_2022 = Dispatch_2022.drop_duplicates('Interval start',keep='last')    

11991/15744 #=76%
278/455 #61%

4912+962-2726-463 #=2685
4737+810-2203-461 #=2883

2051+425 #2476
3916-3139 #777
121-87 #34

(121-87)/(455-278) #=0.19
(135-109)/(455-279) #=0.15
(132-105)/(496-318) #0.15

(3916-3139)/(15774-11991) #0.21
(5715-5500)/(15744-11991) #0.06



year = 2022 
for month in np.array(range(1))+12:    
    #month=12 
    num_days_ = calendar.monthrange(year,month)[1] 
    
    index_EV15 = []
    index_EV30 = []
    
    
    for num_days in np.array(range(num_days_))+1:
    #for num_days in np.array(range(1))+1:    
        print(num_days)
        #num_days =  calendar.monthrange(year,month)[1] 
    
        start_M = datetime(year, month, 1, 0, 0, 0)
        end_M = start_M + timedelta(days=int(num_days))


    
# =============================================================================
#         start_M = datetime(year, month, 7, 0, 0, 0)
#         end_M = start_M + timedelta(days=int(1))
#         num_days=1
# =============================================================================
 

       
        Dispatch_2022_ThisM = Dispatch_2022[(Dispatch_2022['Interval start']>=start_M)&(Dispatch_2022['Interval start']<end_M)]
        Dispatch_2022_ThisM = Dispatch_2022_ThisM.reset_index() 
        
        # create a list of kWh time series for 9 scenarios: V0G, V1Greal, V1Goffline, V1G10, V1G08, V1G06, V1G04, V1G02, V1G00       
        M_data = [np.array(Dispatch_2022_ThisM['V0G [kWh]']).reshape(96*num_days,1), \
                 np.array(Dispatch_2022_ThisM['V1G_real [kWh]']).reshape(96*num_days,1), \
                 np.array(Dispatch_2022_ThisM['Opt_DA [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['Opt_RT_t0 [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['Base [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['Case1 [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['baseline_Base [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['baseline_Case1 [kWh]']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['NCD_Base']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['PD_Base']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['NCD_Case1']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['PD_Case1']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['LMP_DA']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['LMP_RT']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['event hour_Base']).reshape(96*num_days,1),\
                 np.array(Dispatch_2022_ThisM['event hour_Case1']).reshape(96*num_days,1)] 
    
            
        #on-peak hour filter    
        filter_OP = (Dispatch_2022_ThisM['Interval start'].dt.hour>=16)&(Dispatch_2022_ThisM['Interval start'].dt.hour<21) 
    
        
        #TOU for a month
        M_c_TOU = c_e_TOU_AL.copy()
        for i in range(num_days-1):
            M_c_TOU = np.concatenate((M_c_TOU, c_e_TOU_AL), axis=None)       
        M_c_TOU = M_c_TOU.reshape(96*num_days,1)
        
    
    
    
        # Revenue: EV charging service
        #EV charging rate-TOU for a month
    # =============================================================================
    #     M_c_EV_15 = np.ones(shape=(96*num_days,1))*0.15-M_c_TOU
    #     M_c_EV_30 = np.ones(shape=(96*num_days,1))*0.3 -M_c_TOU
    # =============================================================================
        kWh_DA       = np.array( M_data[2]).reshape(96*num_days,1)
        LMP_DA       = np.array( M_data[12]).reshape(96*num_days,1) 
        LMP_RT       = np.array( M_data[13]).reshape(96*num_days,1) 
        
       
        # calculate the NCDC, PDC, energy cost-TOU, market settlement-DAM, RTM, EV service revenue in a for loop
        M_NCDC =  [[] for _ in range(6)]
        M_PDC = [[] for _ in range(6)]
        M_TOU = [[] for _ in range(6)]
        M_Tax = [[] for _ in range(6)]
        M_EV_15 = [[] for _ in range(6)]
        M_EV_30 = [[] for _ in range(6)]
        M_DAM = [[] for _ in range(6)]
        M_RTM = [[] for _ in range(6)]
        M_NetRevenue_15 = [[] for _ in range(6)]
        M_NetRevenue_30 = [[] for _ in range(6)]
        M_NetRevenue_15_wTOU = [[] for _ in range(6)]
        M_NetRevenue_30_wTOU = [[] for _ in range(6)]
        M_tot_EV15 = [[] for _ in range(6)]
        M_tot_EV30 = [[] for _ in range(6)]
        M_TotkWh = [[] for _ in range(6)]
        
        
        kWh_baseline = [[] for _ in range(6)]
        EventHour = [[] for _ in range(6)]
    
        
        for i in range(6): #V0G, V1G_real, Opt_DA, Opt_RT_t0, Base, Case1
            #i=0    
            kWh = np.array(M_data[i]).reshape(96*num_days,1)
            M_TotkWh[i] = sum(kWh)
            M_NCDC[i] = c_NCD *max(kWh)/dt_h
            M_PDC[i] = c_PD  *max(kWh[filter_OP])/dt_h
            M_TOU[i] = sum(np.multiply(M_c_TOU ,kWh))
            #M_Tax[i] = c_tax_all*sum(kWh) + c_tax_SD_Franchise*(M_NCDC[i]+M_PDC[i]+M_TOU[i])
            M_Tax[i] = 0 
            
            #revenue from EV charging service
    # =============================================================================
    #         M_EV_15[i] = sum(np.multiply(kWh, M_c_EV_15))
    #         M_EV_30[i] = sum(np.multiply(kWh, M_c_EV_30))
    # =============================================================================
            M_EV_15[i] = sum(kWh)*0.15
            M_EV_30[i] = sum(kWh)*0.3
            
            
            # revenue from DA market participation (DA settlement + RT settlement)
            if i >= 4: # Base, Case1
    
                kWh_baseline[i] = np.array( M_data[i+2]).reshape(96*num_days,1)
                EventHour[i] = np.array( M_data[i+10]).reshape(96*num_days,1)
                
                M_DAM[i] = sum(LMP_DA*EventHour[i]*np.maximum(kWh_baseline[i]-np.maximum(kWh_DA,kWh),0))
                M_RTM[i] = sum(LMP_RT*EventHour[i]*np.maximum(kWh_DA-kWh, -(kWh_baseline[i]-kWh_DA)))
                
    
    
            else:
                M_DAM[i] = 0
                M_RTM[i]  = 0
                
            M_NetRevenue_15_wTOU[i] = M_EV_15[i]+M_DAM[i]+M_RTM[i]-M_TOU[i]
            M_NetRevenue_30_wTOU[i] = M_EV_30[i]+M_DAM[i]+M_RTM[i]-M_TOU[i]    
            
            M_NetRevenue_15[i] = M_EV_15[i]+M_DAM[i]+M_RTM[i]
            M_NetRevenue_30[i] = M_EV_30[i]+M_DAM[i]+M_RTM[i]     
                       
            M_tot_EV15[i] = M_NCDC[i]+M_PDC[i]+M_TOU[i]+M_Tax[i]-M_NetRevenue_15[i]
            M_tot_EV30[i] = M_NCDC[i]+M_PDC[i]+M_TOU[i]+M_Tax[i]-M_NetRevenue_30[i]
            
            
        #(M_TotkWh[5]/M_TotkWh[4])
        index_EV15 = index_EV15 + [(M_NetRevenue_15_wTOU[5]-M_NetRevenue_15_wTOU[4])/(M_TotkWh[4]-M_TotkWh[5])]
        index_EV30 = index_EV30 + [(M_NetRevenue_30_wTOU[5]-M_NetRevenue_30_wTOU[4])/(M_TotkWh[4]-M_TotkWh[5])]
            
    # =============================================================================
    #     Y_tot = np.concatenate([Y_tot,np.array(M_tot)], axis=1)
    #     Y_TotkWh = np.concatenate([Y_TotkWh,np.array(M_TotkWh)], axis=1)
    # =============================================================================
