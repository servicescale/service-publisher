from __future__ import annotations

import csv
import json
import urllib.request
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Protocol

from .integrations.affiliate_links import decorate_product
from .integrations.google_search_console import SearchConsoleClient, ServiceAccountTokenError
from .models import Output, Product, Signal, Site, SiteSnapshot, new_id, utc_now
from .store import SiteStore


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


class Publisher(Protocol):
    channel: str

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        ...


class SignalProvider(Protocol):
    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        ...


class ProductCatalogSource(Protocol):
    def collect(self, snapshot: SiteSnapshot) -> list[Product]:
        ...


class SiteOpportunityPoolSource:
    def collect(self, snapshot: SiteSnapshot) -> list[OpportunityRecord]:
        records: list[OpportunityRecord] = []
        for raw in snapshot.site.opportunity_pool:
            records.append(
                OpportunityRecord(
                    topic=str(raw["topic"]).strip(),
                    cluster_name=str(raw.get("cluster_name") or self._guess_cluster_name(raw["topic"])).strip(),
                    search_intent=str(raw.get("search_intent") or "informational").strip(),
                    demand_score=int(raw.get("demand_score", 50)),
                    source=str(raw.get("source", "seed")).strip(),
                    confidence=float(raw.get("confidence", 0.7)),
                )
            )
        return records

    def _guess_cluster_name(self, topic: str) -> str:
        words = topic.split()
        return " ".join(words[: min(3, len(words))]).strip() or "general"


class JsonFileDemandSource:
    """Optional demand source loaded from a site-scoped JSON file path in metadata."""

    def collect(self, snapshot: SiteSnapshot) -> list[OpportunityRecord]:
        path_value = snapshot.site.metadata.get("demand_file")
        if not path_value:
            return []

        path = Path(path_value)
        if not path.exists():
            return []

        payload = json.loads(path.read_text(encoding="utf-8"))
        records: list[OpportunityRecord] = []
        for raw in payload:
            records.append(
                OpportunityRecord(
                    topic=str(raw["topic"]).strip(),
                    cluster_name=str(raw.get("cluster_name") or raw["topic"]).strip(),
                    search_intent=str(raw.get("search_intent") or "informational").strip(),
                    demand_score=int(raw.get("demand_score", 50)),
                    source=str(raw.get("source", "json_file")).strip(),
                    confidence=float(raw.get("confidence", 0.65)),
                )
            )
        return records


class CsvDemandSource:
    """CSV-backed demand ingestion configured via site metadata."""

    def collect(self, snapshot: SiteSnapshot) -> list[OpportunityRecord]:
        config = snapshot.site.metadata.get("csv_demand")
        if not config:
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        topic_field = str(config.get("topic_field", "topic"))
        cluster_field = str(config.get("cluster_field", "cluster_name"))
        intent_field = str(config.get("intent_field", "search_intent"))
        score_field = str(config.get("score_field", "demand_score"))
        source_field = str(config.get("source_field", "source"))
        confidence_field = str(config.get("confidence_field", "confidence"))
        min_score = int(config.get("min_score", 0))
        default_source = str(config.get("default_source", "csv_demand"))

        records: list[OpportunityRecord] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                topic = str(row.get(topic_field, "")).strip()
                if not topic:
                    continue
                demand_score = int(float(row.get(score_field, 50) or 50))
                if demand_score < min_score:
                    continue
                records.append(
                    OpportunityRecord(
                        topic=topic,
                        cluster_name=str(row.get(cluster_field) or topic).strip(),
                        search_intent=str(row.get(intent_field) or "informational").strip(),
                        demand_score=demand_score,
                        source=str(row.get(source_field) or default_source).strip(),
                        confidence=float(row.get(confidence_field, 0.7) or 0.7),
                    )
                )
        return records


