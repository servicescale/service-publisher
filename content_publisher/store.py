from __future__ import annotations

import json
from pathlib import Path

from .models import Site, SiteSnapshot, SiteSummary


class SiteStore:
    """File-backed site storage with one isolated state file per site."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def site_dir(self, site_id: str) -> Path:
        return self.root / site_id

    def state_path(self, site_id: str) -> Path:
        return self.site_dir(site_id) / "state.json"

    def summary_path(self, site_id: str) -> Path:
        return self.site_dir(site_id) / "summary.json"

    def report_path(self, site_id: str) -> Path:
        return self.site_dir(site_id) / "report.md"

    def channel_dir(self, site_id: str, channel: str) -> Path:
        return self.site_dir(site_id) / "channels" / channel

    def output_artifact_path(self, site_id: str, channel: str, output_id: str) -> Path:
        return self.channel_dir(site_id, channel) / f"{output_id}.md"

    def exists(self, site_id: str) -> bool:
        return self.state_path(site_id).exists()

    def save(self, snapshot: SiteSnapshot) -> None:
        site_dir = self.site_dir(snapshot.site.id)
        site_dir.mkdir(parents=True, exist_ok=True)
        self.state_path(snapshot.site.id).write_text(
            json.dumps(snapshot.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def save_summary(self, summary: SiteSummary) -> None:
        site_dir = self.site_dir(summary.site_id)
        site_dir.mkdir(parents=True, exist_ok=True)
        self.summary_path(summary.site_id).write_text(
            json.dumps(summary.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def load_summary(self, site_id: str) -> SiteSummary:
        path = self.summary_path(site_id)
        if not path.exists():
            raise FileNotFoundError(f"Missing summary for site: {site_id}")
        return SiteSummary.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_report(self, site_id: str, report: str) -> None:
        site_dir = self.site_dir(site_id)
        site_dir.mkdir(parents=True, exist_ok=True)
        self.report_path(site_id).write_text(report, encoding="utf-8")

    def load(self, site_id: str) -> SiteSnapshot:
        path = self.state_path(site_id)
        if not path.exists():
            raise FileNotFoundError(f"Unknown site: {site_id}")
        return SiteSnapshot.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def init_site(self, site: Site) -> SiteSnapshot:
        snapshot = SiteSnapshot(site=site)
        self.save(snapshot)
        return snapshot

    def list_sites(self) -> list[str]:
        return sorted(path.name for path in self.root.iterdir() if path.is_dir())
