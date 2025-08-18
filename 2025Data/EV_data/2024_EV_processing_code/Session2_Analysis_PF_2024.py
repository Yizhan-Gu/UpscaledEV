# -*- coding: utf-8 -*-
"""
Created on Thu Dec 15 11:58:26 2022

@author: Anne
"""
"""""""""""""""""""""""""""""""""""""""IMPORT PACKAGES HERE"""""""""""""""""""""""""""""""""

from IPython import get_ipython
get_ipython().magic('reset -sf')


import os.path
import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import time
from datetime import datetime                           #pip install dill --user

start_time = time.time()

#%%
"""""""""""""""""""""""""""""""""""""""READ CLEANED DATA HERE"""""""""""""""""""""""""""""""""


dir_Input = os.path.join("C:/Users/Anne/Desktop/Total/Data/EV_PF_UCSD/2024/")
Data = pd.read_csv (dir_Input + 'UCSD_AllSites_Sessions2_wCarInfo_20210504_20240930.csv') #69,844



#Data.columns = Data.columns.str.replace(' ', '')
# =============================================================================
# Data = Data.rename(columns={'Layover(s)': 'Layover', 'ActiveCharging(s)': 'ActiveCharging',
#                                         'Energy(kWh)': 'Energy','GHGSavings(kg)': 'GHGSavings', 
#                                         'GasolineSavings(gallons)': 'GasolineSavings'}) #Change some column names
# =============================================================================


#Data = Data.rename(columns={'Layover(s)': 'Layover', 'ActiveCharging(s)': 'ActiveCharging', 'Energy(kWh)': 'Energy'})


Data['Session start']= pd.to_datetime(Data['Session start']) 
Data['Session end']= pd.to_datetime(Data['Session end']) 



#%%
"""""""""""""""""""""Filter out session data with 1. Layover < 10 mins and 2. Energy < 1 kWh """""""""""""""""""""""""""


Data_QCed = Data[~(Data["Session duration (minutes)"]<10) &  ~(Data["kWh delivered"]<1)]

# Note for PF:
# All data (Data): 69,844, after filtering (Data_filter): 42,649


    
#%%
""""""
""""Filtering data with pre/during/post COVID time frames """"""""""" 

Period = 'Post COVID' # Pre COVID, During COVID, Post COVID

if Period == 'Pre COVID':
    StartDate_My = datetime(2016,4,1)
    EndDate_My = datetime(2019,11,30)
    
elif Period == 'During COVID':
    StartDate_My = datetime(2020,4,1)
    EndDate_My = datetime(2021,8,31)
    
elif Period == 'Post COVID':
    StartDate_My = datetime(2022,2,1)
    EndDate_My = datetime(2024,9,30)
    
    
Start_Date = StartDate_My
End_Date = EndDate_My
    
# Pre COVID: 2016/04/01 - 2019/11/30
# During COVID: 2020/04/01 - 2021/08/31 
# Post COVID: 2022/02/01 - 2024/09/30 

Data_ThisPeriod = Data_QCed[(StartDate_My <= Data_QCed['Session start']) & (Data_QCed['Session start'] <= EndDate_My) \
                                                & (StartDate_My <= Data_QCed['Session end']) & (Data_QCed['Session end'] <= EndDate_My)]

Plaza = list(Data_ThisPeriod['Site'].unique())
Chergers = Data_ThisPeriod['XB Address'].unique()


# explore other options to analyze unique chargers since "XB Address" is mostly nan
Chergers2 = Data_ThisPeriod['Serial #'].unique()
test =  Data_ThisPeriod[Data_ThisPeriod['Serial #'].astype(str)=='1111117385']


# Pre COVID (Data_ThisPeriod): 0
# During COVID (Data_ThisPeriod)--> events:  1,251; plazas:  2; chargers: 47
# Post COVID (Data_ThisPeriod)  --> events: 37,662; plazas: 24; chargers: 52; chargers2: 377  

#What are those data with XB Address == nan?
Charger_nan = Data_ThisPeriod[Data_ThisPeriod['XB Address'].astype(str)=='nan']
  
       
#%%
""""""""""Filtering the data with Plaza name(s) """"""""""" 