class CsvProductCatalogSource:
    """CSV-backed product catalog configured via site metadata."""

    def collect(self, snapshot: SiteSnapshot) -> list[Product]:
        config = snapshot.site.metadata.get("product_catalog")
        if not config:
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        title_field = str(config.get("title_field", "title"))
        url_field = str(config.get("url_field", "url"))
        price_field = str(config.get("price_field", "price"))
        merchant_field = str(config.get("merchant_field", "merchant"))
        tags_field = str(config.get("tags_field", "tags"))
        description_field = str(config.get("description_field", "description"))

        products: list[Product] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                title = str(row.get(title_field, "")).strip()
                url = str(row.get(url_field, "")).strip()
                if not title or not url:
                    continue
                tags = [item.strip().lower() for item in str(row.get(tags_field, "")).split("|") if item.strip()]
                raw_url = str(row.get(url_field, "")).strip()
                product = decorate_product(
                    snapshot.site,
                    Product(
                        id=new_id("product"),
                        site_id=snapshot.site.id,
                        title=title,
                        url=raw_url,
                        price=str(row.get(price_field, "")).strip(),
                        merchant=str(row.get(merchant_field, "")).strip(),
                        tags=tags,
                        description=str(row.get(description_field, "")).strip(),
                    ),
                )
                products.append(product)
        return products


class MarkdownPublisher:
    def __init__(self, store: SiteStore, channel: str) -> None:
        self.store = store
        self.channel = channel

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        artifact_path = self.store.output_artifact_path(snapshot.site.id, self.channel, output.id)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        if not artifact_path.exists():
            artifact_path.write_text(output.body + "\n", encoding="utf-8")

        output.status = "published"
        output.published_at = output.published_at or utc_now()
        output.updated_at = utc_now()
        output.metadata["artifact_path"] = str(artifact_path)
        return output


class JsonCmsPublisher:
    """Publishes outputs to a JSON-speaking CMS endpoint."""

    def __init__(self, endpoint: str, headers: dict[str, str] | None = None, timeout: float = 10.0) -> None:
        self.channel = "website"
        self.endpoint = endpoint
        self.headers = headers or {}
        self.timeout = timeout

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        atom = snapshot.atoms[output.atom_id]
        payload = {
            "site_id": snapshot.site.id,
            "title": output.title,
            "content": output.body,
            "channel": output.channel,
            "kind": output.kind,
            "atom_topic": atom.topic,
            "cluster_id": atom.cluster_id,
            "search_intent": atom.search_intent,
            "metadata": output.metadata,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", **self.headers},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8") or "{}")

        output.status = "published"
        output.published_at = output.published_at or utc_now()
        output.updated_at = utc_now()
        output.metadata["cms_endpoint"] = self.endpoint
        output.metadata["cms_response"] = response_payload
        if "url" in response_payload:
            output.metadata["artifact_path"] = str(response_payload["url"])
        return output


