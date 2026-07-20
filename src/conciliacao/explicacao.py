from __future__ import annotations

import os
from typing import Callable

from conciliacao.models import Pendencia

_MODELO = "llama-3.3-70b-versatile"

_avisou_chave_ausente = False


def _montar_prompt(pendencia: Pendencia) -> str:
    linhas_lancamentos = "\n".join(
        f"- origem: {l.origem}, valor: R$ {l.valor}, data: {l.data.isoformat()}, "
        f"descrição: {l.descricao}"
        for l in pendencia.lancamentos
    )
    return (
        "Você é um analista financeiro explicando uma pendência de conciliação "
        "bancária para um colega. Use SOMENTE os dados abaixo, não invente nomes de "
        "fornecedores nem valores que não estejam listados. Responda em português, "
        "em 1 a 2 frases, tom direto e profissional.\n\n"
        f"Tipo de pendência: {pendencia.tipo}\n"
        f"Lançamentos envolvidos:\n{linhas_lancamentos}\n"
        f"Observação técnica: {pendencia.detalhe}\n"
    )


def _cliente_groq():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY não configurada.")
    from groq import Groq

    return Groq(api_key=api_key)


def chamar_groq(prompt: str) -> str:
    cliente = _cliente_groq()
    resposta = cliente.chat.completions.create(
        model=_MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resposta.choices[0].message.content.strip()


def gerar_explicacao(pendencia: Pendencia, chamar_llm: Callable[[str], str] = chamar_groq) -> str:
    return chamar_llm(_montar_prompt(pendencia))


def gerar_explicacoes(
    pendencias: list[Pendencia], chamar_llm: Callable[[str], str] = chamar_groq
) -> list[Pendencia]:
    global _avisou_chave_ausente

    if not os.environ.get("GROQ_API_KEY"):
        if not _avisou_chave_ausente:
            print(
                "Aviso: GROQ_API_KEY não configurada — pulando geração de explicações "
                "em linguagem natural (o campo 'detalhe' de cada pendência continua "
                "disponível)."
            )
            _avisou_chave_ausente = True
        return pendencias

    return [
        p.model_copy(update={"explicacao": gerar_explicacao(p, chamar_llm)})
        for p in pendencias
    ]
