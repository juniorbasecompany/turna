# Diretivas do Projeto (Fonte da Verdade)

Frontend e backend são projetos independentes no mesmo repositório, comunicando-se exclusivamente via API HTTP; nenhuma camada pode depender, acoplar ou assumir detalhes internos da outra.

Este documento concentra **diretivas que devem ser seguidas** durante a construção do projeto (código, sugestões, revisões e automações).

## Convenções de nomenclatura e idioma

- **Idioma do código**: todo o código-fonte (nomes de classes, arquivos, métodos, variáveis, atributos, etc.) deve ser escrito **em inglês**.
- **Idioma de comunicação**: todos os **comentários**, **documentação** e **mensagens exibidas ao usuário** devem ser escritos **em português**, tanto no **backend** quanto no **frontend**.
- **Singular**: utilize nomes no singular como padrão (ex.: `User`, `Invoice`, `Schedule`).
- **Plural**: evite o uso de nomes no plural, exceto quando estritamente necessário.
- **Listas e arrays**: utilize o sufixo `List` para indicar coleções (ex.: `userList`, `invoiceList`).
- **Exceções por convenção de ferramentas**: quando uma ferramenta ou framework adotar um padrão consolidado (ex.: `alembic/versions/`), preserve a convenção original e registre explicitamente a exceção na documentação do projeto.


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

## Modelos e Multi-Tenant

- **Account**: modelo de pessoa física (login Google), email único global, sem `tenant_id`.
- **Membership**: vínculo Account↔Tenant com `role` e `status` (um Account pode ter múltiplos memberships).
- **Role e Status**: sempre usar do Membership, não do Account (Account.role é apenas legado/conveniência).
- **Tenant isolation**: todas as queries devem filtrar por `tenant_id` do JWT (via `get_current_membership()`).
- **Dependencies**: usar `get_current_membership()` para validar acesso ao tenant, não `get_current_account()` diretamente.
- **JWT**: `role` no token vem do Membership, não do Account.

## API / FastAPI

- **Contratos**: endpoints devem ter schemas claros de request/response.
- **Erros**: padronize respostas de erro (mensagens e status codes).

## Frontend / Autenticação

- **Padrão de carregamento em páginas protegidas**: use `fetch()` diretamente (NÃO use `api.get()` do `lib/api.ts` ou hooks de autenticação), seguindo exatamente o padrão de `/select-tenant` e `/dashboard`:
  - Estrutura: `try { try { fetch() } catch {} } catch {}` - try interno para API, catch que ignora erro
  - Não redirecionar para `/login` em caso de erro de API - apenas mostrar mensagem de erro
  - Isso evita logout desnecessário ao pressionar F5 em caso de erros temporários de rede/servidor
- **F5/Refresh**: ao recarregar a página (F5), tentar carregar dados do servidor. Se falhar, mostrar erro mas NÃO redirecionar para `/login` automaticamente. Apenas redirecionar quando realmente não houver cookie válido (401 real do backend).
- **Redirecionamento automático**: o `lib/api.ts` faz redirecionamento automático para `/login` em 401. Páginas que usam `fetch()` diretamente devem ter exceção adicionada em `lib/api.ts` se usarem `api.get()` em algum lugar (ver `/dashboard` como exceção).
- **Exemplo de padrão** (como `/select-tenant` e `/dashboard`):
  ```tsx
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      try {
        const res = await fetch('/api/endpoint', { credentials: 'include' })
        if (res.ok) {
          const data = await res.json()
          setData(data)
          setLoading(false)
          return
        }
      } catch (err) {
        // Se API falhar, continuar (não redirecionar)
      }
      setError('Não foi possível carregar dados. Tente recarregar a página.')
    } catch (err) {
      setError('Erro ao carregar dados')
    } finally {
      setLoading(false)
    }
  }, [])
  ```

## Execução (Dev): Docker vs Local

- **Padrão (recomendado)**: rodar via **Docker Compose** (API + worker + Postgres + Redis + MinIO).
- **Local (exceção)**: rodar no venv apenas para depuração pontual (scripts/diagnóstico), não como modo “oficial”.
- **Comandos úteis (Docker Compose)**:
  - **Subir stack**: `docker compose up -d --build`
  - **Logs worker**: `docker compose logs -f worker`
  - **Logs API**: `docker compose logs -f api`
- **Comandos úteis (Local / exceção)**:
  - **Rodar worker local**: `python .\app\worker\run.py`
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

