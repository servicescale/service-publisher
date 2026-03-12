from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import Output, Product, Signal, SiteSnapshot


@dataclass
class OpportunityRecord:
    topic: str
    cluster_name: str
    search_intent: str
    demand_score: int
    source: str
    confidence: float = 0.7


class DemandSource(Protocol):
    def collect(self, snapshot: SiteSnapshot) -> list[OpportunityRecord]:
        ...


class OutputSink(Protocol):
    channel: str

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        ...


class SignalSource(Protocol):
    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        ...


class ProductSource(Protocol):
    def collect(self, snapshot: SiteSnapshot) -> list[Product]:
        ...
