from __future__ import annotations

from contextlib import contextmanager
from typing import Callable

from .capabilities.content import ContentCapability
from .capabilities.planning import PlanningCapability
from .capabilities.signals import SignalCapability
from .capabilities.strategy import StrategyCapability
from .models import LoopRun, SiteSnapshot, StageRun, new_id, utc_now
from .reporting import render_site_report
from .store import SiteStore


class LoopOrchestrator:
    def __init__(
        self,
        store: SiteStore,
        planning: PlanningCapability,
        content: ContentCapability,
        signals: SignalCapability,
        strategy: StrategyCapability,
    ) -> None:
        self.store = store
        self.planning = planning
        self.content = content
        self.signals = signals
        self.strategy = strategy

    def run_site(self, site_id: str, *, demand_sources: list, product_sources: list, signal_sources: list, resolve_sink: Callable) -> SiteSnapshot:
        snapshot = self.store.load(site_id)
        site = snapshot.site
        loop_run = LoopRun(id=new_id("loop"), site_id=site.id, run_number=site.loop_runs + 1, started_at=utc_now())
        site.loop_history.append(loop_run)

        with self._record_stage(loop_run, "demand_detection") as stage:
            opportunities = self.planning.detect_demand(snapshot, demand_sources)
            stage.counts["opportunities"] = len(opportunities)
        with self._record_stage(loop_run, "gap_analysis") as stage:
            gaps = self.planning.analyze_gaps(snapshot, opportunities)
            stage.counts["gaps"] = len(gaps)
        with self._record_stage(loop_run, "cluster_planning") as stage:
            clusters = self.planning.plan_clusters(snapshot, gaps)
            stage.counts["clusters_touched"] = len(clusters)
        with self._record_stage(loop_run, "atom_creation") as stage:
            atoms = self.planning.create_atoms(snapshot, clusters, gaps)
            stage.counts["atoms_created"] = len(atoms)
        with self._record_stage(loop_run, "content_generation") as stage:
            products = self.content.sync_products(snapshot, product_sources)
            outputs = self.content.generate_outputs(snapshot, atoms)
            stage.counts["products_loaded"] = len(products)
            stage.counts["outputs_generated"] = len(outputs)
        with self._record_stage(loop_run, "publishing") as stage:
            published_outputs = self.content.deliver_outputs(snapshot, outputs, resolve_sink)
            stage.counts["outputs_published"] = len(published_outputs)
        with self._record_stage(loop_run, "signal_collection") as stage:
            collected_signals = self.signals.collect(snapshot, published_outputs, signal_sources)
            stage.counts["signals_collected"] = len(collected_signals)
        with self._record_stage(loop_run, "insight_generation") as stage:
            insights = self.strategy.generate_insights(snapshot)
            stage.counts["insights_generated"] = len(insights)
        with self._record_stage(loop_run, "strategy_refinement") as stage:
            self.strategy.refine_strategy(snapshot, insights)
            stage.counts["opportunity_pool_size"] = len(snapshot.site.opportunity_pool)

        site.loop_runs += 1
        site.updated_at = utc_now()
        loop_run.completed_at = utc_now()
        loop_run.status = "completed"
        loop_run.summary = {
            "clusters": len(snapshot.clusters),
            "atoms": len(snapshot.atoms),
            "outputs": len(snapshot.outputs),
            "signals": len(snapshot.signals),
            "insights": len(snapshot.insights),
        }
        self.store.save(snapshot)
        summary = self.strategy.build_summary(snapshot)
        self.store.save_summary(summary)
        self.store.save_report(snapshot.site.id, render_site_report(snapshot, summary))
        return snapshot

    @contextmanager
    def _record_stage(self, loop_run: LoopRun, stage_name: str):
        stage = StageRun(stage=stage_name, started_at=utc_now(), completed_at=utc_now(), status="running")
        loop_run.stage_runs.append(stage)
        try:
            yield stage
            stage.status = "completed"
        except Exception as exc:
            stage.status = "failed"
            stage.notes.append(str(exc))
            loop_run.status = "failed"
            raise
        finally:
            stage.completed_at = utc_now()
