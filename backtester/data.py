
from queue import Queue
from typing import Tuple, List

import pandas as pd
import datetime as dt
import yfinance as yf
from events import MarketEvent


class HistoricYFinanceDataHandler:

    def __init__(self, events: Queue, symbol: List, from_to: Tuple):

        self.symbol = symbol[0]
        self.from_date = from_to[0]
        self.to_date = from_to[1]
        self.events = events
        self.latest_symbol_data = []
        self.continue_backtest = True

        self._get_data_from_yfinance()

    def _get_ranges(self):
        
        rans = []

        # conver the stings into datetime

        finish_date = dt.datetime.strptime(self.to_date, '%Y-%m-%d')
        start_date = dt.datetime.strptime(self.from_date, '%Y-%m-%d')
        end_loop = False
        while True:
            end_date = start_date + dt.timedelta(days=6)

            if end_date >= finish_date:
                end_date = finish_date
                end_loop = True

            rans.append(
                [
                    str(start_date.date()),
                    str(end_date.date())
                ]
            )

            start_date = end_date + dt.timedelta(days=1)

            if end_loop:
                break

        return rans

    def _get_data_from_yfinance(self):

        # creates the data frame that will have all the data
        df = pd.DataFrame()

        # create a range of dates
        ranges = self._get_ranges()

        # iterate over the ranges and append into df
        for iii, ii in enumerate(ranges):
            print(f'Getting data for {self.symbol} - {ii}')
            df_temp = yf.download(
                self.symbol,
                start=ii[0],
                end=ii[1],
                interval='1m',
                progress=False
            )
            
            # append into the df
            df = df.append(df_temp)

        df.index = df.index.tz_localize(None)
        self.data_df = df.copy()
        self.data = df.iterrows()

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
                        mkt_data[1][5]]  # volume - skip the adj close
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


