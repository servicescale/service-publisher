import { createSiteSnapshot, LoopRun, Output, Site, SiteSnapshot, SiteSummary, StageName, newId, utcNow } from "@/domain/models";
import { generateOutputs } from "@/lib/engine/content";
import { detectDemand, analyzeGaps, createAtoms, planClusters } from "@/lib/engine/planning";
import { renderSiteReport } from "@/lib/engine/reporting";
import { collectSignals } from "@/lib/engine/signals";
import { buildSummary, generateInsights, refineStrategy } from "@/lib/engine/strategy";
import { publishOutputToCrm } from "@/lib/integrations/supabase-crm";
import { SiteRepository } from "@/lib/repositories/site-repository";

export async function runSiteLoop(repository: SiteRepository, siteId: string): Promise<{ snapshot: SiteSnapshot; summary: SiteSummary; report: string }> {
  const snapshot = (await repository.loadSiteSnapshot(siteId)) ?? createSiteSnapshot(await repository.loadSite(siteId));
  const loopRun: LoopRun = {
    id: newId("loop"),
    siteId,
    runNumber: snapshot.site.loopRuns + 1,
    startedAt: utcNow(),
    completedAt: null,
    status: "running",
    stageRuns: [],
    summary: {}
  };

  snapshot.site.loopHistory.push(loopRun);

  const opportunities = recordStage(loopRun, "demand_detection", () => detectDemand(snapshot));
  const gaps = recordStage(loopRun, "gap_analysis", () => analyzeGaps(snapshot, opportunities));
  const clusters = recordStage(loopRun, "cluster_planning", () => planClusters(snapshot, gaps));
  const atoms = recordStage(loopRun, "atom_creation", () => createAtoms(snapshot, clusters, gaps));
  const outputs = recordStage(loopRun, "content_generation", () => generateOutputs(snapshot, atoms));
  await recordStage(loopRun, "publishing", async () => deliverOutputs(repository, snapshot.site, snapshot, outputs));
  recordStage(loopRun, "signal_collection", () => collectSignals(snapshot, outputs));
  const insights = recordStage(loopRun, "insight_generation", () => generateInsights(snapshot));
  recordStage(loopRun, "strategy_refinement", () => refineStrategy(snapshot, insights));

  snapshot.site.loopRuns += 1;
  snapshot.site.updatedAt = utcNow();
  loopRun.completedAt = utcNow();
  loopRun.status = "completed";
  loopRun.summary = {
    clusters: Object.keys(snapshot.clusters).length,
    atoms: Object.keys(snapshot.atoms).length,
    outputs: Object.keys(snapshot.outputs).length,
    signals: Object.keys(snapshot.signals).length,
    insights: Object.keys(snapshot.insights).length
  };

  const summary = buildSummary(snapshot);
  const report = renderSiteReport(snapshot, summary);

  await repository.saveSiteSnapshot(siteId, snapshot, summary, report);
  return { snapshot, summary, report };
}

async function deliverOutputs(repository: SiteRepository, site: Site, snapshot: SiteSnapshot, outputs: Output[]): Promise<Output[]> {
  const admin = repository.admin();
  for (const output of outputs) {
    if (output.channel === "website") {
      await publishOutputToCrm(admin, snapshot, output);
      output.metadata.artifactPath = `${String(site.metadata.siteUrl ?? "").replace(/\/$/, "")}/${output.metadata.publicSlug ?? ""}`;
    } else {
      output.status = "published";
      output.publishedAt = output.publishedAt ?? utcNow();
      output.updatedAt = utcNow();
    }
    snapshot.atoms[output.atomId].state = "published";
    snapshot.atoms[output.atomId].updatedAt = utcNow();
  }
  return outputs;
}

function recordStage<T>(loopRun: LoopRun, stage: StageName, work: () => T): T;
function recordStage<T>(loopRun: LoopRun, stage: StageName, work: () => Promise<T>): Promise<T>;
function recordStage<T>(loopRun: LoopRun, stage: StageName, work: () => T | Promise<T>): T | Promise<T> {
  const startedAt = utcNow();
  const stageRun = {
    stage,
    startedAt,
    completedAt: startedAt,
    status: "running" as const,
    counts: {},
    notes: []
  };
  loopRun.stageRuns.push(stageRun);

  const finalize = (result: T): T => {
    stageRun.completedAt = utcNow();
    stageRun.status = "completed";
    if (Array.isArray(result)) {
      stageRun.counts.items = result.length;
    }
    return result;
  };

  const fail = (error: unknown): never => {
    stageRun.completedAt = utcNow();
    stageRun.status = "failed";
    stageRun.notes.push(error instanceof Error ? error.message : String(error));
    loopRun.status = "failed";
    throw error;
  };

  try {
    const result = work();
    if (result instanceof Promise) {
      return result.then(finalize).catch(fail);
    }
    return finalize(result);
  } catch (error) {
    return fail(error);
  }
}
