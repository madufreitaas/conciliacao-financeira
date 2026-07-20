from datetime import date
from decimal import Decimal

from conciliacao.matching import classificar_pendencias, match_exato, match_janela
from conciliacao.models import Lancamento


def L(id, origem, data, valor, descricao="X", referencia=None):
    return Lancamento(
        id=id,
        origem=origem,
        data=date.fromisoformat(data),
        valor=Decimal(str(valor)),
        descricao=descricao,
        referencia=referencia,
    )


def test_match_exato_por_valor_e_data():
    banco = [L("B1", "banco", "2026-06-01", "100.00")]
    erp = [L("E1", "erp", "2026-06-01", "100.00")]

    matches, banco_restante, erp_restante = match_exato(banco, erp)

    assert len(matches) == 1
    assert matches[0] == (banco[0], erp[0])
    assert banco_restante == []
    assert erp_restante == []


def test_match_exato_nao_casa_valores_diferentes():
    banco = [L("B1", "banco", "2026-06-01", "100.00")]
    erp = [L("E1", "erp", "2026-06-01", "99.00")]

    matches, banco_restante, erp_restante = match_exato(banco, erp)

    assert matches == []
    assert banco_restante == banco
    assert erp_restante == erp


def test_match_janela_casa_mesmo_valor_com_defasagem_de_data():
    banco = [L("B1", "banco", "2026-06-01", "100.00")]
    erp = [L("E1", "erp", "2026-06-03", "100.00")]

    matches, banco_restante, erp_restante = match_janela(banco, erp, dias=3)

    assert len(matches) == 1
    assert banco_restante == []
    assert erp_restante == []


def test_match_janela_respeita_limite_de_dias():
    banco = [L("B1", "banco", "2026-06-01", "100.00")]
    erp = [L("E1", "erp", "2026-06-10", "100.00")]

    matches, banco_restante, erp_restante = match_janela(banco, erp, dias=3)

    assert matches == []
    assert banco_restante == banco
    assert erp_restante == erp


def test_classificar_pendencias_orfao_banco_e_erp():
    banco_restante = [L("B1", "banco", "2026-06-01", "100.00")]
    erp_restante = [L("E1", "erp", "2026-06-20", "999.00")]

    pendencias = classificar_pendencias(banco_restante, erp_restante)

    tipos = {p.tipo for p in pendencias}
    assert "orfao_banco" in tipos
    assert "orfao_erp" in tipos


def test_classificar_pendencias_duplicidade():
    banco_restante = [
        L("B1", "banco", "2026-06-01", "100.00"),
        L("B2", "banco", "2026-06-01", "100.00"),
    ]
    erp_restante = []

    pendencias = classificar_pendencias(banco_restante, erp_restante)

    assert len(pendencias) == 2
    assert all(p.tipo == "duplicidade" for p in pendencias)


def test_classificar_pendencias_divergencia_valor():
    banco_restante = [L("B1", "banco", "2026-06-01", "100.00")]
    erp_restante = [L("E1", "erp", "2026-06-01", "105.00")]

    pendencias = classificar_pendencias(banco_restante, erp_restante)

    assert len(pendencias) == 1
    assert pendencias[0].tipo == "divergencia_valor"
