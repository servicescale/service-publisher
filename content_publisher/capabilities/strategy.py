from __future__ import annotations

from collections import defaultdict

from ..models import Insight, SiteSnapshot, SiteSummary, new_id, utc_now
from .utils import normalize


class StrategyCapability:
    def generate_insights(self, snapshot: SiteSnapshot) -> list[Insight]:
        insights: list[Insight] = []
        clicks_by_cluster: dict[str, float] = defaultdict(float)
        clicks_by_atom: dict[str, float] = defaultdict(float)

        for atom in snapshot.atoms.values():
            for signal_id in atom.signal_ids:
                signal = snapshot.signals[signal_id]
                if signal.kind == "clicks":
                    clicks_by_atom[atom.id] += signal.value
                    clicks_by_cluster[atom.cluster_id] += signal.value

        existing_keys = {(insight.scope, insight.scope_id, insight.kind): insight.id for insight in snapshot.insights.values()}

        for cluster in snapshot.clusters.values():
            total_clicks = clicks_by_cluster.get(cluster.id, 0.0)
            if total_clicks >= 30:
                key = ("cluster", cluster.id, "expand_cluster")
                if key not in existing_keys:
                    insight = Insight(
                        id=new_id("insight"),
                        site_id=snapshot.site.id,
                        scope="cluster",
                        scope_id=cluster.id,
                        kind="expand_cluster",
                        summary=f"Expand cluster '{cluster.name}' based on strong click performance.",
                        evidence={"clicks": total_clicks, "atom_count": len(cluster.atom_ids)},
                        impact_score=round(total_clicks / max(1, len(cluster.atom_ids)), 2),
                    )
                    snapshot.insights[insight.id] = insight
                    snapshot.site.insight_ids.append(insight.id)
                    insights.append(insight)

        for atom in snapshot.atoms.values():
            total_clicks = clicks_by_atom.get(atom.id, 0.0)
            if total_clicks < 10:
                key = ("atom", atom.id, "deprioritize_atom")
                if key not in existing_keys:
                    insight = Insight(
                        id=new_id("insight"),
                        site_id=snapshot.site.id,
                        scope="atom",
                        scope_id=atom.id,
                        kind="deprioritize_atom",
                        summary=f"Deprioritize low-performing atom '{atom.topic}'.",
                        evidence={"clicks": total_clicks},
                        impact_score=max(1.0, 10 - total_clicks),
                    )
                    snapshot.insights[insight.id] = insight
                    snapshot.site.insight_ids.append(insight.id)
                    atom.insight_ids.append(insight.id)
                    insights.append(insight)
            elif total_clicks >= 20:
                key = ("atom", atom.id, "extend_atom")
                if key not in existing_keys:
                    insight = Insight(
                        id=new_id("insight"),
                        site_id=snapshot.site.id,
                        scope="atom",
                        scope_id=atom.id,
                        kind="extend_atom",
                        summary=f"Create follow-up atoms related to '{atom.topic}'.",
                        evidence={"clicks": total_clicks, "cluster_id": atom.cluster_id},
                        impact_score=round(total_clicks, 2),
                    )
                    snapshot.insights[insight.id] = insight
                    snapshot.site.insight_ids.append(insight.id)
                    atom.insight_ids.append(insight.id)
                    insights.append(insight)
        return insights

    def refine_strategy(self, snapshot: SiteSnapshot, insights: list[Insight]) -> None:
        existing_topics = {normalize(item["topic"]) for item in snapshot.site.opportunity_pool}
        cluster_lookup = snapshot.clusters
        atom_lookup = snapshot.atoms

        for insight in insights:
            if insight.kind == "expand_cluster":
                cluster = cluster_lookup[insight.scope_id]
                cluster.priority = min(100, cluster.priority + 10)
                cluster.updated_at = utc_now()
                follow_up = f"{cluster.name} for beginners"
                if normalize(follow_up) not in existing_topics:
                    snapshot.site.opportunity_pool.append(
                        {
                            "topic": follow_up,
                            "cluster_name": cluster.name,
                            "search_intent": "informational",
                            "demand_score": min(100, cluster.priority),
                            "source": "insight_generation",
                            "confidence": 0.8,
                        }
                    )
                    existing_topics.add(normalize(follow_up))
            elif insight.kind == "extend_atom":
                atom = atom_lookup[insight.scope_id]
                follow_up = f"{atom.topic} comparison"
                if normalize(follow_up) not in existing_topics:
                    snapshot.site.opportunity_pool.append(
                        {
                            "topic": follow_up,
                            "cluster_name": atom.context.get("cluster_name", self._guess_cluster_name(atom.topic)),
                            "search_intent": atom.search_intent,
                            "demand_score": min(100, atom.priority + 5),
                            "source": "insight_generation",
                            "confidence": 0.85,
                        }
                    )
                    existing_topics.add(normalize(follow_up))
            elif insight.kind == "deprioritize_atom":
                atom = atom_lookup[insight.scope_id]
                atom.priority = max(1, atom.priority - 10)
                atom.updated_at = utc_now()

    def build_summary(self, snapshot: SiteSnapshot) -> SiteSummary:
        channel_output_counts: dict[str, int] = defaultdict(int)
        signal_totals: dict[str, float] = defaultdict(float)
        signal_source_totals: dict[str, float] = defaultdict(float)
        cluster_scores: dict[str, float] = defaultdict(float)
        cluster_names = {cluster.id: cluster.name for cluster in snapshot.clusters.values()}
        atom_lookup = snapshot.atoms

        for output in snapshot.outputs.values():
            channel_output_counts[output.channel] += 1
        for signal in snapshot.signals.values():
            signal_totals[signal.kind] += signal.value
            source = str(signal.dimensions.get("source", "engine"))
            signal_source_totals[f"{source}:{signal.kind}"] += signal.value
            output = snapshot.outputs.get(signal.output_id)
            if output is not None:
                atom = atom_lookup.get(output.atom_id)
                if atom is not None and signal.kind == "clicks":
                    cluster_scores[atom.cluster_id] += signal.value

        top_clusters = [
            {"cluster_id": cluster_id, "name": cluster_names.get(cluster_id, cluster_id), "clicks": clicks}
            for cluster_id, clicks in sorted(cluster_scores.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

        return SiteSummary(
            site_id=snapshot.site.id,
            loop_runs=snapshot.site.loop_runs,
            cluster_count=len(snapshot.clusters),
            atom_count=len(snapshot.atoms),
            output_count=len(snapshot.outputs),
            signal_count=len(snapshot.signals),
            insight_count=len(snapshot.insights),
            channel_output_counts=dict(channel_output_counts),
            signal_totals={key: round(value, 2) for key, value in signal_totals.items()},
            signal_source_totals={key: round(value, 2) for key, value in signal_source_totals.items()},
            top_clusters=top_clusters,
            updated_at=utc_now(),
        )

    def _guess_cluster_name(self, topic: str) -> str:
        words = topic.split()
        return " ".join(words[: min(3, len(words))]).strip() or "general"
