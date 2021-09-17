from livetrading.engine import LiveTrading

if __name__ == "__main__":

    timeframe = '1m'
    symbol = 'ETHBTC'
    quantity = 1000

    engine = LiveTrading(timeframe, symbol, quantity)
    engine.run()
