# Copyright © 2026 Vincent Fournet
"""Rental Cockpit business engine.

Everything in this package is plain Python: no web framework, no database,
no network access. The application layer (one level up) loads and saves the
registry, checks who is asking, and calls these functions. Keeping the rules
here makes every calculation testable on its own.

Money is always an integer number of cents. Dates are ``datetime.date``
objects or ISO strings (``YYYY-MM-DD``). Periods are inclusive at the start
and exclusive at the end, which is how nights are counted: a stay from the
10th to the 12th is two nights.
"""

ENGINE_VERSION = "0.1.0"
