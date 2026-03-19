# tuya-mcp TODO

## HA Custom Component — Polling Fix (DONE)

Replaced per-entity SSE polling with a `DataUpdateCoordinator` in `__init__.py` that calls `get_all_statuses` once per 30s cycle. Climate entities now extend `CoordinatorEntity` and read from cached data. Commands still use individual MCP calls.

Files changed: `custom_components/tuya_mcp/__init__.py`, `custom_components/tuya_mcp/climate.py`

## TODO
- [ ] Verify polling fix works after HA restart — no more timeouts
- [ ] Fan speed support was added to `climate.py` — verify all 5 mini-splits respond to fan speed changes
- [ ] Consider bumping `SCAN_INTERVAL` from 30s to 60s if timeouts persist
- [ ] Consider persistent MCP session / connection pooling if single-session-per-poll is still too heavy
