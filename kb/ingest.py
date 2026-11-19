import asyncio
import os
import re
from pathlib import Path


async def ingest(docs_dir: Path = None):
    docs_dir = docs_dir or Path(__file__).with_name("docs")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required to ingest policy chunks")
    try:
        import asyncpg
    except ImportError as exc:
        raise RuntimeError("Install asyncpg and pgvector support") from exc
    from backend.app.llm.client import GeminiClient

    llm = GeminiClient()
    chunks = []
    for path in sorted(docs_dir.glob("*.md")):
        department = path.stem.split("-")[0]
        for index, section in enumerate(re.split(r"\n(?=## )", path.read_text(encoding="utf-8")), start=1):
            if not section.strip():
                continue
            title_match = re.match(r"##\s+(.+)", section)
            sla_match = re.search(r"SLA:\s*(\d+)\s*hours?", section, re.I)
            escalation_match = re.search(r"Escalation:\s*(.+)", section, re.I)
            chunks.append({
                "chunk_id": f"{path.stem}-{index}",
                "doc_title": title_match.group(1).strip() if title_match else path.stem,
                "text": section,
                "department_id": department,
                "sla_hours": int(sla_match.group(1)) if sla_match else None,
                "escalation_rule": escalation_match.group(1).strip() if escalation_match else None,
            })

    embeddings = await llm.embed([chunk["text"] for chunk in chunks])
    conn = await asyncpg.connect(database_url)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS policy_chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_title TEXT,
            text TEXT,
            department_id TEXT,
            sla_hours INTEGER,
            escalation_rule TEXT,
            embedding vector(768)
        )
    """)
    for chunk, embedding in zip(chunks, embeddings):
        await conn.execute("""
            INSERT INTO policy_chunks
                (chunk_id, doc_title, text, department_id, sla_hours, escalation_rule, embedding)
            VALUES ($1,$2,$3,$4,$5,$6,$7::vector)
            ON CONFLICT (chunk_id) DO UPDATE SET
                doc_title=EXCLUDED.doc_title, text=EXCLUDED.text,
                department_id=EXCLUDED.department_id, sla_hours=EXCLUDED.sla_hours,
                escalation_rule=EXCLUDED.escalation_rule, embedding=EXCLUDED.embedding
        """, chunk["chunk_id"], chunk["doc_title"], chunk["text"], chunk["department_id"],
             chunk["sla_hours"], chunk["escalation_rule"], str(embedding))
    await conn.close()
    return len(chunks)


if __name__ == "__main__":
    print(asyncio.run(ingest()))
