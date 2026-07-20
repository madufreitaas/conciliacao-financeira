from datetime import date
from decimal import Decimal

import numpy as np

from conciliacao.matching_semantico import match_semantico
from conciliacao.models import Lancamento


def L(id, origem, data, valor, descricao):
    return Lancamento(
        id=id,
        origem=origem,
        data=date.fromisoformat(data),
        valor=Decimal(str(valor)),
        descricao=descricao,
        referencia=None,
    )


def _embutir_fake(vetores: dict[str, tuple[float, float]]):
    def embutir(textos: list[str]) -> np.ndarray:
        return np.array([vetores[t] for t in textos])

    return embutir


def test_casa_par_com_alta_similaridade_dentro_da_tolerancia():
    banco = [L("B1", "banco", "2026-06-01", "1000.00", "PAG*FORNEC ABC")]
    erp = [L("E1", "erp", "2026-06-02", "1005.00", "Fornecedor ABC Ltda")]

    embutir = _embutir_fake(
        {
            "PAG*FORNEC ABC": (1.0, 0.0),
            "Fornecedor ABC Ltda": (0.99, 0.14),
        }
    )

    matches, banco_restante, erp_restante = match_semantico(
        banco, erp, embutir=embutir, limite_similaridade=0.8
    )

    assert len(matches) == 1
    assert matches[0].banco.id == "B1"
    assert matches[0].erp.id == "E1"
    assert banco_restante == []
    assert erp_restante == []


def test_nao_casa_descricoes_dissimilares_mesmo_com_valor_data_proximos():
    banco = [L("B1", "banco", "2026-06-01", "1000.00", "PAG*FORNEC ABC")]
    erp = [L("E1", "erp", "2026-06-01", "1000.00", "TAXA BANCARIA")]

    embutir = _embutir_fake(
        {
            "PAG*FORNEC ABC": (1.0, 0.0),
            "TAXA BANCARIA": (0.0, 1.0),
        }
    )

    matches, banco_restante, erp_restante = match_semantico(
        banco, erp, embutir=embutir, limite_similaridade=0.8
    )

    assert matches == []
    assert banco_restante == banco
    assert erp_restante == erp


def test_nao_considera_candidato_fora_da_tolerancia_de_valor():
    banco = [L("B1", "banco", "2026-06-01", "1000.00", "PAG*FORNEC ABC")]
    erp = [L("E1", "erp", "2026-06-01", "5000.00", "Fornecedor ABC Ltda")]

    chamadas = []

    def embutir_espiao(textos):
        chamadas.append(textos)
        return np.array([(1.0, 0.0) for _ in textos])

    matches, banco_restante, erp_restante = match_semantico(
        banco, erp, embutir=embutir_espiao, tolerancia_valor=Decimal("50.00")
    )

    assert matches == []
    assert chamadas == []  # nem chegou a chamar o embutir, filtro de valor cortou antes


def test_greedy_prioriza_maior_similaridade_quando_ha_disputa():
    banco = [
        L("B1", "banco", "2026-06-01", "1000.00", "DESC_MEDIA"),
        L("B2", "banco", "2026-06-01", "1000.00", "DESC_ALTA"),
    ]
    erp = [L("E1", "erp", "2026-06-01", "1000.00", "DESC_ALVO")]

    embutir = _embutir_fake(
        {
            "DESC_MEDIA": (0.9, np.sqrt(1 - 0.9**2)),
            "DESC_ALTA": (0.99, np.sqrt(1 - 0.99**2)),
            "DESC_ALVO": (1.0, 0.0),
        }
    )

    matches, banco_restante, erp_restante = match_semantico(
        banco, erp, embutir=embutir, limite_similaridade=0.5
    )

    assert len(matches) == 1
    assert matches[0].banco.id == "B2"  # DESC_ALTA tem maior similaridade com DESC_ALVO
    assert erp_restante == []
    assert banco_restante == banco[:1]
