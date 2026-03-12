from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_snapshot
from .bootstrap import create_site_manifest, write_site_manifest
from .engine import PublishingEngine
from .models import Site
from .reporting import render_site_report
from .store import SiteStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demand-driven content publishing engine")
    parser.add_argument("--data-dir", default="data/sites", help="Directory for site state storage")

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_demo = subparsers.add_parser("seed-demo", help="Create a demo site")
    seed_demo.add_argument("--site-id", required=True)
    seed_demo.add_argument("--name", default="Demo Content Site")

    run_site = subparsers.add_parser("run-site", help="Run the full publishing loop for a site")
    run_site.add_argument("--site-id", required=True)

    show_site = subparsers.add_parser("show-site", help="Print site state as JSON")
    show_site.add_argument("--site-id", required=True)

    init_site = subparsers.add_parser("init-site", help="Create a site from a JSON config file")
    init_site.add_argument("--config", required=True, help="Path to a JSON config file")

    scaffold = subparsers.add_parser("scaffold-site", help="Write a site manifest template to disk")
    scaffold.add_argument("--output", required=True, help="Path for the site manifest JSON file")
    scaffold.add_argument("--site-id", required=True)
    scaffold.add_argument("--name", required=True)
    scaffold.add_argument("--niche-focus", required=True)
    scaffold.add_argument("--target-audience", required=True)
    scaffold.add_argument("--brand-tone", required=True)
    scaffold.add_argument("--monetization-strategy", required=True)
    scaffold.add_argument("--channels", nargs="+", required=True)

    list_sites = subparsers.add_parser("list-sites", help="List known sites")
    run_all = subparsers.add_parser("run-all", help="Run the loop for every initialized site")
    show_summary = subparsers.add_parser("show-summary", help="Print the latest site summary as JSON")
    show_summary.add_argument("--site-id", required=True)
    audit_site = subparsers.add_parser("audit-site", help="Validate a site's stored domain relationships")
    audit_site.add_argument("--site-id", required=True)
    report_site = subparsers.add_parser("report-site", help="Print the generated markdown report for a site")
    report_site.add_argument("--site-id", required=True)
    return parser


def seed_demo_site(site_id: str, name: str) -> Site:
    return Site(
        id=site_id,
        name=name,
        niche_focus="product-led niche publishing",
        target_audience="search-driven buyers",
        brand_tone="clear and practical",
        monetization_strategy="affiliate links and buying guides",
        publishing_channels=["website", "newsletter"],
        opportunity_pool=[
            {
                "topic": "best lego sets for adults",
                "cluster_name": "best lego sets",
                "search_intent": "commercial",
                "demand_score": 82,
                "source": "keyword_dataset",
                "confidence": 0.91,
            },
            {
                "topic": "best lego sets under $100",
                "cluster_name": "best lego sets",
                "search_intent": "commercial",
                "demand_score": 74,
                "source": "search_trends",
                "confidence": 0.86,
            },
            {
                "topic": "lego storage ideas",
                "cluster_name": "lego storage ideas",
                "search_intent": "informational",
                "demand_score": 61,
                "source": "competitor_analysis",
                "confidence": 0.8,
            },
        ],
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    store = SiteStore(args.data_dir)
    engine = PublishingEngine(store)

    if args.command == "seed-demo":
        site = seed_demo_site(args.site_id, args.name)
        store.init_site(site)
        print(f"Seeded demo site '{site.id}' in {Path(args.data_dir).resolve()}")
        return

    if args.command == "run-site":
        snapshot = engine.run_site(args.site_id)
        print(
            json.dumps(
                {
                    "site_id": snapshot.site.id,
                    "loop_runs": snapshot.site.loop_runs,
                    "clusters": len(snapshot.clusters),
                    "atoms": len(snapshot.atoms),
                    "outputs": len(snapshot.outputs),
                    "signals": len(snapshot.signals),
                    "insights": len(snapshot.insights),
                },
                indent=2,
            )
        )
        return

    if args.command == "show-site":
        snapshot = store.load(args.site_id)
        print(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "list-sites":
        print(json.dumps(store.list_sites(), indent=2))
        return

    if args.command == "init-site":
        config_path = Path(args.config)
        site = Site.from_dict(json.loads(config_path.read_text(encoding="utf-8")))
        store.init_site(site)
        print(f"Initialized site '{site.id}' from {config_path}")
        return

    if args.command == "scaffold-site":
        manifest = create_site_manifest(
            site_id=args.site_id,
            name=args.name,
            niche_focus=args.niche_focus,
            target_audience=args.target_audience,
            brand_tone=args.brand_tone,
            monetization_strategy=args.monetization_strategy,
            publishing_channels=args.channels,
        )
        output_path = write_site_manifest(args.output, manifest)
        print(f"Wrote site manifest to {output_path}")
        return

    if args.command == "run-all":
        snapshots = engine.run_all_sites()
        print(
            json.dumps(
                [
                    {
                        "site_id": snapshot.site.id,
                        "loop_runs": snapshot.site.loop_runs,
                        "outputs": len(snapshot.outputs),
                        "signals": len(snapshot.signals),
                        "insights": len(snapshot.insights),
                    }
                    for snapshot in snapshots
                ],
                indent=2,
            )
        )
        return

    if args.command == "show-summary":
        summary = store.load_summary(args.site_id)
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "audit-site":
        snapshot = store.load(args.site_id)
        report = audit_snapshot(snapshot)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return

    if args.command == "report-site":
        report_path = store.report_path(args.site_id)
        if not report_path.exists():
            snapshot = store.load(args.site_id)
            try:
                summary = store.load_summary(args.site_id)
            except FileNotFoundError:
                summary = engine.build_summary(snapshot)
                store.save_summary(summary)
            store.save_report(args.site_id, render_site_report(snapshot, summary))
        print(report_path.read_text(encoding="utf-8"))
        return


if __name__ == "__main__":
    main()