# =============================================================================
# #Plaza = ["SCHOLARS", "PANGEA", "RADY", "HOPKINS", "SOM", "FACULTY CLUB", "GILMAN", "OSLER", "P610"];  #Options are: {SCHOLARS; PANGEA; RADY; HOPKINS; SOM; FACULTY CLUB; GILMAN; OSLER; P610}.
# #Plaza = ["Gilman", "Athena"]
# 
# 
# 
# #Data_plaza = Data_ThisPeriod[Data_ThisPeriod["Site"].isin(Plaza)]
# Data_plaza = Data_ThisPeriod[Data_ThisPeriod["StationName"].str.contains(pat = 'G') | \
#                                        Data_ThisPeriod["StationName"].str.contains(pat = 'A')]
# =============================================================================

Data_plaza = Data_ThisPeriod.copy()



#%%
"""""""""""""""""""""Report the numb of VehicleMake data include nan znd 0 """""""""""""""""""""""""""""

#Data_zero = Data_plaza[Data_plaza['Car Make'].str.contains(pat = '0') ]
Data_complete = Data_plaza[ (Data_plaza['Car Year'].astype(str).str.contains( 'nan') == False) &\
                            (Data_plaza['Car Make'].str.contains( 'nan') == False) &\
                            (Data_plaza['Car Model'].str.contains( 'nan') == False) &\
                            (Data_plaza['Car Battery'].astype(str).str.contains( 'nan') == False)]



   
# PF, post COVID:
    # len(Data_plaza), all data          = 8,016 
    # len(Data_complete), w/o '0' or nan = 7,541
    # with 0 or nan:                         475 
    # len(Data_zero), with 0             =   463
    # wuth 'nan':                        =    12
    
# PF, during COVID:
    # len(Data_plaza), all data          = 1,251 
    # len(Data_complete), w/o '0' or nan = 1,210
    # with 'nan':                        =    41 



#%%
""""""""""EV Stats """""""""""

# =============================================================================
# Data_clean_make = Data_plaza[((~Data_plaza['VehicleMake'].isnull()))];
# Data_clean_make_model = Data_clean_make[((~Data_clean_make['VehicleModel'].isnull()))];
# Data_clean_make_model_year = Data_clean_make_model[((~Data_clean_make_model['VehicleModelYear'].isnull()))];
# =============================================================================


Data_EV = pd.read_csv(r'PowerFlex input for EV statistics to be plugged into master sheet.csv')
Data_EV.columns = Data_EV.columns.str.replace(' ', '')
Data_EV = Data_EV.rename(columns={'Battery(kWh)': 'Battery'})


""""""""""""""""""""""""""""""""""""""""""""" CUSTOMER PROFILING """""""""""""""""""""""""""""""""""""""""""""""
#%% 
######################## Table of Make and Model ########################

temp = pd.DataFrame()
Table_1 = pd.DataFrame()
#unique_make_1 = pd.unique(Data_clean_make_model['VehicleMake'])
unique_make_1 = pd.unique(Data_complete['VehicleMake'])


#unique_model_1 = pd.unique(Data_clean_make_model_year['VehicleModel'])
unique_model_1 = pd.unique(Data_complete['VehicleModel'])



for i in range(len(unique_make_1)):
    
    Data_ThisMake = Data_complete[(Data_complete["VehicleMake"] == unique_make_1[i])]
    
    
    for j in range(len(unique_model_1)):
        
        Data_ThisMake_ThisModel = Data_ThisMake[(Data_ThisMake["VehicleModel"] == unique_model_1[j])]
        if Data_ThisMake_ThisModel.empty == False:
            temp_d = {'Make': [unique_make_1[i]], \
                      'Model': [unique_model_1[j]], \
                      'Year': Data_ThisMake_ThisModel["VehicleModelYear"].iloc[0] ,\
                      'Battery': Data_ThisMake_ThisModel["Car Battery"].iloc[0] ,\
                      'number_events': [len(Data_ThisMake_ThisModel)], \
                      'percent_events': [100*len(Data_ThisMake_ThisModel)/len(Data_complete)]} 
        
            temp = pd.DataFrame(temp_d) 
        
            Table_1 = pd.concat([Table_1, temp], axis=0)

