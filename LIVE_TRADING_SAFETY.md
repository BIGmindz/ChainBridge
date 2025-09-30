# Live Trading Safety Checklist

## BEFORE enabling live trading, ensure:

### Prerequisites
- [ ] API credentials are set in `.env` file
- [ ] `PAPER="false"` in `.env` file
- [ ] Sufficient funds in Kraken account
- [ ] Risk parameters are conservative (2% max per trade)
- [ ] Bot has been tested in paper mode extensively
- [ ] Emergency stop mechanism is available
- [ ] Monitoring and logging are enabled

## EMERGENCY STOP
Set `PAPER="true"` in `.env` and restart bot

## RISK MANAGEMENT
- Max 2% of capital per trade
- Max 5 open positions
- 10-minute cooldown between signals
- Stop-loss and take-profit enabled

## TESTING SEQUENCE
1. Test with paper trading first
2. Test live connection (no orders)
3. Test with very small amounts
4. Monitor closely for first few trades
5. Gradually increase position sizes
