from .core import URI

from .quote import Quote
from .refrence import Refrence
from .trace import Trace

URI.DEFAULT_PROTOCOLS = [Quote, Refrence, Trace]

__all__ = ('URI',)