Table_1 = Table_1.sort_values(by=['percent_events'],ascending=False)

#Table_1.to_csv('Make_Model'+str(Start_Date_string)+'_'+str(End_Date_string) + '.csv', index=False); # export as csv
Table_1.to_csv('Make_Model['+StartDate_My.strftime("%Y%m%d")+']_['+EndDate_My.strftime("%Y%m%d") + '].csv', index=False)





####################################################################################################################################
############################################################Unique Session Analysis #################################################
####################################################################################################################################


""""""""""""""""""""""""""""""""""""""""""""" Pie plot of car make and model percentage """""""""""""""""""""""""""""""""""""""""""""""
#%% 

Make_1 = np.array([]);

for i in range(len(unique_make_1)):
    #Make_1 = np.append(Make_1, len(Data_clean_make_model_year[(Data_clean_make_model_year["VehicleMake"] == unique_make_1[i])]));
    Make_1 = np.append(Make_1, len(Data_complete[(Data_complete["VehicleMake"] == unique_make_1[i])]));



# plt.pie(Make_1, labels=unique_make_1)
# plt.legend()
# plt.show();
##Fig 1
percent = 100.*Make_1/Make_1.sum()

patches, texts = plt.pie(Make_1, startangle=90, radius=1.5)
labels = ['{0} - {1:1.2f} %'.format(i,j) for i,j in zip(unique_make_1,  percent)]

sort_legend = True
if sort_legend:
    patches, labels, dummy =  zip(*sorted(zip(patches, labels, Make_1),
                                          key=lambda unique_make_1: unique_make_1[2],
                                          reverse=True))

plt.legend(patches, labels, loc='best', bbox_to_anchor=(-0.1, 1.),
           fontsize=8)
plt.show();




""""""""""""""""""""""""""""""""""""""""""""" Histograms """""""""""""""""""""""""""""""""""""""""""""""
#%% 


#1 Session start

Session_Start_hour = Data_complete['Session start'].dt.hour
Session_End_hour = Data_complete['Session end'].dt.hour


weights1 = np.ones_like(Session_Start_hour) / len(Session_Start_hour) 
plt.hist(Session_Start_hour, bins = np.linspace(0, 24, 25),  weights = weights1)
plt.xlabel('Hour of The Day')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)




#2 Session end
plt.hist(Session_End_hour, bins = np.linspace(0, 24, 25),  weights = weights1)
plt.xlabel('Hour of The Day')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)




#3 Session duration (minutes) hour

