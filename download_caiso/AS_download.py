# -*- coding: utf-8 -*-
# author: yuying @ 2025/04/18
"""
code use gridstatus for data download (e.g. LMP, AS) from OASIS dataset, find more details below:
https://opensource.gridstatus.io/en/latest/autoapi/gridstatus/caiso/index.html#gridstatus.caiso.CAISO.get_as_prices"

Note:
1) caiso.py has been revised for RTM AS prices download
2) python 3.11 or higher are needed
3) requirement.txt file has been saved

"""

import numpy as np
import calendar
from datetime import datetime
from datetime import timedelta
import requests
import time
import pandas as pd
import matplotlib.pyplot as plt
import gridstatus
# import plotly.express as px
import matplotlib
import matplotlib.dates as mdates
import warnings

warnings.filterwarnings("ignore")


def AS_download(year, market):
    iso = gridstatus.CAISO()

    if market == 'DAM':
        # df = iso.get_as_prices(date="Oct 15, 2022")  # specific date
        df = iso.get_as_prices(start=f"May 1, {year}", end=f"Jan 1, {year + 1}", market=market)  # whole range
    else:
        # df = iso.get_interval_as_prices(date="Oct 15, 2022")  # specific date
        df = iso.get_interval_as_prices(start=f"May 1, {year}", end=f"Jan 1, {year + 1}", market=market)
    df.to_csv('./Exp_data22/LMP_AS_{}/AS_price_{}.csv'.format(market, year), index=False)
    # print(df.head())


def AS_process(year, market):
    df_all = pd.read_csv('./Exp_data22/LMP_AS_{}/AS_price_{}.csv'.format(market, year))
    df = df_all[(df_all["Region"] == "AS_CAISO_EXP") & (df_all["Market"] == market)]
    # df = df_all[(df_all["Region"] == "AS_CAISO") & (df_all["Market"] == market)]

    df['Time'] = pd.to_datetime(df['Time'], utc=True)
    df['datetime'] = df['Time'].dt.tz_convert(None)
    df.drop(columns=['Time', 'Interval Start', 'Interval End'], inplace=True)
    df = df.groupby(['datetime']).agg({
        'Non-Spinning Reserves': 'sum',
        'Regulation Down': 'sum',
        'Regulation Mileage Down': 'sum',
        'Regulation Mileage Up': 'sum',
        'Regulation Up': 'sum',
        'Spinning Reserves': 'sum'}).reset_index()
    df.rename(columns={
        'Non-Spinning Reserves': 'NonSpin',
        'Regulation Down': 'RegDown',
        'Regulation Mileage Down': 'RegDownMileage',
        'Regulation Mileage Up': 'RegUpMileage',
        'Regulation Up': 'RegUp',
        'Spinning Reserves': 'Spin'
    }, inplace=True)

    df.to_csv('./Exp_data22/LMP_AS_{}/AS_price_{}_{}.csv'.format(market, year, market), index=False)


if __name__ == '__main__':
    year = 2022

    # Download Ancillary service price
    markets = ["DAM", 'RTM']
    for market in markets:
        print(year, market)
        AS_download(year, market)
        AS_process(year, market)








