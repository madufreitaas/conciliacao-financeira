from __future__ import annotations

from pathlib import Path

from conciliacao.ingestao import carregar_extrato
from conciliacao.matching import classificar_pendencias, match_exato, match_janela
from conciliacao.matching_semantico import match_semantico
from conciliacao.models import ResultadoConciliacao


def rodar(path_banco: str | Path, path_erp: str | Path) -> ResultadoConciliacao:
    banco = carregar_extrato(path_banco, origem="banco")
    erp = carregar_extrato(path_erp, origem="erp")

    matches_exatos, banco_restante, erp_restante = match_exato(banco, erp)
    matches_janela, banco_restante, erp_restante = match_janela(banco_restante, erp_restante)
    matches_semanticos, banco_restante, erp_restante = match_semantico(banco_restante, erp_restante)
    pendencias = classificar_pendencias(banco_restante, erp_restante)

    return ResultadoConciliacao(
        matches_exatos=matches_exatos,
        matches_janela=matches_janela,
        matches_semanticos=matches_semanticos,
        pendencias=pendencias,
        total_banco=len(banco),
        total_erp=len(erp),
    )
