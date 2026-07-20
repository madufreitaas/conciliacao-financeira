from __future__ import annotations

import re
import warnings
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from conciliacao.models import Lancamento, Origem


def _normalizar_valor(bruto) -> Decimal:
    if isinstance(bruto, (int, float, Decimal)):
        return Decimal(str(round(float(bruto), 2)))
    texto = str(bruto).strip()
    texto = re.sub(r"[^\d,.\-]", "", texto)
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return Decimal(texto).quantize(Decimal("0.01"))


def _normalizar_data(bruto):
    texto = str(bruto).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", texto):
        return pd.to_datetime(texto).date()
    return pd.to_datetime(texto, dayfirst=True).date()


def _normalizar_descricao(bruto) -> str:
    return str(bruto).strip().upper()


def carregar_extrato(path: str | Path, origem: Origem) -> list[Lancamento]:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, dtype=str)

    df.columns = [c.strip().lower() for c in df.columns]

    lancamentos: list[Lancamento] = []
    for idx, row in df.iterrows():
        try:
            lancamento = Lancamento(
                id=str(row["id"]),
                origem=origem,
                data=_normalizar_data(row["data"]),
                valor=_normalizar_valor(row["valor"]),
                descricao=_normalizar_descricao(row["descricao"]),
                referencia=(
                    str(row["referencia"]).strip()
                    if "referencia" in df.columns and pd.notna(row["referencia"])
                    else None
                ),
            )
            lancamentos.append(lancamento)
        except (InvalidOperation, ValueError, KeyError) as exc:
            warnings.warn(f"Linha {idx} de {path.name} ignorada: {exc}")
            continue

    return lancamentos
