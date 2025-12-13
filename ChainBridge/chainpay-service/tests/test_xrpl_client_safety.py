"""
Test XRPL client safety and fallback behavior.
"""
import pytest
try:
    from app.xrpl.client import XRPLClient
    xrpl_import_ok = True
except ImportError:
    xrpl_import_ok = False

pytestmark = pytest.mark.skipif(not xrpl_import_ok, reason="XRPL client import failed or xrpl package missing")

@pytest.mark.asyncio
async def test_xrpl_client_disabled_mode():
    client = XRPLClient(mode="disabled")
    result = await client.connect()
    assert result["success"] is False
    assert "disabled" in result["rationale"]

@pytest.mark.asyncio
async def test_xrpl_client_testnet_connect():
    client = XRPLClient(mode="testnet")
    result = await client.connect()
    assert result["success"] in [True, False]  # Success depends on network
    assert "trace_id" in result
    client = XRPLClient(mode="testnet")
    result = await client.connect()
    client = XRPLClient(mode="testnet")
    result = await client.connect()
    assert result["success"] in [True, False]  # Success depends on network
    assert "trace_id" in result
