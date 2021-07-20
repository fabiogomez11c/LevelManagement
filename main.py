from backtester.portfolio import Backtester

if __name__ == '__main__':
    engine = Backtester()
    engine.run_backtest()

    engine.create_report()
    print('Done')