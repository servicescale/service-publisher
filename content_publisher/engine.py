from __future__ import annotations

from typing import Iterable

from .adapters import (
    AffiliateCsvSignalProvider,
    AnalyticsCsvSignalProvider,
    CsvDemandSource,
    CsvProductCatalogSource,
    CsvSignalProvider,
    HeuristicSignalProvider,
    JsonCmsPublisher,
    JsonFileDemandSource,
    LiveSearchConsoleSignalProvider,
    MarkdownPublisher,
    SearchConsoleCsvSignalProvider,
    SiteOpportunityPoolSource,
    StaticSitePublisher,
)
from .capabilities.content import ContentCapability
from .capabilities.planning import PlanningCapability
from .capabilities.signals import SignalCapability
from .capabilities.strategy import StrategyCapability
from .config import supabase_service_role_key, supabase_url
from .integrations.supabase_crm import SupabaseCrmConfig, SupabaseCrmSink
from .interfaces import DemandSource, OpportunityRecord, OutputSink, ProductSource, SignalSource
from .models import Atom, Cluster, Insight, Output, Product, Signal, Site, SiteSnapshot, SiteSummary
from .orchestration import LoopOrchestrator
from .store import SiteStore


class PublishingEngine:
    """Compatibility facade over the orchestrator + capability services."""

    def __init__(
        self,
        store: SiteStore,
        demand_sources: Iterable[DemandSource] | None = None,
        product_sources: Iterable[ProductSource] | None = None,
        signal_providers: Iterable[SignalSource] | None = None,
        publishers: dict[str, OutputSink] | None = None,
    ) -> None:
        self.store = store
        self.demand_sources = list(demand_sources or [SiteOpportunityPoolSource(), JsonFileDemandSource(), CsvDemandSource()])
        self.product_sources = list(product_sources or [CsvProductCatalogSource()])
        self.signal_providers = list(
            signal_providers
            or [
                LiveSearchConsoleSignalProvider(),
                SearchConsoleCsvSignalProvider(),
                AnalyticsCsvSignalProvider(),
                AffiliateCsvSignalProvider(),
                CsvSignalProvider(),
                HeuristicSignalProvider(),
            ]
        )
        self.publishers = publishers or {"website": StaticSitePublisher(store, "website")}
        self.planning = PlanningCapability()
        self.content = ContentCapability()
        self.signals = SignalCapability()
        self.strategy = StrategyCapability()
        self.orchestrator = LoopOrchestrator(store, self.planning, self.content, self.signals, self.strategy)

    def run_site(self, site_id: str) -> SiteSnapshot:
        return self.orchestrator.run_site(
            site_id,
            demand_sources=self.demand_sources,
            product_sources=self.product_sources,
            signal_sources=self.signal_providers,
            resolve_sink=self._resolve_publisher,
        )

    def run_all_sites(self) -> list[SiteSnapshot]:
        return [self.run_site(site_id) for site_id in self.store.list_sites()]

    def detect_demand(self, site: Site) -> list[OpportunityRecord]:
        return self.planning.detect_demand(self.store.load(site.id), self.demand_sources)

    def analyze_gaps(self, snapshot: SiteSnapshot, opportunities: list[OpportunityRecord]) -> list[OpportunityRecord]:
        return self.planning.analyze_gaps(snapshot, opportunities)

    def plan_clusters(self, snapshot: SiteSnapshot, gaps: list[OpportunityRecord]) -> list[Cluster]:
        return self.planning.plan_clusters(snapshot, gaps)

    def create_atoms(self, snapshot: SiteSnapshot, clusters: list[Cluster], gaps: list[OpportunityRecord]) -> list[Atom]:
        return self.planning.create_atoms(snapshot, clusters, gaps)

    def sync_products(self, snapshot: SiteSnapshot) -> list[Product]:
        return self.content.sync_products(snapshot, self.product_sources)

    def select_products(self, snapshot: SiteSnapshot, atom: Atom, limit: int = 3) -> list[dict[str, str]]:
        return self.content.select_products(snapshot, atom, limit)

    def generate_content(self, snapshot: SiteSnapshot, atoms: list[Atom]) -> list[Output]:
        return self.content.generate_outputs(snapshot, atoms)

    def publish(self, snapshot: SiteSnapshot, outputs: list[Output]) -> list[Output]:
        return self.content.deliver_outputs(snapshot, outputs, self._resolve_publisher)

    def collect_signals(self, snapshot: SiteSnapshot, outputs: list[Output]) -> list[Signal]:
        return self.signals.collect(snapshot, outputs, self.signal_providers)

    def generate_insights(self, snapshot: SiteSnapshot, signals: list[Signal]) -> list[Insight]:
        _ = signals
        return self.strategy.generate_insights(snapshot)

    def refine_strategy(self, snapshot: SiteSnapshot, insights: list[Insight]) -> None:
        self.strategy.refine_strategy(snapshot, insights)

    def build_summary(self, snapshot: SiteSnapshot) -> SiteSummary:
        return self.strategy.build_summary(snapshot)

    def _resolve_publisher(self, site: Site, channel: str) -> OutputSink:
        if channel == "website":
            crm_config = site.metadata.get("crm")
            if isinstance(crm_config, dict) and crm_config.get("provider", "supabase") == "supabase":
                configured_url = str(crm_config.get("supabase_url") or supabase_url(site)).strip()
                configured_key = str(crm_config.get("service_role_key") or supabase_service_role_key(site)).strip()
                if configured_url and configured_key:
                    posts_table = str(crm_config.get("posts_table", "posts"))
                    timeout = float(crm_config.get("timeout", 10.0))
                    publish_status = str(crm_config.get("publish_status", "published"))
                    pillar_fallback = str(crm_config.get("pillar_fallback", "general"))
                    cache_key = f"supabase:{configured_url}:{posts_table}"
                    sink = self.publishers.get(cache_key)
                    if sink is None:
                        sink = SupabaseCrmSink(
                            SupabaseCrmConfig(
                                url=configured_url,
                                service_role_key=configured_key,
                                posts_table=posts_table,
                                timeout=timeout,
                                publish_status=publish_status,
                                pillar_fallback=pillar_fallback,
                            )
                        )
                        self.publishers[cache_key] = sink
                    return sink
            cms_config = site.metadata.get("cms")
            if cms_config:
                endpoint = str(cms_config["endpoint"])
                headers = {str(key): str(value) for key, value in cms_config.get("headers", {}).items()}
                timeout = float(cms_config.get("timeout", 10.0))
                cache_key = f"cms:{endpoint}"
                publisher = self.publishers.get(cache_key)
                if publisher is None:
                    publisher = JsonCmsPublisher(endpoint=endpoint, headers=headers, timeout=timeout)
                    self.publishers[cache_key] = publisher
                return publisher
        publisher = self.publishers.get(channel)
        if publisher is None:
            publisher = MarkdownPublisher(self.store, channel)
            self.publishers[channel] = publisher
        return publisher
