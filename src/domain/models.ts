export type StageName =
  | "demand_detection"
  | "gap_analysis"
  | "cluster_planning"
  | "atom_creation"
  | "content_generation"
  | "publishing"
  | "signal_collection"
  | "insight_generation"
  | "strategy_refinement";

export type OpportunityRecord = {
  topic: string;
  clusterName: string;
  searchIntent: string;
  demandScore: number;
  source: string;
  confidence: number;
};

export type Cluster = {
  id: string;
  siteId: string;
  name: string;
  description: string;
  priority: number;
  atomIds: string[];
  createdAt: string;
  updatedAt: string;
};

export type Atom = {
  id: string;
  siteId: string;
  clusterId: string;
  topic: string;
  searchIntent: string;
  context: Record<string, unknown>;
  priority: number;
  state: "planned" | "generated" | "published";
  sourceRefs: Record<string, unknown>[];
  outputIds: string[];
  signalIds: string[];
  insightIds: string[];
  createdAt: string;
  updatedAt: string;
};

export type Output = {
  id: string;
  siteId: string;
  atomId: string;
  channel: string;
  kind: string;
  title: string;
  body: string;
  status: "draft" | "published";
  metadata: Record<string, unknown>;
  publishedAt: string | null;
  signalIds: string[];
  createdAt: string;
  updatedAt: string;
};

export type Signal = {
  id: string;
  siteId: string;
  outputId: string;
  kind: string;
  value: number;
  capturedAt: string;
  dimensions: Record<string, unknown>;
};

export type Insight = {
  id: string;
  siteId: string;
  scope: "cluster" | "atom";
  scopeId: string;
  kind: string;
  summary: string;
  evidence: Record<string, unknown>;
  impactScore: number;
  createdAt: string;
};

export type Product = {
  id: string;
  siteId: string;
  title: string;
  url: string;
  price: string;
  merchant: string;
  tags: string[];
  description: string;
  createdAt: string;
  updatedAt: string;
};

export type StageRun = {
  stage: StageName;
  startedAt: string;
  completedAt: string;
  status: "running" | "completed" | "failed";
  counts: Record<string, number>;
  notes: string[];
};

export type LoopRun = {
  id: string;
  siteId: string;
  runNumber: number;
  startedAt: string;
  completedAt: string | null;
  status: "running" | "completed" | "failed";
  stageRuns: StageRun[];
  summary: Record<string, unknown>;
};

export type Site = {
  id: string;
  name: string;
  nicheFocus: string;
  targetAudience: string;
  brandTone: string;
  monetizationStrategy: string;
  publishingChannels: string[];
  opportunityPool: Record<string, unknown>[];
  clusterIds: string[];
  atomIds: string[];
  outputIds: string[];
  productIds: string[];
  signalIds: string[];
  insightIds: string[];
  loopHistory: LoopRun[];
  loopRuns: number;
  createdAt: string;
  updatedAt: string;
  metadata: Record<string, unknown>;
};

export type SiteSnapshot = {
  site: Site;
  clusters: Record<string, Cluster>;
  atoms: Record<string, Atom>;
  outputs: Record<string, Output>;
  products: Record<string, Product>;
  signals: Record<string, Signal>;
  insights: Record<string, Insight>;
};

export type SiteSummary = {
  siteId: string;
  loopRuns: number;
  clusterCount: number;
  atomCount: number;
  outputCount: number;
  signalCount: number;
  insightCount: number;
  channelOutputCounts: Record<string, number>;
  signalTotals: Record<string, number>;
  signalSourceTotals: Record<string, number>;
  topClusters: { clusterId: string; name: string; clicks: number }[];
  updatedAt: string;
};

export function utcNow(): string {
  return new Date().toISOString();
}

export function newId(prefix: string): string {
  const random = Math.random().toString(16).slice(2, 14).padEnd(12, "0");
  return `${prefix}_${random}`;
}

export function createSiteSnapshot(site: Site): SiteSnapshot {
  return {
    site,
    clusters: {},
    atoms: {},
    outputs: {},
    products: {},
    signals: {},
    insights: {}
  };
}
