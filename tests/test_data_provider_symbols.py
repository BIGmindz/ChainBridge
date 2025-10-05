import pytest
import types
from typing import List

from src.data_provider import validate_symbols


class DummyExchange:
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.id = "dummy"


def test_validate_symbols_success():
    ex = DummyExchange(["BTC/USD", "ETH/USD"])  # minimal symbol list
    assert validate_symbols(ex, ["BTC/USD"]) == ["BTC/USD"]


def test_validate_symbols_failure():
    ex = DummyExchange(["BTC/USD"])  # only one symbol supported
    with pytest.raises(ValueError):
        validate_symbols(ex, ["ETH/USD"])  # not available
