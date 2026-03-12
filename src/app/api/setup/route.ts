import { NextResponse } from "next/server";
import { createMyLegoGuideManifest } from "@/domain/site-manifest";
import { createSiteSnapshot } from "@/domain/models";
import { renderSiteReport } from "@/lib/engine/reporting";
import { buildSummary } from "@/lib/engine/strategy";
import { SiteRepository } from "@/lib/repositories/site-repository";

export async function GET() {
  const repository = new SiteRepository();
  const site = createMyLegoGuideManifest();
  const snapshot = createSiteSnapshot(site);
  const summary = buildSummary(snapshot);
  const report = renderSiteReport(snapshot, summary);
  await repository.saveSite(site);
  await repository.saveSiteSnapshot(site.id, snapshot, summary, report);
  return NextResponse.json({ status: "ok", siteId: site.id });
}
