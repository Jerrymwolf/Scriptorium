"""Evidence ledger: append-only claim → paper + locator + quote."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from typing import Literal
from scriptorium.paths import ReviewPaths

Direction = Literal["positive", "negative", "neutral", "mixed"]


@dataclass
class EvidenceEntry:
    paper_id: str
    locator: str            # "page:4", "sec:Methods", "abstract", "L120-L135"
    claim: str
    quote: str
    direction: Direction
    concept: str            # short slug for grouping in contradiction-check


def append_evidence(paths: ReviewPaths, entry: EvidenceEntry) -> None:
    paths.evidence.parent.mkdir(parents=True, exist_ok=True)
    with paths.evidence.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def load_evidence(paths: ReviewPaths) -> list[EvidenceEntry]:
    if not paths.evidence.exists():
        return []
    out: list[EvidenceEntry] = []
    with paths.evidence.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(EvidenceEntry(**json.loads(line)))
    return out


def find_by_paper(paths: ReviewPaths, paper_id: str) -> list[EvidenceEntry]:
    return [e for e in load_evidence(paths) if e.paper_id == paper_id]
