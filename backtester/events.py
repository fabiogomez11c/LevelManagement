
from typing import Dict

class Event(object):
    """
    Event is base class providing an interface for all subsequent
    (inherited) events.
    """
    pass

class MarketEvent(Event):
    """
    Handles the event of receiving a new market update with
    corresponding bars2.
    """

    def __init__(self):  # without parameters
        """
        Initialises the MarketEvent.
        """
        self.type = 'MARKET'  # type of the event

class SignalEvent(Event):
    """
    Handles the event of sending a Signal from a Strategy object.
    This is received by a Portfolio object and acted upon.
    """

    def __init__(self, information: Dict):

        self.type = 'SIGNAL'  # type of the event
        self.information = information

class OrderEvent(Event):
    """
    Handles the event of sending an Order to an execution system.
    The order contains a symbol (e.g. GOOG), a type (market or limit),
    quantity and a direction.
    """

    def __init__(self, information: Dict):

        self.type = 'ORDER'  # type of the event
        self.information = information

class FillEvent(Event):
    """
    Encapsulates the notion of a Filled Order, as returned
    from a brokerage. Stores the quantity of an instrument
    actually filled and at what price. In addition, stores
    the commission of the trade from the brokerage.
    """

    def __init__(self, information: Dict):

        self.type = 'FILL'
        self.information = information