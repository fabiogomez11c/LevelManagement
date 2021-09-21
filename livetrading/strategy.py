

class Strategy:

    def __init__(self, parent):

        # store the parameters
        self.parent = parent

    def compute_signal(self, position, symbol):

        information = None

        # get the bars needed
        bars = self.parent.data.data[symbol].iloc[-2:].to_numpy()

        if len(bars) < 2:
            return
        
        fib_pred = bars[-1][7 + 1]
        fib_pred_t_1 = bars[-2][7 + 1]
        fast_pred = bars[-1][8 + 1]
        fast_pred_t_1 = bars[-2][8 + 1]
        high_pred = bars[-1][11 + 1]
        high_pred_t_1 = bars[-2][11 + 1]

        # if we don't have any open position
        if position == 0:

            # check the buy condition
            if fib_pred > fast_pred and fib_pred_t_1 < fast_pred_t_1 \
                and fib_pred > high_pred and fib_pred_t_1 < high_pred_t_1:

                # create a buy order
                information = {
                    'type': 'Long'
                }

                return information

        # if we have an open position
        else:

            # check the close condition
            if fib_pred < fast_pred and fib_pred_t_1 > fast_pred_t_1 \
                and fib_pred < high_pred and fib_pred_t_1 > high_pred_t_1:

                # create a sell order
                information = {
                    'type': 'Exit'
                }

                return information
