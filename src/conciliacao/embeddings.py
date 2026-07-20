from __future__ import annotations

import numpy as np

_modelo = None


def obter_modelo():
    global _modelo
    if _modelo is None:
        from sentence_transformers import SentenceTransformer

        _modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _modelo


def embutir_textos(textos: list[str]) -> np.ndarray:
    modelo = obter_modelo()
    return modelo.encode(textos, normalize_embeddings=True)
