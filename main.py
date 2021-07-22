from backtester.portfolio import Backtester

import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--pairset', action='store')
    parser.add_argument('--datestart', action='store')
    parser.add_argument('--dateend', action='store')
    parser.add_argument('--candle', action='store')
    args = parser.parse_args()

    from_date = args.datestart
    # from_date = '2016-01-01'
    to_date = args.dateend
    # to_date = '2020-12-31'

    time_frame = args.candle

    print(from_date, to_date, time_frame)

    engine = Backtester(from_date=from_date, to_date=to_date, time_frame=time_frame)
    engine.run_backtest()

    engine.create_report()

    print(engine.data.data_df.tail())