class StaticSitePublisher:
    def __init__(self, store: SiteStore, channel: str = "website") -> None:
        self.store = store
        self.channel = channel

    def publish(self, snapshot: SiteSnapshot, output: Output) -> Output:
        site_root = self.store.channel_dir(snapshot.site.id, self.channel)
        pages_dir = site_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        slug = self._slugify(output.title)
        page_path = pages_dir / f"{slug}.html"
        page_path.write_text(self._render_page(snapshot, output), encoding="utf-8")
        (site_root / "index.html").write_text(self._render_index(snapshot), encoding="utf-8")
        (site_root / "sitemap.xml").write_text(self._render_sitemap(snapshot), encoding="utf-8")
        (site_root / "feed.xml").write_text(self._render_feed(snapshot), encoding="utf-8")

        output.status = "published"
        output.published_at = output.published_at or utc_now()
        output.updated_at = utc_now()
        output.metadata["artifact_path"] = str(page_path)
        output.metadata["public_slug"] = slug
        return output

    def _render_page(self, snapshot: SiteSnapshot, output: Output) -> str:
        atom = snapshot.atoms[output.atom_id]
        cluster = snapshot.clusters[atom.cluster_id]
        paragraphs = [
            f"<p>{escape(line)}</p>"
            for line in output.body.splitlines()
            if line.strip() and not line.startswith("# ")
        ]
        recommendations = output.metadata.get("product_recommendations", [])
        recommendation_markup = []
        if recommendations:
            recommendation_markup.extend(
                [
                    "  <section>",
                    "    <h2>Recommended Products</h2>",
                    "    <ul>",
                ]
            )
            for item in recommendations:
                merchant = f" ({escape(item.get('merchant', ''))})" if item.get("merchant") else ""
                price = f" - {escape(item.get('price', ''))}" if item.get("price") else ""
                recommendation_markup.append(
                    f"      <li><a href=\"{escape(item.get('url', '#'))}\">{escape(item.get('title', 'Product'))}</a>{merchant}{price}</li>"
                )
            recommendation_markup.extend(["    </ul>", "  </section>"])
        return "\n".join(
            [
                "<!doctype html>",
                "<html lang=\"en\">",
                "<head>",
                "  <meta charset=\"utf-8\">",
                f"  <title>{escape(output.title)}</title>",
                f"  <meta name=\"description\" content=\"{escape(atom.topic)}\">",
                "  <style>body{font-family:Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.6;}header,footer{color:#444;}a{color:#0f5c4d;}code{background:#f2f2f2;padding:2px 4px;}article{margin-top:24px;} .meta{font-size:0.95rem;color:#666;}</style>",
                "</head>",
                "<body>",
                f"  <header><a href=\"../index.html\">Home</a><h1>{escape(output.title)}</h1></header>",
                f"  <p class=\"meta\">Cluster: {escape(cluster.name)} | Intent: {escape(atom.search_intent)} | Kind: {escape(output.kind)}</p>",
                "  <article>",
                *paragraphs,
                "  </article>",
                *recommendation_markup,
                f"  <footer><p>Generated by Content Publisher for site <code>{escape(snapshot.site.id)}</code>.</p></footer>",
                "</body>",
                "</html>",
            ]
        )

    def _render_index(self, snapshot: SiteSnapshot) -> str:
        website_outputs = [output for output in snapshot.outputs.values() if output.channel == self.channel]
        website_outputs.sort(key=lambda item: item.title.lower())
        items = [
            f"<li><a href=\"pages/{escape(output.metadata.get('public_slug', self._slugify(output.title)))}.html\">{escape(output.title)}</a></li>"
            for output in website_outputs
        ]
        return "\n".join(
            [
                "<!doctype html>",
                "<html lang=\"en\">",
                "<head>",
                "  <meta charset=\"utf-8\">",
                f"  <title>{escape(snapshot.site.name)}</title>",
                "  <style>body{font-family:Georgia,serif;max-width:760px;margin:40px auto;padding:0 20px;line-height:1.6;}a{color:#0f5c4d;}</style>",
                "</head>",
                "<body>",
                f"  <h1>{escape(snapshot.site.name)}</h1>",
                f"  <p>{escape(snapshot.site.niche_focus)}</p>",
                "  <ul>",
                *items,
                "  </ul>",
                "</body>",
                "</html>",
            ]
        )

    def _render_sitemap(self, snapshot: SiteSnapshot) -> str:
        website_outputs = [output for output in snapshot.outputs.values() if output.channel == self.channel]
        website_outputs.sort(key=lambda item: item.updated_at)
        entries = [
            f"  <url><loc>/pages/{escape(output.metadata.get('public_slug', self._slugify(output.title)))}.html</loc><lastmod>{escape(output.updated_at)}</lastmod></url>"
            for output in website_outputs
        ]
        return "\n".join(
            [
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
                *entries,
                "</urlset>",
            ]
        )

    def _render_feed(self, snapshot: SiteSnapshot) -> str:
        website_outputs = [output for output in snapshot.outputs.values() if output.channel == self.channel]
        website_outputs.sort(key=lambda item: item.updated_at, reverse=True)
        items = [
            "\n".join(
                [
                    "  <item>",
                    f"    <title>{escape(output.title)}</title>",
                    f"    <link>/pages/{escape(output.metadata.get('public_slug', self._slugify(output.title)))}.html</link>",
                    f"    <guid>{escape(output.id)}</guid>",
                    f"    <pubDate>{escape(output.published_at or output.updated_at)}</pubDate>",
                    "  </item>",
                ]
            )
            for output in website_outputs[:20]
        ]
        return "\n".join(
            [
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
                "<rss version=\"2.0\">",
                "  <channel>",
                f"    <title>{escape(snapshot.site.name)}</title>",
                f"    <description>{escape(snapshot.site.niche_focus)}</description>",
                "    <link>/</link>",
                *items,
                "  </channel>",
                "</rss>",
            ]
        )

    def _slugify(self, value: str) -> str:
        chars = []
        for char in value.lower():
            if char.isalnum():
                chars.append(char)
            elif chars and chars[-1] != "-":
                chars.append("-")
        return "".join(chars).strip("-") or "output"


