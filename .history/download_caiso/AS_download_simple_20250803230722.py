# -*- coding: utf-8 -*-
# author: yuying @ 2025/04/18
"""
Simple script using local caiso_fixed.py for CAISO data downloading
"""

import numpy as np
import calendar
from datetime import datetime
from datetime import timedelta
import requests
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.dates as mdates
import warnings
import os

# Import your local caiso_fixed.py
import caiso_fixed
from caiso_fixed import CAISO

warnings.filterwarnings("ignore")


def AS_download(year, market):
    iso = CAISO()

    if market == 'DAM':
        # df = iso.get_as_prices(date="Oct 15, 2022")  # specific date
        df = iso.get_as_prices(date=f"Jan 1, {year}", end=f"Aug 1, {year}", market=market, verbose=True)  # whole range
    else:
        # df = iso.get_interval_as_prices(date="Oct 15, 2022")  # specific date
        df = iso.get_interval_as_prices(date=f"Jan 1, {year}", end=f"Aug 1, {year}", market=market, verbose=True)  # whole range
    df.to_csv('/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024/2025Data/LMP_AS_{}/AS_price_{}.csv'.format(market, year), index=False)
    # print(df.head())


def AS_process(year, market):
    df_all = pd.read_csv('/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024/2025Data/LMP_AS_{}/AS_price_{}.csv'.format(market, year))
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

    df.to_csv('/Users/admin/Desktop/EV_program/Total Transfer/PowerFlex_Code/UPSCALeDEV_2024/2025Data/LMP_AS_{}/AS_price_{}_{}.csv'.format(market, year, market), index=False)


if __name__ == '__main__':
    year = 2025

    # Download Ancillary service price
    markets = ["DAM", 'RTM']
    for market in markets:
        print(f"Downloading AS prices for {market} in {year}...")
        AS_download(year, market)
        AS_process(year, market) 