def test_imports() -> None:
    # Ensure the validate script and market utilities import without heavy deps
    from scripts import validate_markets  # noqa: F401
    from src.market_utils import check_markets_have_minima  # noqa: F401

    assert callable(check_markets_have_minima)
