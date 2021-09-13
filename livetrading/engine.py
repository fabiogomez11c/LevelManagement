import binance
import queue
import time

from livetrading.data import BinanceReader

class LiveTrading:

    def __init__(self, timeframe, symbol) -> None:

        self.event = queue.Queue()
        self.last_datetime = None
        
        self.client = binance.Client(
            "fqg1ttuR45eWNLVBegJ41walQ6KksxvjTRLZeXaDHXIe8Q7TkxiYcBu8JpXzbOb9",
            "35IB27RflS7T0vm5CDi3b3vVEx4lVdtTB2lMP0WszCmF4GiGFOdbZVufIJtrcXeZ"
        )

        # create the data handler
        self.data = BinanceReader(
            events=self.event,
            client=self.client,
            time_frame=timeframe,
            symbol=symbol
        )
        self._update_last_datetime()

        # create the strategy handler
        print('Strategy here')
    
    def _update_last_datetime(self):
        self.last_datetime = self.data.data.iloc[-1][0]
    
    def _check_last_datetime(self):
        return self.last_datetime == self.data.data.iloc[-1][0]
    
    def run(self):

        while True:

            time.sleep(1)

            # request data
            self.data.get_data()

            # check if we already have new data
            if self._check_last_datetime():
                continue
            self._update_last_datetime()

            # get the existing positions

            # look for signals

