import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from dotenv import load_dotenv
import uuid
import os
import datetime
from groq import Groq

from sentence_transformers import SentenceTransformer

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import (
    RAQQueryResult,
    RAGSearchResult,
    RAGUpsertResult,
    RAGChunkAndSrc,
)

load_dotenv()

# =========================================================
# GEMINI CONFIG
# =========================================================


# =========================================================
# LOAD EMBEDDING MODEL
# =========================================================

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# =========================================================
# INNGEST CLIENT
# =========================================================

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)

# =========================================================
# INGEST PDF FUNCTION
# =========================================================

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(
        limit=2,
        period=datetime.timedelta(minutes=1),
    ),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.source_id",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context):

    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:

        print("START loading PDF")

        pdf_path = ctx.event.data["pdf_path"]

        source_id = ctx.event.data.get(
            "source_id",
            pdf_path
        )

        chunks = load_and_chunk_pdf(pdf_path)

        print(f"DONE loading PDF | chunks={len(chunks)}")

        return RAGChunkAndSrc(
            chunks=chunks,
            source_id=source_id,
        )

    def _upsert(
        chunks_and_src: RAGChunkAndSrc
    ) -> RAGUpsertResult:

        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id

        print("START embedding documents")

        vecs = embed_texts(
            chunks,
            embedding_model
        )

        print("DONE embedding documents")

        ids = [
            str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{source_id}:{i}"
                )
            )
            for i in range(len(chunks))
        ]

        payloads = [
            {
                "source": source_id,
                "text": chunks[i],
            }
            for i in range(len(chunks))
        ]

        print("START Qdrant upsert")

        store = QdrantStorage()

        store.upsert(
            ids,
            vecs,
            payloads
        )

        print("DONE Qdrant upsert")

        return RAGUpsertResult(
            ingested=len(chunks)
        )

    chunks_and_src = await ctx.step.run(
        "load-and-chunk",
        lambda: _load(ctx),
        output_type=RAGChunkAndSrc,
    )

    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(chunks_and_src),
        output_type=RAGUpsertResult,
    )

    print("DONE ingest function")

    return ingested.model_dump()

# =========================================================
# QUERY PDF FUNCTION
# =========================================================

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(
        event="rag/query_pdf_ai"
    ),
)
async def rag_query_pdf_ai(ctx: inngest.Context):

    def _search(
        question: str,
        top_k: int = 5
    ) -> RAGSearchResult:

        print("START query embedding")

        query_vec = embed_texts(
            [question],
            embedding_model
        )[0]

        print("DONE query embedding")

        print("START Qdrant search")

        store = QdrantStorage()

        results = store.search(
            query_vec,
            top_k
        )

        print("DONE Qdrant search")

        print("RAW RESULTS:", results)

        contexts = []
        sources = []

        for r in results:

            text = r.get("text", "")

            if text and len(text) > 20:
                contexts.append(text)

            sources.append("resume")

        print("CONTEXTS FOUND:", len(contexts))

        return RAGSearchResult(
            contexts=contexts,
            sources=sources
        )

    question = ctx.event.data["question"]

    top_k = int(
        ctx.event.data.get("top_k", 5)
    )

    print("START embed-and-search step")

    found = await ctx.step.run(
        "embed-and-search",
        lambda: _search(question, top_k),
        output_type=RAGSearchResult,
    )

    print("DONE embed-and-search step")

    context_block = "\n\n".join(
        f"- {c}"
        for c in found.contexts
    )

    user_content = (
        "Use the following context to answer the question.\n\n"
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        "Answer ONLY using the provided context."
    )

    print("START Groq infer")

    try:

        client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        )

        answer = completion.choices[0].message.content

        print("DONE Groq infer")

    except Exception as e:

        print("GROQ ERROR:", str(e))

        answer = f"Groq Error: {str(e)}"

    print("DONE query function")

    return {
        "answer": answer,
        "sources": found.sources,
        "num_contexts": len(found.contexts),
    }

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI()

inngest.fast_api.serve(
    app,
    inngest_client,
    [
        rag_ingest_pdf,
        rag_query_pdf_ai,
    ],
)