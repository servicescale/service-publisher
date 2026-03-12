import { NextRequest, NextResponse } from "next/server";
import { createSiteManifest } from "@/domain/site-manifest";
import { createSiteSnapshot } from "@/domain/models";
import { renderSiteReport } from "@/lib/engine/reporting";
import { buildSummary } from "@/lib/engine/strategy";
import { SiteRepository } from "@/lib/repositories/site-repository";

export async function POST(request: NextRequest) {
  const payload = await request.json();
  const site = createSiteManifest(payload);
  const snapshot = createSiteSnapshot(site);
  const summary = buildSummary(snapshot);
  const report = renderSiteReport(snapshot, summary);

  const repository = new SiteRepository();
  await repository.saveSite(site);
  await repository.saveSiteSnapshot(site.id, snapshot, summary, report);

  return NextResponse.json({ status: "ok", siteId: site.id });
}
