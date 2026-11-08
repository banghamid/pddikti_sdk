"""Modul integrasi Neo Feeder PDDIKTI Web Service untuk sistem informasi kampus."""

from pddikti_sdk.feeder.client import (
    AsyncNeoFeederClient,
    FeederException,
    NeoFeederClient,
)

__all__ = [
    "NeoFeederClient",
    "AsyncNeoFeederClient",
    "FeederException",
]
