from __future__ import annotations

from .utils import normalize
from ..integrations.keyword_overlap import evaluate_overlap
from ..interfaces import OpportunityRecord
from ..models import Atom, Cluster, Site, SiteSnapshot, new_id, utc_now


class PlanningCapability:
    def detect_demand(self, snapshot: SiteSnapshot, demand_sources: list) -> list[OpportunityRecord]:
        opportunities: dict[tuple[str, str], OpportunityRecord] = {}
        for source in demand_sources:
            for record in source.collect(snapshot):
                key = (normalize(record.topic), normalize(record.cluster_name))
                current = opportunities.get(key)
                if current is None or record.demand_score > current.demand_score:
                    opportunities[key] = record
        return list(opportunities.values())

    def analyze_gaps(self, snapshot: SiteSnapshot, opportunities: list[OpportunityRecord]) -> list[OpportunityRecord]:
        existing_topics = [atom.topic for atom in snapshot.atoms.values()]
        normalized_topics = {normalize(topic) for topic in existing_topics}
        gaps: list[OpportunityRecord] = []
        for opportunity in opportunities:
            if normalize(opportunity.topic) in normalized_topics:
                continue
            overlap = evaluate_overlap(opportunity.topic, existing_topics)
            if overlap["should_skip"]:
                continue
            gaps.append(opportunity)
        return gaps

    def plan_clusters(self, snapshot: SiteSnapshot, gaps: list[OpportunityRecord]) -> list[Cluster]:
        clusters_by_name = {normalize(cluster.name): cluster for cluster in snapshot.clusters.values()}
        touched: list[Cluster] = []
        for gap in gaps:
            key = normalize(gap.cluster_name)
            cluster = clusters_by_name.get(key)
            if cluster is None:
                cluster = Cluster(
                    id=new_id("cluster"),
                    site_id=snapshot.site.id,
                    name=gap.cluster_name,
                    description=f"Strategic coverage area for {gap.cluster_name}",
                    priority=min(100, gap.demand_score),
                )
                snapshot.clusters[cluster.id] = cluster
                snapshot.site.cluster_ids.append(cluster.id)
                clusters_by_name[key] = cluster
            else:
                cluster.priority = max(cluster.priority, gap.demand_score)
                cluster.updated_at = utc_now()
            if cluster not in touched:
                touched.append(cluster)
        return touched

    def create_atoms(self, snapshot: SiteSnapshot, clusters: list[Cluster], gaps: list[OpportunityRecord]) -> list[Atom]:
        cluster_by_name = {normalize(cluster.name): cluster for cluster in clusters}
        created: list[Atom] = []
        for gap in gaps:
            cluster = cluster_by_name[normalize(gap.cluster_name)]
            atom = Atom(
                id=new_id("atom"),
                site_id=snapshot.site.id,
                cluster_id=cluster.id,
                topic=gap.topic,
                search_intent=gap.search_intent,
                context={
                    "brand_tone": snapshot.site.brand_tone,
                    "target_audience": snapshot.site.target_audience,
                    "monetization_strategy": snapshot.site.monetization_strategy,
                    "demand_score": gap.demand_score,
                    "cluster_name": gap.cluster_name,
                },
                priority=gap.demand_score,
                source_refs=[
                    {
                        "stage": "demand_detection",
                        "source": gap.source,
                        "confidence": gap.confidence,
                        "demand_score": gap.demand_score,
                        "overlap": evaluate_overlap(gap.topic, [existing.topic for existing in snapshot.atoms.values()]),
                    }
                ],
            )
            snapshot.atoms[atom.id] = atom
            snapshot.site.atom_ids.append(atom.id)
            cluster.atom_ids.append(atom.id)
            cluster.updated_at = utc_now()
            created.append(atom)
        return created
