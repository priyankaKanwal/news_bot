"""LangChain-compatible embeddings backed by the Jina AI REST API.

jina-embeddings-v3 is asymmetric: documents and queries must be embedded with
different `task` values, so this class sets the task per method.
"""

import time
from math import sqrt

import requests
from langchain_core.embeddings import Embeddings

JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"

# HTTP statuses worth retrying; anything else is a real error.
_RETRY_STATUSES = {429, 500, 502, 503, 504}


def _normalize(vector: list[float]) -> list[float]:
    norm = sqrt(sum(value * value for value in vector))
    if not norm:
        return vector
    return [value / norm for value in vector]


class JinaEmbeddings(Embeddings):
    """Embed text with Jina's hosted API (documents and queries use different tasks)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        batch_size: int = 32,
        timeout: int = 60,
        max_retries: int = 5,
    ):
        if not api_key:
            raise ValueError(
                "JINA_API_KEY is not set. Add it to your .env file."
            )
        self.model = model
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _post(self, texts: list[str], task: str) -> list[list[float]]:
        payload = {
            "model": self.model,
            "task": task,
            "dimensions": self.dimensions,
            # Cut inputs at the model's 8192-token limit instead of failing.
            "truncate": True,
            "input": texts,
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.post(
                    JINA_EMBEDDINGS_URL,
                    json=payload,
                    timeout=self.timeout,
                )
            except (requests.ConnectionError, requests.Timeout):
                if attempt == self.max_retries:
                    raise
            else:
                if response.status_code not in _RETRY_STATUSES:
                    response.raise_for_status()
                    data = sorted(
                        response.json()["data"],
                        key=lambda item: item["index"],
                    )
                    return [item["embedding"] for item in data]

                if attempt == self.max_retries:
                    response.raise_for_status()

            # Exponential backoff: 1s, 2s, 4s, 8s, 16s.
            time.sleep(2 ** attempt)

        raise RuntimeError("unreachable")

    def _embed(self, texts: list[str], task: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            vectors.extend(_normalize(v) for v in self._post(batch, task))
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts, "retrieval.passage")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "retrieval.query")[0]
