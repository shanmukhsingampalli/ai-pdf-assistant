from typing import List

from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(
    chunk_size=1000,
    chunk_overlap=200
)


def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)

    texts = [d.text for d in docs if getattr(d, "text", None)]

    chunks = []

    for t in texts:
        chunks.extend(splitter.split_text(t))

    return chunks


def embed_texts(texts: List[str], model):
    embeddings = []

    for i, text in enumerate(texts):
        print(f"Embedding chunk {i+1}/{len(texts)}")

        embedding = model.encode(text).tolist()

        embeddings.append(embedding)

    print("DONE embedding")

    return embeddings