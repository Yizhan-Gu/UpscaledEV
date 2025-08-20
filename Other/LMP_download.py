# -*- coding: utf-8 -*-
"""
This code is used to download the yearly LMP data from CAISO OASIS
Created by Yian Chen
Edited by Yizhan Gu
Email: yig031@ucsd.edu
"""

# NOTE: website error with some months' data missing and unable to be unzipped

import numpy as np
import pandas as pd
import calendar
from datetime import datetime
from datetime import timedelta
import requests
from tqdm import tqdm
import time
import zipfile
import os

# change the year according to your needs
year = 2022
dir_Input = os.path.join("/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024/LMP", str(year))
if not os.path.exists(dir_Input):
    os.makedirs(dir_Input)

os.chdir(dir_Input) # change directory from working dir to dir with files


for month in tqdm(np.array(range(12))+1): # 1:12
    num_days = calendar.monthrange(year,month)[1] 

    for day in np.array(range(num_days))+1: # 1:num_days     
        ThisDate1 = datetime(year,month,day)
        ThisDate2 = ThisDate1 + timedelta(hours=24)
        Y1 = ThisDate1.strftime("%Y")
        M1 = ThisDate1.strftime("%m")
        D1 = ThisDate1.strftime("%d")
        Y2 = ThisDate2.strftime("%Y")
        M2 = ThisDate2.strftime("%m")
        D2 = ThisDate2.strftime("%d")
        
        url_DA = (
    f"http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6"
    f"&queryname=PRC_LMP&version=12"
    f"&startdatetime={Y1}{M1}{D1}T07:00-0000"
    f"&enddatetime={Y2}{M2}{D2}T07:00-0000"
    f"&market_run_id=DAM&node=UCM_6_N001"
)
        url_RT = (
    f"http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6"
    f"&queryname=PRC_RTPD_LMP&version=3"
    f"&startdatetime={Y1}{M1}{D1}T07:00-0000"
    f"&enddatetime={Y2}{M2}{D2}T07:00-0000"
    f"&market_run_id=RTPD&node=UCM_6_N001"
)
        url_FM = (
    f"http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6"
    f"&queryname=PRC_INTVL_LMP&version=3"
    f"&startdatetime={Y1}{M1}{D1}T07:00-0000"
    f"&enddatetime={Y2}{M2}{D2}T07:00-0000"
    f"&market_run_id=RTM&node=UCM_6_N001"
)
        # Create separate folders for DA, RT, FM if they don't exist
        dir_DA = os.path.join(dir_Input, "DA")
        dir_RT = os.path.join(dir_Input, "RT")
        dir_FM = os.path.join(dir_Input, "FM")
        for d in [dir_DA, dir_RT, dir_FM]:
            if not os.path.exists(d):
                os.makedirs(d)

        output_DA = os.path.join(dir_DA, f'LMP_DA_{Y1}{M1}{D1}.zip')
        output_RT = os.path.join(dir_RT, f'LMP_RT_{Y1}{M1}{D1}.zip')
        output_FM = os.path.join(dir_FM, f'LMP_FM_{Y1}{M1}{D1}.zip')
        
        r_DA = requests.get(url_DA)
        r_RT = requests.get(url_RT)
        r_FM = requests.get(url_FM)
        with open(output_DA, 'wb') as f:
            f.write(r_DA.content)
        with open(output_RT, 'wb') as f:
            f.write(r_RT.content)
        with open(output_FM, 'wb') as f:
            f.write(r_FM.content)
            
        # time.sleep(1) # in case of error time sleep seconds
            
    print(f"Download month {month} data successful!\n")



# Zip to Csv
extension = ".zip"

# FIXME: Failure to unzip probably b.c. downloading error, not sure how to solve
for item in os.listdir(dir_Input): # loop through items in dir
    if item.endswith(extension): # check for ".zip" extension
        file_path = os.path.join(dir_Input, item) # get full path of file
        if zipfile.is_zipfile(file_path): # verify it's actually a zip file
            try:
                with zipfile.ZipFile(file_path) as zip_ref: # using context manager
                    zip_ref.extractall(dir_Input) # extract file to dir
                print(f"Successfully extracted {item}")
            except zipfile.BadZipFile:
                print(f"Error: {item} is not a valid zip file")
        else:
            print(f"Skipping {item} - not a zip file")










# Old versions
# =============================================================================
         # DA LMP
         # http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_LMP&version=12&startdatetime=
         #20230811T07:00-0000&enddatetime=20230812T07:00-0000&market_run_id=DAM&node=UCM_6_N001            
         #url = r'http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_LMP&version=12&startdatetime=' + \
             #Y1 + M1 + D1 + 'T07:00-0000&enddatetime=' + Y2 + M2 + D2 + 'T07:00-0000' + \
                 #'&market_run_id=DAM&node=UCM_6_N001'
        
# =============================================================================
                                
        # RT LMP
        # http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_RTPD_LMP&version=3&startdatetime=
        #20230811T07:00-0000&enddatetime=20230812T07:00-0000&market_run_id=RTPD&node=UCM_6_N001                
        
# =============================================================================
#         ur2 = r'http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_RTPD_LMP&version=3&startdatetime=' + \
#             Y1 + M1 + D1 + 'T07:00-0000&enddatetime=' + Y2 + M2 + D2 + 'T07:00-0000' + \
#                 '&market_run_id=RTPD&node=UCM_6_N001'
# =============================================================================
                        
        
        # FM LMP
        # http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_INTVL_LMP&version=3&startdatetime=
        # 20230915T07:00-0000&enddatetime=20230915T08:00-0000&market_run_id=RTM&node=UCM_6_N001                       
        
        #ur3 = r'http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_INTVL_LMP&version=3&startdatetime=' + \
            #Y1 + M1 + D1 + 'T07:00-0000&enddatetime=' + Y2 + M2 + D2 + 'T07:00-0000' + \
                #'&market_run_id=RTM&node=UCM_6_N001' 
                  
        # output file names
# =============================================================================
#         output1 = r'C:\Users\Anne\Desktop\Total\Data\LMP' + '\LMP_DA_' + Y1 + M1 + D1 + '.zip'
#         output2 = r'C:\Users\Anne\Desktop\Total\Data\LMP' + '\LMP_RT_' + Y1 + M1 + D1 + '.zip'
# =============================================================================
        #output3 = r'/Users/isabelmartinez/Downloads/ThesisCode/Data_2024/LMP/' + '/LMP_FM_' + Y1 + M1 + D1 + '.zip'
        
        # create zip files
# =============================================================================
#         r1 = requests.get(url)
#         r2 = requests.get(ur2)
# =============================================================================
        #r3 = requests.get(ur3)
        
# =============================================================================
#         with open(output1, 'wb') as f:
#             f.write(r1.content)
#             
#         with open(output2, 'wb') as f:     
#             f.write(r2.content)
# =============================================================================
            
    #with open(output3, 'wb') as f:     
        #f.write(r3.content)
        
    #time.sleep(50)



        
        
        


    
    
