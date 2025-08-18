import copy
import io
import time
import warnings
from contextlib import redirect_stderr
from zipfile import ZipFile

import numpy as np
import pandas as pd
import requests
import tabula
from tabulate import tabulate
from termcolor import colored

# Import only what's available from gridstatus
from gridstatus import utils
from gridstatus.base import (
    GridStatus,
    ISOBase,
    Markets,
    NoDataFoundException,
    NotSupported,
)
from gridstatus.decorators import support_date_range
from gridstatus.gs_logging import logger
from gridstatus.lmp_config import lmp_config

# Create a simple caiso_utils replacement
def make_timestamp(time_str, today, timezone):
    """Simple replacement for caiso_utils.make_timestamp"""
    from datetime import datetime
    import pytz
    
    # Parse the time string and combine with today's date
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    combined = datetime.combine(today.date(), time_obj)
    
    # Localize to the timezone
    tz = pytz.timezone(timezone)
    return tz.localize(combined)

def check_latest_value_time(df, column):
    """Simple replacement for caiso_utils.check_latest_value_time"""
    # Find the last non-null value in the specified column
    last_valid = df[column].dropna().iloc[-1] if not df[column].dropna().empty else None
    return last_valid

# Create caiso_utils module
class caiso_utils:
    make_timestamp = make_timestamp
    check_latest_value_time = check_latest_value_time

CURRENT_BASE = "https://www.caiso.com/outlook/current"
HISTORY_BASE = "https://www.caiso.com/outlook/history"

DAY_AHEAD_MARKET_MARKET_RUN_ID = "DAM"
REAL_TIME_DISPATCH_MARKET_RUN_ID = "RTD"

