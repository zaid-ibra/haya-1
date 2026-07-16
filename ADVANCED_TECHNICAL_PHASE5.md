# Advanced Technical Analysis — Phase 5

Phase 5 adds an approximate Volume Profile module to the deterministic analysis engine.

## Outputs

- Point of Control (`POC`)
- Value Area High (`VAH`)
- Value Area Low (`VAL`)
- High Volume Nodes (`HVN`)
- Low Volume Nodes (`LVN`)
- Latest-price location relative to the value area

The module accepts standard `volume` or MT5 `tick_volume`. For decentralized FX and many XAUUSD feeds, tick volume represents market activity rather than centralized exchange volume. Therefore its scoring weight is capped at 8 points per side and should be treated as confluence rather than proof of institutional flow.

Results are available at:

```python
result.volume_profile
```
