from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid


class QdrantStorage:
    def __init__(
        self,
        collection_name="docs",
        host="localhost",
        port=6333,
        vector_size=384
    ):
        self.collection_name = collection_name

        self.client = QdrantClient(
            host=host,
            port=port
        )

        collections = self.client.get_collections().collections
        exists = any(
            c.name == collection_name
            for c in collections
        )

        if not exists:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )

    def upsert(
        self,
        texts,
        embeddings,
        metadata=None
    ):
        points = []

        for i, (text, embedding) in enumerate(
            zip(texts, embeddings)
        ):
            payload = {
                "text": text
            }

            if metadata:
                payload.update(metadata)

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    def search(
        self,
        query_embedding,
        limit=5
    ):
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=limit
        )

        return [
            {
                "score": point.score,
                "text": point.payload["text"]
            }
            for point in results.points
        ]