OASIS_DATASET_CONFIG = {
    "transmission_interface_usage": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "TRNS_USAGE",
            "version": 1,
        },
        "params": {
            "market_run_id": ["DAM", "HASP", "RRPD"],
            # you can also specify a specific interface
            "ti_id": "ALL",
            "ti_direction": ["ALL", "E", "I"],
        },
    },
    "schedule_by_tie": {
        "query": {
            "path": "GroupZip",
            "resultformat": 6,
            "version": 12,
        },
        "params": {
            "groupid": [
                "RTD_ENE_SCH_BY_TIE_GRP",
                "DAM_ENE_SCH_BY_TIE_GRP",
                "RUC_ENE_SCH_BY_TIE_GRP",
                "RTPD_ENE_SCH_BY_TIE_GRP",
            ],
        },
        "meta": {
            "max_query_frequency": "1d",
        },
    },
    "as_requirements": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "AS_REQ",
            "version": 1,
        },
        "params": {
            "market_run_id": ["DAM", "HASP", "RTM", "2DA"],
            "anc_type": ["ALL", "NR", "RD", "RU", "SR", "RMD", "RMU"],
            "anc_region": [
                "ALL",
                "AS_CAISO",
                "AS_CAISO_EXP",
                "AS_NP26",
                "AS_NP26_EXP",
                "AS_SP26",
                "AS_SP26_EXP",
            ],
        },
    },
    "as_clearing_prices": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_AS",
            "version": 12,
        },
        "params": {
            "market_run_id": ["DAM", "HASP"],
            "anc_type": ["ALL", "NR", "RD", "RMD", "RMU", "RU", "SR"],
            "anc_region": [
                "ALL",
                "AS_CAISO",
                "AS_SP26_EXP",
                "AS_SP26",
                "AS_CAISO_EXP",
                "AS_NP26_EXP",
                "AS_NP26",
            ],
        },
    },
    # add by YY @ 2025/04/18
    "as_interval_clearing_prices": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_INTVL_AS",
            "version": 1,
        },
        "params": {
            "market_run_id": ["RTM"],
            "anc_type": ["ALL", "NR", "RD", "RMD", "RMU", "RU", "SR"],
            "anc_region": [
                "ALL",
                "AS_CAISO",
                "AS_SP26_EXP",
                "AS_SP26",
                "AS_CAISO_EXP",
                "AS_NP26_EXP",
                "AS_NP26",
            ],
        },
    },
    #
    "fuel_prices": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_FUEL",
            "version": 1,
        },
        "params": {
            "fuel_region_id": "ALL",
        },
    },
    "ghg_allowance": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_GHG_ALLOWANCE",
            "version": 1,
        },
        "params": {},
    },
    "wind_and_solar_forecast": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "SLD_REN_FCST",
            "version": 1,
        },
        "params": {"market_run_id": "DAM"},
    },
    "pnode_map": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "ATL_PNODE_MAP",
            "version": 1,
        },
        "params": {
            "pnode_id": "ALL",
        },
    },
    "lmp_day_ahead_hourly": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_LMP",
            "version": 12,
        },
        "params": {
            "market_run_id": "DAM",
            "node": None,
            "grp_type": [None, "ALL", "ALL_APNODES"],
        },
    },
    "lmp_real_time_5_min": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_INTVL_LMP",
            "version": 3,
        },
        "params": {
            "market_run_id": "RTM",
            "node": None,
            "grp_type": [None, "ALL", "ALL_APNODES"],
        },
    },
    "lmp_real_time_15_min": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "PRC_RTPD_LMP",
            "version": 3,
        },
        "params": {
            "market_run_id": "RTPD",
            "node": None,
            "grp_type": [None, "ALL", "ALL_APNODES"],
        },
    },
    "demand_forecast": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "SLD_FCST",
            "version": 1,
        },
        "params": {
            "market_run_id": ["7DA", "2DA", "DAM", "ACTUAL", "RTM"],
        },
    },
    "as_results": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "AS_RESULTS",
            "version": 1,
        },
        "params": {
            "market_run_id": ["DAM", "HASP", "RTM"],
            "anc_type": ["ALL", "NR", "RD", "RU", "SR", "RMD", "RMU"],
            "anc_region": [
                "ALL",
                "AS_CAISO",
                "AS_CAISO_EXP",
                "AS_NP26",
                "AS_NP26_EXP",
                "AS_SP26",
                "AS_SP26_EXP",
            ],
        },
    },
    "excess_btm_production": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "ENE_EBTMP_PERF_DATA",
            "version": 11,
        },
        "params": {},
        "meta": {
            "publish_delay": "3 months",
        },
    },
    "public_bids": {
        "query": {
            "path": "GroupZip",
            "resultformat": 6,
            "version": 3,
        },
        "params": {
            "groupid": ["PUB_DAM_GRP", "PUB_RTM_GRP"],
        },
        "meta": {
            "publish_delay": "90 days",
            "max_query_frequency": "1d",
        },
    },
    "tie_flows_real_time": {
        "query": {
            "path": "SingleZip",
            "resultformat": 6,
            "queryname": "ENE_EIM_TRANSFER_TIE",
            "version": 4,
        },
        "params": {
            "baa_grp_id": "ALL",
            "market_run_id": REAL_TIME_DISPATCH_MARKET_RUN_ID,
        },
    },
    "tie_schedule_day_ahead_hourly": {
        "query": {
            "path": "GroupZip",
            "resultformat": 6,
            "version": 12,
        },
        "params": {
            "groupid": ["DAM_ENE_SCH_BY_TIE_GRP"],
            "market_run_id": DAY_AHEAD_MARKET_MARKET_RUN_ID,
        },
    },
}


def _determine_lmp_frequency(args: dict) -> str:
    """if querying all must use 1d frequency"""
    locations = args.get("locations", "")
    market = args.get("market", "")
    # due to limitations of OASIS api
    if isinstance(locations, str) and locations.lower() in ["all", "all_ap_nodes"]:
        if market == Markets.REAL_TIME_5_MIN:
            return "1h"
        elif market == Markets.REAL_TIME_15_MIN:
            return "1h"
        elif market == Markets.DAY_AHEAD_HOURLY:
            return "1D"
        else:
            raise NotSupported(f"Market {market} not supported")
    else:
        return "31D"


