"""Evidence-first gate: every sentence in synthesis.md must be backed by evidence.jsonl.

The sentence splitter is abbreviation-aware: it does NOT split immediately after
a small allow-list of abbreviations that end in a period (e.g., "e.g.", "i.e.",
"et al.", "cf.", "fig.", "eq.", "vs.", "approx."). This avoids the v0.1 defect
where "Several stimulants (e.g. caffeine, modafinil) improve WM." would be split
into two fragments and the second fragment marked as unsupported.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from scriptorium.paths import ReviewPaths
from scriptorium.storage.evidence import load_evidence

_CITE = re.compile(r"\[([A-Za-z0-9_.\-]+):([^\]]+)\]")

# Abbreviation allow-list: tokens ending in '.' that should NOT trigger a split.
_ABBREVS = {
    "e.g.", "i.e.", "et al.", "cf.", "fig.", "eq.", "vs.", "approx.",
    "etc.", "ca.", "no.", "vol.", "ed.", "eds.", "pp.",
}


def parse_citations(text: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _CITE.finditer(text)]


def _ends_with_abbrev(buf: str) -> bool:
    """Return True if `buf` ends with one of the allow-list abbreviations."""
    low = buf.lower().rstrip()
    for ab in _ABBREVS:
        if low.endswith(ab):
            return True
    return False


def split_sentences(text: str) -> list[str]:
    """Abbreviation-aware sentence splitter."""
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    sentences: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(body)
    while i < n:
        ch = body[i]
        buf.append(ch)
        if ch in ".!?":
            # peek: are we at sentence end? (whitespace + uppercase or '[' or end-of-text)
            j = i + 1
            while j < n and body[j] in " \t":
                j += 1
            at_end = j >= n
            next_starts_sentence = (
                at_end
                or (body[j] in "\n\r")
                or (body[j].isupper() if j < n else False)
                or (j < n and body[j] == "[")
            )
            buf_str = "".join(buf)
            # If we just ended an abbreviation, do NOT split.
            if next_starts_sentence and not _ends_with_abbrev(buf_str):
                s = buf_str.strip()
                if s:
                    sentences.append(s)
                buf = []
                i = j
                continue
        i += 1
    tail = "".join(buf).strip()
    if tail:
        sentences.append(tail)
    return [s for s in sentences if s]


@dataclass
class VerificationReport:
    ok: bool
    unsupported_sentences: list[str] = field(default_factory=list)
    missing_citations: list[tuple[str, str]] = field(default_factory=list)

    def apply_strict(self, src: str) -> str:
        out_lines: list[str] = []
        for line in src.splitlines():
            keep = True
            for s in self.unsupported_sentences:
                if s in line:
                    line = line.replace(s, "").strip()
                    if not line:
                        keep = False
            for paper, loc in self.missing_citations:
                line = line.replace(f"[{paper}:{loc}]", "")
            line = line.rstrip()
            if line or not keep:
                out_lines.append(line)
        return "\n".join(out_lines)

    def apply_lenient(self, src: str) -> str:
        out = src
        for s in self.unsupported_sentences:
            out = out.replace(s, f"{s} [UNSUPPORTED]")
        return out


def verify_synthesis(text: str, paths: ReviewPaths) -> VerificationReport:
    ledger = load_evidence(paths)
    have = {(e.paper_id, e.locator) for e in ledger}
    sentences = split_sentences(text)
    unsupported: list[str] = []
    missing: list[tuple[str, str]] = []
    for s in sentences:
        cites = parse_citations(s)
        if not cites:
            unsupported.append(s)
            continue
        for c in cites:
            if c not in have:
                missing.append(c)
    ok = not unsupported and not missing
    return VerificationReport(ok=ok, unsupported_sentences=unsupported, missing_citations=missing)
