from __future__ import annotations

import json
import os
import time
from typing import Callable

from conciliacao.models import Pendencia

_MODELO = "meta-llama/llama-3.3-70b-instruct"
_BASE_URL = "https://openrouter.ai/api/v1"
_MAX_TENTATIVAS_RATE_LIMIT = 6
_ESPERA_MAXIMA_SEGUNDOS = 300  # teto por tentativa, evita esperar por horas de uma vez

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


def _montar_prompt_lote(pendencias: list[Pendencia]) -> str:
    blocos = []
    for i, p in enumerate(pendencias, start=1):
        linhas_lancamentos = "\n".join(
            f"    - origem: {l.origem}, valor: R$ {l.valor}, data: {l.data.isoformat()}, "
            f"descrição: {l.descricao}"
            for l in p.lancamentos
        )
        blocos.append(
            f"Item {i} (uso interno, não cite esse número na resposta):\n"
            f"  tipo: {p.tipo}\n"
            f"  lançamentos:\n{linhas_lancamentos}\n"
            f"  observação técnica: {p.detalhe}"
        )
    lista_pendencias = "\n\n".join(blocos)

    return (
        "Você é um analista financeiro explicando pendências de conciliação bancária "
        "para um colega. Para CADA item abaixo, escreva uma explicação em português, "
        "1 a 2 frases, tom direto e profissional, como se estivesse comentando aquele "
        "lançamento isoladamente. Use SOMENTE os dados fornecidos — não invente nomes "
        "de fornecedores nem valores. NÃO mencione a palavra 'item', 'pendência N' ou "
        "qualquer numeração/rótulo interno na explicação — comece direto pelo fato "
        "(ex: 'O lançamento de R$ ... no banco...').\n\n"
        f"{lista_pendencias}\n\n"
        f"Responda em JSON, exatamente neste formato, com {len(pendencias)} itens na "
        "mesma ordem dos itens acima, sem nenhum texto fora do JSON:\n"
        '{"explicacoes": ["explicação do item 1", "explicação do item 2", "..."]}'
    )


def _extrair_explicacoes(texto: str, quantidade_esperada: int) -> list[str]:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
        texto = texto.strip()

    dados = json.loads(texto)
    explicacoes = dados["explicacoes"]
    if len(explicacoes) != quantidade_esperada:
        raise ValueError(
            f"esperava {quantidade_esperada} explicações, recebeu {len(explicacoes)}"
        )
    return explicacoes


def _cliente_openrouter():
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY não configurada.")
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=_BASE_URL)


def chamar_openrouter(prompt: str) -> str:
    from openai import RateLimitError

    cliente = _cliente_openrouter()
    for tentativa in range(1, _MAX_TENTATIVAS_RATE_LIMIT + 1):
        try:
            resposta = cliente.chat.completions.create(
                model=_MODELO,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            return resposta.choices[0].message.content.strip()
        except RateLimitError as exc:
            espera = min(
                float(exc.response.headers.get("retry-after", 15)),
                _ESPERA_MAXIMA_SEGUNDOS,
            )
            print(
                f"OpenRouter: limite de taxa atingido, aguardando {espera:.0f}s "
                f"(tentativa {tentativa}/{_MAX_TENTATIVAS_RATE_LIMIT})..."
            )
            time.sleep(espera + 1)

    raise RuntimeError(
        f"OpenRouter: limite de taxa persistente após {_MAX_TENTATIVAS_RATE_LIMIT} tentativas."
    )


def gerar_explicacao(
    pendencia: Pendencia, chamar_llm: Callable[[str], str] = chamar_openrouter
) -> str:
    return chamar_llm(_montar_prompt(pendencia))


def gerar_explicacoes(
    pendencias: list[Pendencia], chamar_llm: Callable[[str], str] = chamar_openrouter
) -> list[Pendencia]:
    global _avisou_chave_ausente

    if not pendencias:
        return pendencias

    if not os.environ.get("OPENROUTER_API_KEY"):
        if not _avisou_chave_ausente:
            print(
                "Aviso: OPENROUTER_API_KEY não configurada — pulando geração de "
                "explicações em linguagem natural (o campo 'detalhe' de cada "
                "pendência continua disponível)."
            )
            _avisou_chave_ausente = True
        return pendencias

    try:
        resposta = chamar_llm(_montar_prompt_lote(pendencias))
        explicacoes = _extrair_explicacoes(resposta, len(pendencias))
    except Exception as exc:
        print(f"Aviso: falha ao gerar explicações em lote: {exc}")
        return pendencias

    return [
        p.model_copy(update={"explicacao": explicacoes[i]}) for i, p in enumerate(pendencias)
    ]