def _determine_oasis_frequency(args: dict) -> str:
    dataset_config = copy.deepcopy(OASIS_DATASET_CONFIG[args["dataset"]])
    # get meta if it exists. and then max_query_frequency if it exists
    meta = dataset_config.get("meta", {})
    max_query_frequency = meta.get("max_query_frequency", None)
    if max_query_frequency is not None:
        return max_query_frequency

    return "31D"


def _get_historical(
    file: str,
    date: str | pd.Timestamp,
    column: str,
    verbose: bool = False,
) -> pd.DataFrame:
    """Get the historical data file from CAISO given a data series name, formats, and returns a pandas dataframe.

    Args:
        file (str): The name of the data we are wanting, which is equivalent to the file to get from CAISO
        date (str | pd.Timestamp): The date of the data to get from CAISO
        column (str): The column to check for the latest value time
        verbose (bool, optional): Whether to print out the URL being fetched, defaults to False

    Returns:
        pd.DataFrame: A pandas dataframe of the data
    """
    # NOTE: The cache buster is necessary because CAISO will serve cached data from cloudfront on the same url if the url has not changed.
    cache_buster = int(pd.Timestamp.now(tz=CAISO.default_timezone).timestamp())
    if utils.is_today(date, CAISO.default_timezone):
        url: str = f"{CURRENT_BASE}/{file}.csv?_={cache_buster}"
        latest = True
    else:
        date_str: str = date.strftime("%Y%m%d")
        url: str = f"{HISTORY_BASE}/{date_str}/{file}.csv?_={cache_buster}"
        latest = False
    logger.info(f"Fetching URL: {url}")
    df = pd.read_csv(url)

    # sometimes there are extra rows at the end, so this lets us ignore them
    df = df.dropna(subset=["Time"])

    # drop every column after Time where values
    # are all null. this happens during spring DST
    # change and caiso keeps the non-existent hour
    # but has nulls for all other columns
    df = df.dropna(subset=df.columns[1:], how="all")

    # for the latest data, we want to check if the data is actually from the previous day and update the date accordingly
    if latest:
        latest_file_time = caiso_utils.check_latest_value_time(df, column)
        current_caiso_time = pd.Timestamp.now(tz=CAISO.default_timezone)

        if latest_file_time > current_caiso_time:
            date = date - pd.Timedelta(days=1)

    df["Time"] = df["Time"].apply(
        caiso_utils.make_timestamp,
        today=date,
        timezone=CAISO.default_timezone,
    )

    # sometimes returns midnight, which is technically the next day
    # to be careful, let's check if that is the case before dropping
    if df.iloc[-1]["Time"].hour == 0:
        df = df.iloc[:-1]

    # insert interval start/end columns
    df.insert(1, "Interval Start", df["Time"])

    # be careful if this is ever not 5 minutes
    df.insert(2, "Interval End", df["Time"] + pd.Timedelta(minutes=5))

    return df


def _caiso_handle_start_end(
    date: str | pd.Timestamp,
    end: str | pd.Timestamp | None = None,
) -> tuple[str, str]:
    start = date.tz_convert("UTC")

    if end:
        end = end
        end = end.tz_convert("UTC")
    else:
        end = start + pd.DateOffset(1)

    start = start.strftime("%Y%m%dT%H:%M-0000")
    end = end.strftime("%Y%m%dT%H:%M-0000")

    return start, end


