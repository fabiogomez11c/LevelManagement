
from queue import Queue
from typing_extensions import final

from backtester.events import OrderEvent, FillEvent, SignalEvent, MarketEvent
from backtester.data import CSVReader, TwelveData
from backtester.strategy import Strategy
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt

plt.style.use('seaborn')

from typing import Tuple, List

import warnings
warnings.filterwarnings('ignore')


class Backtester:

    commision = 0.002

    def __init__(self, from_date: str = '', to_date: str = '', time_frame : str = '1D', symbol = 'AAPL'):

        # Reset the initial parameters
        self.symbol = symbol
        self.open_trades = {}
        self.closed_trades = []
        self.event = None
        self.trade_id = 1
        self.portfolio_returns = []
        self.buy_hold_returns = []
        self.returns_dates = []

        # clean the log file
        open('./backtester/log.txt', 'w').close()

        self.trades = pd.DataFrame()

        # create the queue object
        self.event = Queue()

        # import the historical data and clean it
        # self.data = CSVReader(self.event, from_date=from_date, to_date=to_date, time_frame=time_frame)
        self.data = TwelveData(self.event, from_date=from_date, to_date=to_date, time_frame=time_frame,
            symbol=self.symbol)
    
    def _log(self, message):
        bars = self.data.get_latest_bars(1)
        timestamp = str(bars[-1][0])
        finalMessage = timestamp + ' | ' + str(message)

        print(finalMessage)

        with open('./backtester/log.txt', 'a') as f:
            f.write(finalMessage + '\n')
            f.close()
    
    def _market_message(self):

        message = ''

        bars = self.data.get_latest_bars(1)[-1]
        message = f'{self.symbol} | Open: {bars[1]}, High: {bars[2]}, Low: {bars[3]}, Close: {bars[4]}, c/r fib: {bars[5]}, c/r fast: {bars[6]}, fib_pred: {bars[7]}, fast_pred: {bars[8]}, fast_ma: {bars[9]}, slow_pred: {bars[10]}, high_pred: {bars[11]}'

        return message
    
    def _order_message(self, message):

        return self.symbol + ' | ORDER: ' + str(message)
 
    def run_backtest(self):
        """
        This method runs the backtesting loop, it is designed to work with/without
        multiprocessing.
        """       

        # cleaning some properties
        self.open_trades = {}

        # create the strategy instance
        strategy = Strategy(self.event, self.data)

        # run the loop
        while True:

            # check if there is more self.data
            if self.data.continue_backtest:
                self.data.update_bars()
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
                        self.update_from_market()
                        self._log(self._market_message())
                    # check if signal to trade
                    if the_event.type == 'SIGNAL':
                        self.update_from_signal(the_event)
                    # check if order to fill
                    if the_event.type == 'ORDER':
                        self.update_from_order(the_event)
                    if the_event.type == 'FILL':
                        self.update_from_fill(the_event)

        # get and clean the trades
        self.trades = pd.DataFrame(self.closed_trades)
    
    def update_from_market(self):

        bars = self.data.get_latest_bars(2)

        if len(bars) < 2:
            return

        close = bars[-1][4]
        close_t_1 = bars[-2][4]

        self.buy_hold_returns.append(close/close_t_1 - 1)

        self.returns_dates.append(bars[-1][0])

        if len(self.open_trades) == 0:
            self.portfolio_returns.append(0.0)
        else:
            t_return = close / close_t_1 - 1
            self.portfolio_returns.append(t_return)

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

        if information['type'] in ['Long', 'Short']:

            # we don't have any position
            self.open_trades['UniqueID'] = self.trade_id
            self.trade_id += 1
            self.open_trades['Entry Date'] = information['datetime']
            self.open_trades['Entry Price'] = information['price'] * (1 + self.commision)
            self.open_trades['Type'] = information['type']

            self._log(self._order_message(self.open_trades))

        elif 'Exit' in information['type']:

            # we only have one open position
            self.open_trades['Exit Date'] = information['datetime']
            self.open_trades['Exit Price'] = information['price'] * (1 - self.commision)
            self.open_trades['Exit Type'] = information['type']

            # % PnL computation
            self.open_trades['Profit/Loss in %'] = \
                (self.open_trades['Exit Price'] / self.open_trades['Entry Price'] - 1) * 100

            self._log(self._order_message(self.open_trades))

            # storing and cleaning
            self.closed_trades.append(self.open_trades)
            self.open_trades = {}
    
    def create_report(self):

        report = {}
        self.trades = pd.DataFrame(self.closed_trades)

        if len(self.trades) == 0:
            print()
            print("There isn't any trade, try a different set of parameters.")
            return

        # returns
        returns = self.portfolio_returns
        returns = np.array(returns) + 1
        returns = np.cumprod(returns)

        market_returns = self.buy_hold_returns
        market_returns = np.array(market_returns) + 1
        market_returns = np.cumprod(market_returns)

        # Total trades
        report['Number of Trades'] = len(self.closed_trades)

        # Total profit or loss
        report['Total Return (%)'] = (returns[-1] - 1) * 100 - (report['Number of Trades'] * self.commision * 100)

        # Total market return
        report['Market Return (%)'] = (market_returns[-1] - 1) * 100

        # Total positive trades
        temp = self.trades.loc[self.trades['Profit/Loss in %'] > 0]
        report['Positive Trades'] = len(temp)

        # Win rate
        report['Winrate (%)'] = (report['Positive Trades']/report['Number of Trades']) * 100

        # Average win
        temp = self.trades.loc[self.trades['Profit/Loss in %'] > 0]['Profit/Loss in %']
        report['Avg. Win'] = np.mean(temp)

        # Average loss
        temp = self.trades.loc[self.trades['Profit/Loss in %'] < 0]['Profit/Loss in %']
        report['Avg. Loss'] = np.mean(temp)

        print(pd.DataFrame(report, index=['Values']).T)

        # Ploting
        temp = pd.DataFrame([returns, market_returns]).T
        temp.index = self.returns_dates
        temp.columns = ['Cumulative Return', 'Market Returns']
        temp.plot(figsize=(10,10))
        plt.show()

