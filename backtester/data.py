
from queue import Queue
from typing import Tuple, List

import pandas as pd
import numpy as np
import datetime as dt
import yfinance as yf
from events import MarketEvent


class CSVReader:

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

    def __init__(self, events: Queue):

        self.events = events
        self.latest_symbol_data = []
        self.continue_backtest = True

        self._get_data()

    def _get_data(self):

        # read the csv with the information
        df = pd.read_csv('input.csv', header=0)

        # change column's name
        df.columns = ['date', 'open', 'high', 'low', 'close']

        # convert date column into dates
        df['date'] = pd.to_datetime(df['date'], format="%Y-%m-%dT%H:%M:%SZ")

        # fill empty values and cleaning
        df = df[pd.to_numeric(df['close'], errors='coerce').notnull()]
        df = df.fillna(method='ffill')

        # compute indicators
        self._compute_indicators(df)

        # clean the information for the backtester
        df.index = df.index.tz_localize(None)  # removing the tz
        self.data_df = df.copy()  # storing in other property the dataframe
        self.data = df.iterrows()  # creating the iter object
    
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

    def _get_new_bar(self):
        """
        Returns the latest bar from the data feed as a tuple of
        (symbol, datetime, open, low, high, close, volume).
        """
        for mkt_data in self.data:
            yield tuple([mkt_data[0],
                        mkt_data[1][0],  # open
                        mkt_data[1][1],  # high
                        mkt_data[1][2],  # low
                        mkt_data[1][3],  # close
                        mkt_data[1][5],  # c/r fib
                        mkt_data[1][6],  # c/r fast
                        mkt_data[1][7],  # fib_pred
                        mkt_data[1][8],  # fast_pred
                        mkt_data[1][9],  # fast_ma
                        mkt_data[1][10],  # slow_pred
                        mkt_data[1][11]],  # high_pred
                        )

    def get_latest_bars(self, N=1):
        """
        Returns the last N bars2 from the latest_symbol list,
        or N-k if less available.
        """
        try:
            # This is updated every time self.update_bars is executed
            bars_list = self.latest_symbol_data
        except KeyError:
            print("That symbol is not available in the historical data set.")
        else:
            return bars_list[-N:]

    def update_bars(self):
        """
        Pushes the latest bar to the latest_symbol_data structure
        for all symbols in the symbol list.
        """

        try:
            bar = self._get_new_bar().__next__()  # This works because we have an iterator
        except StopIteration:
            self.continue_backtest = False
        else:
            if bar is not None:
                # update this for the method self.get_latest_bar
                self.latest_symbol_data.append(bar)
        self.events.put(MarketEvent())  # put a market event


