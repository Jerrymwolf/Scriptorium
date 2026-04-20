"""Basic contradiction finder: positive vs negative on the same concept."""
from __future__ import annotations
from dataclasses import dataclass
from itertools import groupby
from scriptorium.paths import ReviewPaths
from scriptorium.storage.evidence import EvidenceEntry, load_evidence


@dataclass
class ContradictionPair:
    concept: str
    a: EvidenceEntry
    b: EvidenceEntry


def find_contradictions(paths: ReviewPaths) -> list[ContradictionPair]:
    rows = sorted(load_evidence(paths), key=lambda e: e.concept)
    pairs: list[ContradictionPair] = []
    for concept, group in groupby(rows, key=lambda e: e.concept):
        items = list(group)
        positives = [e for e in items if e.direction == "positive"]
        negatives = [e for e in items if e.direction == "negative"]
        for p in positives:
            for n in negatives:
                pairs.append(ContradictionPair(concept=concept, a=p, b=n))
    return pairs
