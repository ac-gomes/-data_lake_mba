# Data Lake MBA

Pipeline de dados AWS com arquitetura **Transient → Bronze → Silver → Gold**.
O bucket ativo é `datalake-bucket-turma-c-trabalho-mba`, na região `us-east-1`.

Última execução validada em 2026-11-01: 11 etapas, validação remota 6/6,
auditoria Athena 6/6 e 24 testes locais aprovados. O lote validado teve 100
pedidos Bronze, 2 válidos em Silver, 2 agregações Gold e 98 rejeitados em
Quarentena. Silver e Gold reconciliaram em `50.121,36`.

## Arquitetura S3

```text
s3://datalake-bucket-turma-c-trabalho-mba/
├── transient/<entidade>/ingest_date=<data>/batch_id=<id>/
├── bronze/<entidade>/ingest_date=<data>/batch_id=<id>/
├── silver/fato_vendas/ingest_date=<data>/batch_id=<id>/
├── gold/analises_vendas/ingest_date=<data>/batch_id=<id>/
├── quarantine/pedidos_rejeitados/ingest_date=<data>/batch_id=<id>/
└── athena-results/
```

Cada execução recebe um `ingest_date` e um `batch_id`. A ingestão grava em
Transient e promove uma cópia verificada para Bronze. Athena lê Bronze para
materializar Silver e Gold em Parquet/Snappy. `raw/` e `processed/` não fazem
parte do bucket ativo. O bucket anterior foi removido após validar o novo.

Transient não tem política Lifecycle configurada; configure retenção antes de
esperar limpeza automática.

## Pré-requisitos

- Python 3.8 ou superior.
- Credenciais AWS ativas com permissões para S3, Athena e Glue Data Catalog.
- Token de sessão atualizado, caso use credenciais temporárias.

Crie o ambiente e instale as dependências:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Configure `.env` na raiz do projeto. Não coloque credenciais reais em código,
tasks, documentação ou Git:

```env
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>
AWS_SESSION_TOKEN=<session-token>
AWS_REGION=us-east-1
```

Use `.env.example` como modelo e mantenha os valores reais somente em `.env`,
que é ignorado pelo Git.

## Iniciar o ambiente

Execute as 11 etapas do pipeline:

```bash
python mba_setup_ambiente.py \
  --bucket datalake-bucket-turma-c-trabalho-mba \
  --quantidade 100
```

As etapas criam prefixes, copiam dados Raw legados caso existam, geram as
bases locais, carregam um lote em Transient/Bronze, configuram o catálogo,
validam o ambiente, aplicam DQ, materializam Silver e Gold e auditam o lote.
O bucket anterior já foi removido; o bucket acima é o destino ativo.

O setup não remove objetos em reexecuções. Ele recria os metadados Athena de
Silver e Gold para o schema particionado atual e mantém o `OutputLocation`
quando já está correto.

## Testes e validação

Rode a suíte local antes de mudanças:

```bash
python -m pytest -q proximas_etapas/scripts
```

Validar somente os recursos remotos de S3/Athena:

```bash
python mba_teste_remoto_ambiente.py datalake-bucket-turma-c-trabalho-mba
```

Validar regras, contagem e equivalência Silver/Gold no Athena:

```bash
python mba_validar_camadas_athena.py datalake-bucket-turma-c-trabalho-mba
```

Auditar apenas um lote específico:

```bash
python mba_auditar_athena.py \
  datalake-bucket-turma-c-trabalho-mba \
  YYYY-MM-DD BATCH_ID
```

Executar consultas analíticas opcionais:

```bash
python mba_analise_athena.py datalake-bucket-turma-c-trabalho-mba
```

## Módulos do pipeline

| Módulo | Funções principais | Responsabilidade |
|---|---|---|
| `datalake/Dados/mba_gerar_bases.py` | `gerar_dados`, `main` | Executa os geradores locais. |
| `datalake/Dados/mba_base_clientes.py` | `gerar_clientes` | Gera clientes com IDs a partir de 505. |
| `datalake/Dados/mba_base_produtos.py` | `gerar_produtos` | Gera produtos com IDs a partir de 9001. |
| `datalake/Dados/mba_base_pedidos.py` | `gerar_pedidos` | Gera pedidos e garante ao menos um par de IDs válido. |
| `datalake/Dados/mba_base_order.py` | `gerar_data`, `gerar_orders` | Gera `orders.csv`, auxiliar e fora da ingestão. |
| `datalake/mba_create_bucket_env.py` | `client`, `ensure_environment` | Cria o bucket, se ausente, e apenas prefixes ausentes. |
| `datalake/mba_migrar_raw_para_bronze.py` | `client`, `migrate_raw_to_bronze` | Copia dados Raw legados para Bronze sem apagar a origem. |
| `datalake/mba_ingestao_env.py` | `client`, `ingest_data_files` | Grava Transient, verifica tamanho e promove cópia para Bronze. |
| `datalake/mba_configurar_output_athena.py` | `client`, `ensure_output` | Configura o output do workgroup `primary` se necessário. |
| `datalake/mba_setup_athena.py` | `client`, `execute`, `setup_catalog` | Cria tabelas Bronze e atualiza partições/metadados. |
| `mba_setup_ambiente.py` | `etapa`, `setup`, `main` | Orquestra as 11 etapas e interrompe na primeira falha. |
| `mba_teste_remoto_ambiente.py` | `clients`, `run_check`, `test_environment` | Confere S3, catálogo e workgroup; somente leitura. |
| `mba_processar_silver.py` | `avaliar_registro`, `processar_pedidos`, `publicar_quarentena_s3` | Aplica DQ local, grava staging e publica rejeitados. |
| `mba_materializar_silver_athena.py` | `build_silver_sql`, `execute_sql`, `main` | Lê Bronze, grava Silver Parquet/Snappy e registra partição. |
| `mba_processar_gold.py` | `build_gold_sql`, `execute_sql`, `main` | Agrega Silver por UF/categoria e grava Gold. |
| `mba_auditar_athena.py` | `executar_query`, `obter_resultados`, `main` | Audita tabelas, contagens e totais do lote. |
| `mba_validar_camadas_athena.py` | `executar_query`, `obter_resultados`, `main` | Valida cálculo Silver e equivalência Silver/Gold. |
| `mba_analise_athena.py` | `executar_query`, `obter_resultados`, `main` | Executa consultas analíticas opcionais em Bronze. |

## Segurança antes de publicar

- `AWS_CREDENTIAL` foi removido do tracking atual e ignorado; a cópia local
  permanece para o ambiente. Rotacione as credenciais antes da publicação:
  o caminho já existiu no histórico Git interno.
- O identificador antigo do bucket também aparece no histórico. O histórico
  não foi reescrito nesta preparação; não publique os commits antigos sem
  primeiro planejar a limpeza de histórico e seus efeitos no remoto.
- `datalake/` foi convertido de gitlink para uma pasta normal do repositório
  único. Nenhuma publicação ou push foi feito.

Os demais arquivos Markdown e os dados CSV locais continuam disponíveis no
workspace, mas foram retirados do conjunto rastreado/publicável.

O ambiente AWS foi migrado e testado. A publicação no GitHub não foi executada.