#plt.hist([list(Data_complete['Session duration (minutes)']/60)], bins = np.linspace(0, 24, 25), density=True)
weights1 = np.ones_like(Data_complete['Session duration (minutes)']) / len(Data_complete['Session duration (minutes)']) 
plt.hist(Data_complete['Session duration (minutes)']/60, bins = np.linspace(0, 24, 25),  weights = weights1)
plt.xlabel('Session duration [hr]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)




#4 Charging hour

#plt.hist([list(Data_complete['Charging duration (minutes)']/60)], bins = np.linspace(0, 24, 25), density=True)
plt.hist( Data_complete['Charging duration (minutes)']/60, bins = np.linspace(0, 24, 25), weights = weights1)
plt.xlabel('Charging Duration [hr]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)




#5 Idle hour

plt.hist( (Data_complete['Session duration (minutes)']-Data_complete['Charging duration (minutes)'])/60, bins = np.linspace(0, 24, 25), weights = weights1)
plt.xlabel('Idle Duration [hr]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)




#6 Energy demand

plt.hist( Data_complete['kWh delivered'], bins = np.linspace(0, 70, 71), weights = weights1)  
plt.xlabel('Energy Demand [kWh]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15) 





#7 Battery capacity

#plt.hist([list(Data_complete['Battery'])], bins = np.linspace(0, 160, 161), density=True)
plt.hist( Data_complete['Car Battery'], bins = np.linspace(0, 160, 161), weights = weights1)  
plt.xlabel('Battery Capacity [kWh]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)  # Set the font size for y tick labels
# plt.rc('legend', fontsize=18) # Set the legend font size
# plt.rc('figure', titlesize=20) # Set the font size of the figure title




#8 Energy delivered / Battery size 

#plt.hist( Data_complete['kWh delivered']/ Data_complete['Battery'], bins = np.linspace(0, 2, 21), density=True )
plt.hist(  Data_complete['kWh delivered']/ Data_complete['Car Battery'], bins = np.linspace(0, 2, 21), weights = weights1)
plt.xlabel('Energy Delivered/Battery Capacity [-]')
plt.ylabel('Frequency [-]')
plt.show()

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)



Data_complete_BESS_0to20 = Data_complete[Data_complete['Car Battery']<20]
Data_complete_BESS_20to40 = Data_complete[(Data_complete['Car Battery']>20) &\
                                          (Data_complete['Car Battery']<40)]
Data_complete_BESS_40to60 = Data_complete[(Data_complete['Car Battery']>40) &\
                                          (Data_complete['Car Battery']<60)]
Data_complete_BESS_60above = Data_complete[Data_complete['Car Battery']>60]    





# Energy delivered / Battery capacity , with four catagories

weights1 = np.ones_like(Data_complete_BESS_0to20['kWh delivered']) / len(Data_complete_BESS_0to20['kWh delivered']) 
weights2 = np.ones_like(Data_complete_BESS_20to40['kWh delivered']) / len( Data_complete_BESS_20to40['kWh delivered']) 
weights3 = np.ones_like(Data_complete_BESS_40to60['kWh delivered']) / len(Data_complete_BESS_40to60['kWh delivered']) 
weights4 = np.ones_like(Data_complete_BESS_60above['kWh delivered']) / len(Data_complete_BESS_60above['kWh delivered']) 


x1 = Data_complete_BESS_0to20['kWh delivered']/Data_complete_BESS_0to20['Car Battery']
x2 = Data_complete_BESS_20to40['kWh delivered']/Data_complete_BESS_20to40['Car Battery']
x3 = Data_complete_BESS_40to60['kWh delivered']/Data_complete_BESS_40to60['Car Battery']
x4 = Data_complete_BESS_60above['kWh delivered']/Data_complete_BESS_60above['Car Battery'] 

#kwargs = dict(histtype='stepfilled', alpha=0.3,  bins=40)

plt.hist(x1, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 41), weights = weights1)
plt.hist(x2, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 41), weights = weights2)
plt.hist(x3, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 41), weights = weights3)
plt.hist(x4, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 41), weights = weights4)
plt.legend(["<=20 kWh", ">20 and <=40 kWh", ">40 and <=60 kWh", ">60 kWh"])
plt.xlabel('Energy Delivered/Battery Capacity [-]')
plt.ylabel('Frequency [-]')
plt.show()





####################################################################################################################################
############################################################Plots instead of Histograms #################################################
####################################################################################################################################


