import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv

load_dotenv()

from conciliacao.explicacao import gerar_explicacoes
from conciliacao.persistencia import salvar_execucao
from conciliacao.pipeline import rodar
from conciliacao.relatorio import gerar_relatorio_excel

if __name__ == "__main__":
    base = Path(__file__).resolve().parents[1]
    raiz = base / "data" / "raw"

    inicio = time.perf_counter()
    resultado = rodar(raiz / "extrato_banco.csv", raiz / "extrato_erp.csv")
    resultado.pendencias = gerar_explicacoes(resultado.pendencias)
    tempo_execucao_segundos = time.perf_counter() - inicio

    print(f"Total banco: {resultado.total_banco}")
    print(f"Total ERP: {resultado.total_erp}")
    print(f"Matches exatos: {len(resultado.matches_exatos)}")
    print(f"Matches por janela: {len(resultado.matches_janela)}")
    print(f"Matches semânticos: {len(resultado.matches_semanticos)}")
    print(f"Pendências: {len(resultado.pendencias)}")

    contagem_tipos = Counter(p.tipo for p in resultado.pendencias)
    for tipo, qtd in contagem_tipos.items():
        print(f"  - {tipo}: {qtd}")

    print(f"% conciliação automática: {resultado.pct_conciliado_automatico}%")
    print(f"Tempo de execução: {tempo_execucao_segundos:.2f}s")

    salvar_execucao(resultado, tempo_execucao_segundos)

    if resultado.pendencias and resultado.pendencias[0].explicacao:
        print("\nExemplo de explicação gerada:")
        print(f"  {resultado.pendencias[0].explicacao}")

    destino = base / "data" / "output" / "relatorio_conciliacao.xlsx"
    destino.parent.mkdir(parents=True, exist_ok=True)
    gerar_relatorio_excel(resultado, tempo_execucao_segundos, destino)
    print(f"\nRelatório exportado em: {destino}")
