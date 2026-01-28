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
  - **Privacidade**: `Account.name` é privado - apenas o próprio usuário vê.
  - **Criação**: Account é criado quando o usuário faz login/registro via Google OAuth pela primeira vez (sem precisar de convite). Também pode ser criado ao aceitar um convite se ainda não existir.
  - **Atualização de nome**: `Account.name` sempre vem do Google OAuth, nunca de `member.name`. Atualiza apenas se NULL/vazio no login.
- **member**: vínculo Account↔Tenant com `role` e `status` (um Account pode ter múltiplos members).
  - **Convites pendentes**: `account_id` pode ser `NULL` para convites pendentes (antes do usuário aceitar).
  - **Campo email**: `member.email` é o email público na clínica (pode ser diferente de `Account.email`).
    - **Uso inicial**: Quando `account_id` é `NULL`, o campo `email` identifica o convite pendente e é usado para vincular ao Account na aceitação.
    - **Sincronização**: Após aceitar/rejeitar convite, se `member.email` estiver vazio, é preenchido uma vez com `account.email`.
    - **Independência**: Depois da sincronização inicial, `member.email` é completamente independente e pode ser editado/apagado livremente pelo admin.
    - **Edição manual**: Admin pode editar `member.email` via `PUT /member/{id}` sem restrições.
    - **Privacidade**: `Account.email` permanece privado; apenas `member.email` é exposto no painel e endpoints de tenant.
  - **Campo name**: `member.name` é o nome público na clínica (pode ser diferente de `Account.name`).
    - **Atualização automática**: Preenchido apenas se NULL (ao aceitar convite ou primeiro login).
    - **Edição manual**: Admin pode editar `member.name` via `PUT /member/{id}` sem restrições.
    - **Fonte**: Pode vir do convite (placeholder), do Google ao aceitar/login (se NULL), ou edição manual.
  - **Vinculação**: ao aceitar convite ou fazer login, members PENDING são vinculados ao Account pelo email.
  - **Criação de convite**: Ao convidar usuário sem Account, cria member com `account_id=NULL` e `email`. Account é criado apenas quando usuário aceita convite ou faz login.
  - **Painel de member**: Não deve ter relação com Account. Não usa `account_id` para criar ou editar member. Nome e email são editáveis livremente.
- **Role e Status**: sempre usar do member, não do Account (Account.role é apenas legado/conveniência).
- **Tenant isolation**: todas as queries devem filtrar por `tenant_id` do JWT (via `get_current_member()`).
- **Dependencies**: usar `get_current_member()` para validar acesso ao tenant, não `get_current_account()` diretamente.
- **JWT**: contém apenas `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`. Dados como email, name, role são obtidos do banco via endpoints.

### Relação Demand → Schedule (1:1)

- **Cada Demand gera exatamente uma Schedule** (relação 1:1 garantida pelo banco via UNIQUE constraint).
- **FK `schedule.demand_id`**: NOT NULL, UNIQUE, ON DELETE CASCADE.
- **Hospital da Schedule**: obtido via `demand.hospital_id` (JOIN), não há `hospital_id` direto na tabela Schedule.
- **Integridade**: ao excluir uma Demand, a Schedule correspondente é excluída automaticamente (CASCADE).
- **Criação manual**: ao criar Schedule manualmente, deve-se especificar `demand_id` (não `hospital_id`).
- **Geração automática**: o worker cria uma Schedule para cada Demand processada, usando `demand_id`.
- **Profissionais para escala**: o worker carrega profissionais da tabela `member` do tenant (`member.attribute`). Apenas members ACTIVE; attribute exige `sequence` (numérico), `can_peds` (bool), `vacation` (lista de pares). Ordenação por `sequence`.

### Separação Account (privado) vs member (público)

