from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from conciliacao.models import Lancamento, Pendencia

MatchPar = tuple[Lancamento, Lancamento]


def match_exato(
    banco: list[Lancamento], erp: list[Lancamento]
) -> tuple[list[MatchPar], list[Lancamento], list[Lancamento]]:
    """Casa por referência+valor+data (quando há referência) ou valor+data exatos."""
    banco_restante = list(banco)
    erp_restante = list(erp)
    matches: list[MatchPar] = []

    for lb in list(banco_restante):
        candidato = None
        for le in erp_restante:
            mesma_chave = (
                lb.referencia is not None
                and le.referencia is not None
                and lb.referencia == le.referencia
                and lb.valor == le.valor
                and lb.data == le.data
            )
            mesmo_valor_data = lb.valor == le.valor and lb.data == le.data
            if mesma_chave or (lb.referencia is None and mesmo_valor_data):
                candidato = le
                break
            if lb.referencia is not None and le.referencia is not None and mesmo_valor_data:
                candidato = le
                break

        if candidato is not None:
            matches.append((lb, candidato))
            banco_restante.remove(lb)
            erp_restante.remove(candidato)

    return matches, banco_restante, erp_restante


def match_janela(
    banco: list[Lancamento],
    erp: list[Lancamento],
    dias: int = 3,
    tolerancia_valor: Decimal = Decimal("0.00"),
) -> tuple[list[MatchPar], list[Lancamento], list[Lancamento]]:
    """Casa por valor (com tolerância) dentro de uma janela de dias, quando a data diverge."""
    banco_restante = list(banco)
    erp_restante = list(erp)
    matches: list[MatchPar] = []

    for lb in list(banco_restante):
        candidato = None
        for le in erp_restante:
            diff_valor = abs(lb.valor - le.valor)
            diff_dias = abs((lb.data - le.data).days)
            if diff_valor <= tolerancia_valor and diff_dias <= dias:
                candidato = le
                break

        if candidato is not None:
            matches.append((lb, candidato))
            banco_restante.remove(lb)
            erp_restante.remove(candidato)

    return matches, banco_restante, erp_restante


def classificar_pendencias(
    banco_restante: list[Lancamento],
    erp_restante: list[Lancamento],
    janela_divergencia_dias: int = 1,
    limite_divergencia_valor: Decimal = Decimal("10.00"),
) -> list[Pendencia]:
    pendencias: list[Pendencia] = []

    banco_livre = list(banco_restante)
    erp_livre = list(erp_restante)

    # Duplicidade: dois ou mais lançamentos com mesmo valor+data no mesmo lado.
    for grupo, origem in ((banco_livre, "banco"), (erp_livre, "erp")):
        vistos: dict[tuple, list[Lancamento]] = {}
        for l in grupo:
            vistos.setdefault((l.valor, l.data), []).append(l)
        for chave, itens in vistos.items():
            if len(itens) > 1:
                for item in itens:
                    pendencias.append(
                        Pendencia(
                            tipo="duplicidade",
                            lancamentos=[item],
                            detalhe=(
                                f"Possível duplicidade em {origem}: valor {item.valor} "
                                f"na data {item.data} aparece {len(itens)} vezes."
                            ),
                        )
                    )
                for item in itens:
                    if item in grupo:
                        grupo.remove(item)

    # Divergência de valor: mesma data (+/- janela) mas valor diferente dentro do limite.
    usados_erp: set[str] = set()
    for lb in list(banco_livre):
        candidato = None
        for le in erp_livre:
            if le.id in usados_erp:
                continue
            diff_dias = abs((lb.data - le.data).days)
            diff_valor = abs(lb.valor - le.valor)
            if diff_dias <= janela_divergencia_dias and Decimal("0") < diff_valor <= limite_divergencia_valor:
                candidato = le
                break
        if candidato is not None:
            pendencias.append(
                Pendencia(
                    tipo="divergencia_valor",
                    lancamentos=[lb, candidato],
                    detalhe=(
                        f"Lançamento de R$ {lb.valor} no banco não bate exatamente com "
                        f"R$ {candidato.valor} no ERP (diferença de R$ {abs(lb.valor - candidato.valor)})."
                    ),
                )
            )
            banco_livre.remove(lb)
            erp_livre.remove(candidato)
            usados_erp.add(candidato.id)

    # O que sobrar é órfão.
    for lb in banco_livre:
        pendencias.append(
            Pendencia(
                tipo="orfao_banco",
                lancamentos=[lb],
                detalhe=f"Lançamento de R$ {lb.valor} no banco sem correspondente no ERP.",
            )
        )
    for le in erp_livre:
        pendencias.append(
            Pendencia(
                tipo="orfao_erp",
                lancamentos=[le],
                detalhe=f"Lançamento de R$ {le.valor} no ERP sem correspondente no banco.",
            )
        )

    return pendencias
