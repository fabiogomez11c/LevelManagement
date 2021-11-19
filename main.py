from os import error
from backtester.portfolio import Backtester

import argparse

if __name__ == '__main__':

    print("""
    Welcome to the Backtester!

    Keep in mind that the valid arguments for the --candle parameters are:

        1min, 5min, 15min, 30min, 45min, 1h, 2h, 4h, 8h, 1day, 1week, 1month
    
    Enjoy!
    """)

    parser = argparse.ArgumentParser()
    parser.add_argument('--pairset', action='store')
    parser.add_argument('--datestart', action='store')
    parser.add_argument('--dateend', action='store')
    parser.add_argument('--candle', action='store')
    args = parser.parse_args()


    #from_date = args.datestart
    from_date = '2021-01-01'

    #to_date = args.dateend
    to_date = '2021-04-21'

    #time_frame = args.candle
    time_frame = '4h'

    #symbol = args.pairset
    symbol = 'LINK/USD'

    if from_date is None or to_date is None or time_frame is None or symbol is None:
        raise NotImplementedError('One or more parameters were not defined')


    engine = Backtester(from_date=from_date, to_date=to_date, time_frame=time_frame, symbol=symbol)
    engine.run_backtest()

    engine.create_report()

    print('Done')
