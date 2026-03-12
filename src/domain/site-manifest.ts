import { Site, utcNow } from "@/domain/models";

export function createSiteManifest(input: {
  id: string;
  name: string;
  nicheFocus: string;
  targetAudience: string;
  brandTone: string;
  monetizationStrategy: string;
  publishingChannels: string[];
  opportunityPool?: Record<string, unknown>[];
  metadata?: Record<string, unknown>;
}): Site {
  const now = utcNow();
  return {
    id: input.id,
    name: input.name,
    nicheFocus: input.nicheFocus,
    targetAudience: input.targetAudience,
    brandTone: input.brandTone,
    monetizationStrategy: input.monetizationStrategy,
    publishingChannels: input.publishingChannels,
    opportunityPool: input.opportunityPool ?? [],
    clusterIds: [],
    atomIds: [],
    outputIds: [],
    productIds: [],
    signalIds: [],
    insightIds: [],
    loopHistory: [],
    loopRuns: 0,
    createdAt: now,
    updatedAt: now,
    metadata: input.metadata ?? {}
  };
}

export function createMyLegoGuideManifest(): Site {
  return createSiteManifest({
    id: "mylegoguide",
    name: "My LEGO Guide",
    nicheFocus: "lego product guides and buying content",
    targetAudience: "adult builders, gift buyers, and collectors",
    brandTone: "clear, practical, and commercial without hype",
    monetizationStrategy: "affiliate links and buying guides",
    publishingChannels: ["website", "newsletter"],
    opportunityPool: [
      {
        topic: "best lego sets for adults",
        cluster_name: "best lego sets",
        search_intent: "commercial",
        demand_score: 82,
        source: "seed",
        confidence: 0.91
      },
      {
        topic: "best lego sets under $100",
        cluster_name: "best lego sets",
        search_intent: "commercial",
        demand_score: 74,
        source: "seed",
        confidence: 0.87
      },
      {
        topic: "lego gift ideas for adults",
        cluster_name: "lego gift guides",
        search_intent: "commercial",
        demand_score: 78,
        source: "seed",
        confidence: 0.88
      },
      {
        topic: "best retired lego sets to buy",
        cluster_name: "retired lego sets",
        search_intent: "commercial",
        demand_score: 69,
        source: "seed",
        confidence: 0.82
      }
    ],
    metadata: {
      siteUrl: "https://mylegoguide.com"
    }
  });
}
