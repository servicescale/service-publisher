import csv
import tempfile
import unittest
from pathlib import Path

from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


class ConnectorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_csv_demand_source_creates_atoms_from_keyword_rows(self) -> None:
        csv_path = Path(self.temp_dir.name) / "keywords.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["keyword", "cluster", "intent", "score", "source", "confidence"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "keyword": "best pour over kettle",
                    "cluster": "coffee kettles",
                    "intent": "commercial",
                    "score": "71",
                    "source": "keyword_export",
                    "confidence": "0.92",
                }
            )
            writer.writerow(
                {
                    "keyword": "ignore low score",
                    "cluster": "coffee kettles",
                    "intent": "informational",
                    "score": "15",
                    "source": "keyword_export",
                    "confidence": "0.5",
                }
            )

        site = Site(
            id="coffee",
            name="Coffee Site",
            niche_focus="coffee gear",
            target_audience="home brewers",
            brand_tone="clear",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            metadata={
                "csv_demand": {
                    "path": str(csv_path),
                    "topic_field": "keyword",
                    "cluster_field": "cluster",
                    "intent_field": "intent",
                    "score_field": "score",
                    "min_score": 50,
                }
            },
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("coffee")
        topics = {atom.topic for atom in snapshot.atoms.values()}

        self.assertIn("best pour over kettle", topics)
        self.assertNotIn("ignore low score", topics)

    def test_static_site_publisher_writes_html_page_and_index(self) -> None:
        site = Site(
            id="lego",
            name="Lego Site",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego")
        output = next(iter(snapshot.outputs.values()))
        page_path = Path(output.metadata["artifact_path"])
        index_path = self.store.channel_dir("lego", "website") / "index.html"
        sitemap_path = self.store.channel_dir("lego", "website") / "sitemap.xml"
        feed_path = self.store.channel_dir("lego", "website") / "feed.xml"

        self.assertTrue(page_path.exists())
        self.assertTrue(index_path.exists())
        self.assertTrue(sitemap_path.exists())
        self.assertTrue(feed_path.exists())
        self.assertEqual(page_path.suffix, ".html")
        self.assertIn(output.title, page_path.read_text(encoding="utf-8"))
        self.assertIn(output.title, index_path.read_text(encoding="utf-8"))
        self.assertIn(output.metadata["public_slug"], sitemap_path.read_text(encoding="utf-8"))
        self.assertIn(output.title, feed_path.read_text(encoding="utf-8"))

    def test_product_catalog_is_injected_into_generated_outputs(self) -> None:
        catalog_path = Path(self.temp_dir.name) / "products.csv"
        with catalog_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["title", "url", "price", "merchant", "tags", "description"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "title": "Adult Builder LEGO Set",
                    "url": "https://example.com/adult-lego",
                    "price": "$129",
                    "merchant": "Example Store",
                    "tags": "lego|adults|sets",
                    "description": "A LEGO set for adult builders.",
                }
            )

        site = Site(
            id="lego-products",
            name="Lego Products",
            niche_focus="lego products",
            target_audience="adult builders",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
            metadata={"product_catalog": {"path": str(catalog_path)}},
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego-products")
        output = next(iter(snapshot.outputs.values()))

        self.assertEqual(len(snapshot.products), 1)
        self.assertTrue(output.metadata["product_recommendations"])
        self.assertIn("Adult Builder LEGO Set", output.body)

    def test_csv_signal_provider_imports_real_metrics(self) -> None:
        signal_path = Path(self.temp_dir.name) / "signals.csv"
        with signal_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["topic", "channel", "kind", "value", "captured_at"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "topic": "best lego sets for adults",
                    "channel": "website",
                    "kind": "search_clicks",
                    "value": "41",
                    "captured_at": "2026-03-12T00:00:00+00:00",
                }
            )

        site = Site(
            id="lego-signals",
            name="Lego Signals",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
            metadata={"signal_csv": {"path": str(signal_path)}},
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego-signals")
        signal_kinds = {signal.kind for signal in snapshot.signals.values()}

        self.assertIn("search_clicks", signal_kinds)

    def test_affiliate_csv_provider_imports_network_metrics(self) -> None:
        catalog_path = Path(self.temp_dir.name) / "affiliate-products.csv"
        with catalog_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["title", "url", "price", "merchant", "tags", "description"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "title": "Adult Builder LEGO Set",
                    "url": "https://example.com/adult-lego",
                    "price": "$129",
                    "merchant": "Example Store",
                    "tags": "lego|adults|sets",
                    "description": "A LEGO set for adult builders.",
                }
            )

        affiliate_path = Path(self.temp_dir.name) / "affiliate.csv"
        with affiliate_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["topic", "product_title", "clicks", "conversions", "revenue", "date"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "topic": "best lego sets for adults",
                    "product_title": "Adult Builder LEGO Set",
                    "clicks": "9",
                    "conversions": "2",
                    "revenue": "18.75",
                    "date": "2026-03-12",
                }
            )

        site = Site(
            id="lego-affiliate",
            name="Lego Affiliate",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
            metadata={
                "product_catalog": {"path": str(catalog_path)},
                "affiliate_csv": {"path": str(affiliate_path)},
            },
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego-affiliate")
        summary = self.store.load_summary("lego-affiliate")
        signal_kinds = {signal.kind for signal in snapshot.signals.values()}

        self.assertIn("affiliate_network_clicks", signal_kinds)
        self.assertIn("affiliate_network_conversions", signal_kinds)
        self.assertIn("affiliate_network_revenue", signal_kinds)
        self.assertIn("affiliate_network:affiliate_network_revenue", summary.signal_source_totals)

    def test_search_console_csv_provider_imports_query_metrics(self) -> None:
        gsc_path = Path(self.temp_dir.name) / "gsc.csv"
        with gsc_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["query", "clicks", "impressions", "position", "date"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "query": "best lego sets for adults",
                    "clicks": "24",
                    "impressions": "310",
                    "position": "7.4",
                    "date": "2026-03-12",
                }
            )

        site = Site(
            id="lego-gsc",
            name="Lego GSC",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
            metadata={"gsc_csv": {"path": str(gsc_path)}},
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego-gsc")
        summary = self.store.load_summary("lego-gsc")
        report_text = self.store.report_path("lego-gsc").read_text(encoding="utf-8")
        signal_kinds = {signal.kind for signal in snapshot.signals.values()}

        self.assertIn("gsc_clicks", signal_kinds)
        self.assertIn("gsc_impressions", signal_kinds)
        self.assertIn("gsc_avg_position", signal_kinds)
        self.assertIn("google_search_console:gsc_clicks", summary.signal_source_totals)
        self.assertIn("google_search_console:gsc_clicks", report_text)

    def test_analytics_csv_provider_imports_page_metrics(self) -> None:
        analytics_path = Path(self.temp_dir.name) / "analytics.csv"
        with analytics_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["topic", "channel", "pageviews", "engaged_sessions", "revenue", "date"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "topic": "best lego sets for adults",
                    "channel": "website",
                    "pageviews": "120",
                    "engaged_sessions": "55",
                    "revenue": "12.5",
                    "date": "2026-03-12",
                }
            )

        site = Site(
            id="lego-analytics",
            name="Lego Analytics",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best lego sets for adults",
                    "cluster_name": "best lego sets",
                    "search_intent": "commercial",
                    "demand_score": 80,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
            metadata={"analytics_csv": {"path": str(analytics_path)}},
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego-analytics")
        signal_kinds = {signal.kind for signal in snapshot.signals.values()}

        self.assertIn("analytics_pageviews", signal_kinds)
        self.assertIn("analytics_engaged_sessions", signal_kinds)
        self.assertIn("analytics_revenue", signal_kinds)


if __name__ == "__main__":
    unittest.main()
