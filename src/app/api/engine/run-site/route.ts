import { NextRequest, NextResponse } from "next/server";
import { runSiteLoop } from "@/lib/engine/orchestrator";
import { SiteRepository } from "@/lib/repositories/site-repository";

function authorized(request: NextRequest): boolean {
  const secret = process.env.CRON_SECRET;
  if (!secret) {
    return false;
  }
  return request.headers.get("authorization") === `Bearer ${secret}`;
}

export async function POST(request: NextRequest) {
  if (!authorized(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = (await request.json().catch(() => ({}))) as { siteId?: string };
  const siteId = body.siteId ?? "mylegoguide";

  const repository = new SiteRepository();
  const result = await runSiteLoop(repository, siteId);
  return NextResponse.json({
    status: "ok",
    siteId,
    summary: result.summary
  });
}
