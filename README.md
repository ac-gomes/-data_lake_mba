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
materializar Silver e Gold em Parquet/Snappy.

Transient não tem política Lifecycle configurada; configure retenção antes de
esperar limpeza automática.

### Responsabilidades das camadas

| Camada | Conteúdo e formato | Responsabilidade |
|---|---|---|
| Transient | JSON/CSV de entrada por entidade, `ingest_date` e `batch_id` | Staging do lote antes da promoção. Os objetos permanecem no bucket. |
| Bronze | Cópia dos arquivos de entrada, sem transformação | Fonte preservada para consulta e processamento no Athena. |
| Silver | Parquet com compressão Snappy, tabela `silver_fato_vendas` | Pedidos válidos enriquecidos com cliente/produto e `valor_total`. |
| Gold | Parquet com compressão Snappy, tabela `gold_analises_vendas` | Métricas agregadas por UF e categoria para consumo analítico. |

Quarentena e resultados Athena são áreas operacionais, não camadas medalhão.
Quarentena guarda JSON com os registros rejeitados e seus motivos. `athena-results/`
guarda os arquivos de resultado das consultas SQL.

Os objetos Bronze mantêm os formatos de entrada: `clientes.json` em JSON Lines
e `pedidos.csv`/`produtos.csv` em CSV com cabeçalho. Silver e Gold usam Parquet
com compressão Snappy. Silver contém chaves e atributos de cliente/produto,
`quantidade`, `preco`, `valor_total` e `data_pedido`. Gold contém uma linha por
UF/categoria com pedidos distintos, itens, faturamento, ticket médio e data de
referência.

As partições `ingest_date` e `batch_id` identificam a mesma execução em Bronze,
Silver, Gold e Quarentena. Isso permite reprocessar e auditar um lote sem
misturá-lo com outros.

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

Para iniciar a configuração, copie o template e preencha os valores locais:

```bash
cp .env.example .env
```

## Iniciar o ambiente

Execute as 11 etapas do pipeline:

```bash
python mba_setup_ambiente.py \
  --bucket datalake-bucket-turma-c-trabalho-mba \
  --quantidade 100
```

O setup executa as etapas abaixo em sequência e para na primeira falha:

1. Verifica o bucket e cria somente prefixes ausentes.
2. Prepara a Bronze para incorporar entradas disponíveis antes da carga atual.
3. Gera clientes, produtos, pedidos e o arquivo auxiliar `orders.csv` em
  `datalake/Dados/`.
4. Envia clientes, produtos e pedidos para Transient, confere o tamanho e
  promove cópias para Bronze.
5. Configura o `OutputLocation` do workgroup `primary` sem alterar um valor que
  já esteja correto.
6. Cria o database e as tabelas Bronze no Glue Data Catalog; atualiza os
  metadados das tabelas Silver/Gold.
7. Verifica bucket, prefixes, objetos Bronze, catálogo e workgroup Athena.
8. Aplica Data Quality e publica rejeitados na Quarentena.
9. Usa Athena para materializar Silver em Parquet/Snappy e registrar a partição.
10. Usa Athena para materializar Gold em Parquet/Snappy e registrar a partição.
11. Executa a auditoria Athena para o `ingest_date` e `batch_id` do lote.

Ao final, os artefatos esperados são:

- arquivos de clientes, pedidos e produtos gerados para o lote;
- objetos de entrada em Transient e suas cópias verificadas em Bronze;
- tabelas Bronze no Glue Data Catalog;
- staging CSV de Silver e Quarentena no workspace;
- rejeitados em JSON no S3, quando houver registros inválidos;
- Silver e Gold em Parquet/Snappy, com partições do lote;
- resultados, metadados e manifests das consultas em `athena-results/`.

O arquivo `orders.csv` não é enviado para S3. A validação de IDs, a checagem de
quantidade positiva e a contagem de rejeições são feitas pelo módulo Python de
Data Quality; a materialização SQL da Silver repete os filtros e joins lendo
as tabelas Bronze no Athena.

