# Diretivas do Projeto

Frontend e backend são projetos independentes no mesmo repositório, comunicando-se exclusivamente via API HTTP. Nenhuma camada pode depender, acoplar ou assumir detalhes internos da outra.

Este documento define **regras e convenções** a seguir no código, revisões e automações.

## Convenções de nomenclatura e idioma

- **Código**: em inglês (classes, arquivos, métodos, variáveis, atributos).
- **Comentários, documentação e mensagens ao usuário**: em português.
- **Singular**: usar nomes no singular como padrão (ex.: `User`, `Invoice`).
- **Plural**: evitar, exceto quando estritamente necessário.
- **Coleções**: sufixo `List` (ex.: `userList`, `invoiceList`).
- **Exceções**: quando uma ferramenta tiver padrão consolidado (ex.: `alembic/versions/`), manter o padrão e registrar a exceção na documentação.

## Datas e horários

- **Tipo**: todos os campos de data/hora devem ser `timestamptz` (PostgreSQL). Não usar `date`, `time` nem `timestamp without time zone`.
- **Nomes**: todo campo de data/hora termina com `_at` (`created_at`, `start_at`, `end_at`, `published_at`).
- **API**: entrada e saída em ISO 8601 completo, com offset ou `Z`. Timestamps sem fuso explícito são inválidos.
- **Armazenamento**: instantes normalizados em UTC.
- **Tenant**: campo `timezone` no padrão IANA (ex.: `America/Sao_Paulo`).
- **Exibição**: conversão de fuso apenas no frontend ou camada de apresentação.
- **Períodos**: “dia inteiro” como intervalo `[start_at, end_at)`.
- **Jobs e relatórios**: usam timestamps normalizados; não aplicam conversão de fuso internamente.

## Python

- Preferir Python (evitar PowerShell quando houver alternativa).
- Seguir o estilo de formatação e indentação dos arquivos similares do repositório.
- Alterar apenas o que estiver diretamente relacionado ao assunto em questão.

## Banco / Alembic

- Toda mudança de schema deve ter migration Alembic.
- Manter nomes e padrões alinhados ao histórico das migrations existentes.

## Modelos e multi-tenant

### Account
- Pessoa física (login Google), email único global, sem `tenant_id`.
- `Account.name` é privado: apenas o próprio usuário vê; vem do Google OAuth.
- Criação: no primeiro login/registro via Google OAuth ou ao aceitar convite.

### Member
- Vínculo Account↔Tenant com role e status. Um Account pode ter múltiplos members.
- Convites pendentes: `account_id` pode ser NULL; o campo `email` identifica o convite.
- `member.email`: público na clínica; pode ser editado pelo admin. Sincroniza uma vez com `account.email` se vazio ao aceitar/rejeitar convite.
- `member.name`: público na clínica; preenchido automaticamente se NULL (ao aceitar convite ou primeiro login); depois editável pelo admin.
- Painel de member: não exibe dados do Account; cria/edita member com `email` e `name` públicos.

### Tenant e acesso
- Role e status vêm do member, não do Account.
- Todas as queries devem filtrar por `tenant_id` do JWT (via `get_current_member()`).
- Usar `get_current_member()` para validar acesso ao tenant, não `get_current_account()` diretamente.
- JWT contém apenas `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`. Email, name e role vêm do banco via endpoints.

### Demand com estado de escala
- Uma única tabela Demand: demanda cirúrgica e estado da escala (schedule_status, schedule_result_data, pdf_file_id, generated_at, published_at, etc.).
- Demandas só extraídas têm campos de escala opcionais nulos ou default.
- O worker atualiza cada Demand com o resultado da alocação (schedule_status, schedule_result_data, generated_at, job_id).
- Início e fim da cirurgia são `start_time` e `end_time`. Período da geração fica em `job.input_data` quando necessário.
- Para GENERATE_SCHEDULE, `Job.result_data` não persiste payload pesado; apenas mínimo para UI (ex.: allocation_count) ou só marcar COMPLETED.
- Profissionais para escala: carregados de `member` do tenant (`member.attribute`); members ACTIVE; attribute com sequence, can_peds, vacation. Ordenação por sequence.

