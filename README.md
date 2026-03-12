# Content Publisher

Next.js-first demand-driven publishing system for operating niche sites with a shared planning loop and Supabase-backed delivery.

The canonical product vision for this repository lives in [PRODUCT.md](/Users/patrickfong/Development/content-publisher/PRODUCT.md). Local agent instructions live in [AGENTS.md](/Users/patrickfong/Development/content-publisher/AGENTS.md).

## Core Model

The engine is built around the domain vocabulary defined in `PRODUCT.md`:

- `Site`
- `Cluster`
- `Atom`
- `Output`
- `Signal`
- `Insight`

The loop remains:

`Demand Detection -> Gap Analysis -> Cluster Planning -> Atom Creation -> Content Generation -> Publishing -> Signal Collection -> Insight Generation -> Strategy Refinement`

## Current Implementation

Primary application:
- [src/app](/Users/patrickfong/Development/content-publisher/src/app)
- [src/lib](/Users/patrickfong/Development/content-publisher/src/lib)
- [src/domain](/Users/patrickfong/Development/content-publisher/src/domain)

Legacy bootstrap engine code still exists under [content_publisher](/Users/patrickfong/Development/content-publisher/content_publisher) as a reference layer while the repo is being replatformed. It is no longer the intended production packaging.

Current capabilities:

- Next.js App Router delivery layer
- Supabase-backed `engine_sites`, `site_snapshots`, and `posts` persistence
- TypeScript domain model and loop orchestration
- API route for seeding a site manifest
- API route for running the full site loop on demand or by cron
- published website outputs written into Supabase `posts`
- homepage and dynamic slug pages rendering directly from published posts
- seed SQL for `mylegoguide`
- SQL schema for initial launch on Supabase

## Launch

1. Apply [supabase/schema.sql](/Users/patrickfong/Development/content-publisher/supabase/schema.sql) in Supabase.
2. Seed [supabase/seed.mylegoguide.sql](/Users/patrickfong/Development/content-publisher/supabase/seed.mylegoguide.sql), or call `/api/setup` after deploy.
3. Set environment variables from [.env.example](/Users/patrickfong/Development/content-publisher/.env.example) in Vercel.
4. Deploy this repo to Vercel.
5. Trigger `POST /api/engine/run-site` with `Authorization: Bearer $CRON_SECRET` and body `{"siteId":"mylegoguide"}`.

## CLI

The Python CLI remains available during the replatforming period:

Initialize or scaffold sites:

```bash
python3 -m content_publisher --data-dir data/sites scaffold-site \
  --output data/site.json \
  --site-id lego \
  --name "LEGO Site" \
  --niche-focus "lego products" \
  --target-audience "search-driven buyers" \
  --brand-tone "clear and practical" \
  --monetization-strategy "affiliate links" \
  --channels website newsletter

python3 -m content_publisher --data-dir data/sites init-site --config data/site.json
python3 -m content_publisher --data-dir data/sites seed-demo --site-id demo
```

Run and inspect:

```bash
python3 -m content_publisher --data-dir data/sites run-site --site-id demo
python3 -m content_publisher --data-dir data/sites run-all
python3 -m content_publisher --data-dir data/sites show-site --site-id demo
python3 -m content_publisher --data-dir data/sites show-summary --site-id demo
python3 -m content_publisher --data-dir data/sites audit-site --site-id demo
python3 -m content_publisher --data-dir data/sites report-site --site-id demo
python3 -m content_publisher --data-dir data/sites list-sites
```

Service-publisher-compatible environment shortcuts:

```bash
export GSC_SERVICE_ACCOUNT_JSON=your-base64-encoded-service-account-json
export NEXT_PUBLIC_SITE_URL=https://your-site.com
export CRON_SECRET=your-shared-secret
```

These can be overridden per site via `site.metadata`.

## Testing

Run the test suite with:

```bash
python3 -m unittest discover -s tests -v
```

## Repository Layout

- [src/app](/Users/patrickfong/Development/content-publisher/src/app): Next.js routes and pages
- [src/domain](/Users/patrickfong/Development/content-publisher/src/domain): canonical TypeScript domain model
- [src/lib/engine](/Users/patrickfong/Development/content-publisher/src/lib/engine): loop orchestration and capabilities
- [src/lib/repositories](/Users/patrickfong/Development/content-publisher/src/lib/repositories): Supabase-backed site and snapshot persistence
- [src/lib/integrations](/Users/patrickfong/Development/content-publisher/src/lib/integrations): delivery integrations
- [supabase/schema.sql](/Users/patrickfong/Development/content-publisher/supabase/schema.sql): initial database schema
- [supabase/seed.mylegoguide.sql](/Users/patrickfong/Development/content-publisher/supabase/seed.mylegoguide.sql): initial site seed
- [content_publisher/audit.py](/Users/patrickfong/Development/content-publisher/content_publisher/audit.py): integrity checks
- [content_publisher/reporting.py](/Users/patrickfong/Development/content-publisher/content_publisher/reporting.py): markdown reporting
- [content_publisher/config.py](/Users/patrickfong/Development/content-publisher/content_publisher/config.py): shared env/site config resolution
- [content_publisher/google_auth.py](/Users/patrickfong/Development/content-publisher/content_publisher/google_auth.py): service-account JWT token exchange
- [content_publisher/affiliate.py](/Users/patrickfong/Development/content-publisher/content_publisher/affiliate.py): affiliate URL rewriting
- [content_publisher/seo.py](/Users/patrickfong/Development/content-publisher/content_publisher/seo.py): overlap and tokenization heuristics
- [tests/](/Users/patrickfong/Development/content-publisher/tests): unit coverage

## Next Work

The major remaining step is replacing local export-driven connectors with live service integrations for:

- Search Console / analytics APIs
- production CMS targets
- affiliate network APIs
