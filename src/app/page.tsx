import Link from "next/link";
import { SiteRepository } from "@/lib/repositories/site-repository";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const repository = new SiteRepository(createSupabaseServerClient());
  const posts = await repository.listPublishedPosts(9);
  const summary = await repository.getSiteSummary("mylegoguide");

  return (
    <main className="shell">
      <header className="site-header">
        <Link className="brand" href="/">
          My LEGO Guide
        </Link>
        <Link className="cta" href="/api/setup">
          Seed Site
        </Link>
      </header>

      <section className="hero">
        <div className="hero-card">
          <p className="eyebrow">Demand-Driven Publishing</p>
          <h1>LEGO buying guides delivered straight from the engine.</h1>
          <p>
            This app is the live delivery layer for the publishing engine. It reads published
            outputs from Supabase and keeps the planning loop above the CMS substrate.
          </p>
          <p>
            Run the loop with a signed POST to <code>/api/engine/run-site</code> and the published
            website outputs will appear here.
          </p>
        </div>
        <aside className="panel">
          <p className="eyebrow">Site Summary</p>
          <div className="report-grid">
            <div className="metric">
              <strong>{summary?.loopRuns ?? 0}</strong>
              Loop runs
            </div>
            <div className="metric">
              <strong>{summary?.clusterCount ?? 0}</strong>
              Clusters
            </div>
            <div className="metric">
              <strong>{summary?.atomCount ?? 0}</strong>
              Atoms
            </div>
            <div className="metric">
              <strong>{summary?.outputCount ?? 0}</strong>
              Outputs
            </div>
          </div>
        </aside>
      </section>

      <section>
        <h2 className="section-title">Latest Guides</h2>
        <div className="grid">
          {posts.map((post) => (
            <Link className="card" key={post.id} href={`/${post.slug}`}>
              <p className="meta">{post.pillar?.replace(/_/g, " ") ?? "guide"}</p>
              <h2>{post.title}</h2>
              <p className="muted">{post.meta_description ?? "Published from the demand-driven engine."}</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
