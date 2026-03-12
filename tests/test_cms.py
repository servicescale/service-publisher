import io
import json
import tempfile
import unittest
from unittest.mock import patch

from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


class _MockResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CmsPublishingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_website_channel_can_publish_to_json_cms(self) -> None:
        site = Site(
            id="cms-site",
            name="CMS Site",
            niche_focus="lego products",
            target_audience="buyers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website", "newsletter"],
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
                "cms": {
                    "endpoint": "https://cms.example.test/posts",
                    "headers": {"X-Test-Token": "abc123"},
                }
            },
        )
        self.store.init_site(site)

        captured: dict[str, object] = {}

        def fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return _MockResponse(
                {
                    "id": "cms-1",
                    "url": "https://cms.example.test/posts/1",
                    "status": "published",
                }
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            snapshot = self.engine.run_site("cms-site")

        website_output = next(output for output in snapshot.outputs.values() if output.channel == "website")
        newsletter_output = next(output for output in snapshot.outputs.values() if output.channel == "newsletter")

        self.assertEqual(captured["url"], "https://cms.example.test/posts")
        self.assertEqual(captured["body"]["title"], website_output.title)
        self.assertEqual(captured["body"]["atom_topic"], "best lego sets for adults")
        self.assertEqual(website_output.metadata["cms_response"]["status"], "published")
        self.assertEqual(website_output.metadata["artifact_path"], "https://cms.example.test/posts/1")
        self.assertIn("artifact_path", newsletter_output.metadata)
        self.assertNotIn("cms_response", newsletter_output.metadata)


if __name__ == "__main__":
    unittest.main()
