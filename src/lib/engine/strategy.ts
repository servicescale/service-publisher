import { Atom, Insight, SiteSnapshot, SiteSummary, utcNow, newId } from "@/domain/models";

export function generateInsights(snapshot: SiteSnapshot): Insight[] {
  const clicksByCluster = new Map<string, number>();
  const clicksByAtom = new Map<string, number>();
  const insights: Insight[] = [];

  for (const atom of Object.values(snapshot.atoms)) {
    const clicks = atom.signalIds
      .map((signalId) => snapshot.signals[signalId])
      .filter((signal) => signal?.kind === "clicks")
      .reduce((sum, signal) => sum + signal.value, 0);

    clicksByAtom.set(atom.id, clicks);
    clicksByCluster.set(atom.clusterId, (clicksByCluster.get(atom.clusterId) ?? 0) + clicks);
  }

  for (const cluster of Object.values(snapshot.clusters)) {
    const clicks = clicksByCluster.get(cluster.id) ?? 0;
    if (clicks >= 30) {
      const insight: Insight = {
        id: newId("insight"),
        siteId: snapshot.site.id,
        scope: "cluster",
        scopeId: cluster.id,
        kind: "expand_cluster",
        summary: `Expand cluster '${cluster.name}' based on strong click performance.`,
        evidence: { clicks, atomCount: cluster.atomIds.length },
        impactScore: Number((clicks / Math.max(1, cluster.atomIds.length)).toFixed(2)),
        createdAt: utcNow()
      };
      snapshot.insights[insight.id] = insight;
      snapshot.site.insightIds.push(insight.id);
      insights.push(insight);
    }
  }

  for (const atom of Object.values(snapshot.atoms)) {
    const clicks = clicksByAtom.get(atom.id) ?? 0;
    if (clicks < 10) {
      const insight = buildAtomInsight(snapshot, atom, "deprioritize_atom", `Deprioritize low-performing atom '${atom.topic}'.`, { clicks }, Math.max(1, 10 - clicks));
      insights.push(insight);
    } else if (clicks >= 20) {
      const insight = buildAtomInsight(snapshot, atom, "extend_atom", `Create follow-up atoms related to '${atom.topic}'.`, { clicks, clusterId: atom.clusterId }, clicks);
      insights.push(insight);
    }
  }

  return insights;
}

function buildAtomInsight(
  snapshot: SiteSnapshot,
  atom: Atom,
  kind: string,
  summary: string,
  evidence: Record<string, unknown>,
  impactScore: number
): Insight {
  const insight: Insight = {
    id: newId("insight"),
    siteId: snapshot.site.id,
    scope: "atom",
    scopeId: atom.id,
    kind,
    summary,
    evidence,
    impactScore,
    createdAt: utcNow()
  };
  snapshot.insights[insight.id] = insight;
  snapshot.site.insightIds.push(insight.id);
  atom.insightIds.push(insight.id);
  return insight;
}

export function refineStrategy(snapshot: SiteSnapshot, insights: Insight[]): void {
  const existingTopics = new Set(snapshot.site.opportunityPool.map((item) => String(item.topic ?? "").toLowerCase()));

  for (const insight of insights) {
    if (insight.kind === "expand_cluster") {
      const cluster = snapshot.clusters[insight.scopeId];
      if (!cluster) {
        continue;
      }
      cluster.priority = Math.min(100, cluster.priority + 10);
      cluster.updatedAt = utcNow();
      const topic = `${cluster.name} for beginners`;
      if (!existingTopics.has(topic.toLowerCase())) {
        snapshot.site.opportunityPool.push({
          topic,
          cluster_name: cluster.name,
          search_intent: "informational",
          demand_score: cluster.priority,
          source: "insight_generation",
          confidence: 0.8
        });
        existingTopics.add(topic.toLowerCase());
      }
    }

    if (insight.kind === "extend_atom") {
      const atom = snapshot.atoms[insight.scopeId];
      if (!atom) {
        continue;
      }
      const topic = `${atom.topic} comparison`;
      if (!existingTopics.has(topic.toLowerCase())) {
        snapshot.site.opportunityPool.push({
          topic,
          cluster_name: String(atom.context.clusterName ?? "general"),
          search_intent: atom.searchIntent,
          demand_score: Math.min(100, atom.priority + 5),
          source: "insight_generation",
          confidence: 0.85
        });
        existingTopics.add(topic.toLowerCase());
      }
    }

    if (insight.kind === "deprioritize_atom") {
      const atom = snapshot.atoms[insight.scopeId];
      if (atom) {
        atom.priority = Math.max(1, atom.priority - 10);
        atom.updatedAt = utcNow();
      }
    }
  }
}

export function buildSummary(snapshot: SiteSnapshot): SiteSummary {
  const channelOutputCounts: Record<string, number> = {};
  const signalTotals: Record<string, number> = {};
  const signalSourceTotals: Record<string, number> = {};
  const clusterScores: Record<string, number> = {};

  for (const output of Object.values(snapshot.outputs)) {
    channelOutputCounts[output.channel] = (channelOutputCounts[output.channel] ?? 0) + 1;
  }

  for (const signal of Object.values(snapshot.signals)) {
    signalTotals[signal.kind] = Number(((signalTotals[signal.kind] ?? 0) + signal.value).toFixed(2));
    const source = String(signal.dimensions.source ?? "engine");
    const key = `${source}:${signal.kind}`;
    signalSourceTotals[key] = Number(((signalSourceTotals[key] ?? 0) + signal.value).toFixed(2));

    const output = snapshot.outputs[signal.outputId];
    if (signal.kind === "clicks" && output) {
      const atom = snapshot.atoms[output.atomId];
      if (atom) {
        clusterScores[atom.clusterId] = (clusterScores[atom.clusterId] ?? 0) + signal.value;
      }
    }
  }

  const topClusters = Object.entries(clusterScores)
    .sort((left, right) => right[1] - left[1])
    .slice(0, 5)
    .map(([clusterId, clicks]) => ({
      clusterId,
      name: snapshot.clusters[clusterId]?.name ?? clusterId,
      clicks
    }));

  return {
    siteId: snapshot.site.id,
    loopRuns: snapshot.site.loopRuns,
    clusterCount: Object.keys(snapshot.clusters).length,
    atomCount: Object.keys(snapshot.atoms).length,
    outputCount: Object.keys(snapshot.outputs).length,
    signalCount: Object.keys(snapshot.signals).length,
    insightCount: Object.keys(snapshot.insights).length,
    channelOutputCounts,
    signalTotals,
    signalSourceTotals,
    topClusters,
    updatedAt: utcNow()
  };
}
