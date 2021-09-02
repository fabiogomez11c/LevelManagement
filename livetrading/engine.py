import binance

class LiveTrading:

    def __init__(self) -> None:
        
        self.client = binance.Client(
            "fqg1ttuR45eWNLVBegJ41walQ6KksxvjTRLZeXaDHXIe8Q7TkxiYcBu8JpXzbOb9",
            "35IB27RflS7T0vm5CDi3b3vVEx4lVdtTB2lMP0WszCmF4GiGFOdbZVufIJtrcXeZ"
        )

        self.depth = self.client.get_order_book(symbol='BNBBTC')
