export function normalize(value: string): string {
  return value.toLowerCase().trim().replace(/\s+/g, " ");
}

export function tokenize(value: string): string[] {
  return normalize(value)
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);
}

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "output";
}

export function jaccardSimilarity(a: string, b: string): number {
  const left = new Set(tokenize(a));
  const right = new Set(tokenize(b));
  if (left.size === 0 || right.size === 0) {
    return 0;
  }
  const intersection = [...left].filter((token) => right.has(token)).length;
  const union = new Set([...left, ...right]).size;
  return intersection / union;
}

export function overlapSignal(topic: string, existingTopics: string[]): { shouldSkip: boolean; nearestMatches: string[] } {
  const ranked = existingTopics
    .map((candidate) => ({ candidate, score: jaccardSimilarity(topic, candidate) }))
    .filter((item) => item.score >= 0.6)
    .sort((left, right) => right.score - left.score);
  return {
    shouldSkip: ranked.some((item) => item.score >= 0.8),
    nearestMatches: ranked.slice(0, 3).map((item) => item.candidate)
  };
}
