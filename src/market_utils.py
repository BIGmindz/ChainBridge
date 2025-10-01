from typing import Dict, List

ALIAS_MAP = {
    "BTC": ["XBT"],
    "XBT": ["BTC"],
    "USDT": ["USD"],
}


def _symbol_variants(symbol: str) -> List[str]:
    """Generate common symbol variants to match different exchange naming.

    Examples: 'BTC/USD' -> ['BTC/USD', 'XBT/USD', 'BTC-USD', 'XBT-USD']
    """
    variants = set()
    if "/" in symbol:
        base, quote = symbol.split("/")
    elif "-" in symbol:
        base, quote = symbol.split("-")
    else:
        # fallback: return symbol as-is
        return [symbol]

    bases = [base]
    if base in ALIAS_MAP:
        bases.extend(ALIAS_MAP[base])

    quotes = [quote]
    if quote in ALIAS_MAP:
        quotes.extend(ALIAS_MAP[quote])

    for b in bases:
        for q in quotes:
            variants.add(f"{b}/{q}")
            variants.add(f"{b}-{q}")

    return list(variants)  # type: ignore


def check_markets_have_minima(markets: Dict[str, dict], symbols: List[str]) -> List[str]:
    """Return a list of symbols missing minima (cost.min or amount.min).

    This helper normalizes different shapes in exchange market metadata.
    """
    missing = []
    for s in symbols:
        m = markets.get(s)
        # Try common variants if exact symbol not present
        if m is None:
            for alt in _symbol_variants(s):
                if alt in markets:
                    m = markets.get(alt)
                    break
        if not m:
            missing.append(s)  # type: ignore
            continue
        limits = m.get("limits", {}) or {}
        cost_limit = limits.get("cost")
        amount_limit = limits.get("amount")
        has_cost = False
        has_amount = False
        if isinstance(cost_limit, dict):
            has_cost = bool(cost_limit.get("min"))
        elif isinstance(cost_limit, (int, float)):
            has_cost = cost_limit > 0

        if isinstance(amount_limit, dict):
            has_amount = bool(amount_limit.get("min"))
        elif isinstance(amount_limit, (int, float)):
            has_amount = amount_limit > 0

        if not (has_cost or has_amount):
            missing.append(s)  # type: ignore

    return missing


def get_minima_report(markets: Dict[str, dict], symbols: List[str]) -> Dict[str, dict]:
    """Return a diagnostic map of symbol -> detected minima information.

    Example return value:
    {
      "BTC/USD": {"found_as": "BTC/USD", "cost_min": 10.0, "amount_min": None},
      "KIN/USD": {"found_as": None}
    }
    """
    report = {}
    for s in symbols:
        m = markets.get(s)
        found_as = s
        if m is None:
            for alt in _symbol_variants(s):
                if alt in markets:
                    m = markets.get(alt)
                    found_as = alt
                    break

        if not m:
            report[s] = {"found_as": None}
            continue

        limits = m.get("limits", {}) or {}
        cost_limit = limits.get("cost")
        amount_limit = limits.get("amount")

        def _extract_min(v):
            if v is None:
                return None
            if isinstance(v, dict):
                return v.get("min")
            if isinstance(v, (int, float)):
                return v
            return None

        report[s] = {
            "found_as": found_as,
            "cost_min": _extract_min(cost_limit),
            "amount_min": _extract_min(amount_limit),
        }

    return report
