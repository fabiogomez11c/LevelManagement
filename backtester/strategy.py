
from events import MarketEvent, SignalEvent, FillEvent
# from data import KibotDataHandler
from queue import Queue

import numpy as np
import pandas as pd
import collections
import datetime as dt
from typing import Tuple

PARAMS_LIST = [
    'longtriggerPct',
    'stopLossPct',
    'shorttriggerPct',
    'coverPct',
    'waitMinutes',
    'useLong',
    'useShort'
]

PARAMS = collections.namedtuple(
    'params',
    PARAMS_LIST
)


class LongStrategy:

    def __init__(self, events: Queue, data: KibotDataHandler, parameters: collections.namedtuple):

        # store the parameters
        self.events = events
        self.data = data
        self.parameters = parameters

        self.quantity = 100
        self.wait_minutes = parameters.waitMinutes  # wait minutes after the open

        # initial values in the strategy
        self.CurrentPosition = dict((k, []) for k in self.data.symbol_list)
        self.CurrentStopLoss = dict((k, None) for k in self.data.symbol_list)
        self.CurrentCoverPx = dict((k, None) for k in self.data.symbol_list)
        self.trailingSl = dict((k, False) for k in self.data.symbol_list)
        self.trailingCover = dict((k, False) for k in self.data.symbol_list)
        self.CurrentLow = dict((k, 100000) for k in self.data.symbol_list)
        self.CurrentHigh = dict((k, 0) for k in self.data.symbol_list)

    def compute_signal(self, event: MarketEvent):

        if event.type == 'MARKET':  # there is a new bar
            for s in self.data.symbol_list:
                # get the bars needed
                bars = self.data.get_latest_bars(s)

                # reset the current low
                if bars[-1][0].hour == 15 and bars[-1][0].minute == 59:
                    self.CurrentLow[s] = 1000000
                else:
                    # check if a new low of day
                    if self.CurrentLow[s] > bars[-1][3]:
                        self.CurrentLow[s] = bars[-1][3]

                # reset the current high
                if bars[-1][0].hour == 15 and bars[-1][0].minute == 59:
                    self.CurrentHigh[s] = 0
                else:
                    if self.CurrentHigh[s] < bars[-1][2]:
                        self.CurrentHigh[s] = bars[-1][2]

                # if we don't have any open position
                if len(self.CurrentPosition[s]) == 0:

                    # avoid trading at the end of the day
                    if bars[-1][0].hour == 15 and bars[-1][0].minute == 59:
                        continue

                    # check if new day
                    # this condition creates a dependency on the timezone
                    dt_temp = dt.datetime(
                        bars[-1][0].year,
                        bars[-1][0].month,
                        bars[-1][0].day,
                        9,
                        30
                    )
                    diff_temp = bars[-1][0] - dt_temp

                    if diff_temp.seconds/60 >= self.wait_minutes:

                        # check if we should trade
                        threshold = (self.CurrentLow[s] * (1 + self.parameters.longtriggerPct))
                        # check to go long
                        if bars[-1][2] >= threshold and self.parameters.useLong:

                            # check if gap
                            if threshold < bars[-1][3]:
                                entry_price = bars[-1][1]  # entry at the open
                            else:
                                entry_price = threshold  # entry at the threshold

                            # open a new long position
                            information = {
                                'datetime': bars[-1][0],
                                'price': entry_price,
                                'quantity': self.quantity,
                                'amount': self.quantity*entry_price,
                                'type': 'Long',
                                'symbol': s
                            }

                            # send signal
                            signal = SignalEvent(information)
                            self.events.put(signal)

                            self.CurrentPosition[s] = [information]
                            self.CurrentStopLoss[s] = information['price'] * (1 - self.parameters.stopLossPct)
                            self.trailingSl[s] = True

                            continue

                        # check if we should trade
                        threshold = (self.CurrentHigh[s] * (1 - self.parameters.shorttriggerPct))
                        # check to go short
                        if bars[-1][3] <= threshold and self.parameters.useShort:
                            # check if gap
                            if threshold > bars[-1][2]:
                                entry_price = bars[-1][1]  # entry at the open
                            else:
                                entry_price = threshold  # entry at the threshold

                            # open a new long position
                            information = {
                                'datetime': bars[-1][0],
                                'price': entry_price,
                                'quantity': self.quantity,
                                'amount': self.quantity*entry_price,
                                'type': 'Short',
                                'symbol': s
                            }

                            # send signal
                            signal = SignalEvent(information)
                            self.events.put(signal)

                            self.CurrentPosition[s] = [information]
                            self.CurrentCoverPx[s] = information['price'] * (1 + self.parameters.coverPct)
                            self.trailingCover[s] = True

                            continue

                # if we have an open position
                else:

                    # check if it's EOD
                    # this condition creates a dependency to the timezone of the data
                    if bars[-1][0].hour == 15 and bars[-1][0].minute == 59:
                        # close the existing position
                        information = {
                            'datetime': bars[-1][0],
                            'price': bars[-1][4],
                            'type': f'Exit {self.CurrentPosition[s][0]["type"]}',
                            'symbol': s
                        }

                        # send signal
                        signal = SignalEvent(information)
                        self.events.put(signal)

                        self.CurrentPosition[s] = []
                        self.CurrentStopLoss[s] = None
                        self.trailingSl[s] = False

                    # check if we have activated the trailing stop
                    elif self.trailingSl[s]:

                        # check if we are long
                        if self.CurrentPosition[s][0]['type'] == 'Long':

                            # check update the price of the SL
                            if (bars[-1][2] * (1 - self.parameters.stopLossPct)) > self.CurrentStopLoss[s]:
                                self.CurrentStopLoss[s] = bars[-1][2] * (1 - self.parameters.stopLossPct)

                            # check if the stop should be executed
                            if bars[-1][3] <= self.CurrentStopLoss[s]:

                                # close the existing position
                                information = {
                                    'datetime': bars[-1][0],
                                    'price': self.CurrentStopLoss[s],
                                    'type': 'Exit Long',
                                    'symbol': s
                                }

                                # send signal
                                signal = SignalEvent(information)
                                self.events.put(signal)

                                # recalculate the current low
                                self.CurrentLow[s] = self.CurrentStopLoss[s]

                                self.CurrentPosition[s] = []
                                self.CurrentStopLoss[s] = None
                                self.trailingSl[s] = False

                    # check if we have activate the trailing to cover
                    elif self.trailingCover[s]:

                        # check if we are short
                        if self.CurrentPosition[s][0]['type'] == 'Short':
                            # check update the price of the SL
                            if (bars[-1][3] * (1 + self.parameters.coverPct)) < self.CurrentCoverPx[s]:
                                self.CurrentCoverPx[s] = bars[-1][3] * (1 + self.parameters.coverPct)

                            # check if the stop should be executed
                            if bars[-1][2] >= self.CurrentCoverPx[s]:

                                # close the existing position
                                information = {
                                    'datetime': bars[-1][0],
                                    'price': self.CurrentCoverPx[s],
                                    'type': 'Exit Short',
                                    'symbol': s
                                }

                                # send signal
                                signal = SignalEvent(information)
                                self.events.put(signal)

                                # recalculate the current low
                                self.CurrentHigh[s] = self.CurrentCoverPx[s]

                                self.CurrentPosition[s] = []
                                self.CurrentCoverPx[s] = None
                                self.trailingCover[s] = False