### Separação Account (privado) vs Member (público)
- **Account**: dados de autenticação; não expor nem permitir edição por admins do tenant.
- **Member**: dados da clínica; visíveis e editáveis pelo admin.
- `GET /me`: retorna account_name (privado) e member_name (público).
- `GET /member/list`: retorna apenas member_name e member_email.
- Convite por email usa `member.email`. AuditLog registra member.name e member.email.

**Futuro:** Painel de Account com regras de acesso restritas (apenas o próprio usuário vê seus dados).

## API / FastAPI

- Endpoints com schemas claros de request/response.
- Respostas de erro padronizadas (mensagens e status codes).

## Fluxo de autenticação e seleção de clínica

- **Navegação**: ACTIVE == 1 e PENDING == 0 → dashboard; ACTIVE == 0 e PENDING == 0 → criação automática de clínica e dashboard; caso contrário → tela de seleção.
- **Criação automática de clínica**: quando o usuário não tem tenant, o sistema cria Tenant (name "Clínica", timezone America/Sao_Paulo, locale pt-BR, currency BRL) e member ADMIN ACTIVE. Endpoint: `POST /auth/google/create-tenant`.
- **Tela de seleção** (`/select-tenant`): lista clínicas ACTIVE e convites PENDING; botão "Criar clínica" apenas se ACTIVE == 0.
- Endpoints de auth: `POST /auth/google`, `POST /auth/google/register`, `POST /auth/google/select-tenant`, `POST /auth/google/create-tenant`, `POST /auth/switch-tenant`, `GET /auth/tenant/list`, `GET /auth/invites`, `POST /auth/invites/{id}/accept`, `POST /auth/invites/{id}/reject`, `POST /auth/dev/token` (dev).

## Frontend: menu e navegação

- Ordem do menu lateral: Dashboard, Hospitais, Clínicas, Associados, Arquivos, Demandas, Escalas, Jobs.
- Clínicas e Associados: apenas para role admin.

## Frontend: páginas protegidas

- Usar `protectedFetch()` de `lib/api.ts` para chamadas de API (trata 401 e padroniza erros).
- Não usar `api.get()` nem hooks de autenticação para dados de página.
- Estrutura: try externo, `protectedFetch()`, catch com set de erro para exibição no ActionBar. Nunca redirecionar para `/login` em erro de API (evitar logout indevido em F5).
- Erros 401: mensagem padronizada "Sessão expirada. Por favor, faça login novamente."; erros exibidos no ActionBar.
- Rotas `/login` e `/select-tenant` não redirecionam em 401; rotas `/api/*` idem; demais rotas (exceto `/`) são tratadas como protegidas e não redirecionam. Redirecionar para `/login` somente em 401 real (cookie inválido).
- Ao recarregar a página: sempre tentar carregar dados; em falha, mostrar mensagem de erro; não redirecionar para `/login` exceto em 401 real.

## Execução (dev)

- Backend em `backend/`, frontend em `frontend/`, `docker-compose.yml` na raiz. Comandos Docker e Alembic a partir da raiz.
- Padrão: Docker Compose (API, worker, Postgres, Redis, MinIO). Local/venv apenas para depuração.
- Comandos úteis (raiz): `docker compose up -d --build`, `docker compose logs -f worker`, `docker compose logs -f api`. Worker local: em `backend/`, `python -m app.worker.run` (requer `.env` e infra rodando).
- Portas: API em `http://localhost:8000`. OAuth (Google): origin depende de host/porta; configurar Authorized JavaScript origins no Google Console.

## Estilo e UX

- Consistência com o código existente. Código simples e explícito.
- **Proibido** efeitos de hover (classes `hover:`, `group-hover:`): elementos interativos devem estar sempre visíveis e funcionais (experiência consistente com mobile).

## Scripts e dependências

- Scripts Python: prefixo `script_` no nome; executáveis; sem efeitos colaterais indesejados ao importar.
- Dependências: versões atuais/seguras; justificativa clara para novas; manter `requirements.txt` atualizado.

## Segurança

- Nunca commitar credenciais; usar variáveis de ambiente e arquivos ignorados.
- Evitar logar dados sensíveis (tokens, headers, PII).

## Consulta à web

- Priorizar fontes atuais e verificáveis; se não houver, sinalizar que a informação pode não ser confiável.
