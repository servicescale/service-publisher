import os
import tempfile
import unittest
from unittest.mock import patch

from content_publisher.affiliate import build_affiliate_url
from content_publisher.config import gsc_service_account_json, site_url
from content_publisher.engine import PublishingEngine
from content_publisher.google_auth import ServiceAccountTokenError
from content_publisher.models import Site
from content_publisher.seo import jaccard_similarity, overlap_signal
from content_publisher.store import SiteStore


class ShortcutReuseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_affiliate_url_builder_adds_tracking_and_amazon_tag(self) -> None:
        url = build_affiliate_url(
            "https://www.amazon.com.au/example-product",
            source="easykidslunches",
            medium="gear",
            campaign="gear-page",
            content="featured-pick",
            associate_tag="easy03-22",
        )

        self.assertIn("utm_source=easykidslunches", url)
        self.assertIn("utm_medium=gear", url)
        self.assertIn("utm_campaign=gear-page", url)
        self.assertIn("utm_content=featured-pick", url)
        self.assertIn("tag=easy03-22", url)

    def test_overlap_signal_matches_service_publisher_style_deduping(self) -> None:
        overlap = overlap_signal(
            "best lego sets for adults",
            ["top lego sets for adults", "kids lego storage ideas"],
        )

        self.assertTrue(overlap["nearest_matches"])
        self.assertGreaterEqual(jaccard_similarity("best lego sets for adults", "top lego sets for adults"), 0.6)

    def test_env_config_falls_back_to_service_publisher_names(self) -> None:
        site = Site(
            id="env-site",
            name="Env Site",
            niche_focus="gear",
            target_audience="buyers",
            brand_tone="clear",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
        )
        with patch.dict(
            os.environ,
            {
                "GSC_SERVICE_ACCOUNT_JSON": "abc123",
                "NEXT_PUBLIC_SITE_URL": "https://example.com",
            },
            clear=False,
        ):
            self.assertEqual(gsc_service_account_json(site), "abc123")
            self.assertEqual(site_url(site), "https://example.com")

    def test_live_gsc_provider_is_safe_when_token_exchange_fails(self) -> None:
        site = Site(
            id="live-gsc",
            name="Live GSC",
            niche_focus="lego",
            target_audience="buyers",
            brand_tone="clear",
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
                "site_url": "https://example.com",
                "gsc_service_account_json": "not-real",
            },
        )
        self.store.init_site(site)

        with patch(
            "content_publisher.integrations.google_search_console.fetch_service_account_token",
            side_effect=ServiceAccountTokenError("bad"),
        ):
            snapshot = self.engine.run_site("live-gsc")

        self.assertTrue(snapshot.signals)


if __name__ == "__main__":
    unittest.main()
