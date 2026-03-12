import json
import tempfile
import unittest
from unittest.mock import patch

from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


class _MockResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> "_MockResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class CrmPublishingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_website_channel_can_publish_to_supabase_crm(self) -> None:
        site = Site(
            id="crm-site",
            name="CRM Site",
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
                "site_url": "https://example.com",
                "crm": {
                    "provider": "supabase",
                    "supabase_url": "https://db.example.supabase.co",
                    "service_role_key": "service-role-key",
                },
            },
        )
        self.store.init_site(site)

        captured: list[dict[str, object]] = []

        def fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
            captured.append(
                {
                    "url": request.full_url,
                    "method": request.get_method(),
                    "timeout": timeout,
                    "headers": dict(request.header_items()),
                    "body": request.data.decode("utf-8") if request.data else "",
                }
            )
            if request.get_method() == "GET":
                return _MockResponse([])
            return _MockResponse(
                [
                    {
                        "id": "post-1",
                        "slug": "best-lego-sets-for-adults",
                        "status": "published",
                        "published_at": "2026-03-12T00:00:00+00:00",
                    }
                ]
            )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            snapshot = self.engine.run_site("crm-site")

        website_output = next(output for output in snapshot.outputs.values() if output.channel == "website")
        newsletter_output = next(output for output in snapshot.outputs.values() if output.channel == "newsletter")

        self.assertEqual(captured[0]["method"], "GET")
        self.assertEqual(captured[1]["method"], "POST")
        self.assertIn("/rest/v1/posts", str(captured[1]["url"]))
        payload = json.loads(str(captured[1]["body"]))
        self.assertEqual(payload["title"], website_output.title)
        self.assertEqual(payload["slug"], "best-lego-sets-for-adults")
        self.assertEqual(payload["status"], "published")
        self.assertIn("content_md", payload)
        self.assertEqual(website_output.metadata["artifact_path"], "https://example.com/best-lego-sets-for-adults")
        self.assertEqual(website_output.metadata["crm"]["provider"], "supabase")
        self.assertIn("artifact_path", newsletter_output.metadata)
        self.assertNotIn("crm", newsletter_output.metadata)

    def test_existing_slug_is_updated_instead_of_inserted(self) -> None:
        site = Site(
            id="crm-update-site",
            name="CRM Update Site",
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
                "crm": {
                    "provider": "supabase",
                    "supabase_url": "https://db.example.supabase.co",
                    "service_role_key": "service-role-key",
                }
            },
        )
        self.store.init_site(site)

        methods: list[str] = []

        def fake_urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
            methods.append(request.get_method())
            if request.get_method() == "GET":
                return _MockResponse([{"id": "post-1", "slug": "best-lego-sets-for-adults"}])
            return _MockResponse([{"id": "post-1", "slug": "best-lego-sets-for-adults", "status": "published"}])

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            snapshot = self.engine.run_site("crm-update-site")

        output = next(iter(snapshot.outputs.values()))
        self.assertEqual(methods, ["GET", "PATCH"])
        self.assertEqual(output.metadata["crm"]["record"]["id"], "post-1")
