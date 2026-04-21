"""Write `scriptorium-queries.md` with the five canonical queries (§6.4).

Idempotent: if the file already exists it is left untouched and the caller
sees the sentinel warning `W_QUERIES_EXIST`.
"""
from __future__ import annotations

from pathlib import Path


_BODY = """# Scriptorium Dataview queries

These five Dataview queries ship with Scriptorium v0.3. They work against
any review directory under `reviews/` in this vault.

## Every evidence row in the vault

```dataview
TABLE claim, direction FROM "reviews" WHERE contains(file.name, "evidence")
```

## Every review that cites kennedy2017

```dataview
LIST FROM "reviews" WHERE contains(file.content, "kennedy2017")
```

## Most-cited reviews by outlink count

```dataview
TABLE length(file.outlinks) AS "references" FROM "reviews" WHERE contains(file.name, "synthesis") SORT length(file.outlinks) DESC
```

## Positive-direction evidence by concept

```dataview
TABLE concept, direction FROM "reviews" FLATTEN direction WHERE direction = "positive"
```

## Contradiction files

```dataview
LIST FROM "reviews" WHERE contains(file.name, "contradictions")
```
"""


def write_query_file(path: Path) -> str:
    """Write the canonical file. Returns `"written"` or `"W_QUERIES_EXIST"`."""
    path = Path(path)
    if path.exists():
        return "W_QUERIES_EXIST"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_BODY, encoding="utf-8")
    return "written"
