import { Atom, Cluster, OpportunityRecord, SiteSnapshot, newId, utcNow } from "@/domain/models";
import { normalize, overlapSignal } from "@/lib/engine/utils";

export function detectDemand(snapshot: SiteSnapshot): OpportunityRecord[] {
  const pool = snapshot.site.opportunityPool;
  const opportunities = new Map<string, OpportunityRecord>();

  for (const raw of pool) {
    const record: OpportunityRecord = {
      topic: String(raw.topic ?? "").trim(),
      clusterName: String(raw.cluster_name ?? raw.clusterName ?? raw.topic ?? "general").trim(),
      searchIntent: String(raw.search_intent ?? raw.searchIntent ?? "informational").trim(),
      demandScore: Number(raw.demand_score ?? raw.demandScore ?? 50),
      source: String(raw.source ?? "seed").trim(),
      confidence: Number(raw.confidence ?? 0.7)
    };
    if (!record.topic) {
      continue;
    }
    const key = `${normalize(record.topic)}::${normalize(record.clusterName)}`;
    const current = opportunities.get(key);
    if (!current || record.demandScore > current.demandScore) {
      opportunities.set(key, record);
    }
  }

  return [...opportunities.values()];
}

export function analyzeGaps(snapshot: SiteSnapshot, opportunities: OpportunityRecord[]): OpportunityRecord[] {
  const existingTopics = Object.values(snapshot.atoms).map((atom) => atom.topic);
  const normalizedTopics = new Set(existingTopics.map(normalize));

  return opportunities.filter((opportunity) => {
    if (normalizedTopics.has(normalize(opportunity.topic))) {
      return false;
    }
    return !overlapSignal(opportunity.topic, existingTopics).shouldSkip;
  });
}

export function planClusters(snapshot: SiteSnapshot, gaps: OpportunityRecord[]): Cluster[] {
  const byName = new Map<string, Cluster>();
  for (const cluster of Object.values(snapshot.clusters)) {
    byName.set(normalize(cluster.name), cluster);
  }

  const touched: Cluster[] = [];
  for (const gap of gaps) {
    const key = normalize(gap.clusterName);
    let cluster = byName.get(key);
    if (!cluster) {
      cluster = {
        id: newId("cluster"),
        siteId: snapshot.site.id,
        name: gap.clusterName,
        description: `Strategic coverage area for ${gap.clusterName}`,
        priority: Math.min(100, gap.demandScore),
        atomIds: [],
        createdAt: utcNow(),
        updatedAt: utcNow()
      };
      snapshot.clusters[cluster.id] = cluster;
      snapshot.site.clusterIds.push(cluster.id);
      byName.set(key, cluster);
    } else {
      cluster.priority = Math.max(cluster.priority, gap.demandScore);
      cluster.updatedAt = utcNow();
    }
    if (!touched.find((candidate) => candidate.id === cluster.id)) {
      touched.push(cluster);
    }
  }

  return touched;
}

export function createAtoms(snapshot: SiteSnapshot, clusters: Cluster[], gaps: OpportunityRecord[]): Atom[] {
  const clusterByName = new Map(clusters.map((cluster) => [normalize(cluster.name), cluster]));
  const created: Atom[] = [];

  for (const gap of gaps) {
    const cluster = clusterByName.get(normalize(gap.clusterName));
    if (!cluster) {
      continue;
    }
    const atom: Atom = {
      id: newId("atom"),
      siteId: snapshot.site.id,
      clusterId: cluster.id,
      topic: gap.topic,
      searchIntent: gap.searchIntent,
      context: {
        brandTone: snapshot.site.brandTone,
        targetAudience: snapshot.site.targetAudience,
        monetizationStrategy: snapshot.site.monetizationStrategy,
        demandScore: gap.demandScore,
        clusterName: gap.clusterName
      },
      priority: gap.demandScore,
      state: "planned",
      sourceRefs: [
        {
          stage: "demand_detection",
          source: gap.source,
          confidence: gap.confidence,
          demandScore: gap.demandScore
        }
      ],
      outputIds: [],
      signalIds: [],
      insightIds: [],
      createdAt: utcNow(),
      updatedAt: utcNow()
    };
    snapshot.atoms[atom.id] = atom;
    snapshot.site.atomIds.push(atom.id);
    cluster.atomIds.push(atom.id);
    cluster.updatedAt = utcNow();
    created.push(atom);
  }

  return created;
}
