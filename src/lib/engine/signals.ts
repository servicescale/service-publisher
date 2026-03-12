import { Output, Signal, SiteSnapshot, newId, utcNow } from "@/domain/models";

export function collectSignals(snapshot: SiteSnapshot, outputs: Output[]): Signal[] {
  const runNumber = snapshot.site.loopRuns + 1;
  const collected: Signal[] = [];

  for (const output of outputs) {
    const atom = snapshot.atoms[output.atomId];
    const demandScore = Number(atom.context.demandScore ?? atom.priority);
    const impressions = Math.max(10, demandScore * 12 + runNumber * 7);
    const clicks = Math.max(1, Math.round(impressions * Math.min(0.35, 0.06 + demandScore / 400)));
    const revenue = Number((clicks * 0.42).toFixed(2));

    const signalSpecs = [
      { kind: "impressions", value: impressions },
      { kind: "clicks", value: clicks },
      { kind: "affiliate_revenue", value: revenue }
    ];

    for (const spec of signalSpecs) {
      const signal: Signal = {
        id: newId("signal"),
        siteId: snapshot.site.id,
        outputId: output.id,
        kind: spec.kind,
        value: spec.value,
        capturedAt: utcNow(),
        dimensions: { runNumber, channel: output.channel, source: "engine_heuristic" }
      };
      snapshot.signals[signal.id] = signal;
      snapshot.site.signalIds.push(signal.id);
      output.signalIds.push(signal.id);
      atom.signalIds.push(signal.id);
      collected.push(signal);
    }
  }

  return collected;
}