O setup não remove objetos em reexecuções. Ele recria os metadados Athena de
Silver e Gold para o schema particionado atual e mantém o `OutputLocation`
quando já está correto.

## Testes e validação

### Suíte automatizada local

Execute antes de alterar código:

```bash
python -m pytest -q proximas_etapas/scripts
```

A suíte contém 24 casos e cobre regras de qualidade, transformação de registros,
gravação de Silver/Quarentena, builders SQL, partições, promoção Transient→Bronze,
validação de IDs gerados, importação idempotente e a ordem Silver→Gold→auditoria.
Os testes que simulam S3 usam clientes fake; pytest não escreve no AWS. São
testes unitários e de integração local entre geradores, DQ, ingestão e
orquestração, não uma execução AWS.

### Validações remotas AWS

Esses comandos acessam os serviços AWS. O teste remoto é somente leitura; os
validadores executam queries Athena e gravam resultados em `athena-results/`.

Validar infraestrutura S3, catálogo e workgroup:

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

O setup informa o `batch_id` criado ao iniciar a auditoria. Para repetir a
auditoria manualmente, use os valores exibidos pelo pipeline.

A auditoria Athena executa seis verificações: tabelas no catálogo, contagens por
camada para o lote, reconciliação de faturamento Bronze/Silver/Gold, localização
dos arquivos Parquet da Silver e Gold (`$path`) e agregação Gold por UF. A
validação independente também checa a fórmula `valor_total = quantidade * preco`
e a igualdade entre os totais Silver e Gold.

## Data Quality, Athena e logs

O DQ verifica três regras por pedido:

- `quantidade > 0`;
- `cliente_id` existe na base de clientes;
- `produto_id` existe na base de produtos.

Um registro que falha em qualquer regra não entra na Silver. O registro e todos
os motivos são gravados em
`quarantine/pedidos_rejeitados/ingest_date=<data>/batch_id=<id>/rejeitados.json`.
O processamento exibe as contagens de válidos/rejeitados e interrompe se a
publicação S3 da Quarentena falhar.

As regras DQ são executadas pelo módulo Python sobre os arquivos do lote. Athena
é usado para ler as tabelas Bronze, materializar Silver e Gold, validar os
resultados e auditar as partições. O `valor_total` da Silver é calculado como
`quantidade * preco`; Gold agrega pedidos, itens, faturamento e ticket médio por
UF/categoria.

O prefixo `logs/` é criado como estrutura, mas o código atual não grava nele logs
estruturados de DQ. Os resultados das queries Athena ficam em
`s3://datalake-bucket-turma-c-trabalho-mba/athena-results/`; os IDs das queries,
contagens e status das etapas são impressos no terminal. A Quarentena é o
registro persistente dos detalhes de cada rejeição. Portanto, hoje não existe
uma tabela nem um arquivo Athena de log de Data Quality; Athena consulta os
dados e persiste os resultados das próprias queries.

## Módulos do pipeline

| Módulo | Funções principais | Responsabilidade |
|---|---|---|
| `datalake/Dados/mba_gerar_bases.py` | `gerar_dados`, `main` | Executa os geradores locais. |
| `datalake/Dados/mba_base_clientes.py` | `gerar_clientes` | Gera clientes com IDs a partir de 505. |
| `datalake/Dados/mba_base_produtos.py` | `gerar_produtos` | Gera produtos com IDs a partir de 9001. |
| `datalake/Dados/mba_base_pedidos.py` | `gerar_pedidos` | Gera pedidos e garante ao menos um par de IDs válido. |
| `datalake/Dados/mba_base_order.py` | `gerar_data`, `gerar_orders` | Gera `orders.csv`, auxiliar e fora da ingestão. |
| `datalake/mba_create_bucket_env.py` | `client`, `ensure_environment` | Cria o bucket, se ausente, e apenas prefixes ausentes. |
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
