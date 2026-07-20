import json
from datetime import date
from decimal import Decimal

from conciliacao.explicacao import gerar_explicacao, gerar_explicacoes
from conciliacao.models import Lancamento, Pendencia


def _pendencia(explicacao=None, id="B1"):
    lancamento = Lancamento(
        id=id,
        origem="banco",
        data=date.fromisoformat("2026-06-01"),
        valor=Decimal("1240.00"),
        descricao="PAG*FORNEC ABC",
        referencia=None,
    )
    return Pendencia(
        tipo="orfao_banco",
        lancamentos=[lancamento],
        detalhe="Lançamento de R$ 1240.00 no banco sem correspondente no ERP.",
        explicacao=explicacao,
    )


def test_gerar_explicacao_usa_o_chamar_llm_injetado():
    prompts_recebidos = []

    def chamar_llm_fake(prompt: str) -> str:
        prompts_recebidos.append(prompt)
        return "Explicação gerada pelo fake."

    resultado = gerar_explicacao(_pendencia(), chamar_llm=chamar_llm_fake)

    assert resultado == "Explicação gerada pelo fake."
    assert len(prompts_recebidos) == 1
    assert "1240.00" in prompts_recebidos[0]
    assert "orfao_banco" in prompts_recebidos[0]


def test_gerar_explicacoes_sem_chave_retorna_pendencias_sem_alterar(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    pendencias = [_pendencia()]
    resultado = gerar_explicacoes(pendencias, chamar_llm=lambda p: "não deveria ser chamado")

    assert resultado[0].explicacao is None


def test_gerar_explicacoes_com_chave_preenche_explicacao_em_lote(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-fake-para-teste")

    prompts_recebidos = []

    def chamar_llm_fake(prompt: str) -> str:
        prompts_recebidos.append(prompt)
        return json.dumps({"explicacoes": ["Explicação 1.", "Explicação 2."]})

    pendencias = [_pendencia(id="B1"), _pendencia(id="B2")]
    resultado = gerar_explicacoes(pendencias, chamar_llm=chamar_llm_fake)

    assert len(prompts_recebidos) == 1  # uma única chamada para todas as pendências
    assert resultado[0].explicacao == "Explicação 1."
    assert resultado[1].explicacao == "Explicação 2."
    assert pendencias[0].explicacao is None  # original não é mutado


def test_gerar_explicacoes_aceita_json_com_cercas_de_markdown(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-fake-para-teste")

    def chamar_llm_fake(prompt: str) -> str:
        corpo = json.dumps({"explicacoes": ["Explicação única."]})
        return f"```json\n{corpo}\n```"

    resultado = gerar_explicacoes([_pendencia()], chamar_llm=chamar_llm_fake)

    assert resultado[0].explicacao == "Explicação única."


def test_gerar_explicacoes_degrada_sem_quebrar_se_lote_falhar(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-fake-para-teste")

    def chamar_llm_falha(prompt: str) -> str:
        raise RuntimeError("falha simulada do Groq")

    pendencias = [_pendencia(id="B1"), _pendencia(id="B2")]
    resultado = gerar_explicacoes(pendencias, chamar_llm=chamar_llm_falha)

    assert resultado[0].explicacao is None
    assert resultado[1].explicacao is None


def test_gerar_explicacoes_degrada_se_quantidade_nao_bate(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "chave-fake-para-teste")

    def chamar_llm_fake(prompt: str) -> str:
        return json.dumps({"explicacoes": ["Só uma explicação."]})

    pendencias = [_pendencia(id="B1"), _pendencia(id="B2")]
    resultado = gerar_explicacoes(pendencias, chamar_llm=chamar_llm_fake)

    assert resultado[0].explicacao is None
    assert resultado[1].explicacao is None
