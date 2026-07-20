from __future__ import annotations

from decimal import Decimal
from typing import Callable

import numpy as np

from conciliacao.embeddings import embutir_textos
from conciliacao.models import Lancamento, MatchSemantico


def match_semantico(
    banco_restante: list[Lancamento],
    erp_restante: list[Lancamento],
    embutir: Callable[[list[str]], np.ndarray] = embutir_textos,
    limite_similaridade: float = 0.55,
    tolerancia_valor: Decimal = Decimal("50.00"),
    dias: int = 5,
) -> tuple[list[MatchSemantico], list[Lancamento], list[Lancamento]]:
    candidatos: list[tuple[Lancamento, Lancamento]] = []
    for lb in banco_restante:
        for le in erp_restante:
            diff_valor = abs(lb.valor - le.valor)
            diff_dias = abs((lb.data - le.data).days)
            if diff_valor <= tolerancia_valor and diff_dias <= dias:
                candidatos.append((lb, le))

    if not candidatos:
        return [], list(banco_restante), list(erp_restante)

    descricoes_banco = [c[0].descricao for c in candidatos]
    descricoes_erp = [c[1].descricao for c in candidatos]
    embeddings_banco = embutir(descricoes_banco)
    embeddings_erp = embutir(descricoes_erp)

    similaridades = np.sum(np.asarray(embeddings_banco) * np.asarray(embeddings_erp), axis=1)

    pares_ordenados = sorted(
        zip(candidatos, similaridades), key=lambda item: item[1], reverse=True
    )

    banco_livre = list(banco_restante)
    erp_livre = list(erp_restante)
    matches: list[MatchSemantico] = []

    for (lb, le), similaridade in pares_ordenados:
        if similaridade < limite_similaridade:
            break
        if lb not in banco_livre or le not in erp_livre:
            continue
        matches.append(MatchSemantico(banco=lb, erp=le, similaridade=float(similaridade)))
        banco_livre.remove(lb)
        erp_livre.remove(le)

    return matches, banco_livre, erp_livre
