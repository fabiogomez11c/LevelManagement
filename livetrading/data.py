from queue import Queue
from binance import Client

import pandas as pd
import numpy as np
import datetime as dt

seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}

CONSTANTS = {
    '1m': Client.KLINE_INTERVAL_1MINUTE,
    '3m': Client.KLINE_INTERVAL_3MINUTE,
    '5m': Client.KLINE_INTERVAL_5MINUTE,
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '2h': Client.KLINE_INTERVAL_2HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
    '6h': Client.KLINE_INTERVAL_6HOUR,
    '8h': Client.KLINE_INTERVAL_8HOUR,
    '12h': Client.KLINE_INTERVAL_12HOUR,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '3d': Client.KLINE_INTERVAL_3DAY,
    '1w': Client.KLINE_INTERVAL_1WEEK,
    '1M': Client.KLINE_INTERVAL_1MONTH,
}

def convert_to_seconds(s):
    return int(s[:-1]) * seconds_per_unit[s[-1]]

class BinanceReader:

    fib_params = {
    "lookback": 33,
    "smooth": 2,
    "method": 3
    }
    fast_params = {
        "lookback": 12,
        "smooth": 12,
        "method": 2
    }
    slow_params = {
        "lookback1": 3,
        "method1": 2,
        "lookback2": 14,
        "method2": 2
    }
    high_params = {
        "lookback": 9,
        "smooth": 13,
        "method": 1
    }

    def __init__(self, events: Queue, client, symbol, time_frame:str = '1d'):

        self.events = events
        self.latest_symbol_data = []
        self.client = client
        self.symbol = symbol
        self.data = {}
        self.timeframe = time_frame
        if self.timeframe is None:
            self.timeframe = '1d'

        for i in self.symbol:
            self.get_data(i)

    def get_data(self, symbol):

        # get a response from binance
        start_time = dt.datetime.now() - (dt.timedelta(seconds=convert_to_seconds(self.timeframe))*100)
        start_time = start_time.strftime(format='%Y-%m-%d %H:%M')
        resp = self.client.get_historical_klines(
            symbol=symbol,
            interval=CONSTANTS[self.timeframe],
            start_str=start_time,
        )

        # cleaning the data
        df = pd.DataFrame(resp).loc[:, 0:6]
        df.columns = ['dateopen', 'open', 'high', 'low', 'close', 'volume', 'dateclose']

        def stamp_time(x):
            return dt.datetime.fromtimestamp(x/1e3)
        
        # changing the format of the timestamp
        df['dateopen'] = df['dateopen'].apply(stamp_time)
        df['dateclose'] = df['dateclose'].apply(stamp_time)

        # convert date column into dates
        df = df.set_index('dateopen', drop=True)

        # clean the columns
        for i in ['open', 'high', 'low', 'close']:
            df[i] = df[i].astype(float)

        # fill empty values and cleaning
        # df = df[pd.to_numeric(df['close'], errors='coerce').notnull()]
        # df = df.fillna(method='ffill')

        # time frame conversion
        # df = df.resample(self.timeframe).agg({
        #     'open': 'first',
        #     'high': 'max',
        #     'low': 'min',
        #     'close': 'last'
        # }).fillna(method='ffill')

        # filtering by date
        # if self.from_date != '':
        #     df = df.loc[df.index >= self.from_date]
        # if self.to_date != '':
        #     df = df.loc[df.index <= self.to_date]

        # compute indicators
        self.data[symbol] = self._compute_indicators(df)

        # clean the information for the backtester
        # self.data_df = df.copy()  # storing in other property the dataframe
        # self.data = df.iterrows()  # creating the iter object
    
    def _compute_indicators(self, data: pd.DataFrame):
        """
        Method to compute all the preliminar indicators for necessary for the
        strategy
        """
        # Creating gain and loss columns
        data["c/r fib"] = 100 * (data['close'] - data['low'].rolling(self.fib_params["lookback"]).min()) / (data['high'].rolling(self.fib_params["lookback"]).max() - data['low'].rolling(self.fib_params["lookback"]).min())
        data["c/r fast"] = 100 * (data['close'] - data['low'].rolling(self.fast_params["lookback"]).min()) / (data['high'].rolling(self.fast_params["lookback"]).max() - data['low'].rolling(self.fast_params["lookback"]).min())

        # Helper function to calculate exponential moving average of the rsi
        # values = list of data points for which exponential moving average will be calculated
        # offset = number of days the base indicator was calculated for 
        # length = number of periods for exponential moving average calculation (smooth factor)
        def sma(values, offset, length, method):
            res = np.zeros((len(values),))
            for ind, i in enumerate(values):
                if ind == offset + length - 2:
                    res[ind] = np.nanmean(values[offset-1:offset+length-1])
                elif ind > offset + length - 2:
                    res[ind] = 2 / (length + 1) * i + res[ind-1] * (1 - 2 / (length+1)) if method == 2 else res[ind-1] * (1-1/length) + i / length
                else:
                    res[ind] = np.nan
            return res
        
        # Calculating Fib
        if self.fib_params["method"] in [1,2]:
            data["fib_pred"] = sma(np.array(data["c/r fib"].values), self.fib_params["lookback"], self.fib_params["smooth"], self.fib_params["method"])
        else:
            data["fib_pred"] = data["c/r fib"].rolling(self.fib_params["smooth"]).mean()
        
        # Calculating Fast
        if self.fast_params["method"] in [1,2]:
            data["fast_pred"] = sma(np.array(data["c/r fast"].values), self.fast_params["lookback"], self.fast_params["smooth"], self.fast_params["method"])
        else:
            data["fast_pred"] = data["c/r fast"].rolling(self.fast_params["smooth"]).mean()
        
        # Calculating Slow
        if self.slow_params["method1"] in [1,2]:
            offset = self.fast_params["lookback"] + self.fast_params["smooth"] -1
            data["fast_ma"] = sma(np.array(data["fast_pred"].values), offset, self.slow_params["lookback1"], self.slow_params["method1"])
        else:
            data["fast_ma"] = data["fast"].rolling(self.slow_params["lookback1"]).mean()
            
        if self.slow_params["method2"] in [1,2]:
            offset = self.fast_params["lookback"] + self.fast_params["smooth"] + self.slow_params["lookback1"] - 2
            data["slow_pred"] = sma(np.array(data["fast_ma"].values), offset, self.slow_params["lookback2"], self.slow_params["method2"])
        else:
            data["slow_pred"] = data["fast_ma"].rolling(self.slow_params["lookback2"]).mean()
        
        # Calculating High
        if self.high_params["method"] in [1,2]:
            offset = self.fast_params["lookback"] + self.fast_params["smooth"] + self.slow_params["lookback1"] + self.slow_params["lookback2"] + self.high_params["lookback"] - 4
            data["high_pred"] = sma(np.array(data["slow_pred"].values), offset, self.high_params["smooth"], self.high_params["method"])
        else:
            data["high_pred"] = data["slow_pred"].rolling(self.high_params["smooth"]).mean()
        
        return data

