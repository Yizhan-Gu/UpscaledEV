"""
Simple patch to add get_interval_as_prices method to gridstatus CAISO class
"""

import pandas as pd
import requests
import time
import io
from zipfile import ZipFile
from gridstatus import CAISO


def get_interval_as_prices(
    self,
    date: str | pd.Timestamp,
    end: str | pd.Timestamp | None = None,
    market: str = "RTM",
    sleep: int = 10,
    verbose: bool = True,
) -> pd.DataFrame:
    """Return AS prices for a given date for each region

    Arguments:
        date (datetime.date, str): date to return data

        end (datetime.date, str): last date of range to return data.
            If None, returns only date. Defaults to None.

        market (str): Defaults to RTM.

        verbose (bool, optional): print out url being fetched. Defaults to False.

    Returns:
        pandas.DataFrame: A DataFrame of AS prices
    """

    # Handle date range
    if end is None:
        end = date + pd.Timedelta(days=1)
    
    # Convert to UTC format
    start_str = pd.to_datetime(date).tz_convert("UTC").strftime("%Y%m%dT%H:%M-0000")
    end_str = pd.to_datetime(end).tz_convert("UTC").strftime("%Y%m%dT%H:%M-0000")

    # Build OASIS API URL
    base_url = "http://oasis.caiso.com/oasisapi/SingleZip?"
    params = {
        "resultformat": 6,
        "queryname": "PRC_INTVL_AS",
        "version": 1,
        "market_run_id": market,
        "anc_type": "ALL",
        "anc_region": "ALL",
        "startdatetime": start_str,
        "enddatetime": end_str,
    }

    url = base_url + "&".join([f"{k}={v}" for k, v in params.items()])

    if verbose:
        print(f"Fetching URL: {url}")

    # Make request with retries
    retry_num = 0
    while retry_num < 3:
        r = requests.get(url)

        if r.status_code == 200:
            break

        retry_num += 1
        print(f"Failed to get data from CAISO. Error: {r.status_code}")
        print(f"Retrying {retry_num}...")
        time.sleep(sleep)

    # Check if we got valid data
    if (
        "Content-Disposition" not in r.headers
        or ".xml.zip;" in r.headers["Content-Disposition"]
        or b".xml" in r.content
    ):
        time.sleep(sleep)
        return pd.DataFrame()

    # Parse the zip file
    z = ZipFile(io.BytesIO(r.content))

    # Parse and concat all files
    dfs = []
    for f in z.namelist():
        df = pd.read_csv(z.open(f))
        dfs.append(df)
    
    if not dfs:
        return pd.DataFrame()
    
    df = pd.concat(dfs)

    # Handle time columns
    for col in df.columns:
        if col.endswith("_GMT"):
            df[col] = pd.to_datetime(df[col], utc=True)

    # Find start and end time columns
    start_cols = ["INTERVALSTARTTIME_GMT", "INTERVAL_START_GMT", "STARTTIME_GMT", "START_DATE_GMT"]
    end_cols = ["INTERVALENDTIME_GMT", "INTERVAL_END_GMT", "ENDTIME_GMT", "END_DATE_GMT"]
    
    start_col = None
    end_col = None
    for col in start_cols:
        if col in df.columns:
            start_col = col
            df = df.sort_values(by=start_col)
            break
    for col in end_cols:
        if col in df.columns:
            end_col = col
            break

    if start_col in df.columns:
        df[start_col] = df[start_col].dt.tz_convert("US/Pacific")
        df[end_col] = df[end_col].dt.tz_convert("US/Pacific")

        df.rename(
            columns={
                start_col: "Interval Start",
                end_col: "Interval End",
            },
            inplace=True,
        )

        df.insert(0, "Time", df["Interval Start"])

    # Rename columns
    df = df.rename(
        columns={
            "ANC_REGION": "Region",
            "MARKET_RUN_ID": "Market",
        },
    )

    # Map AS types
    as_type_map = {
        "NR": "Non-Spinning Reserves",
        "RD": "Regulation Down",
        "RMD": "Regulation Mileage Down",
        "RMU": "Regulation Mileage Up",
        "RU": "Regulation Up",
        "SR": "Spinning Reserves",
    }
    df["ANC_TYPE"] = df["ANC_TYPE"].map(as_type_map)

    # Pivot the data
    df = df.pivot_table(
        index=[
            "Time",
            "Interval Start",
            "Interval End",
            "Region",
            "Market",
        ],
        columns="ANC_TYPE",
        values="MW",
    ).reset_index()

    df = df.fillna(0)
    df.columns.name = None

    # Avoid rate limiting
    time.sleep(sleep)

    return df


# Add the method to the CAISO class
CAISO.get_interval_as_prices = get_interval_as_prices 