from pathlib import Path
from fredapi import Fred
import pandas as pd
import datetime as dt

import os
#os.listdir() #if cant find apikey txt

cwd = os.getcwd()  
print('current work directory is '+cwd)####used to be C:\Users\CP85VC

#DONT CHANGE DIR FROM HERE, CHANGE FROM ANACONDA PROMPT AND LAUNCH FROM THERE SO CAN USE WORK/OFFICE SAME:
# os.chdir(r'C:\Users\CP85VC\OneDrive - ING\BWAM\PythonFed')
#sys.path #returns all working directories 

from fredapi import Fred

### home
filename = 'FRED_apikey.txt'
#f = open(filename, 'r')

###  office 
f = open("C:/Users/CP85VC/OneDrive - ING/BWAM/FRED_apikey.txt", 'r')

fred_key = f.read().split()[-1] #last string of text file has api key

#The API key is set using the api_key variable, a 32 character lower-cased alpha-numeric string.
f.close()

# Create Fred Object
fred = Fred(api_key = fred_key) #main object for searchign and data pulls

r'''
if i log in from Zbook, my python is in a diff path, so i need to add below for BbgTicker & FredTicker
import sys
sys.path.append(
    r"C:\Users\CP85VC\OneDrive - ING\BWAM\PythonProjectsOffice_2026.08"
    )

## add path for FredTicker.py

sys.path.append(
    r"C:\Users\CP85VC\OneDrive - ING\BWAM\PythonProjectsOffice_2026.08\FredAPI"
    )
'''

class FredTicker:

    def __init__(
        self,
        tickers: str,
        cache_dir: str
    ):

        self.tickers = tickers

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.cache_file = (
            self.cache_dir
            / f"{self._safe_name(tickers)}.parquet"
        )

        self._data = None

    @staticmethod
    def _safe_name(tickers: str) -> str:
        return (
            tickers
            .replace(" ", "_")
            .replace("/", "_")
        )

    @property
    def data(self) -> pd.DataFrame:

        if self._data is None:
            self.load()

        return self._data

    def load(self) -> pd.DataFrame:

        if self.cache_file.exists():

            self._data = pd.read_parquet(
                self.cache_file
            )

            self._data.index = pd.to_datetime(
                self._data.index
            )

            self._data.index.name = "date"

        else:

            self._data = pd.DataFrame(
                columns=[self.tickers],
                dtype=float
            )

            self._data.index = pd.DatetimeIndex(
                [],
                name="date"
            )

        return self._data

    def update(
        self,
        start_date=None,
        end_date=None
    ) -> pd.DataFrame:

        existing = self.load()

        # --------------------------------------------------
        # Determine where the FRED download should begin
        # --------------------------------------------------

        if not existing.empty:

            last_date = existing.index.max()
            today = pd.Timestamp.today().normalize()

            if last_date >= today:

                print(
                    f"{self.tickers}: cache already current"
                )

                return existing

            fetch_start = (
                last_date
                + pd.Timedelta(days=1)
            ).strftime("%Y-%m-%d")

        else:

            fetch_start = start_date

        print(
            f"{self.tickers}: "
            f"updating from {fetch_start}"
        )

        # --------------------------------------------------
        # Download from FRED
        # fred.get_series() returns a pandas Series
        # --------------------------------------------------

        new_data = fred.get_series(
            self.tickers,
            observation_start=fetch_start,
            observation_end=end_date
        )

        if new_data is None or new_data.empty:

            print(
                f"{self.tickers}: no new observations"
            )

            return existing

        # --------------------------------------------------
        # Convert the FRED Series to a DataFrame
        # --------------------------------------------------

        new_data = new_data.to_frame(
            name=self.tickers
        )

        new_data.index = pd.to_datetime(
            new_data.index
        )

        new_data.index.name = "date"

        # Ensure values are numeric
        new_data[self.tickers] = pd.to_numeric(
            new_data[self.tickers],
            errors="coerce"
        )

        # --------------------------------------------------
        # Merge with existing cache
        # --------------------------------------------------

        combined = pd.concat(
            [existing, new_data]
        )

        combined = (
            combined
            .sort_index()
            .loc[
                ~combined.index.duplicated(
                    keep="last"
                )
            ]
        )

        # --------------------------------------------------
        # Save updated cache
        # --------------------------------------------------

        combined.to_parquet(
            self.cache_file
        )

        self._data = combined

        print(
            f"{self.tickers}: "
            f"cache updated to {combined.index.max():%Y-%m-%d}"
        )

        return combined


cache_dir = (r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData")


r'''
test = FredTicker('FEDFUNDS', cache_dir)

df_test =  test.update(start_date= dt.datetime(1940,5,5), end_date= None)
df_test.tail()


fedfunds = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\FEDFUNDS.parquet")
fedfunds.loc['2024-09':'2024-10']  #

mask = abs(fedfunds['FEDFUNDS'].diff()) > 0.10
mask.loc['2024':]
fedfunds.loc[mask].loc['2023':]
fedfunds.tail(10)

pcCore = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\PCEPILFE.parquet")
pcCore.tail(2)

pcCoreYoY = pcCore.pct_change(12)

spoos = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\SPX_Index.parquet")
twos = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\USGG2YR_Index.parquet")
tens = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\USGG10YR_Index.parquet")

fedfunds_pce = pd.concat([fedfunds/100, pcCoreYoY, twos/100, tens/100, spoos ], axis = 1).ffill() 

fedfunds_pce.loc['2018':].plot(grid = True, figsize = (12,6), secondary_y = 'SPX Index')

ax = fedfunds_pce.loc['2018':].drop(columns = 'SPX Index').plot(grid = True, figsize = (12,6))

fedfunds_pce.loc['2018':, 'SPX Index'].plot(ax = ax, secondary_y = True, ls = '--', color = 'grey')
fedfunds_pce.plot()



usdcnh = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\USDCNH_Curncy.parquet")
usdcnh6m  = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\USDCNH6M_Curncy.parquet")
usdcnh_fam = pd.concat([usdcnh, usdcnh6m], axis = 1)
usdcnh_fam.tail()

usdcnh_fam.loc['2018':].plot(grid = True, figsize = (12,6), secondary_y= ['USDCNH6M Curncy'])

'''
