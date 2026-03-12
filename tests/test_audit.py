import tempfile
import unittest

from content_publisher.audit import audit_snapshot
from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


class AuditTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_audit_passes_for_valid_snapshot(self) -> None:
        site = Site(
            id="lego",
            name="Lego Site",
            niche_focus="lego",
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

        report = audit_snapshot(snapshot)

        self.assertTrue(report.valid)
        self.assertEqual(report.errors, [])

    def test_audit_detects_relationship_breakage(self) -> None:
        site = Site(
            id="gear",
            name="Gear Site",
            niche_focus="outdoor gear",
            target_audience="campers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "best camping stove",
                    "cluster_name": "camping stoves",
                    "search_intent": "commercial",
                    "demand_score": 85,
                    "source": "seed",
                    "confidence": 0.9,
                }
            ],
        )
        self.store.init_site(site)
        snapshot = self.engine.run_site("gear")

        atom = next(iter(snapshot.atoms.values()))
        atom.cluster_id = "cluster_missing"

        report = audit_snapshot(snapshot)

        self.assertFalse(report.valid)
        self.assertTrue(any("missing cluster" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
