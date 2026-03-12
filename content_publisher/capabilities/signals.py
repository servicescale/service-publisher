from __future__ import annotations

from ..models import Output, Signal, SiteSnapshot


class SignalCapability:
    def collect(self, snapshot: SiteSnapshot, outputs: list[Output], signal_sources: list) -> list[Signal]:
        collected: list[Signal] = []
        run_number = snapshot.site.loop_runs + 1
        for output in outputs:
            for provider in signal_sources:
                for signal in provider.collect(snapshot, output, run_number):
                    snapshot.signals[signal.id] = signal
                    snapshot.site.signal_ids.append(signal.id)
                    output.signal_ids.append(signal.id)
                    snapshot.atoms[output.atom_id].signal_ids.append(signal.id)
                    collected.append(signal)
        return collected
