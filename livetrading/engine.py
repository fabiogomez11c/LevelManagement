import binance
import queue
import time

from livetrading.data import BinanceReader
from livetrading.strategy import Strategy

class LiveTrading:

    def __init__(self, timeframe, symbol, baseQuantity) -> None:

        self.event = queue.Queue()
        self.last_datetime = None
        self.symbol = symbol
        self.contra = dict((i, i[:-3]) for i in self.symbol)
        # self.contra = symbol[0:3]
        self.base = dict((i, i[-3::]) for i in self.symbol)
        # self.base = symbol[3::]
        self.quantity = baseQuantity

        open('./livetrading/log.txt', 'w').close()
        
        self.client = binance.Client(
            "ifWJ8ujCxzYk6Kuo6tgrUGZj905BeOhRHH2DKhtjUazETm5jGvPFaeXuaMn281To",
            "AzYaqKrlpzdwGlHac6qhfMl94rr05Jld92pmsMFyPVwfPzkFC4fyJP53aNUK3hgO",
            tld="us"
        )

        # create the data handler
        self.data = BinanceReader(
            events=self.event,
            client=self.client,
            time_frame=timeframe,
            symbol=symbol
        )

        for i in self.symbol:
            self._update_last_datetime(i)

        # create the strategy handler
        self.strategy = Strategy(self)
    
    def _log(self, message, symbol):
        timestamp = self.data.data[symbol].iloc[-1:].index[0]
        finalMessage = str(timestamp) + ' | ' + message

        print(finalMessage)

        with open('./livetrading/log.txt', 'a') as f:
            f.write(finalMessage + '\n')
            f.close()

    def _market_message(self, symbol):

        message = ''

        bars = self.data.data[symbol].iloc[-1:].to_numpy()[0]
        message = f'{symbol} | Open: {bars[0]}, High: {bars[1]}, Low: {bars[2]}, Close: {bars[3]}, c/r fib: {bars[6]}, c/r fast: {bars[7]}, fib_pred: {bars[8]}, fast_pred: {bars[9]}, fast_ma: {bars[10]}, slow_pred: {bars[11]}, high_pred: {bars[12]}'

        return message
    
    def _order_message(self, message, symbol):
        return symbol + ' | ORDER: ' + str(message)

    def _update_last_datetime(self, symbol):
        self.last_datetime = self.data.data[symbol].iloc[-1].name
    
    def _check_last_datetime(self, symbol):
        return self.last_datetime == self.data.data[symbol].iloc[-1].name
    
    def run(self):
        print('ALGORITHM RUNNING...')

        while True:
            # loop to check that there is a new candle
            for s in self.symbol:
                # iterate till we have a new data for this symbol
                while True:
                    time.sleep(1)
                    # request data
                    self.data.get_data(s)

                    # check if we already have new data
                    if self._check_last_datetime(s):
                        continue
                    else:
                        break
                
            # loop for symbols
            for s in self.symbol:

                self._update_last_datetime(s)
                self._log(self._market_message(s), s)

                # get the existing positions
                contra = float(self.client.get_asset_balance(asset=self.contra[s])['free'])

                # look for signals
                info = self.strategy.compute_signal(contra, s)

                # send orders
                if info is not None:
                    if info['type'] == 'Long':
                        qty = self.getUSDprices(s)
                        self._log({'type': 'long', 'quantity': qty}, s)
                        self.client.order_market_buy(
                            symbol=s,
                            quantity=qty
                        )
                    elif info['type'] == 'Exit':
                        qty = contra
                        self._log({'type': 'short', 'quantity': qty}, s)
                        self.client.order_market_sell(
                            symbol=s,
                            quantity=qty
                        )
    
    def getUSDprices(self, symbol):

        quantity = self.quantity
        
        # get all the prices
        prices = self.client.get_all_tickers()

        if 'USD' not in symbol:
            newSymbol = self.base + 'USD'
            auxPrice = [i['price'] for i in prices if i.get('symbol') and i.get('symbol') == newSymbol]
            # look for the quantity
            quantity = quantity / float(auxPrice[0])
        
        return quantity
