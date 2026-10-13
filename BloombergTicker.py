
from pathlib import Path
import pandas as pd
from xbbg import blp
import pyarrow.parquet as pq

print("hello from BloombergTicker_v2.py")

class BloombergTicker:

    def __init__(
        self,
        tickers: str,
        cache_dir: str,  #  r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData"
        field: str = "PX_LAST"
    ):

        self.tickers = tickers
        self.field = field

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.cache_file = (
            self.cache_dir /
            f"{self._safe_name(tickers)}.parquet"
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
    def data(self):

        if self._data is None:
            self.load()

        return self._data

    def load(self) -> pd.DataFrame:

        '''
        Already cached datasets we just load
        
        '''

        if self.cache_file.exists():

            self._data = pd.read_parquet(
                self.cache_file
            )

            self._data.index = pd.to_datetime(
                self._data.index
            )

        else:

            self._data = pd.DataFrame()

        return self._data

    def update(
        self,
        start_date=None ,#change later back to "2000-01-01" or whatever
        end_date=None
    ) -> pd.DataFrame:

        existing = self.load()

        #if len(existing):
        if not existing.empty:
            
            last_date = existing.index.max()
            today = pd.Timestamp.today().normalize()
            if last_date >= today:
                print(
                    f"{self.tickers}: cache already current"    
                )
                return existing

            fetch_start = (
                last_date +
                pd.Timedelta(days=1)
            ).strftime("%Y-%m-%d")

        else:

            fetch_start = start_date

        print(
            f"{self.tickers}: "
            f"updating from {fetch_start}"
        )

        print('existing 8=========) ', existing)

        #returns Narwhalas Dataframe
        new_data = blp.bdh(
            tickers=self.tickers,
            flds=self.field,
            start_date=fetch_start,
            end_date=end_date
        ) 
        if len(new_data) == 0:

            return existing
        
        #print("new_data 8=========)", new_data)

        # --------------------------------------------------
        # Convert Narwhals / Arrow output to pandas
        # --------------------------------------------------
        
        native = new_data.to_native()
        #print("native 8===========", native)

        # If Narwhals gives a PyArrow Table
        if hasattr(native, "to_pandas"):
            df = native.to_pandas()
        else:
            # fallback if native is already pandas-like
            df = pd.DataFrame(native)

        # --------------------------------------------------
        # Validate Bloomberg long-format output
        # --------------------------------------------------

        required_cols = {
            "ticker", #note its not tickers here as bdh returns ticker but requries tickerS as argument
            "date", 
            "field", 
            "value"}

        missing_cols = required_cols.difference(df.columns)

        if missing_cols:
            raise ValueError(
                f"Bloomberg output missing columns: {missing_cols}. "
                f"Available columns: {list(df.columns)}"
            )

        # --------------------------------------------------
        # Important: convert the DATE COLUMN, not the index before pivoting. date32[day] is Arrow data type
        # --------------------------------------------------
        df["date"] = pd.to_datetime(df["date"]
                    .astype("datetime64[ns]") #this is key!! arrow converts to datetime64[s]
                    )

        # Keep only PX_LAST
        df = df[
            df["ticker"].eq(self.tickers) 
            & df["field"].eq("PX_LAST")
        ].copy()
        
        #debug:  print("df 8===========", df)
        
        # --------------------------------------------------
        # Pivot long -> wide
        # --------------------------------------------------
        wide = (
            df.pivot_table(
                index="date",
                columns="ticker",#note its not tickers here as bdh returns ticker but requries tickerS as argument
                values="value",
                aggfunc="last"
            )
            .sort_index()
        )
        wide.columns = [self.field] #stored PX_LAST
        wide.columns = [self.tickers] #stores AUDUSD which in eed to create_Techs class!
        wide.index.name = 'date'
        wide.index = pd.to_datetime(wide.index.values) #using .values often stirp away Arrow weirdness
        # Keep requested column order
        #wide = wide.reindex(columns=[self.tickers])

        #debug  print("wide 8========", wide )

        # flatten Bloomberg columns
        #if isinstance(new_data.columns, pd.MultiIndex):
        #if isinstance(df.columns, pd.MultiIndex):
        #if isinstance(wide.columns, pd.MultiIndex):

          #  wide.columns = [
         #       c[1]
           #     for c in wide.columns
           # ]
            
        # --------------------------------------------------
        # Merge with existing cache
        # --------------------------------------------------

        combined = pd.concat(
            [existing, wide] # df] #new_data]
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
        
        #print(type(wide.index))
        #print(wide.index.dtype)
        #print(wide.reset_index)
        
        combined.to_parquet(
            self.cache_file
        )

        #debug 
        #tmp = pd.read_parquet(self.cache_file)

        #print(tmp.index.dtype)

        self._data = combined

        return combined
    
#home :  C:\Users\home\OneDrive\MacroData    
#audusd = BloombergTicker(tickers= "AUDUSD Curncy",
#                      cache_dir = r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData"
#                        )
#udusd.update(start_date= "1990-01-01")
#audusd.data


#test = pd.read_parquet(r"C:\Users\CP85VC\OneDrive - ING\BWAM\MacroData\AUDUSD_Curncy.parquet")
#test.head()#.loc['2026':].plot()
# from marketdata import BloombergTicker