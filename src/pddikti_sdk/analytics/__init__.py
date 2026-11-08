"""Modul analisis dan agregasi data pendidikan tinggi."""

from pddikti_sdk.analytics.ratio import (
    LaporanRasioPT,
    LaporanRasioProdi,
    RatioAnalyzer,
    StatusKepatuhanRasio,
)
from pddikti_sdk.analytics.aggregator import DataAggregator
from pddikti_sdk.analytics.excel_exporter import (
    ExcelReportGenerator,
    export_laporan_rasio_excel,
)

__all__ = [
    "LaporanRasioPT",
    "LaporanRasioProdi",
    "RatioAnalyzer",
    "StatusKepatuhanRasio",
    "DataAggregator",
    "ExcelReportGenerator",
    "export_laporan_rasio_excel",
]