**Princípio fundamental**:
- **`Account.*`**: Privado - dados de autenticação, não devem ser expostos ou editados por administradores de tenant.
  - **`Account.name`**: Privado - apenas o próprio usuário vê. Sempre vem do Google OAuth, nunca de `member.name`.
  - **`Account.email`**: Privado - usado apenas para login/autenticação, não deve ser exposto em endpoints de tenant.
- **`member.*`**: Público - dados da clínica, visíveis para admins do tenant, podem ser editados livremente.
  - **`member.name`**: Público - nome na clínica, visível para admins do tenant. Pode ser editado por admin.
  - **`member.email`**: Público - email na clínica, visível para admins do tenant. Pode ser editado por admin.

**Regras de atualização**:
- **`Account.name`**: Atualiza apenas se NULL/vazio no login via Google OAuth.
- **`Account.email`**: Nunca atualizado a partir de `member.email`.
- **`member.name`**: Atualiza automaticamente apenas se NULL (ao aceitar convite ou primeiro login). Depois pode ser editado manualmente por admin.
- **`member.email`**: Sincroniza uma vez com `account.email` se estiver vazio ao aceitar/rejeitar convite. Depois é completamente independente e pode ser editado/apagado.

**Uso em endpoints**:
- **`GET /me`**: Retorna ambos `account_name` (privado) e `member_name` (público).
- **`GET /member/list`**: Retorna apenas `member_name` e `member_email` (não `account_name` nem `account_email`). ✅ Implementado
- **`POST /member`**: Cria member com `email` e `name` públicos (não requer `account_id`). ✅ Implementado
- **`PUT /member/{id}`**: Permite editar `member.name` e `member.email` (apenas admin). ✅ Implementado
- **Email de convite**: Usa `member.email` (não `account.email`). ✅ Implementado
- **AuditLog**: Registra `member.name` e `member.email` (não dados do account).

**Painel de member**: ✅ Implementado
- Não exibe ou usa dados do Account (`account_email`, `account_name`).
- Permite criar member sem `account_id` (apenas com `email` e `name`).
- Permite editar `member.email` e `member.name` livremente.
- Checkbox "Enviar convite" funciona tanto para member novo quanto existente.

**Painel de Accounts** (futuro):
- Atualmente mostra `account.name`, mas terá regras de acesso restritas no futuro.
- `Account.name` é privado - apenas o próprio usuário deve ver.

## API / FastAPI

- **Contratos**: endpoints devem ter schemas claros de request/response.
- **Erros**: padronize respostas de erro (mensagens e status codes).

## Fluxo de Autenticação e Seleção de Clínica

### Navegação Após Login Google OAuth

**Regras de navegação automática** (implementadas no frontend):
- **`ACTIVE == 1` e `PENDING == 0`**: Entra direto no dashboard (sem mostrar tela de seleção).
- **`ACTIVE == 0` e `PENDING == 0`**: Cria clínica automaticamente com dados default e entra no dashboard.
- **Caso contrário**: Mostra tela de seleção com clínicas ACTIVE e convites PENDING.

**Criação automática de clínica**:
- Quando usuário não tem nenhum tenant, sistema cria automaticamente:
  - `name`: "Clínica"
  - `slug`: Gerado automaticamente (`clinica-{timestamp}`)
  - `timezone`: "America/Sao_Paulo"
  - `locale`: "pt-BR"
  - `currency`: "BRL"
- Cria também member ADMIN ACTIVE para o criador.
- Endpoint: `POST /auth/google/create-tenant` (cria tenant e retorna JWT diretamente).

**Tela de seleção** (`/select-tenant`):
- Mostra lista de clínicas ACTIVE (se houver).
- Mostra lista de convites PENDING (se houver).
- Botão "Criar clínica" aparece apenas se `ACTIVE == 0`.
- Após rejeitar convite, recarrega snapshot e aplica regras de navegação automática.

