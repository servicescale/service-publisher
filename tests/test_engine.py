import json
import tempfile
import unittest

from content_publisher.engine import PublishingEngine
from content_publisher.models import Site
from content_publisher.store import SiteStore


def build_site(site_id: str, topic: str, cluster_name: str, demand_score: int) -> Site:
    return Site(
        id=site_id,
        name=f"Site {site_id}",
        niche_focus="niche publishing",
        target_audience="buyers",
        brand_tone="useful",
        monetization_strategy="affiliate links",
        publishing_channels=["website"],
        opportunity_pool=[
            {
                "topic": topic,
                "cluster_name": cluster_name,
                "search_intent": "commercial",
                "demand_score": demand_score,
                "source": "keyword_dataset",
                "confidence": 0.9,
            }
        ],
    )


class PublishingEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = SiteStore(self.temp_dir.name)
        self.engine = PublishingEngine(self.store)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_site_executes_full_loop(self) -> None:
        site = build_site("lego", "best lego sets for adults", "best lego sets", 80)
        self.store.init_site(site)

        snapshot = self.engine.run_site("lego")

        self.assertEqual(snapshot.site.loop_runs, 1)
        self.assertEqual(len(snapshot.clusters), 1)
        self.assertEqual(len(snapshot.atoms), 1)
        self.assertEqual(len(snapshot.outputs), 1)
        self.assertEqual(len(snapshot.signals), 3)
        self.assertGreaterEqual(len(snapshot.insights), 2)
        self.assertEqual(len(snapshot.site.loop_history), 1)
        self.assertEqual(len(snapshot.site.loop_history[0].stage_runs), 9)

        atom = next(iter(snapshot.atoms.values()))
        output = next(iter(snapshot.outputs.values()))
        cluster = next(iter(snapshot.clusters.values()))

        self.assertEqual(atom.cluster_id, cluster.id)
        self.assertIn(atom.id, cluster.atom_ids)
        self.assertEqual(output.atom_id, atom.id)
        self.assertEqual(output.status, "published")
        self.assertTrue(output.signal_ids)

    def test_run_all_sites_executes_every_initialized_site(self) -> None:
        self.store.init_site(build_site("lego", "best lego sets for adults", "best lego sets", 80))
        self.store.init_site(build_site("gear", "best camping stove", "camping stoves", 85))

        snapshots = self.engine.run_all_sites()

        self.assertEqual({snapshot.site.id for snapshot in snapshots}, {"lego", "gear"})
        self.assertEqual(self.store.load("lego").site.loop_runs, 1)
        self.assertEqual(self.store.load("gear").site.loop_runs, 1)

    def test_sites_remain_isolated(self) -> None:
        site_a = build_site("lego", "best lego sets for adults", "best lego sets", 80)
        site_b = build_site("lunch", "nut free lunchbox ideas", "lunchbox ideas", 55)
        self.store.init_site(site_a)
        self.store.init_site(site_b)

        self.engine.run_site("lego")

        lego_snapshot = self.store.load("lego")
        lunch_snapshot = self.store.load("lunch")

        self.assertEqual(len(lego_snapshot.atoms), 1)
        self.assertEqual(len(lunch_snapshot.atoms), 0)
        self.assertTrue(self.store.state_path("lego").exists())
        self.assertTrue(self.store.state_path("lunch").exists())
        self.assertNotEqual(
            json.loads(self.store.state_path("lego").read_text(encoding="utf-8")),
            json.loads(self.store.state_path("lunch").read_text(encoding="utf-8")),
        )

    def test_insights_feed_future_atom_creation(self) -> None:
        site = build_site("gear", "best camping stove", "camping stoves", 85)
        self.store.init_site(site)

        first_run = self.engine.run_site("gear")
        self.assertGreaterEqual(len(first_run.insights), 2)
        self.assertGreaterEqual(len(first_run.site.opportunity_pool), 3)

        second_run = self.engine.run_site("gear")
        topics = {atom.topic for atom in second_run.atoms.values()}

        self.assertIn("camping stoves for beginners", topics)
        self.assertIn("best camping stove comparison", topics)
        self.assertGreaterEqual(second_run.site.loop_runs, 2)

    def test_summary_is_persisted_after_run(self) -> None:
        site = build_site("coffee", "best espresso machine", "espresso machines", 78)
        site.publishing_channels = ["website", "newsletter"]
        self.store.init_site(site)

        snapshot = self.engine.run_site("coffee")
        summary = self.store.load_summary("coffee")

        self.assertEqual(summary.site_id, "coffee")
        self.assertEqual(summary.loop_runs, snapshot.site.loop_runs)
        self.assertEqual(summary.output_count, len(snapshot.outputs))
        self.assertEqual(summary.channel_output_counts["website"], 1)
        self.assertEqual(summary.channel_output_counts["newsletter"], 1)
        self.assertTrue(self.store.report_path("coffee").exists())
        report_text = self.store.report_path("coffee").read_text(encoding="utf-8")
        self.assertIn("Site Report: Site coffee", report_text)
        self.assertIn("## Latest Run", report_text)


if __name__ == "__main__":
    unittest.main()
