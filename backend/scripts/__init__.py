"""Backend scripts — utility runners not part of production API.

This package contains CLI utilities and background job scripts that operate on the domain modules
but are not part of the production API layer. Scripts here can orchestrate multiple domains
and combine them in ways that would violate import boundaries if done in api/ or modules/.

For example:
- calibrate_signal_thresholds.py: orchestrates data, TA, patterns, and strategy generation
  for historical threshold calibration.
"""
