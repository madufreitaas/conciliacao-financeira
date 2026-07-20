from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from faker import Faker

fake = Faker("pt_BR")

# Descrições estilo "extrato bancário" para o mesmo fornecedor.
PREFIXOS_BANCO = ["PAG*", "TED ", "PIX ", "DOC "]


@dataclass
class LinhaGerada:
    id_verdade: int
    fornecedor: str
    valor: Decimal
    data: date
    referencia: str
    linha_banco: dict | None = field(default=None)
    linha_erp: dict | None = field(default=None)


def _descricao_banco(fornecedor: str) -> str:
    prefixo = random.choice(PREFIXOS_BANCO)
    nome_curto = fornecedor.upper().replace("LTDA", "").replace("S/A", "").strip()
    nome_curto = nome_curto[:20].strip()
    return f"{prefixo}{nome_curto} LTDA"


def _descricao_erp(fornecedor: str, referencia: str) -> str:
    return f"{fornecedor} - NF {referencia}"


def gerar_dataset(
    n_transacoes: int = 250,
    pct_descricao_divergente: float = 0.10,
    pct_duplicidade: float = 0.05,
    pct_orfao: float = 0.05,
    pct_divergencia_centavos: float = 0.05,
    seed: int | None = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    linhas_banco: list[dict] = []
    linhas_erp: list[dict] = []
    gabarito: list[dict] = []

    data_base = date(2026, 6, 1)

    for i in range(n_transacoes):
        fornecedor = fake.company()
        valor = Decimal(str(round(random.uniform(50, 5000), 2)))
        data_transacao = data_base + timedelta(days=random.randint(0, 45))
        referencia = str(random.randint(1000, 9999))

        id_banco = f"B{i:04d}"
        id_erp = f"E{i:04d}"

        roll = random.random()

        if roll < pct_orfao:
            # Lançamento existe em apenas um dos lados.
            if random.random() < 0.5:
                linhas_banco.append(
                    {
                        "id": id_banco,
                        "data": data_transacao,
                        "valor": valor,
                        "descricao": _descricao_banco(fornecedor),
                        "referencia": referencia,
                    }
                )
                gabarito.append(
                    {"id_banco": id_banco, "id_erp": None, "tipo_esperado": "orfao_banco"}
                )
            else:
                linhas_erp.append(
                    {
                        "id": id_erp,
                        "data": data_transacao,
                        "valor": valor,
                        "descricao": _descricao_erp(fornecedor, referencia),
                        "referencia": referencia,
                    }
                )
                gabarito.append(
                    {"id_banco": None, "id_erp": id_erp, "tipo_esperado": "orfao_erp"}
                )
            continue

        # Valor e data podem divergir levemente entre os dois lados.
        valor_erp = valor
        data_erp = data_transacao
        tipo_esperado = "match_exato"

        if roll < pct_orfao + pct_divergencia_centavos:
            valor_erp = valor + Decimal(str(round(random.uniform(0.01, 5.00), 2)))
            tipo_esperado = "divergencia_valor"
        elif roll < pct_orfao + pct_divergencia_centavos + pct_descricao_divergente:
            data_erp = data_transacao + timedelta(days=random.randint(1, 3))
            tipo_esperado = "match_janela"

        linhas_banco.append(
            {
                "id": id_banco,
                "data": data_transacao,
                "valor": valor,
                "descricao": _descricao_banco(fornecedor),
                "referencia": referencia,
            }
        )
        linhas_erp.append(
            {
                "id": id_erp,
                "data": data_erp,
                "valor": valor_erp,
                "descricao": _descricao_erp(fornecedor, referencia),
                "referencia": referencia,
            }
        )
        gabarito.append(
            {"id_banco": id_banco, "id_erp": id_erp, "tipo_esperado": tipo_esperado}
        )

        # Duplicidade: repete a linha em um dos lados (independente do caso acima).
        if random.random() < pct_duplicidade:
            lado = random.choice(["banco", "erp"])
            if lado == "banco":
                dup_id = f"{id_banco}D"
                linhas_banco.append(
                    {
                        "id": dup_id,
                        "data": data_transacao,
                        "valor": valor,
                        "descricao": _descricao_banco(fornecedor),
                        "referencia": referencia,
                    }
                )
                gabarito.append(
                    {"id_banco": dup_id, "id_erp": None, "tipo_esperado": "duplicidade"}
                )
            else:
                dup_id = f"{id_erp}D"
                linhas_erp.append(
                    {
                        "id": dup_id,
                        "data": data_erp,
                        "valor": valor_erp,
                        "descricao": _descricao_erp(fornecedor, referencia),
                        "referencia": referencia,
                    }
                )
                gabarito.append(
                    {"id_banco": None, "id_erp": dup_id, "tipo_esperado": "duplicidade"}
                )

    df_banco = pd.DataFrame(linhas_banco)
    df_erp = pd.DataFrame(linhas_erp)
    df_gabarito = pd.DataFrame(gabarito)
    return df_banco, df_erp, df_gabarito


def salvar_dataset(destino: str = "data/raw") -> None:
    import os

    os.makedirs(destino, exist_ok=True)
    df_banco, df_erp, df_gabarito = gerar_dataset()
    df_banco.to_csv(os.path.join(destino, "extrato_banco.csv"), index=False)
    df_erp.to_csv(os.path.join(destino, "extrato_erp.csv"), index=False)
    df_gabarito.to_csv(os.path.join(destino, "gabarito.csv"), index=False)
    print(f"Gerado: {len(df_banco)} lançamentos banco, {len(df_erp)} lançamentos ERP")
