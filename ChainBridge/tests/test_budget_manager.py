from budget_manager import BudgetManager


class DummyExchange:
    def __init__(self, markets):
        self._markets = markets

    def load_markets(self):
        return self._markets


def test_ensure_minimum_from_markets() -> None:
    # Market with cost.min and amount.min
    markets = {
        "TEST/USD": {
            "limits": {"cost": {"min": 7.5}, "amount": {"min": 2}},
            "precision": {"amount": 2},
        }
    }
    ex = DummyExchange(markets)
    bm = BudgetManager(initial_capital=100.0, exchange=ex)

    # price 1 => qty min 2 => required usd = 2, but cost.min = 7.5 should prevail
    size = bm._ensure_minimum_order_size("TEST/USD", 1.0, price=1.0)
    assert size >= 7.5

    # if price is high, still enforce cost min
    size2 = bm._ensure_minimum_order_size("TEST/USD", 5.0, price=10.0)
    assert size2 >= 7.5


def test_fallback_defaults_when_no_markets() -> None:
    bm = BudgetManager(initial_capital=100.0, exchange=None)
    size = bm._ensure_minimum_order_size("UNKNOWN/USD", 1.0, price=1.0)
    assert size >= 5.0


def test_update_and_close_position() -> None:
    bm = BudgetManager(initial_capital=100.0)
    # open a position at price 10, size 10 => quantity 1
    res = bm.open_position("FOO/USD", "BUY", entry_price=10.0, position_size=10.0)
    pos = res["position"]
    pid = pos["id"]

    # update with a price at or above take_profit -> should close
    tp = pos["take_profit"]
    bm.update_position(pid, tp)
    # update_position closes and returns the close result
    assert pid not in bm.positions
