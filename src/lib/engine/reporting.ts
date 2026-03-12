import { SiteSnapshot, SiteSummary } from "@/domain/models";

export function renderSiteReport(snapshot: SiteSnapshot, summary: SiteSummary): string {
  return [
    `# ${snapshot.site.name}`,
    "",
    `- Site ID: ${snapshot.site.id}`,
    `- Loop runs: ${summary.loopRuns}`,
    `- Clusters: ${summary.clusterCount}`,
    `- Atoms: ${summary.atomCount}`,
    `- Outputs: ${summary.outputCount}`,
    `- Signals: ${summary.signalCount}`,
    `- Insights: ${summary.insightCount}`,
    "",
    "## Top Clusters",
    ...summary.topClusters.map((cluster) => `- ${cluster.name}: ${cluster.clicks} clicks`)
  ].join("\n");
}