**Endpoints de autenticação**:
- `POST /auth/google`: Login (retorna token direto ou `requires_tenant_selection=True`).
- `POST /auth/google/register`: Cadastro (cria Account se não existir).
- `POST /auth/google/select-tenant`: Seleciona tenant e emite JWT.
- `POST /auth/google/create-tenant`: Cria clínica automaticamente e emite JWT (quando account não tem nenhum tenant ACTIVE).
- `POST /auth/switch-tenant`: Troca de tenant (sem Google OAuth).
- `GET /auth/tenant/list`: Lista tenants ACTIVE e convites PENDING.
- `GET /auth/invites`: Lista convites pendentes do usuário.
- `POST /auth/invites/{id}/accept`: Aceita convite.
- `POST /auth/invites/{id}/reject`: Rejeita convite.
- `POST /auth/dev/token`: Endpoint de desenvolvimento para gerar token (apenas em dev).

## Frontend / Autenticação

## Menu e Navegação

**Ordem do menu lateral** (implementado em `frontend/components/Sidebar.tsx`):
1. Dashboard
2. Hospitais
3. Clínicas (admin-only)
4. Associados (admin-only)
5. Arquivos
6. Demandas
7. Escalas
8. Jobs

**Itens admin-only**: Clínicas e Associados são visíveis apenas para usuários com role `admin`.

## Padrão de carregamento em páginas protegidas

- **Use `protectedFetch()` de `lib/api.ts`** para todas as chamadas de API.
  Esta função trata 401 automaticamente e padroniza mensagens de erro.
- **Nunca use `api.get()` do `lib/api.ts`** nem hooks de autenticação.
- **Estrutura obrigatória**:
  - `try` externo para controle geral
  - Chamada usando `protectedFetch()` que trata erros automaticamente
  - `catch` captura erros e seta no estado para exibição no ActionBar
- **Nunca redirecionar para `/login`** em erro de API.
- **Motivo**: evitar logout indevido ao pressionar F5 em falhas temporárias.

### Tratamento de Erros 401 - ⚠️ REGRA OBRIGATÓRIA

**Todas as páginas protegidas devem usar `protectedFetch()` que garante:**
- ✅ Erros 401 sempre retornam a mensagem padronizada: "Sessão expirada. Por favor, faça login novamente."
- ✅ Todos os erros são exibidos no ActionBar (nunca em outros lugares)
- ✅ Tratamento consistente em todas as páginas

**Ao criar uma nova página protegida:**
1. Importe `protectedFetch` de `@/lib/api`
2. Use `protectedFetch<T>(url, options)` em vez de `fetch()` direto
3. Capture erros no `catch` e set no estado `error`
4. Exiba erros no ActionBar (padrão já implementado)

## F5 / Refresh

- Ao recarregar a página, **sempre tentar carregar os dados**.
- Se falhar:
  - Mostrar mensagem de erro
  - **Não redirecionar automaticamente para `/login`**
- Redirecionar para `/login` **somente em 401 real** (cookie inválido).

## Redirecionamento automático (`lib/api.ts`) - ⚠️ ATENÇÃO CRÍTICA

### Problema Identificado

O `AuthProvider` (usado no `RootLayout` via `Providers`) utiliza `api.get()` do `lib/api.ts` para verificar autenticação ao montar a aplicação. O `lib/api.ts` possui lógica que redireciona automaticamente para `/login` quando recebe 401, **exceto para páginas específicas que seguem padrões definidos**.

### Quando o Problema Ocorre

- Ao criar uma **nova página protegida** que usa `fetch()` direto (correto)
- O `AuthProvider` tenta carregar autenticação usando `api.get()` (que usa `lib/api.ts`)
- Se houver 401 durante essa verificação, `lib/api.ts` redireciona para `/login` **mesmo que a página use `fetch()` direto**
- **Resultado**: Ao pressionar F5 na nova página, o usuário é redirecionado para `/login` indevidamente

### Solução Implementada

**O `lib/api.ts` usa um padrão de rota automático que detecta páginas protegidas sem precisar listar cada uma individualmente.**

