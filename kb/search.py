import hashlib
import math
import os
import re
from pathlib import Path
from typing import Optional


DOCS_DIR = Path(__file__).with_name("docs")


def _load_chunks():
    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        department = path.stem.split("-")[0]
        doc_title = path.stem.replace("-", " ").title()
        text = path.read_text(encoding="utf-8")
        for index, section in enumerate(re.split(r"\n(?=## )", text), start=1):
            if not section.strip():
                continue
            title_match = re.match(r"##\s+(.+)", section)
            title = title_match.group(1).strip() if title_match else doc_title
            sla_match = re.search(r"SLA:\s*(\d+)\s*hours?", section, re.I)
            escalation_match = re.search(r"Escalation:\s*(.+)", section, re.I)
            chunk_id = f"{path.stem}-{index}"
            chunks.append({
                "chunk_id": chunk_id,
                "doc_title": title,
                "text": section,
                "department_id": department,
                "sla_hours": int(sla_match.group(1)) if sla_match else None,
                "escalation_rule": escalation_match.group(1).strip() if escalation_match else None,
                "score": 0.0,
            })
    return chunks


def _mock_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.lower().encode("utf-8")).digest()
    return [digest[i] / 255.0 for i in range(32)]


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    denom = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / denom if denom else 0.0


async def policy_search(query: str, department_id: Optional[str] = None, k: int = 4) -> list[dict]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            import asyncpg
            llm = None
            embedding = None
            from backend.app.llm.client import GeminiClient
            llm = GeminiClient()
            embedded = await llm.embed([query])
            embedding = embedded[0]
            conn = await asyncpg.connect(database_url)
            sql = """
                SELECT chunk_id, doc_title, text, department_id, sla_hours,
                       escalation_rule, 1 - (embedding <=> $1::vector) AS score
                FROM policy_chunks
                WHERE ($2::text IS NULL OR department_id = $2)
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """
            rows = await conn.fetch(sql, str(embedding), department_id, k)
            await conn.close()
            return [dict(row) for row in rows]
        except Exception:
            pass

    chunks = _load_chunks()
    if department_id:
        chunks = [c for c in chunks if c["department_id"] == department_id] or chunks
    query_vector = _mock_embedding(query)
    for chunk in chunks:
        lexical = sum(1 for token in re.findall(r"\w+", query.lower()) if token in chunk["text"].lower())
        chunk["score"] = round(min(1.0, lexical * 0.18 + _cosine(query_vector, _mock_embedding(chunk["text"])) * 0.12), 4)
    chunks.sort(key=lambda item: item["score"], reverse=True)
    return chunks[:k]
