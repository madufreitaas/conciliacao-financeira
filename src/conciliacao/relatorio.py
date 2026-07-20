from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import BinaryIO, Union

import pandas as pd
from openpyxl.styles import Font

from conciliacao.models import ResultadoConciliacao

TEMPO_MANUAL_MINUTOS_POR_LANCAMENTO = 3  # estimativa documentada, não medição real


def df_matches_exatos(resultado: ResultadoConciliacao) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id_banco": lb.id,
                "id_erp": le.id,
                "valor": lb.valor,
                "data": lb.data,
                "descricao_banco": lb.descricao,
                "descricao_erp": le.descricao,
            }
            for lb, le in resultado.matches_exatos
        ]
    )


def df_matches_janela(resultado: ResultadoConciliacao) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id_banco": lb.id,
                "id_erp": le.id,
                "valor_banco": lb.valor,
                "valor_erp": le.valor,
                "data_banco": lb.data,
                "data_erp": le.data,
                "dias_diferenca": abs((lb.data - le.data).days),
                "descricao_banco": lb.descricao,
                "descricao_erp": le.descricao,
            }
            for lb, le in resultado.matches_janela
        ]
    )


def df_matches_semanticos(resultado: ResultadoConciliacao) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "id_banco": m.banco.id,
                "id_erp": m.erp.id,
                "valor_banco": m.banco.valor,
                "valor_erp": m.erp.valor,
                "data_banco": m.banco.data,
                "data_erp": m.erp.data,
                "descricao_banco": m.banco.descricao,
                "descricao_erp": m.erp.descricao,
                "similaridade": round(m.similaridade, 4),
            }
            for m in resultado.matches_semanticos
        ]
    )


def df_pendencias(resultado: ResultadoConciliacao) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "tipo": p.tipo,
                "ids": ", ".join(l.id for l in p.lancamentos),
                "origens": ", ".join(l.origem for l in p.lancamentos),
                "valores": ", ".join(str(l.valor) for l in p.lancamentos),
                "datas": ", ".join(l.data.isoformat() for l in p.lancamentos),
                "detalhe": p.detalhe,
                "explicacao": p.explicacao or "",
            }
            for p in resultado.pendencias
        ]
    )


def df_resumo(resultado: ResultadoConciliacao, tempo_execucao_segundos: float) -> pd.DataFrame:
    contagem_tipos = Counter(p.tipo for p in resultado.pendencias)
    total_lancamentos = resultado.total_banco + resultado.total_erp
    tempo_manual_horas = (total_lancamentos * TEMPO_MANUAL_MINUTOS_POR_LANCAMENTO) / 60

    linhas = [
        ("Total lançamentos banco", resultado.total_banco),
        ("Total lançamentos ERP", resultado.total_erp),
        ("Matches exatos", len(resultado.matches_exatos)),
        ("Matches por janela de data", len(resultado.matches_janela)),
        ("Matches semânticos", len(resultado.matches_semanticos)),
        ("Pendências", len(resultado.pendencias)),
    ]
    for tipo, qtd in contagem_tipos.items():
        linhas.append((f"  - {tipo}", qtd))
    linhas += [
        ("% conciliação automática", f"{resultado.pct_conciliado_automatico}%"),
        ("Tempo de execução do agente (segundos)", round(tempo_execucao_segundos, 2)),
        (
            f"Tempo manual estimado (~{TEMPO_MANUAL_MINUTOS_POR_LANCAMENTO} min/lançamento, estimativa)",
            f"{round(tempo_manual_horas, 1)} horas",
        ),
    ]
    return pd.DataFrame(linhas, columns=["Métrica", "Valor"])


def gerar_relatorio_excel(
    resultado: ResultadoConciliacao,
    tempo_execucao_segundos: float,
    destino: Union[str, Path, BinaryIO],
) -> None:
    abas = {
        "Resumo": df_resumo(resultado, tempo_execucao_segundos),
        "Matches Exatos": df_matches_exatos(resultado),
        "Matches Janela": df_matches_janela(resultado),
        "Matches Semanticos": df_matches_semanticos(resultado),
        "Pendencias": df_pendencias(resultado),
    }

    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        for nome_aba, df in abas.items():
            df.to_excel(writer, sheet_name=nome_aba, index=False)
            planilha = writer.sheets[nome_aba]
            for celula in planilha[1]:
                celula.font = Font(bold=True)
            planilha.freeze_panes = "A2"
            for coluna in planilha.columns:
                maior_comprimento = max(
                    (len(str(c.value)) for c in coluna if c.value is not None), default=10
                )
                planilha.column_dimensions[coluna[0].column_letter].width = min(
                    maior_comprimento + 2, 60
                )
