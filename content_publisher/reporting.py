from __future__ import annotations

from .models import SiteSnapshot, SiteSummary


def render_site_report(snapshot: SiteSnapshot, summary: SiteSummary) -> str:
    site = snapshot.site
    latest_run = site.loop_history[-1] if site.loop_history else None

    lines = [
        f"# Site Report: {site.name}",
        "",
        f"- Site ID: `{site.id}`",
        f"- Niche Focus: {site.niche_focus}",
        f"- Loop Runs: {site.loop_runs}",
        f"- Clusters: {summary.cluster_count}",
        f"- Atoms: {summary.atom_count}",
        f"- Outputs: {summary.output_count}",
        f"- Products: {len(snapshot.products)}",
        f"- Signals: {summary.signal_count}",
        f"- Insights: {summary.insight_count}",
        "",
        "## Channels",
        "",
    ]

    for channel, count in sorted(summary.channel_output_counts.items()):
        lines.append(f"- {channel}: {count} outputs")

    lines.extend(["", "## Signal Totals", ""])
    for kind, value in sorted(summary.signal_totals.items()):
        lines.append(f"- {kind}: {value}")

    lines.extend(["", "## Signal Sources", ""])
    if summary.signal_source_totals:
        for key, value in sorted(summary.signal_source_totals.items()):
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No source-specific signal totals yet.")

    lines.extend(["", "## Top Clusters", ""])
    if summary.top_clusters:
        for item in summary.top_clusters:
            lines.append(f"- {item['name']}: {item['clicks']} clicks")
    else:
        lines.append("- No cluster performance yet.")

    lines.extend(["", "## Latest Run", ""])
    if latest_run is None:
        lines.append("- No loop runs recorded.")
    else:
        lines.append(f"- Run Number: {latest_run.run_number}")
        lines.append(f"- Status: {latest_run.status}")
        lines.append(f"- Started At: {latest_run.started_at}")
        lines.append(f"- Completed At: {latest_run.completed_at or 'in progress'}")
        lines.append("")
        lines.append("### Stage Counts")
        lines.append("")
        for stage in latest_run.stage_runs:
            if stage.counts:
                counts = ", ".join(f"{key}={value}" for key, value in sorted(stage.counts.items()))
            else:
                counts = "no counts"
            lines.append(f"- {stage.stage}: {counts}")

    lines.extend(["", "## Recent Insights", ""])
    recent_insights = list(snapshot.insights.values())[-10:]
    if recent_insights:
        for insight in recent_insights:
            lines.append(f"- {insight.kind}: {insight.summary}")
    else:
        lines.append("- No insights generated yet.")

    return "\n".join(lines) + "\n"
