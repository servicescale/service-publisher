import { Site, SiteSnapshot, SiteSummary } from "@/domain/models";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

type SnapshotRow = {
  site_id: string;
  snapshot: SiteSnapshot;
  summary: SiteSummary | null;
  report_md: string | null;
};

type SiteRow = {
  id: string;
  name: string;
  niche_focus: string;
  target_audience: string;
  brand_tone: string;
  monetization_strategy: string;
  publishing_channels: string[];
  opportunity_pool: Record<string, unknown>[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export class SiteRepository {
  constructor(private readonly client = createSupabaseAdminClient()) {}

  admin() {
    return this.client;
  }

  async loadSite(siteId: string): Promise<Site> {
    const { data, error } = await this.client
      .from("engine_sites")
      .select("*")
      .eq("id", siteId)
      .single();

    if (error || !data) {
      throw new Error(error?.message ?? `Unknown site: ${siteId}`);
    }

    return mapSiteRow(data as unknown as SiteRow);
  }

  async loadSiteSnapshot(siteId: string): Promise<SiteSnapshot | null> {
    const { data, error } = await this.client
      .from("site_snapshots")
      .select("site_id,snapshot,summary,report_md")
      .eq("site_id", siteId)
      .maybeSingle();

    if (error) {
      throw new Error(error.message);
    }

    return (data as unknown as SnapshotRow | null)?.snapshot ?? null;
  }

  async saveSite(site: Site): Promise<void> {
    const row = {
      id: site.id,
      name: site.name,
      niche_focus: site.nicheFocus,
      target_audience: site.targetAudience,
      brand_tone: site.brandTone,
      monetization_strategy: site.monetizationStrategy,
      publishing_channels: site.publishingChannels,
      opportunity_pool: site.opportunityPool,
      metadata: site.metadata,
      updated_at: new Date().toISOString()
    };

    const { error } = await this.client.from("engine_sites").upsert(row);
    if (error) {
      throw new Error(error.message);
    }
  }

  async saveSiteSnapshot(siteId: string, snapshot: SiteSnapshot, summary: SiteSummary, report: string): Promise<void> {
    const { error } = await this.client.from("site_snapshots").upsert({
      site_id: siteId,
      snapshot,
      summary,
      report_md: report,
      updated_at: new Date().toISOString()
    });
    if (error) {
      throw new Error(error.message);
    }
  }

  async listPublishedPosts(limit = 12): Promise<Array<{ id: string; title: string; slug: string; meta_description: string | null; pillar: string | null; published_at: string | null }>> {
    const { data, error } = await this.client
      .from("posts")
      .select("id,title,slug,meta_description,pillar,published_at")
      .eq("status", "published")
      .order("published_at", { ascending: false })
      .limit(limit);

    if (error) {
      throw new Error(error.message);
    }

    return data ?? [];
  }

  async getPublishedPost(slug: string): Promise<{ id: string; title: string; slug: string; meta_description: string | null; pillar: string | null; content_md: string; published_at: string | null } | null> {
    const { data, error } = await this.client
      .from("posts")
      .select("id,title,slug,meta_description,pillar,content_md,published_at")
      .eq("slug", slug)
      .eq("status", "published")
      .maybeSingle();

    if (error) {
      throw new Error(error.message);
    }

    return data;
  }

  async getSiteSummary(siteId: string): Promise<SiteSummary | null> {
    const { data, error } = await this.client
      .from("site_snapshots")
      .select("summary")
      .eq("site_id", siteId)
      .maybeSingle();

    if (error) {
      throw new Error(error.message);
    }

    return ((data as unknown as { summary: SiteSummary | null } | null)?.summary) ?? null;
}
}

function mapSiteRow(row: SiteRow): Site {
  return {
    id: row.id,
    name: row.name,
    nicheFocus: row.niche_focus,
    targetAudience: row.target_audience,
    brandTone: row.brand_tone,
    monetizationStrategy: row.monetization_strategy,
    publishingChannels: row.publishing_channels ?? [],
    opportunityPool: row.opportunity_pool ?? [],
    clusterIds: [],
    atomIds: [],
    outputIds: [],
    productIds: [],
    signalIds: [],
    insightIds: [],
    loopHistory: [],
    loopRuns: 0,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    metadata: row.metadata ?? {}
  };
}
