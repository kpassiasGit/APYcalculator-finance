"""Finlytics — an AI-powered personal finance and stock analytics toolkit.

The package bundles four cooperating layers:

* :mod:`finlytics.fx`        – currency conversion and APY/compound projections.
* :mod:`finlytics.stocks`    – market data, technical indicators and risk metrics.
* :mod:`finlytics.portfolio` – multi-asset portfolio analytics.
* :mod:`finlytics.ai`        – ML forecasting, Monte-Carlo projection and an
                               optional LLM analyst.

Everything is also exposed through a single command line entry point
(``python -m finlytics`` / the ``finlytics`` console script).
"""

from __future__ import annotations

__version__ = "2.0.0"
__author__ = "kpassiasGit"

from finlytics.apy import APYResult, project_apy
from finlytics.stocks import StockAnalysis, StockAnalyzer

__all__ = [
    "__version__",
    "__author__",
    "APYResult",
    "project_apy",
    "StockAnalyzer",
    "StockAnalysis",
]
