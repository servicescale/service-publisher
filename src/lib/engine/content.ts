import { Atom, Output, Product, SiteSnapshot, newId, utcNow } from "@/domain/models";
import { slugify, tokenize } from "@/lib/engine/utils";

export function selectProducts(snapshot: SiteSnapshot, atom: Atom, limit = 3): Product[] {
  const searchTerms = new Set([
    ...tokenize(atom.topic),
    ...tokenize(String(atom.context.clusterName ?? ""))
  ]);

  const ranked = Object.values(snapshot.products)
    .map((product) => {
      const productTerms = new Set([
        ...tokenize(product.title),
        ...tokenize(product.description),
        ...product.tags.map((tag) => tag.toLowerCase())
      ]);
      const overlap = [...searchTerms].filter((term) => productTerms.has(term)).length;
      return { overlap, product };
    })
    .filter((item) => item.overlap > 0)
    .sort((left, right) => right.overlap - left.overlap);

  return ranked.slice(0, limit).map((item) => item.product);
}

export function generateOutputs(snapshot: SiteSnapshot, atoms: Atom[]): Output[] {
  const outputs: Output[] = [];

  for (const atom of atoms) {
    const recommendations = selectProducts(snapshot, atom).map((product) => ({
      productId: product.id,
      title: product.title,
      url: product.url,
      price: product.price,
      merchant: product.merchant
    }));

    for (const channel of snapshot.site.publishingChannels.length ? snapshot.site.publishingChannels : ["website"]) {
      const title = renderTitle(atom.topic, channel);
      const output: Output = {
        id: newId("output"),
        siteId: snapshot.site.id,
        atomId: atom.id,
        channel,
        kind: chooseOutputKind(snapshot.site.monetizationStrategy, channel),
        title,
        body: renderBody(snapshot.site.name, snapshot.site.targetAudience, snapshot.site.brandTone, atom, channel, recommendations),
        status: "draft",
        metadata: {
          siteId: snapshot.site.id,
          clusterId: atom.clusterId,
          atomId: atom.id,
          searchIntent: atom.searchIntent,
          channel,
          publicSlug: slugify(title),
          productRecommendations: recommendations
        },
        publishedAt: null,
        signalIds: [],
        createdAt: utcNow(),
        updatedAt: utcNow()
      };
      snapshot.outputs[output.id] = output;
      snapshot.site.outputIds.push(output.id);
      atom.outputIds.push(output.id);
      outputs.push(output);
    }

    atom.state = "generated";
    atom.updatedAt = utcNow();
  }

  return outputs;
}

export function chooseOutputKind(strategy: string, channel: string): string {
  if (channel === "newsletter") {
    return "email_snippet";
  }
  if (channel === "social") {
    return "social_post";
  }
  if (strategy.toLowerCase().includes("affiliate")) {
    return "buying_guide";
  }
  return "article";
}

export function renderTitle(topic: string, channel: string): string {
  const base = topic.replace(/\b\w/g, (char) => char.toUpperCase());
  if (channel === "newsletter") {
    return `${base}: Weekly Pick`;
  }
  if (channel === "social") {
    return `${base} Quick Take`;
  }
  return base;
}

export function renderBody(
  siteName: string,
  targetAudience: string,
  brandTone: string,
  atom: Atom,
  channel: string,
  recommendations: { title: string; merchant: string; price: string; url: string; productId: string }[]
): string {
  const lines = [
    `# ${renderTitle(atom.topic, channel)}`,
    "",
    `Site: ${siteName}`,
    `Audience: ${targetAudience}`,
    `Tone: ${brandTone}`,
    `Intent: ${atom.searchIntent}`,
    `Cluster: ${String(atom.context.clusterName ?? "general")}`,
    "",
    "This output was generated from an Atom inside the demand-driven publishing loop.",
    "It is designed to satisfy search intent and move readers toward relevant product choices."
  ];

  if (recommendations.length > 0) {
    lines.push("", "## Recommended Products", "");
    for (const item of recommendations) {
      lines.push(`- [${item.title}](${item.url})${item.merchant ? ` - ${item.merchant}` : ""}${item.price ? ` - ${item.price}` : ""}`);
    }
  }

  return lines.join("\n");
}
