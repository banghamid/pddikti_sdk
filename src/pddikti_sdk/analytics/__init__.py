"""Modul analisis dan agregasi data pendidikan tinggi."""

from pddikti_sdk.analytics.ratio import (
    LaporanRasioPT,
    LaporanRasioProdi,
    RatioAnalyzer,
    StatusKepatuhanRasio,
)
from pddikti_sdk.analytics.aggregator import DataAggregator

__all__ = [
    "LaporanRasioPT",
    "LaporanRasioProdi",
    "RatioAnalyzer",
    "StatusKepatuhanRasio",
    "DataAggregator",
]
