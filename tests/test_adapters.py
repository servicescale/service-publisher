import json
import tempfile
import unittest
from pathlib import Path

from content_publisher.adapters import HeuristicSignalProvider
from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


class AdapterIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_json_demand_source_is_ingested(self) -> None:
        demand_file = Path(self.temp_dir.name) / "demand.json"
        demand_file.write_text(
            json.dumps(
                [
                    {
                        "topic": "best espresso grinder",
                        "cluster_name": "espresso grinders",
                        "search_intent": "commercial",
                        "demand_score": 77,
                        "source": "json_fixture",
                        "confidence": 0.88,
                    }
                ]
            ),
            encoding="utf-8",
        )
        site = Site(
            id="coffee",
            name="Coffee Site",
            niche_focus="coffee gear",
            target_audience="home baristas",
            brand_tone="precise",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            metadata={"demand_file": str(demand_file)},
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("coffee")

        topics = {atom.topic for atom in snapshot.atoms.values()}
        self.assertIn("best espresso grinder", topics)

    def test_publish_creates_site_scoped_artifact(self) -> None:
        site = Site(
            id="outdoor",
            name="Outdoor Site",
            niche_focus="camping gear",
            target_audience="campers",
            brand_tone="practical",
            monetization_strategy="affiliate links",
            publishing_channels=["website", "newsletter"],
            opportunity_pool=[
                {
                    "topic": "best camping lantern",
                    "cluster_name": "camping lanterns",
                    "search_intent": "commercial",
                    "demand_score": 70,
                    "source": "seed",
                    "confidence": 0.8,
                }
            ],
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("outdoor")
        artifact_paths = [Path(output.metadata["artifact_path"]) for output in snapshot.outputs.values()]

        self.assertEqual(len(snapshot.outputs), 2)
        for artifact_path in artifact_paths:
            self.assertTrue(artifact_path.exists())
            self.assertIn("/outdoor/channels/", str(artifact_path))

        newsletter_output = next(output for output in snapshot.outputs.values() if output.channel == "newsletter")
        self.assertIn("Weekly Pick", newsletter_output.title)
        self.assertIn(newsletter_output.title, Path(newsletter_output.metadata["artifact_path"]).read_text(encoding="utf-8"))

    def test_signal_collection_is_idempotent_per_run_number(self) -> None:
        site = Site(
            id="lunch",
            name="Lunch Site",
            niche_focus="school lunches",
            target_audience="parents",
            brand_tone="helpful",
            monetization_strategy="affiliate links",
            publishing_channels=["website"],
            opportunity_pool=[
                {
                    "topic": "high protein school lunches",
                    "cluster_name": "school lunch ideas",
                    "search_intent": "informational",
                    "demand_score": 64,
                    "source": "seed",
                    "confidence": 0.78,
                }
            ],
        )
        self.store.init_site(site)

        snapshot = self.engine.run_site("lunch")
        output = next(iter(snapshot.outputs.values()))
        initial_count = len(output.signal_ids)
        provider = HeuristicSignalProvider()

        duplicate_collection = provider.collect(snapshot, output, run_number=1)

        self.assertEqual(len(duplicate_collection), 0)
        self.assertEqual(len(output.signal_ids), initial_count)


if __name__ == "__main__":
    unittest.main()