# =============================================================================
# LayoverDuration_hr = Data_complete['Session duration (minutes)']/60
# ChargingDuration_hr = Data_complete['Charging duration (minutes)']/60/60
# IdleDuration_hr = LayoverDuration_hr - ChargingDuration_hr
# BatteryCapacity = Data_complete['Car Battery']
# EnergyOverBattery = Data_complete['kWh delivered']/ Data_complete['Car Battery']
# 
# x_12345 = list(np.linspace(0, 24, 25))
# x_6 = list(np.linspace(5, 75, 8))
# x_6_width = (75-5)/(8-1)
# x_7 = list(np.linspace(5, 165, 17))
# x_7_width = (165-5)/(17-1)
# x_8 = list(np.linspace(0.05, 1.05, 11))
# x_8_width = (1.05-0.05)/(11-1)
# 
# y_1_PlugInTime_aux = np.array([])
# y_2_PlugOutTime_aux = np.array([])
# y_3_LayoverDuration_aux = np.array([]) 
# y_4_ChargingDuration_aux = np.array([]) 
# y_5_IdleDuration_aux = np.array([]) 
# y_6_EnergyDemand_aux = np.array([]) 
# y_7_BatteryCapacity_aux = np.array([]) 
# y_8_EnergyDemandOverBatteryCapacity_aux = np.array([]) 
# 
# 
# for i in range(2):
#     #i = int(0)
#     y_1_PlugInTime = np.array([])                        
#     y_2_PlugOutTime = np.array([])
#     y_3_LayoverDuration = np.array([])
#     y_4_ChargingDuration = np.array([])
#     y_5_IdleDuration = np.array([])
#     y_6_EnergyDemand = np.array([])
#     y_7_BatteryCapacity = np.array([])
#     y_8_EnergyDemandOverBatteryCapacity = np.array([])
# 
#     for j in range(len(x_12345)):
#         #j = int(0)
#         y_1_PlugInTime =  np.append(y_1_PlugInTime , len(list(x for x in Session_End_hour if  x == x_12345[j]))/len(Session_End_hour) )
#         y_2_PlugOutTime = np.append(y_2_PlugOutTime, len(list(x for x in Session_End_hour if  x == x_12345[j]))/len(Session_End_hour) )
#         y_3_LayoverDuration = np.append(y_3_LayoverDuration, len(list(x for x in LayoverDuration_hr if j-0.5 <= x <= j+0.5))/len(LayoverDuration_hr))
#         y_4_ChargingDuration = np.append(y_4_ChargingDuration, len(list(x for x in ChargingDuration_hr if j-0.5 <= x <= j+0.5))/len(ChargingDuration_hr))
#         y_5_IdleDuration =  np.append(y_5_IdleDuration, len(list(x for x in IdleDuration_hr if j-0.5 <= x <= j+0.5))/len(IdleDuration_hr))
#         
#     for j in x_6:
#         y_6_EnergyDemand = np.append(y_6_EnergyDemand, len(list(x for x in IdleDuration_hr if j-x_6_width  <= x <= j+x_6_width ))/len(IdleDuration_hr))
#         
#     for j in x_7:
#         y_7_BatteryCapacity = np.append(y_7_BatteryCapacity, len(list(x for x in BatteryCapacity if j-x_7_width  <= x <= j+x_7_width ))/len(BatteryCapacity))
#         
#     for j in x_8:
#         y_8_EnergyDemandOverBatteryCapacity = np.append( y_8_EnergyDemandOverBatteryCapacity, len(list(x for x in EnergyOverBattery if j-x_8_width  <= x <= j+x_8_width ))/len(EnergyOverBattery))
# 
#     y_1_PlugInTime_aux = np.append(y_1_PlugInTime_aux ,y_1_PlugInTime)
#     y_2_PlugOutTime_aux = np.append(y_2_PlugOutTime_aux, y_2_PlugOutTime)
#     y_3_LayoverDuration_aux = np.append(y_3_LayoverDuration_aux, y_3_LayoverDuration)
#     y_4_ChargingDuration_aux = np.append(y_4_ChargingDuration_aux, y_4_ChargingDuration)
#     y_5_IdleDuration_aux = np.append(y_5_IdleDuration_aux, y_5_IdleDuration)
#     y_6_EnergyDemand_aux = np.append(y_6_EnergyDemand_aux, y_6_EnergyDemand)
#     y_7_BatteryCapacity_aux = np.append(y_7_BatteryCapacity_aux, y_7_BatteryCapacity)
#     y_8_EnergyDemandOverBatteryCapacity_aux = np.append(y_8_EnergyDemandOverBatteryCapacity_aux, y_8_EnergyDemandOverBatteryCapacity)
# 
# #1 Session start
# test = y_2_PlugOutTime_aux[0:25]
# test1 = y_2_PlugOutTime_aux[25:50]
# 
# plt.plot(x_12345, y_2_PlugOutTime_aux[0:25], 'r', x_12345, y_2_PlugOutTime_aux[25:50], 'g')
# plt.xlabel("Plug-in hour of day", fontsize=20);
# plt.ylabel("Frequency[-]", fontsize=20);
# plt.title("Unique driver analysis", fontsize = 20)
# # plt.xticks(np.arange(0, 25, 5))
# plt.legend([ 'During COVID', 'Post COVID'])
# plt.show()
# =============================================================================




############################################ #sessions/week/driver - For Social Science ############################################
#%%
####################################################################################################################################
############################################################Unique Driver Analysis #################################################
####################################################################################################################################