class CAISO(ISOBase):
    """California Independent System Operator (CAISO)"""

    name = "California ISO"
    iso_id = "caiso"
    default_timezone = "US/Pacific"

    status_homepage = "https://www.caiso.com/TodaysOutlook/Pages/default.aspx"
    interconnection_homepage = "https://rimspub.caiso.com/rimsui/logon.do"

    # Markets PRC_INTVL_LMP, PRC_RTPD_LMP, PRC_LMP
    markets = [
        Markets.REAL_TIME_5_MIN,
        Markets.REAL_TIME_15_MIN,
        Markets.DAY_AHEAD_HOURLY,
    ]

    trading_hub_locations = [
        "TH_NP15_GEN-APND",
        "TH_SP15_GEN-APND",
        "TH_ZP26_GEN-APND",
    ]

    def _current_day(self):
        # get current date from stats api
        return self.get_status(date="latest").time.date()

    def get_stats(self, verbose: bool = False) -> dict:
        stats_url = CURRENT_BASE + "/stats.txt"
        r = self._get_json(stats_url, verbose=verbose)
        return r

    def get_status(self, date: str = "latest", verbose: bool = False) -> str:
        """Get Current Status of the Grid. Only date="latest" is supported

        Known possible values: Normal, Restricted Maintenance Operations, Flex Alert
        """

        if date == "latest":
            # todo is it possible for this to return more than one element?
            r = self.get_stats(verbose=verbose)

            time = pd.to_datetime(r["slotDate"]).tz_localize("US/Pacific")
            # can only store one value for status so we concat them together
            status = ", ".join(r["gridstatus"])
            reserves = r["Current_reserve"]

            return GridStatus(time=time, status=status, reserves=reserves, iso=self)
        else:
            raise NotSupported()

    def list_oasis_datasets(self, dataset: str | None = None):
        """List all available OASIS datasets and their parameters.

        Args:
            dataset (str, optional): dataset to return data for. If None, returns all datasets.
        """

        for dataset_name, config in OASIS_DATASET_CONFIG.items():
            if dataset is not None and dataset_name not in dataset:
                continue
            print(colored(f"Dataset: {dataset_name}", "cyan"))
            if len(config["params"]) == 0:
                print("    No parameters")
            else:
                table_data = []
                for k, v in config["params"].items():
                    default = v[0] if isinstance(v, list) else v
                    possible_values = (
                        ", ".join(str(val) for val in v)
                        if isinstance(v, list)
                        else "N/A"
                    )
                    table_data.append([k, default, possible_values])

                print(
                    tabulate(
                        table_data,
                        headers=[
                            "Parameter",
                            "Default",
                            "Possible Values",
                        ],
                        tablefmt="grid",
                    ),
                )

            print("\n")

    @support_date_range(frequency=_determine_oasis_frequency)
    def get_oasis_dataset(
        self,
        dataset: str,
        date: str | pd.Timestamp,
        end: str | pd.Timestamp | None = None,
        params: dict | None = None,
        raw_data: bool = True,
        sleep: int = 5,
        verbose: bool = False,
    ) -> pd.DataFrame:
        """Return data from OASIS for a given dataset

        Args:
            dataset (str): dataset to return data for. See CAISO.list_oasis_datasets
                for supported datasets
            date (str, pd.Timestamp): date to return data
            end (str, pd.Timestamp, optional): last date of range to return data.
                If None, returns only date. Defaults to None.
            params (dict): dictionary of parameters to pass to dataset.
                See CAISO.list_oasis_datasets for supported parameters
            raw_data (bool, optional): return raw data from OASIS. Defaults to True.
            sleep (int, optional): number of seconds to sleep between
                requests. Defaults to 5.
            verbose (bool, optional): print out url being fetched. Defaults to False.

        Raises:
            ValueError: if parameter is not supported for dataset
            ValueError: if parameter value is not supported for dataset

        Returns:
            pd.DataFrame: A DataFrame of data from OASIS
        """

        # deepcopy to avoid modifying original
        dataset_config = copy.deepcopy(OASIS_DATASET_CONFIG[dataset])
        logger.debug(f"Dataset config: {dataset_config}")

        if params is None:
            params = {}

        for p in params:
            if p not in dataset_config["params"]:
                raise ValueError(
                    f"Parameter {p} not supported for dataset {dataset}",
                )

            # if it's a list, make sure param value is in list
            if (
                isinstance(dataset_config["params"][p], list)
                and params[p] not in dataset_config["params"][p]
            ):
                raise ValueError(
                    f"Parameter {p} not supported for dataset {dataset}",
                )

            dataset_config["params"][p] = params[p]

        # if any dataset_config values are list,
        # take first as default
        for k, v in dataset_config["params"].items():
            if isinstance(v, list):
                dataset_config["params"][k] = v[0]

        # combine kv from query and params
        config_flat = {
            **dataset_config["query"],
            **dataset_config["params"],
        }

        # filter out null values
        config_flat = {k: v for k, v in config_flat.items() if v is not None}

        df = self._get_oasis(
            config=config_flat,
            start=date,
            end=end,
            raw_data=raw_data,
            verbose=verbose,
            sleep=sleep,
        )

        if df is None:
            if end:
                logger.warning(f"No data for {date} to {end}")
            else:
                logger.warning(f"No data for {date}")
            return pd.DataFrame()

        return df

    def _get_oasis(
        self,
        config: dict,
        start: str | pd.Timestamp,
        end: str | pd.Timestamp | None = None,
        raw_data: bool = False,
        verbose: bool = False,
        sleep: int = 5,
    ) -> pd.DataFrame | None:
        start, end = _caiso_handle_start_end(start, end)
        config = copy.deepcopy(config)
        config["startdatetime"] = start
        config["enddatetime"] = end

        base_url = f"http://oasis.caiso.com/oasisapi/{config.pop('path')}?"

        url = base_url + "&".join(
            [f"{k}={v}" for k, v in config.items()],
        )

        logger.info(f"Fetching URL: {url}")

        retry_num = 0
        while retry_num < 3:
            r = requests.get(url)

            if r.status_code == 200:
                break

            retry_num += 1
            logger.error(f"Failed to get data from CAISO. Error: {r.status_code}")
            logger.error(f"Retrying {retry_num}...")
            time.sleep(sleep)

        # this is when no data is available
        if (
            "Content-Disposition" not in r.headers
            or ".xml.zip;" in r.headers["Content-Disposition"]
            or b".xml" in r.content
        ):
            # avoid rate limiting
            time.sleep(sleep)
            return None

        z = ZipFile(io.BytesIO(r.content))

        # parse and concat all files
        dfs = []
        logger.debug(f"Found {len(z.namelist())} files: {z.namelist()}")
        for f in z.namelist():
            logger.debug(f"Parsing file: {f}")
            df = pd.read_csv(z.open(f))
            dfs.append(df)
        df = pd.concat(dfs)

        # if col ends in _GMT, then try to parse as UTC
        for col in df.columns:
            if col.endswith("_GMT"):
                df[col] = pd.to_datetime(
                    df[col],
                    utc=True,
                )

        # handle different column names
        # across different datasets
        start_cols = [
            "INTERVALSTARTTIME_GMT",
            "INTERVAL_START_GMT",
            "STARTTIME_GMT",
            "START_DATE_GMT",
        ]
        end_cols = [
            "INTERVALENDTIME_GMT",
            "INTERVAL_END_GMT",
            "ENDTIME_GMT",
            "END_DATE_GMT",
        ]
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

        if not raw_data and start_col in df.columns:
            df[start_col] = df[start_col].dt.tz_convert(
                CAISO.default_timezone,
            )

            df[end_col] = df[end_col].dt.tz_convert(
                CAISO.default_timezone,
            )

            df.rename(
                columns={
                    start_col: "Interval Start",
                    end_col: "Interval End",
                },
                inplace=True,
            )

            df.insert(0, "Time", df["Interval Start"])

        # avoid rate limiting
        time.sleep(sleep)

        return df

    # NOTE: added by YY_XIE @ 2025/04/18 for ancillary service price for RTM
    @support_date_range(frequency="HOUR_START") # AK: modified to "HOUR_START" instead of "DAY_START"
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

        params = {
            "market_run_id": market,
        }

        df = self.get_oasis_dataset(
            dataset="as_interval_clearing_prices",
            start=date,
            end=end,
            params=params,
            sleep=sleep,
            verbose=verbose,
            raw_data=False,
        )

        df = df.rename(
            columns={
                "ANC_REGION": "Region",
                "MARKET_RUN_ID": "Market",
            },
        )

        as_type_map = {
            "NR": "Non-Spinning Reserves",
            "RD": "Regulation Down",
            "RMD": "Regulation Mileage Down",
            "RMU": "Regulation Mileage Up",
            "RU": "Regulation Up",
            "SR": "Spinning Reserves",
        }
        df["ANC_TYPE"] = df["ANC_TYPE"].map(as_type_map)

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

        return df 