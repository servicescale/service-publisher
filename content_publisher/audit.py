from __future__ import annotations

from dataclasses import dataclass, field

from .models import SiteSnapshot


@dataclass
class AuditReport:
    site_id: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "site_id": self.site_id,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "stats": self.stats,
        }


def audit_snapshot(snapshot: SiteSnapshot) -> AuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    site = snapshot.site

    for cluster in snapshot.clusters.values():
        if cluster.site_id != site.id:
            errors.append(f"Cluster {cluster.id} belongs to site {cluster.site_id}, expected {site.id}.")
        if cluster.id not in site.cluster_ids:
            errors.append(f"Cluster {cluster.id} missing from site.cluster_ids.")
        for atom_id in cluster.atom_ids:
            atom = snapshot.atoms.get(atom_id)
            if atom is None:
                errors.append(f"Cluster {cluster.id} references missing atom {atom_id}.")
                continue
            if atom.cluster_id != cluster.id:
                errors.append(f"Atom {atom.id} points to cluster {atom.cluster_id}, expected {cluster.id}.")

    for atom in snapshot.atoms.values():
        if atom.site_id != site.id:
            errors.append(f"Atom {atom.id} belongs to site {atom.site_id}, expected {site.id}.")
        if atom.id not in site.atom_ids:
            errors.append(f"Atom {atom.id} missing from site.atom_ids.")
        if atom.cluster_id not in snapshot.clusters:
            errors.append(f"Atom {atom.id} references missing cluster {atom.cluster_id}.")
        if not atom.source_refs:
            warnings.append(f"Atom {atom.id} has no source_refs provenance.")
        for output_id in atom.output_ids:
            output = snapshot.outputs.get(output_id)
            if output is None:
                errors.append(f"Atom {atom.id} references missing output {output_id}.")
                continue
            if output.atom_id != atom.id:
                errors.append(f"Output {output.id} points to atom {output.atom_id}, expected {atom.id}.")

    for output in snapshot.outputs.values():
        if output.site_id != site.id:
            errors.append(f"Output {output.id} belongs to site {output.site_id}, expected {site.id}.")
        if output.id not in site.output_ids:
            errors.append(f"Output {output.id} missing from site.output_ids.")
        if output.atom_id not in snapshot.atoms:
            errors.append(f"Output {output.id} references missing atom {output.atom_id}.")
        if output.status == "published" and "artifact_path" not in output.metadata:
            warnings.append(f"Output {output.id} is published without artifact_path metadata.")
        for signal_id in output.signal_ids:
            if signal_id not in snapshot.signals:
                errors.append(f"Output {output.id} references missing signal {signal_id}.")

    for signal in snapshot.signals.values():
        if signal.site_id != site.id:
            errors.append(f"Signal {signal.id} belongs to site {signal.site_id}, expected {site.id}.")
        if signal.id not in site.signal_ids:
            errors.append(f"Signal {signal.id} missing from site.signal_ids.")
        if signal.output_id not in snapshot.outputs:
            errors.append(f"Signal {signal.id} references missing output {signal.output_id}.")
        if "run_number" not in signal.dimensions:
            warnings.append(f"Signal {signal.id} is missing run_number dimension.")

    for insight in snapshot.insights.values():
        if insight.site_id != site.id:
            errors.append(f"Insight {insight.id} belongs to site {insight.site_id}, expected {site.id}.")
        if insight.id not in site.insight_ids:
            errors.append(f"Insight {insight.id} missing from site.insight_ids.")
        if insight.scope == "cluster" and insight.scope_id not in snapshot.clusters:
            errors.append(f"Insight {insight.id} references missing cluster {insight.scope_id}.")
        if insight.scope == "atom" and insight.scope_id not in snapshot.atoms:
            errors.append(f"Insight {insight.id} references missing atom {insight.scope_id}.")

    if site.loop_runs != len([run for run in site.loop_history if run.status == "completed"]):
        warnings.append("site.loop_runs does not match completed loop history length.")

    for loop_run in site.loop_history:
        if len(loop_run.stage_runs) != 9:
            warnings.append(f"Loop run {loop_run.id} recorded {len(loop_run.stage_runs)} stages instead of 9.")

    return AuditReport(
        site_id=site.id,
        valid=not errors,
        errors=errors,
        warnings=warnings,
        stats={
            "clusters": len(snapshot.clusters),
            "atoms": len(snapshot.atoms),
            "outputs": len(snapshot.outputs),
            "signals": len(snapshot.signals),
            "insights": len(snapshot.insights),
            "loop_history": len(site.loop_history),
        },
    )
