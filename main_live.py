from livetrading.engine import LiveTrading

if __name__ == "__main__":

    timeframe = '1h'
    symbol = ['ETHBTC', 'BTCUSD', 'LINKUSD', 'ADAUSD']
    quantity = 1000

    engine = LiveTrading(timeframe, symbol, quantity)
    engine.run()

