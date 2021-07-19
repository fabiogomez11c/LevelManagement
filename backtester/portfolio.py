
from queue import Queue
from events import OrderEvent, FillEvent, SignalEvent
from data import CSVReader
from strategy import LongStrategy, PARAMS
import pandas as pd
import numpy as np
import datetime as dt

from typing import Tuple, List

import warnings
warnings.filterwarnings('ignore')


class Backtester:

    def __init__(self):

        # Reset the initial parameters
        self.open_trades = {}
        self.closed_trades = []
        self.event = None

        self.trades = pd.DataFrame()

    def run_backtest(self, strategy_params: Tuple):
        """
        This method runs the backtesting loop, it is designed to work with/without
        multiprocessing.
        """       

        # Converting the strategy_params into a namedtupled
        strat_params = PARAMS(*strategy_params)

        # create the queue object
        self.event = Queue()

        # import the historical data and clean it
        self.data = CSVReader(self.event)

        # cleaning some properties
        self.open_trades = dict((k, {}) for k in self.data.symbol_list)

        # create the strategy instance
        strategy = LongStrategy(self.event, self.data, strat_params)

        # run the loop
        while True:

            # check if there is more self.data
            if self.data.continue_backtest:
                self.data.update_bars()
                # self.log(self.data.get_latest_bars())
            else:
                # exit the backtest
                break

            while True:
                if self.event.qsize() != 0:
                    the_event = self.event.get()
                else:
                    # we should exit the loop to update the self.data.df
                    break

                if the_event is not None:
                    if the_event.type == 'MARKET':
                        # check market data with strategy
                        strategy.compute_signal(the_event)
                    # check if signal to trade
                    if the_event.type == 'SIGNAL':
                        self.update_from_signal(the_event)
                    # check if order to fill
                    if the_event.type == 'ORDER':
                        self.update_from_order(the_event)
                    if the_event.type == 'FILL':
                        self.update_from_fill(the_event)
                        strategy.update_from_fill(the_event)

        # get and clean the trades
        self.trades = pd.DataFrame(self.closed_trades)

    def trades_report(self):
        """
        Generates a trades report in a pandas dataframe
        """

        trades = Trades(pd.DataFrame(self.trades))

        return trades

    def update_from_signal(self, event: SignalEvent):
        if event.type == 'SIGNAL':
            self._generate_order(event)
    
    def _generate_order(self, event: SignalEvent):
        order = OrderEvent(event.information)
        self.event.put(order)

    def update_from_order(self, event: OrderEvent):
        fill_event = FillEvent(event.information)
        self.event.put(fill_event)

    def update_from_fill(self, event: FillEvent):

        information = event.information
        sym = information['symbol']

        if information['type'] in ['Long', 'Short']:

            # we don't have any position
            self.open_trades[sym]['UniqueID'] = shortuuid.ShortUUID().random(length=10)
            self.open_trades[sym]['Entry Date'] = information['datetime']
            self.open_trades[sym]['Entry Price'] = information['price']
            self.open_trades[sym]['Quantity'] = information['quantity']
            self.open_trades[sym]['Amount'] = information['amount']
            self.open_trades[sym]['Type'] = information['type']
            self.open_trades[sym]['Symbol'] = information['symbol']

        elif 'Exit' in information['type']:

            # we only have one open position
            self.open_trades[sym]['Exit Date'] = information['datetime']
            self.open_trades[sym]['Exit Price'] = information['price']
            self.open_trades[sym]['Exit Type'] = information['type']

            # PnL computation
            direction = 1 if self.open_trades[sym]['Type'] == 'Long' else -1
            self.open_trades[sym]['Profit/Loss in Dollars'] = \
                (self.open_trades[sym]['Exit Price'] - self.open_trades[sym]['Entry Price'])
            self.open_trades[sym]['Profit/Loss in Dollars'] = \
                self.open_trades[sym]['Profit/Loss in Dollars'] * self.open_trades[sym]['Quantity']
            self.open_trades[sym]['Profit/Loss in Dollars'] *= direction

            # % PnL computation
            self.open_trades[sym]['Profit/Loss in %'] = \
                (self.open_trades[sym]['Profit/Loss in Dollars']/self.open_trades[sym]['Amount'])*100

            # update the running amount
            self.running_amount += self.open_trades[sym]['Profit/Loss in Dollars']

            # storing and cleaning
            self.closed_trades.append(self.open_trades[sym])
            self.open_trades[sym] = {}
