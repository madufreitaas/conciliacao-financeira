from __future__ import annotations

import numpy as np


def embutir_textos(textos: list[str]) -> np.ndarray:
    """Vetoriza textos por similaridade de n-gramas de caracteres (TF-IDF).

    Não é um embedding semântico de verdade — é uma aproximação leve (sem
    torch/modelo pesado) adequada para o caso de uso: descrições que divergem
    na formatação/grafia (ex: "PAG*FORNEC ABC" vs "Fornecedor ABC Ltda"), não
    em significado. Precisa ser chamada com todos os textos do lote de uma vez
    (banco + ERP juntos), já que o vocabulário é ajustado a cada chamada.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    vetorizador = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
    return vetorizador.fit_transform(textos).toarray()
