from decimal import Decimal

import pandas as pd
import pytest

from conciliacao.ingestao import carregar_extrato


@pytest.fixture
def csv_banco(tmp_path):
    path = tmp_path / "banco.csv"
    df = pd.DataFrame(
        [
            {"id": "B1", "data": "01/06/2026", "valor": "1.234,56", "descricao": " pag*forn abc ", "referencia": "1001"},
            {"id": "B2", "data": "2026-06-02", "valor": 500.0, "descricao": "ted fulano", "referencia": ""},
        ]
    )
    df.to_csv(path, index=False)
    return path


def test_carrega_e_normaliza_valores_com_virgula(csv_banco):
    lancamentos = carregar_extrato(csv_banco, origem="banco")

    assert len(lancamentos) == 2
    assert lancamentos[0].valor == Decimal("1234.56")
    assert lancamentos[0].descricao == "PAG*FORN ABC"
    assert lancamentos[0].referencia == "1001"


def test_normaliza_datas_em_formatos_diferentes(csv_banco):
    lancamentos = carregar_extrato(csv_banco, origem="banco")

    assert lancamentos[0].data.isoformat() == "2026-06-01"
    assert lancamentos[1].data.isoformat() == "2026-06-02"


def test_linha_invalida_e_ignorada_sem_derrubar_pipeline(tmp_path):
    path = tmp_path / "banco_invalido.csv"
    df = pd.DataFrame(
        [
            {"id": "B1", "data": "01/06/2026", "valor": "abc", "descricao": "teste", "referencia": ""},
            {"id": "B2", "data": "02/06/2026", "valor": "100,00", "descricao": "ok", "referencia": ""},
        ]
    )
    df.to_csv(path, index=False)

    with pytest.warns(UserWarning):
        lancamentos = carregar_extrato(path, origem="banco")

    assert len(lancamentos) == 1
    assert lancamentos[0].id == "B2"