Data_ss = Data_complete[ ~Data_complete['User'].isnull() == ~Data_complete['Car Battery'].isnull() ]

unique_drivers = pd.unique(Data_ss['User']) # 569 for PF

Data_ss = Data_ss.rename(columns={'Car Battery': 'CarBattery', 'kWh delivered': 'kWhdelivered', 'Charging duration (minutes)': 'Chargingduration'})
                            

Driver_sessions = np.array([]) # want to know total session number for each driver
Driver_battery = np.array([])
Driver_TotEnergy = np.array([])   # want to know total energy delivered for each driver
Driver_TotChargDuration = np.array([])

for i in range(len(unique_drivers)):
    #ThisDriver = unique_drivers[0]
    ThisDriver = unique_drivers[i]
    Driver_battery = np.append(Driver_battery, Data_ss[Data_ss["User"] == ThisDriver].CarBattery.mean())
    Driver_sessions = np.append(Driver_sessions, len(Data_ss[Data_ss["User"] == ThisDriver]));
    Driver_TotEnergy = np.append(Driver_TotEnergy, Data_ss[Data_ss["User"] == ThisDriver].kWhdelivered.sum())
    Driver_TotChargDuration = np.append(Driver_TotChargDuration, Data_ss[Data_ss["User"] == ThisDriver].Chargingduration.sum()/60) 

#Driver_SessionsPerWeek = Driver_sessions/ (End_Date-Start_Date).days/7
Driver_SessionsPerWeek = 7 * Driver_sessions/ (End_Date-Start_Date).days
Driver_EnergyPerSession = Driver_TotEnergy/Driver_sessions
Driver_EnergyPerSessionOverBattery = Driver_EnergyPerSession/Driver_battery
Driver_AvgChargPw = Driver_TotEnergy/Driver_TotChargDuration


Data_UniqueDriver = pd.DataFrame({    'User ID': unique_drivers,\
                                      'Battery capacity (kWh)': Driver_battery,\
                                      'Total Session numb': Driver_sessions,\
                                      'Total Energy Delivered (kWh)': Driver_TotEnergy,\
                                      'Total Charging Duration (hr)': Driver_TotChargDuration,\
                                      'Session Per Week': Driver_SessionsPerWeek,\
                                      'Energy Per Session (kWh)' : Driver_EnergyPerSession,\
                                      'Ratio of Energy Per Session to Battery Capacity' : Driver_EnergyPerSessionOverBattery,\
                                      'Avg Charging Power (kW)' : Driver_AvgChargPw})


    
Data_UniqueDriver.to_csv('UniqueDriver Analysis['+StartDate_My.strftime("%Y%m%d")+']_['+EndDate_My.strftime("%Y%m%d") + '].csv', index=False)    
test = Data_UniqueDriver['Total Session numb'].sum()





""""""""""""""""""""""""""""""""""""""""""""" Histograms """""""""""""""""""""""""""""""""""""""""""""""
#%%    


# Session Number per Week
    
weights = np.ones_like(Driver_SessionsPerWeek) / len(Driver_SessionsPerWeek) 
plt.hist( Driver_SessionsPerWeek, bins = np.linspace(0, 5, 51), weights = weights)    

plt.xlabel('Session Number Per Week[-]')
#plt.ylabel('Probability [-]')
plt.ylabel('Frequency [-]')

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)    
plt.show()
   



# Battery capacity

weights = np.ones_like(Driver_battery) / len(Driver_battery) 
plt.hist([list(Driver_battery)], bins =  np.linspace(0, 160, 161), weights = weights)
plt.xlabel('Battery Capacity [kWh]')
plt.ylabel('Frequency [-]')

plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)
plt.show()




Data_UniqueDriver_BESS_0to20 = Data_UniqueDriver[Data_UniqueDriver['Battery capacity (kWh)']<20]
Data_UniqueDriver_BESS_20to40 =Data_UniqueDriver[(Data_UniqueDriver['Battery capacity (kWh)']>20) &\
                                                 (Data_UniqueDriver['Battery capacity (kWh)']<40)]
Data_UniqueDriver_BESS_40to60 = Data_UniqueDriver[(Data_UniqueDriver['Battery capacity (kWh)']>40) &\
                                                  (Data_UniqueDriver['Battery capacity (kWh)']<60)]
