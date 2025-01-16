# -*- coding: utf-8 -*-
"""
Created on Fri Aug 11 07:05:41 2023

@author: Anne
"""
import numpy as np
import calendar
from datetime import datetime
from datetime import timedelta
import requests
import time

year = 2022


for month in np.array(range(11))+2:
    #month = 1    
    num_days = calendar.monthrange(year,month)[1] 


    for day in np.array(range(num_days))+1: 
        # day = 2       
        ThisDate1 = datetime(year,month,day)
        ThisDate2 = ThisDate1 + timedelta(hours=24)
        Y1 = 2024#ThisDate1.strftime("%Y")
        M1 = 3#ThisDate1.strftime("%m")
        D1 = 10#ThisDate1.strftime("%d")
        Y2 = 2024#ThisDate2.strftime("%Y")
        M2 = 3#ThisDate2.strftime("%m")
        D2 = 11#ThisDate2.strftime("%d")

        
# =============================================================================
#         # DA LMP
#         #http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_LMP&version=12&startdatetime=
#         #20230811T07:00-0000&enddatetime=20230812T07:00-0000&market_run_id=DAM&node=UCM_6_N001            
#         url = r'http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_LMP&version=12&startdatetime=' + \
#             Y1 + M1 + D1 + 'T07:00-0000&enddatetime=' + Y2 + M2 + D2 + 'T07:00-0000' + \
#                 '&market_run_id=DAM&node=UCM_6_N001'
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
        
        ur3 = r'http://oasis.caiso.com/oasisapi/SingleZip?resultformat=6&queryname=PRC_INTVL_LMP&version=3&startdatetime=' + \
            Y1 + M1 + D1 + 'T07:00-0000&enddatetime=' + Y2 + M2 + D2 + 'T07:00-0000' + \
                '&market_run_id=RTM&node=UCM_6_N001' 
                
        print(ur3)   
        # output file names
# =============================================================================
#         output1 = r'C:\Users\Anne\Desktop\Total\Data\LMP' + '\LMP_DA_' + Y1 + M1 + D1 + '.zip'
#         output2 = r'C:\Users\Anne\Desktop\Total\Data\LMP' + '\LMP_RT_' + Y1 + M1 + D1 + '.zip'
# =============================================================================
        output3 = r'/Users/isabelmartinez/Downloads/ThesisCode/Data_2024/LMP/' + '/LMP_FM_' + Y1 + M1 + D1 + '.zip'
        
        # create zip files
# =============================================================================
#         r1 = requests.get(url)
#         r2 = requests.get(ur2)
# =============================================================================
        r3 = requests.get(ur3)
        
# =============================================================================
#         with open(output1, 'wb') as f:
#             f.write(r1.content)
#             
#         with open(output2, 'wb') as f:     
#             f.write(r2.content)
# =============================================================================
            
    with open(output3, 'wb') as f:     
        f.write(r3.content)
        
    time.sleep(50)



        
        
        


    
    
