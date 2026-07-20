import io
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from conciliacao.explicacao import gerar_explicacoes
from conciliacao.persistencia import carregar_historico, salvar_execucao
from conciliacao.pipeline import rodar
from conciliacao.relatorio import (
    df_matches_exatos,
    df_matches_janela,
    df_matches_semanticos,
    df_pendencias,
    df_resumo,
    gerar_relatorio_excel,
)

st.set_page_config(page_title="Conciliação Financeira", page_icon="🧾")
st.title("Agente de Conciliação Financeira")
st.write(
    "Faça upload do extrato bancário e do razão/ERP para conciliar automaticamente "
    "por valor, data e similaridade semântica de descrição."
)

col1, col2 = st.columns(2)
with col1:
    arquivo_banco = st.file_uploader("Extrato bancário", type=["csv", "xlsx"])
with col2:
    arquivo_erp = st.file_uploader("Extrato ERP", type=["csv", "xlsx"])

if not os.environ.get("GROQ_API_KEY"):
    st.info(
        "GROQ_API_KEY não configurada — as pendências vão sair sem explicação em "
        "linguagem natural (só com o detalhe técnico)."
    )

if st.button("Rodar conciliação", disabled=not (arquivo_banco and arquivo_erp)):
    with st.spinner("Conciliando..."):
        with tempfile.TemporaryDirectory() as tmpdir:
            path_banco = Path(tmpdir) / arquivo_banco.name
            path_erp = Path(tmpdir) / arquivo_erp.name
            path_banco.write_bytes(arquivo_banco.getvalue())
            path_erp.write_bytes(arquivo_erp.getvalue())

            inicio = time.perf_counter()
            resultado = rodar(path_banco, path_erp)
            resultado.pendencias = gerar_explicacoes(resultado.pendencias)
            tempo_execucao_segundos = time.perf_counter() - inicio

    salvar_execucao(resultado, tempo_execucao_segundos)

    st.success("Conciliação concluída!")

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("% conciliação automática", f"{resultado.pct_conciliado_automatico}%")
    col_b.metric("Pendências", len(resultado.pendencias))
    col_c.metric("Tempo de execução", f"{tempo_execucao_segundos:.2f}s")

    st.subheader("Resumo")
    st.dataframe(df_resumo(resultado, tempo_execucao_segundos), hide_index=True)

    st.subheader(f"Matches exatos ({len(resultado.matches_exatos)})")
    st.dataframe(df_matches_exatos(resultado), hide_index=True)

    st.subheader(f"Matches por janela de data ({len(resultado.matches_janela)})")
    st.dataframe(df_matches_janela(resultado), hide_index=True)

    st.subheader(f"Matches semânticos ({len(resultado.matches_semanticos)})")
    st.dataframe(df_matches_semanticos(resultado), hide_index=True)

    st.subheader(f"Pendências ({len(resultado.pendencias)})")
    st.dataframe(df_pendencias(resultado), hide_index=True)

    buffer = io.BytesIO()
    gerar_relatorio_excel(resultado, tempo_execucao_segundos, buffer)
    buffer.seek(0)
    st.download_button(
        "Baixar relatório completo (Excel)",
        data=buffer,
        file_name="relatorio_conciliacao.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.subheader("Histórico de execuções")
historico = carregar_historico()
if historico:
    st.dataframe(historico, hide_index=True)
else:
    st.caption(
        "Nenhum histórico disponível — configure SUPABASE_URL e "
        "SUPABASE_SERVICE_ROLE_KEY no .env para registrar e ver execuções passadas."
    )
