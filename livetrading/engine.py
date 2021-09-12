import binance
import queue
import time

from livetrading.data import BinanceReader

class LiveTrading:

    def __init__(self, timeframe, symbol) -> None:

        self.event = queue.Queue()
        
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

        # create the strategy handler
        print('Strategy here')
    
    def run(self):

        while True:

            time.sleep(1)

            # request data
            self.data.get_data()

            # get the existing positions

            # look for signals

