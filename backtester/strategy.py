
from backtester.events import MarketEvent, SignalEvent, FillEvent
from backtester.data import CSVReader
from queue import Queue

import numpy as np
import pandas as pd
import datetime as dt
from typing import ClassVar, Tuple


class Strategy:

    def __init__(self, events: Queue, data: CSVReader):

        # store the parameters
        self.events = events
        self.data = data

        self.quantity = 100

        # initial values in the strategy
        self.CurrentPosition = []

    def compute_signal(self, event: MarketEvent):

        if event.type == 'MARKET':  # there is a new bar
            # get the bars needed
            bars = self.data.get_latest_bars(2)

            if len(bars) < 2:
                return

            # if we don't have any open position
            if len(self.CurrentPosition) == 0:

                # check the buy condition
                if bars[-1][7] > bars[-1][8] and bars[-2][7] < bars[-2][8] \
                    and bars[-1][7] > bars[-1][11] and bars[-2][7] < bars[-2][11]:

                    # create a buy order
                    information = {
                        'datetime': bars[-1][0],
                        'price': bars[-1][4],
                        'type': 'Long'
                    }

                    # send the buy order
                    signal = SignalEvent(information=information)
                    self.events.put(signal)

                    # update current position
                    self.CurrentPosition = [information]

            # if we have an open position
            else:

                # check the close condition
                if bars[-1][7] < bars[-1][8] and bars[-2][7] > bars[-2][8] \
                    and bars[-1][7] < bars[-1][11] and bars[-2][7] > bars[-2][11]:

                    # create a sell order
                    information = {
                        'datetime': bars[-1][0],
                        'price': bars[-1][4],
                        'type': 'Exit'
                    }

                    # send the sell order
                    signal = SignalEvent(information=information)
                    self.events.put(signal)

                    # update current position
                    self.CurrentPosition = []
