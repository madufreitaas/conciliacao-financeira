from datetime import date
from decimal import Decimal

from conciliacao.explicacao import gerar_explicacao, gerar_explicacoes
from conciliacao.models import Lancamento, Pendencia


def _pendencia(explicacao=None):
    lancamento = Lancamento(
        id="B1",
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
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    pendencias = [_pendencia()]
    resultado = gerar_explicacoes(pendencias, chamar_llm=lambda p: "não deveria ser chamado")

    assert resultado[0].explicacao is None


def test_gerar_explicacoes_com_chave_preenche_explicacao(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-fake-para-teste")

    def chamar_llm_fake(prompt: str) -> str:
        return "Texto explicativo em português."

    pendencias = [_pendencia()]
    resultado = gerar_explicacoes(pendencias, chamar_llm=chamar_llm_fake)

    assert resultado[0].explicacao == "Texto explicativo em português."
    assert pendencias[0].explicacao is None  # original não é mutado


def test_gerar_explicacoes_continua_apos_falha_em_uma_pendencia(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "chave-fake-para-teste")

    chamadas = []

    def chamar_llm_falha_na_primeira(prompt: str) -> str:
        chamadas.append(prompt)
        if len(chamadas) == 1:
            raise RuntimeError("falha simulada do Groq")
        return "Explicação da segunda pendência."

    pendencias = [_pendencia(), _pendencia()]
    resultado = gerar_explicacoes(pendencias, chamar_llm=chamar_llm_falha_na_primeira)

    assert len(chamadas) == 2  # a segunda pendência foi processada mesmo após a falha na primeira
    assert resultado[0].explicacao is None
    assert resultado[1].explicacao == "Explicação da segunda pendência."
