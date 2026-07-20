# Projeto: Agente de Conciliação Financeira Automática

## 1. Problema que resolve

Toda empresa que opera com múltiplas fontes de lançamento financeiro (extrato bancário,
ERP, planilha de contas a pagar/receber) perde horas conciliando manualmente. O problema
não é só bater valores exatos: nomes de fornecedores vêm grafados de formas diferentes,
datas têm defasagem de compensação, e um mesmo pagamento pode aparecer dividido ou
agrupado nos dois lados. Conciliação por igualdade exata de string ou valor falha nesses
casos e é isso que gera retrabalho manual.

## 2. Proposta de valor (o gancho do post/README)

Um agente que concilia dois extratos por similaridade semântica e contextual, não por
match exato: entende que "PAG*FORNEC ABC LTDA" e "Fornecedor ABC Ltda - NF 1234" são a
mesma coisa, sinaliza divergências reais (valor, duplicidade, lançamento órfão) e explica
o motivo de cada pendência em linguagem natural.

## 3. Escopo do MVP

- Upload de dois arquivos (CSV/XLSX): extrato bancário e razão/ERP.
- Normalização dos dados (datas, valores, descrições) via Python/Pandas.
- Matching em camadas:
  1. Match exato (valor + data + referência).
  2. Match por janela de data + valor (tolerância configurável, ex: +/- 3 dias).
  3. Match semântico via embeddings ou LLM para descrições divergentes.
- Classificação de cada linha não conciliada: "possível duplicidade", "lançamento
  órfão banco", "lançamento órfão ERP", "divergência de valor".
- Explicação em linguagem natural gerada por LLM para cada pendência (ex: "Este
  lançamento de R$ 1.240,00 no banco não tem correspondente no ERP; o fornecedor mais
  próximo por nome é X, mas o valor diverge em R$ 40,00").
- Relatório final exportável (Excel ou dashboard simples) com o resumo de conciliação.

## 4. Fora de escopo (v1)

- Conciliação multi-moeda.
- Integração direta com banco (Open Finance) — v1 usa upload de arquivo.
- Aprendizado contínuo (feedback loop de correções do usuário) — fica para v2.

## 5. Arquitetura sugerida

```
Frontend simples (Streamlit ou FastAPI + HTML)
        │
        ▼
FastAPI backend
        │
        ├── Módulo de ingestão (Pandas): lê CSV/XLSX, normaliza colunas
        ├── Módulo de matching determinístico (regras de valor/data)
        ├── Módulo de matching semântico (embeddings ou chamada a LLM)
        ├── Módulo de explicação (LLM gera texto por pendência)
        └── Persistência (Postgres/Supabase) do histórico de conciliações
        │
        ▼
Output: Excel/relatório + endpoint de consulta
```

## 6. Stack recomendada (reaproveitando o que você já domina)

- **Python** + Pandas para ingestão e normalização.
- **FastAPI** para orquestrar o pipeline (mesma base do oc-agent-automation).
- **Pydantic** para os modelos de dados (lançamento, pendência, relatório).
- **PostgreSQL via Supabase** para guardar histórico e permitir consulta posterior.
- **LLM (Claude via API/OpenRouter)** para o matching semântico e geração de explicações.
- Opcional: **LangGraph** se quiser modelar como agente com etapas de decisão
  (mesma arquitetura do projeto de OCs).

## 7. Dados de teste

Não use dados reais da empresa. Gerar um dataset sintético com Python (Faker) simulando:
- 200-300 lançamentos bancários.
- 200-300 lançamentos de ERP.
- Inserir de propósito: 10% de nomes divergentes, 5% de duplicidades, 5% de lançamentos
  órfãos, algumas divergências de centavos.

## 8. Métricas para mostrar no LinkedIn/GitHub

- % de conciliação automática vs manual.
- Tempo de execução do pipeline.
- Comparação "antes x depois": quantas horas um analista levaria vs segundos do agente.
- Print do relatório final com as explicações em linguagem natural (esse é o diferencial
  visual que chama atenção).

## 9. Roadmap sugerido

1. Ingestão + normalização + matching determinístico (semana 1).
2. Matching semântico + camada de explicação via LLM (semana 2).
3. Relatório final + polimento visual + README caprichado (semana 3).
4. Gravar vídeo curto (30-60s) mostrando upload → relatório, para o post.

## 10. Ideia de título para o post no LinkedIn

"Criei um agente que concilia extratos bancários e ERP sem precisar de match exato -
e ele explica cada pendência como um analista explicaria."
