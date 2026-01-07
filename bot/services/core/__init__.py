"""
Core services package.

This file exists to make relative imports reliable (non-namespace package),
because the codebase imports these modules both as `services.*` and `bot.services.*`
depending on runtime entrypoint / PYTHONPATH.
"""