class HeuristicSignalProvider:
    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        atom = snapshot.atoms[output.atom_id]
        demand_score = int(atom.context.get("demand_score", atom.priority))
        impressions = max(10, demand_score * 12 + run_number * 7)
        clicks = max(1, round(impressions * min(0.35, 0.06 + demand_score / 400)))
        revenue = round(clicks * 0.42, 2)

        existing = {
            (signal.kind, signal.dimensions.get("run_number"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }

        signals: list[Signal] = []
        for kind, value in (
            ("impressions", float(impressions)),
            ("clicks", float(clicks)),
            ("affiliate_revenue", float(revenue)),
        ):
            key = (kind, run_number)
            if key in existing:
                continue
            signals.append(
                Signal(
                    id=new_id("signal"),
                    site_id=snapshot.site.id,
                    output_id=output.id,
                    kind=kind,
                    value=value,
                    captured_at=utc_now(),
                    dimensions={"run_number": run_number, "channel": output.channel},
                )
            )
        return signals


class CsvSignalProvider:
    """Imports search or affiliate metrics from a CSV export declared in site metadata."""

    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        config = snapshot.site.metadata.get("signal_csv")
        if not config:
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        topic_field = str(config.get("topic_field", "topic"))
        channel_field = str(config.get("channel_field", "channel"))
        kind_field = str(config.get("kind_field", "kind"))
        value_field = str(config.get("value_field", "value"))
        date_field = str(config.get("date_field", "captured_at"))
        source_name = str(config.get("source_name", "csv_signal_import"))

        atom = snapshot.atoms[output.atom_id]
        normalized_topic = self._normalize(atom.topic)
        existing = {
            (signal.kind, signal.dimensions.get("run_number"), signal.dimensions.get("source"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }

        signals: list[Signal] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_topic = self._normalize(str(row.get(topic_field, "")).strip())
                row_channel = str(row.get(channel_field, output.channel)).strip() or output.channel
                if row_topic != normalized_topic or row_channel != output.channel:
                    continue
                kind = str(row.get(kind_field, "")).strip()
                if not kind:
                    continue
                key = (kind, run_number, source_name)
                if key in existing:
                    continue
                signals.append(
                    Signal(
                        id=new_id("signal"),
                        site_id=snapshot.site.id,
                        output_id=output.id,
                        kind=kind,
                        value=float(row.get(value_field, 0) or 0),
                        captured_at=str(row.get(date_field) or utc_now()),
                        dimensions={"run_number": run_number, "channel": output.channel, "source": source_name},
                    )
                )
                existing.add(key)
        return signals

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().split())


class SearchConsoleCsvSignalProvider:
    """Imports Search Console-style performance rows from CSV exports."""

    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        config = snapshot.site.metadata.get("gsc_csv")
        if not config or output.channel != "website":
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        query_field = str(config.get("query_field", "query"))
        clicks_field = str(config.get("clicks_field", "clicks"))
        impressions_field = str(config.get("impressions_field", "impressions"))
        position_field = str(config.get("position_field", "position"))
        date_field = str(config.get("date_field", "date"))
        source_name = str(config.get("source_name", "google_search_console"))

        atom = snapshot.atoms[output.atom_id]
        topic = self._normalize(atom.topic)
        existing = {
            (signal.kind, signal.dimensions.get("run_number"), signal.dimensions.get("source"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }
        aggregates = {"gsc_clicks": 0.0, "gsc_impressions": 0.0, "gsc_avg_position": 0.0}
        positions: list[float] = []
        captured_at = utc_now()

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                query = self._normalize(str(row.get(query_field, "")).strip())
                if query != topic:
                    continue
                aggregates["gsc_clicks"] += float(row.get(clicks_field, 0) or 0)
                aggregates["gsc_impressions"] += float(row.get(impressions_field, 0) or 0)
                if row.get(position_field):
                    positions.append(float(row.get(position_field, 0) or 0))
                captured_at = str(row.get(date_field) or captured_at)

        if positions:
            aggregates["gsc_avg_position"] = round(sum(positions) / len(positions), 2)

        signals: list[Signal] = []
        for kind, value in aggregates.items():
            if value <= 0 and kind != "gsc_avg_position":
                continue
            if kind == "gsc_avg_position" and not positions:
                continue
            key = (kind, run_number, source_name)
            if key in existing:
                continue
            signals.append(
                Signal(
                    id=new_id("signal"),
                    site_id=snapshot.site.id,
                    output_id=output.id,
                    kind=kind,
                    value=value,
                    captured_at=captured_at,
                    dimensions={"run_number": run_number, "channel": output.channel, "source": source_name},
                )
            )
        return signals

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().split())


class LiveSearchConsoleSignalProvider:
    """Live GSC ingestion using the service-account pattern from service-publisher."""

    SEARCHANALYTICS_API = "https://searchconsole.googleapis.com/webmasters/v3"
    SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        if output.channel != "website":
            return []

        live_config = snapshot.site.metadata.get("live_gsc", {})
        if live_config.get("enabled") is False:
            return []

        client = SearchConsoleClient(snapshot.site)
        if not client.enabled():
            return []

        atom = snapshot.atoms[output.atom_id]
        existing = {
            (signal.kind, signal.dimensions.get("run_number"), signal.dimensions.get("source"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }

        try:
            rows = client.query_exact_topic(atom.topic, days=int(live_config.get("days", 7)))
        except (OSError, ServiceAccountTokenError, urllib.error.URLError):
            return []

        aggregates = {
            "gsc_live_clicks": sum(float(row.get("clicks", 0)) for row in rows),
            "gsc_live_impressions": sum(float(row.get("impressions", 0)) for row in rows),
        }
        positions = [float(row.get("position", 0)) for row in rows if row.get("position") is not None]
        if positions:
            aggregates["gsc_live_avg_position"] = round(sum(positions) / len(positions), 2)

        signals: list[Signal] = []
        for kind, value in aggregates.items():
            if value <= 0:
                continue
            key = (kind, run_number, "google_search_console_live")
            if key in existing:
                continue
            signals.append(
                Signal(
                    id=new_id("signal"),
                    site_id=snapshot.site.id,
                    output_id=output.id,
                    kind=kind,
                    value=value,
                    captured_at=utc_now(),
                    dimensions={"run_number": run_number, "channel": output.channel, "source": "google_search_console_live"},
                )
            )
        return signals


class AnalyticsCsvSignalProvider:
    """Imports analytics CSV exports keyed by topic or page title."""

    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        config = snapshot.site.metadata.get("analytics_csv")
        if not config:
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        topic_field = str(config.get("topic_field", "topic"))
        channel_field = str(config.get("channel_field", "channel"))
        pageviews_field = str(config.get("pageviews_field", "pageviews"))
        engaged_field = str(config.get("engaged_sessions_field", "engaged_sessions"))
        revenue_field = str(config.get("revenue_field", "revenue"))
        date_field = str(config.get("date_field", "date"))
        source_name = str(config.get("source_name", "analytics_export"))

        atom = snapshot.atoms[output.atom_id]
        topic = self._normalize(atom.topic)
        existing = {
            (signal.kind, signal.dimensions.get("run_number"), signal.dimensions.get("source"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }
        aggregates = {"analytics_pageviews": 0.0, "analytics_engaged_sessions": 0.0, "analytics_revenue": 0.0}
        captured_at = utc_now()

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_topic = self._normalize(str(row.get(topic_field, "")).strip())
                row_channel = str(row.get(channel_field, output.channel)).strip() or output.channel
                if row_topic != topic or row_channel != output.channel:
                    continue
                aggregates["analytics_pageviews"] += float(row.get(pageviews_field, 0) or 0)
                aggregates["analytics_engaged_sessions"] += float(row.get(engaged_field, 0) or 0)
                aggregates["analytics_revenue"] += float(row.get(revenue_field, 0) or 0)
                captured_at = str(row.get(date_field) or captured_at)

        signals: list[Signal] = []
        for kind, value in aggregates.items():
            if value <= 0:
                continue
            key = (kind, run_number, source_name)
            if key in existing:
                continue
            signals.append(
                Signal(
                    id=new_id("signal"),
                    site_id=snapshot.site.id,
                    output_id=output.id,
                    kind=kind,
                    value=value,
                    captured_at=captured_at,
                    dimensions={"run_number": run_number, "channel": output.channel, "source": source_name},
                )
            )
        return signals

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().split())


class AffiliateCsvSignalProvider:
    """Imports affiliate network exports keyed by topic and optionally product title."""

    def collect(self, snapshot: SiteSnapshot, output: Output, run_number: int) -> list[Signal]:
        config = snapshot.site.metadata.get("affiliate_csv")
        if not config:
            return []

        path = Path(config["path"])
        if not path.exists():
            return []

        topic_field = str(config.get("topic_field", "topic"))
        product_field = str(config.get("product_field", "product_title"))
        clicks_field = str(config.get("clicks_field", "clicks"))
        conversions_field = str(config.get("conversions_field", "conversions"))
        revenue_field = str(config.get("revenue_field", "revenue"))
        date_field = str(config.get("date_field", "date"))
        source_name = str(config.get("source_name", "affiliate_network"))

        atom = snapshot.atoms[output.atom_id]
        normalized_topic = self._normalize(atom.topic)
        recommended_titles = {
            self._normalize(item.get("title", ""))
            for item in output.metadata.get("product_recommendations", [])
            if item.get("title")
        }
        existing = {
            (signal.kind, signal.dimensions.get("run_number"), signal.dimensions.get("source"))
            for signal in snapshot.signals.values()
            if signal.output_id == output.id
        }

        aggregates = {
            "affiliate_network_clicks": 0.0,
            "affiliate_network_conversions": 0.0,
            "affiliate_network_revenue": 0.0,
        }
        captured_at = utc_now()
        matched_product = ""

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                row_topic = self._normalize(str(row.get(topic_field, "")).strip())
                row_product = self._normalize(str(row.get(product_field, "")).strip())
                if row_topic != normalized_topic and (recommended_titles and row_product not in recommended_titles):
                    continue
                aggregates["affiliate_network_clicks"] += float(row.get(clicks_field, 0) or 0)
                aggregates["affiliate_network_conversions"] += float(row.get(conversions_field, 0) or 0)
                aggregates["affiliate_network_revenue"] += float(row.get(revenue_field, 0) or 0)
                captured_at = str(row.get(date_field) or captured_at)
                matched_product = str(row.get(product_field, "")).strip() or matched_product

        signals: list[Signal] = []
        for kind, value in aggregates.items():
            if value <= 0:
                continue
            key = (kind, run_number, source_name)
            if key in existing:
                continue
            signals.append(
                Signal(
                    id=new_id("signal"),
                    site_id=snapshot.site.id,
                    output_id=output.id,
                    kind=kind,
                    value=value,
                    captured_at=captured_at,
                    dimensions={
                        "run_number": run_number,
                        "channel": output.channel,
                        "source": source_name,
                        "matched_product": matched_product,
                    },
                )
            )
        return signals

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().split())
