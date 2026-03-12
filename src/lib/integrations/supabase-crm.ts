import { Output, SiteSnapshot, utcNow } from "@/domain/models";

type SupabaseAdminLike = {
  from: (table: string) => {
    select: (columns: string) => {
      eq: (column: string, value: string) => {
        maybeSingle: () => Promise<{ data: { id: string; slug: string } | null; error: { message: string } | null }>;
      };
    };
    insert: (payload: Record<string, unknown>) => {
      select: (columns: string) => {
        single: () => Promise<{ data: Record<string, unknown> | null; error: { message: string } | null }>;
      };
    };
    update: (payload: Record<string, unknown>) => {
      eq: (column: string, value: string) => {
        select: (columns: string) => {
          single: () => Promise<{ data: Record<string, unknown> | null; error: { message: string } | null }>;
        };
      };
    };
  };
};

export async function publishOutputToCrm(
  admin: SupabaseAdminLike,
  snapshot: SiteSnapshot,
  output: Output,
  table = "posts"
): Promise<Output> {
  const atom = snapshot.atoms[output.atomId];
  const slug = String(output.metadata.publicSlug ?? output.title);
  const publishedAt = output.publishedAt ?? utcNow();
  const payload = {
    title: output.title,
    slug,
    meta_description: buildMetaDescription(atom.topic, output.body),
    pillar: String(atom.context.clusterName ?? "general").toLowerCase().replace(/\s+/g, "_"),
    content_md: output.body,
    status: "published",
    published_at: publishedAt
  };

  const existing = await admin.from(table).select("id,slug").eq("slug", slug).maybeSingle();
  if (existing.error) {
    throw new Error(existing.error.message);
  }

  const response = existing.data
    ? await admin.from(table).update(payload).eq("slug", slug).select("id,slug,status,published_at").single()
    : await admin.from(table).insert(payload).select("id,slug,status,published_at").single();

  if (response.error) {
    throw new Error(response.error.message);
  }

  output.status = "published";
  output.publishedAt = publishedAt;
  output.updatedAt = utcNow();
  output.metadata.crm = {
    provider: "supabase",
    table,
    record: response.data
  };
  return output;
}

function buildMetaDescription(topic: string, body: string): string {
  const text = body.replace(/\s+/g, " ").trim();
  const snippet = text ? text.slice(0, 140) : `${topic} guide`;
  return snippet.slice(0, 155);
}
