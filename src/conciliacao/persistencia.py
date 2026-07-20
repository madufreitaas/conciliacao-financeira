from __future__ import annotations

import os

from conciliacao.models import ResultadoConciliacao

_TABELA = "execucoes_conciliacao"

_avisou_config_ausente = False


def _config_presente() -> bool:
    return bool(os.environ.get("SUPABASE_URL")) and bool(
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    )


def _cliente_supabase():
    url = os.environ.get("SUPABASE_URL")
    chave = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not chave:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY não configuradas.")
    from supabase import create_client

    return create_client(url, chave)


def salvar_execucao(resultado: ResultadoConciliacao, tempo_execucao_segundos: float) -> None:
    global _avisou_config_ausente

    if not _config_presente():
        if not _avisou_config_ausente:
            print(
                "Aviso: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configuradas — "
                "pulando o registro desta execução no histórico."
            )
            _avisou_config_ausente = True
        return

    cliente = _cliente_supabase()
    cliente.table(_TABELA).insert(
        {
            "total_banco": resultado.total_banco,
            "total_erp": resultado.total_erp,
            "matches_exatos": len(resultado.matches_exatos),
            "matches_janela": len(resultado.matches_janela),
            "matches_semanticos": len(resultado.matches_semanticos),
            "pendencias": len(resultado.pendencias),
            "pct_conciliado_automatico": resultado.pct_conciliado_automatico,
            "tempo_execucao_segundos": round(tempo_execucao_segundos, 2),
        }
    ).execute()


def carregar_historico(limite: int = 20) -> list[dict]:
    if not _config_presente():
        return []

    cliente = _cliente_supabase()
    resposta = (
        cliente.table(_TABELA)
        .select("*")
        .order("criado_em", desc=True)
        .limit(limite)
        .execute()
    )
    return resposta.data