**Lógica implementada:**
- **Rotas de autenticação** (`/login`, `/select-tenant`): não redirecionam
- **Rotas de API** (`/api/*`): não redirecionam (não são páginas)
- **Páginas protegidas**: qualquer rota que não seja de autenticação, API ou raiz (`/`) é automaticamente considerada protegida e não redireciona
- **Outras rotas**: redirecionam para `/login`

**Vantagens:**
- ✅ **Automático**: novas páginas em `app/(protected)/` são detectadas automaticamente
- ✅ **Sem manutenção manual**: não precisa adicionar cada página à lista
- ✅ **Código mais limpo**: lógica baseada em padrões, não em listas

### Código Implementado

```typescript
// Em frontend/lib/api.ts, função apiRequest
if (response.status === 401) {
    if (typeof window !== 'undefined') {
        const path = window.location.pathname

        // Rotas de autenticação: não redirecionar
        const isAuthRoute = path.startsWith('/login') || path.startsWith('/select-tenant')

        // Rotas de API: não redirecionar (não são páginas)
        const isApiRoute = path.startsWith('/api')

        // Páginas protegidas: todas as outras rotas (exceto raiz) são assumidas como protegidas
        // Todas as páginas em app/(protected)/ seguem o padrão de usar fetch() direto
        // e gerenciam seus próprios erros 401, então não devem ser redirecionadas automaticamente
        const isProtectedRoute = path !== '/' && !isAuthRoute && !isApiRoute

        // Redirecionar apenas se não for rota de autenticação, API ou protegida
        if (!isAuthRoute && !isApiRoute && !isProtectedRoute) {
            window.location.href = '/login'
        }
    }
    throw new ApiError('Não autenticado', 401)
}
```

### Checklist ao Criar Nova Página Protegida

- [ ] Página usa `fetch()` direto (não `api.get()`)
- [ ] Página segue padrão try/catch interno/externo (catch interno ignora erro)
- [ ] Página NÃO redireciona para `/login` em 401
- [ ] **Nenhuma ação adicional necessária** - a página será detectada automaticamente pelo padrão de rota
- [ ] Testado pressionando F5 - não deve redirecionar para `/login`

### Motivo Técnico

O `AuthProvider` é montado no `RootLayout` e executa em **todas as páginas**, incluindo páginas protegidas. Ele usa `api.get()` que por sua vez usa `lib/api.ts`. Mesmo que sua página use `fetch()` direto e trate 401 corretamente, o `AuthProvider` pode causar redirecionamento se não estiver na lista de exceções.

## Referência

- Padrão implementado em todas as páginas em `app/(protected)/`

## Execução (Dev): Docker vs Local

- **Estrutura**: Backend em `backend/`, frontend em `frontend/`, `docker-compose.yml` na raiz. Comandos Docker e Alembic são executados a partir da raiz do repositório.
- **Padrão (recomendado)**: rodar via **Docker Compose** (API + worker + Postgres + Redis + MinIO).
- **Local (exceção)**: rodar no venv apenas para depuração pontual (scripts/diagnóstico), não como modo “oficial”.
- **Comandos úteis (Docker Compose)** — executar na **raiz** do repo:
  - **Subir stack**: `docker compose up -d --build`
  - **Logs worker**: `docker compose logs -f worker`
  - **Logs API**: `docker compose logs -f api`
- **Comandos úteis (Local / exceção)**:
  - **Rodar worker local**: a partir de `backend/`, `python -m app.worker.run` (requer `backend/.env` e infra rodando).
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

## Efeitos de Hover / Mobile

- **Proibição**: **não usar** efeitos de hover (classes `hover:`, `group-hover:`) no projeto.
- **Motivo**: experiência deve ser consistente entre desktop e mobile; usuários vão usar muito no telefone.
- **Regra**: todos os elementos interativos devem estar sempre visíveis e funcionais, sem depender de hover para aparecer ou mudar de estado.

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