Data_UniqueDriver_BESS_60above = Data_UniqueDriver[Data_UniqueDriver['Battery capacity (kWh)']>60]    




# Session Number per Week , with four catagories

weights1 = np.ones_like(Data_UniqueDriver_BESS_0to20['Battery capacity (kWh)']) / len(Data_UniqueDriver_BESS_0to20['Battery capacity (kWh)']) 
weights2 = np.ones_like(Data_UniqueDriver_BESS_20to40['Battery capacity (kWh)']) / len(Data_UniqueDriver_BESS_20to40['Battery capacity (kWh)']) 
weights3 = np.ones_like(Data_UniqueDriver_BESS_40to60['Battery capacity (kWh)']) / len(Data_UniqueDriver_BESS_40to60['Battery capacity (kWh)']) 
weights4 = np.ones_like(Data_UniqueDriver_BESS_60above['Battery capacity (kWh)']) / len(Data_UniqueDriver_BESS_60above['Battery capacity (kWh)']) 


x1 = Data_UniqueDriver_BESS_0to20['Session Per Week']
x2 = Data_UniqueDriver_BESS_20to40['Session Per Week']
x3 = Data_UniqueDriver_BESS_40to60['Session Per Week']
x4 = Data_UniqueDriver_BESS_60above['Session Per Week']


plt.hist(x1, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 11), weights = weights1)
plt.hist(x2, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 11), weights = weights2)
plt.hist(x3, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 11), weights = weights3)
plt.hist(x4, histtype='stepfilled', alpha=0.3, bins = np.linspace(0, 1, 11), weights = weights4)
plt.legend(["<=20 kWh", ">20 and <=40 kWh", ">40 and <=60 kWh", ">60 kWh"])
plt.xlabel('Session Number Per Week[-]')
plt.ylabel('Frequency [-]')
plt.show()





############################################# sessions/week/driver >=1 - For Social Science ############################################
#%%


# Exclude those drivers with session per week < 1

Data_UniqueDriver_filter = Data_UniqueDriver[Data_UniqueDriver['Session Per Week']>=1]
test = Data_UniqueDriver_filter['Total Session numb'].sum()



""""""""""""""""""""""""""""""""""""""""""""" Histograms """""""""""""""""""""""""""""""""""""""""""""""
#%%



# Average Charging Power [kW]
    
weights = np.ones_like(Driver_AvgChargPw) / len(Driver_AvgChargPw) 
plt.hist( Driver_AvgChargPw, bins = np.linspace(0, 10, 11), weights = weights)    

plt.xlabel('Average Charging Power [kW]')
plt.ylabel('Frequency [-]')

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)    
plt.show()



# Energy Delivered Per Week
    
Driver_EnergyPerWeek = 7 * Driver_TotEnergy/ (End_Date-Start_Date).days

plt.hist( Driver_EnergyPerWeek, bins = np.linspace(0, 20, 21), weights = weights)    

plt.xlabel('Energy Delivered Per Week [kWh]')
plt.ylabel('Frequency [-]')

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)    
plt.show()




# Ratio of Energy Per Session to Battery Capacity
    
plt.hist( Driver_EnergyPerSessionOverBattery, bins = np.linspace(0, 2, 21), weights = weights)    

plt.xlabel(' Ratio of Energy Per Session to Battery Capacity [-]')
plt.ylabel('Frequency [-]')

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)  
plt.show()




# Charging Energy Per Session [kWh]
     
plt.hist( Driver_EnergyPerSession, bins = np.linspace(0, 80, 81), weights = weights)    

plt.xlabel('Energy Delivered Per Session [kWh]')
plt.ylabel('Frequency [-]')

# plt.rc('font', size=12)      # Set the default text font size
plt.rc('axes', titlesize=15)   # Set the axes title font size
plt.rc('axes', labelsize=15)   # Set the axes labels font size
plt.rc('xtick', labelsize=15)  # Set the font size for x tick labels
plt.rc('ytick', labelsize=15)    
plt.show()








print("\n--- Runtime is %s seconds ---" % (time.time() - start_time))