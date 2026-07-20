from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel

Origem = Literal["banco", "erp"]
TipoPendencia = Literal[
    "duplicidade", "orfao_banco", "orfao_erp", "divergencia_valor"
]


class Lancamento(BaseModel):
    id: str
    origem: Origem
    data: date
    valor: Decimal
    descricao: str
    referencia: Optional[str] = None


class Pendencia(BaseModel):
    tipo: TipoPendencia
    lancamentos: list[Lancamento]
    detalhe: str
    explicacao: Optional[str] = None


class MatchSemantico(BaseModel):
    banco: Lancamento
    erp: Lancamento
    similaridade: float


class ResultadoConciliacao(BaseModel):
    matches_exatos: list[tuple[Lancamento, Lancamento]]
    matches_janela: list[tuple[Lancamento, Lancamento]]
    matches_semanticos: list[MatchSemantico] = []
    pendencias: list[Pendencia]
    total_banco: int
    total_erp: int

    @property
    def total_conciliado(self) -> int:
        return (
            len(self.matches_exatos)
            + len(self.matches_janela)
            + len(self.matches_semanticos)
        )

    @property
    def pct_conciliado_automatico(self) -> float:
        total = max(self.total_banco, self.total_erp)
        if total == 0:
            return 0.0
        return round(100 * self.total_conciliado / total, 2)
