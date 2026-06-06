import os
import uuid
from qdrant_client.models import Filter, FieldCondition, MatchValue
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)


class QdrantStorage:

    def __init__(
        self,
        collection_name="docs",
        vector_size=384,
    ):

        self.collection_name = collection_name

        self.client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        #self.client.delete_collection("docs")
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
                   distance=Distance.COSINE,
                ),
            )

# Always ensure source index exists
        try:
          self.client.create_payload_index(
        collection_name=collection_name,
        field_name="source",
        field_schema="keyword"
        )
        except Exception:
            pass

    def upsert(
        self,
        texts,
        embeddings,
        metadata=None,
    ):

        points = []

        for text, embedding in zip(
            texts,
            embeddings,
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
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    def search(
      self,
      query_embedding,
      limit=5,
      source=None,
    ):


        query_filter = None

        if source and source != "All PDFs":
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="source",
                            match=MatchValue(value=source)
                        )
                    ]
        )

        results = self.client.query_points(
                      collection_name=self.collection_name,
                      query=query_embedding,
                      limit=limit,
                     query_filter=query_filter,  
        )

        return [
            {
            "score": point.score,
             "text": point.payload["text"],
             "source": point.payload.get("source", "Unknown PDF")
            }
            for point in results.points
        ]