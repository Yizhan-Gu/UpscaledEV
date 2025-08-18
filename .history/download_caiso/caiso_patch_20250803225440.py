"""
Patch to add get_interval_as_prices method to gridstatus CAISO class
"""

import pandas as pd
from gridstatus import CAISO
from gridstatus.decorators import support_date_range


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

    # Define the dataset configuration for interval AS prices
    dataset_config = {
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
    }

    # Use the existing get_oasis_dataset method
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


# Add the method to the CAISO class
CAISO.get_interval_as_prices = get_interval_as_prices 