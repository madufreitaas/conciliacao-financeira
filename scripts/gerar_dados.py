import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from conciliacao.gerar_dados import salvar_dataset

if __name__ == "__main__":
    destino = Path(__file__).resolve().parents[1] / "data" / "raw"
    salvar_dataset(str(destino))
