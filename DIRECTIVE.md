# Diretivas do Projeto (Fonte da Verdade)

Este documento concentra **diretivas que devem ser seguidas** durante a construção do projeto (código, sugestões, revisões e automações).

## Nome de classe, arquivo, objeto, atributo, etc
- **Singular**: sempre dê preferência a nomes no singular.
- **Plural**: evite usar.
- **Listas e Arrays**: use o sufixo List.
- **Exceções por convenção de tooling**: quando uma ferramenta possui convenção/padrão consolidado (ex.: `alembic/versions/`), mantenha o padrão e documente a exceção.

## Datas e Horários

- **Tipo obrigatório**: todos os campos de data/hora devem ser `timestamptz` (PostgreSQL).
- **Proibição**: não usar `date`, `time` ou `timestamp without time zone`.
- **Convenção de nomes**: todo campo de data/hora termina com `_at` (`created_at`, `start_at`, `end_at`, `published_at`).
- **Formato da API**: entrada e saída sempre em ISO 8601 completo, com offset ou `Z`.
- **Validação**: timestamps sem fuso explícito são inválidos e devem ser rejeitados pela API.
- **Armazenamento**: todos os instantes são normalizados e armazenados em UTC.
- **Timezone do Tenant**: cada Tenant deve possuir um campo `timezone` no padrão IANA (ex.: `America/Sao_Paulo`).
- **Exibição**: conversão de fuso ocorre apenas no frontend ou camada de apresentação.
- **Períodos integrais**: “dia inteiro” deve ser modelado como intervalo `[start_at, end_at)`.
- **Jobs e relatórios**: sempre usam timestamps normalizados; nunca aplicam conversão de fuso internamente.

## Python

- **Preferência**: sempre prefira **Python** (evite PowerShell quando houver alternativa).
- **Estilo**: siga o padrão de formatação/indentação já usado nos arquivos similares do repositório.
- **Mudanças**: altere apenas o que estiver diretamente relacionado ao assunto que está sendo tratado (evite refatoração desnecessária).

## Banco / Alembic

- **Migrações**: toda mudança de schema deve vir acompanhada de migration Alembic.
- **Consistência**: mantenha nomes e padrões alinhados ao histórico das migrations existentes.

## API / FastAPI

- **Contratos**: endpoints devem ter schemas claros de request/response.
- **Erros**: padronize respostas de erro (mensagens e status codes).

## Execução (Dev): Docker vs Local

- **Padrão (recomendado)**: rodar via **Docker Compose** (API + worker + Postgres + Redis + MinIO).
- **Local (exceção)**: rodar no venv apenas para depuração pontual (scripts/diagnóstico), não como modo “oficial”.
- **Portas**:
  - **Docker Compose**: API em `http://localhost:8000`
  - **Local**: a porta pode variar (ex.: `8001`) e isso impacta integrações.
- **Hosts de serviços (env vars)**:
  - **Dentro do Docker**: usar nomes de service (`REDIS_URL=redis://redis:6379/0`, `DATABASE_URL=...@postgres...`)
  - **Rodando local com infra no Docker**: usar `localhost` (`REDIS_URL=redis://localhost:6379/0`, `DATABASE_URL=...@localhost:5433...`)
- **OAuth (Google)**: o **origin** depende de host/porta; ao trocar (ex. `8001` → `8000`) é necessário atualizar **Authorized JavaScript origins** no Google Console para evitar `origin_mismatch`.

## Estilo / Formatters

- **Consistência**: priorize consistência com o código existente (imports, nomes, organização de módulos).
- **Legibilidade**: prefira código simples e explícito a "mágica".

## Scripts

- **Nome**: quando criar um script Python, use o prefixo **`script_`** no nome do arquivo.
- **Isolamento**: scripts devem ser executáveis e não devem introduzir efeitos colaterais indesejados ao serem importados.

## Dependências

- **Atualidade**: ao adicionar dependências, prefira versões atuais/seguras.
- **Justificativa**: toda dependência nova deve ter um motivo claro.
- **Requisitos**: mantenha o arquivo requirements.txt atualizado.

## Segurança

- **Segredos**: nunca commitar credenciais/chaves/tokens; use variáveis de ambiente e arquivos ignorados.
- **Dados sensíveis**: evite logar informações sensíveis (tokens, headers, PII).

## Consulta à Web (quando aplicável)

- **Atualidade**: ao consultar a web, priorize fontes atuais e verificáveis; se não houver, sinalize que pode não ser confiável.

