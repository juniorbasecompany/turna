# Checklist: Implementação Membership.name (Nome Público na Clínica)

## Decisões Documentadas
Ver `DECISOES_MEMBERSHIP_NAME.md` para todas as decisões tomadas.

---

## Fase 1: Backend - Modelo e Migração

### 1.1 Migração Alembic
- [x] Criar migration para adicionar campo `name` em `Membership`
  - Campo: `name: str | None` (nullable)
  - Tipo: `VARCHAR` ou `TEXT`
  - Default: `NULL`
- [x] Script de migração de dados:
  - Copiar `account.name` → `membership.name` para todos os memberships com `status = 'ACTIVE'`
  - Deixar `NULL` para memberships com outros status
- [ ] **Teste**: Verificar que migration aplica sem erros
- [ ] **Teste**: Verificar que dados foram migrados corretamente

### 1.2 Atualizar Modelo Membership
- [x] Adicionar campo `name: str | None = Field(default=None)` em `app/model/membership.py`
- [x] **Teste**: Verificar que modelo compila sem erros

---

## Fase 2: Backend - Endpoints de Autenticação

### 2.1 Atualizar `accept_invite()`
- [x] Em `app/api/auth.py`, função `accept_invite()`:
  - Após mudar status para ACTIVE, verificar se `membership.name` é NULL
  - Se NULL, preencher com `name` do Google (extraído do JWT ou do account)
  - **Nota**: Precisa obter nome do Google - pode vir do `account.name` (se já foi atualizado) ou do token
- [ ] **Teste**: Aceitar convite → `membership.name` deve ser preenchido se NULL

### 2.2 Atualizar `auth_google()` e `auth_google_register()`
- [x] Em `app/api/auth.py`:
  - **`auth_google()`**:
    - Extrair `name` do Google token
    - Atualizar `account.name` apenas se estiver NULL/vazio
    - **NUNCA** atualizar `account.name` a partir de `membership.name`
  - **`auth_google_register()`**:
    - Se account já existe: seguir mesma lógica de `auth_google()`
    - Se account novo: criar com `name` do Google
- [ ] **Teste**: Login com account existente → `account.name` atualiza apenas se NULL
- [ ] **Teste**: Login com account novo → `account.name` preenchido do Google

### 2.3 Atualizar preenchimento de `membership.name` no login
- [x] Após autenticar, verificar se há membership ACTIVE para o tenant
- [x] Se `membership.name` for NULL, preencher com `name` do Google (do `account.name` atualizado)
- [ ] **Teste**: Login após aceitar convite → `membership.name` preenchido se NULL

---

## Fase 3: Backend - JWT e Endpoints de Dados

### 3.0 Limpeza do JWT - Remover campos não utilizados ⚠️

**Análise completa realizada**: Verificados todos os campos do JWT e seu uso no código.

#### Campos a REMOVER (não são usados em nenhum lugar):

1. **`email`** ❌
   - **Evidência**: Nenhum código faz `payload.get("email")` ou `payload["email"]`
   - **Motivo**: Email sempre vem do banco via `get_current_account().email`
   - **Impacto da remoção**: Nenhum (dados sempre consultados do banco)

2. **`name`** ❌
   - **Evidência**: Nenhum código faz `payload.get("name")` ou `payload["name"]`
   - **Motivo**: Nome sempre vem do banco via endpoint `/me` (frontend sempre chama `/api/me`)
   - **Impacto da remoção**: Nenhum (frontend não decodifica JWT, sempre usa `/api/me`)

3. **`role`** ⚠️
   - **Evidência**:
     - Middleware coloca em `request.state.role` (linha 47 de `tenant.py`)
     - Nenhum código lê `request.state.role`
     - `require_role()` valida via banco (`get_current_membership().role`), não usa JWT
   - **Motivo**: Validação de role sempre consulta banco, nunca confia no JWT
   - **Impacto da remoção**: Nenhum (validação sempre via banco)

4. **`membership_id`** ⚠️
   - **Evidência**:
     - Middleware coloca em `request.state.membership_id` (linha 49 de `tenant.py`)
     - Nenhum código lê `request.state.membership_id`
     - Membership sempre buscado do banco via `get_current_membership()`
   - **Motivo**: Membership sempre vem do banco, não do JWT
   - **Impacto da remoção**: Nenhum (membership sempre consultado do banco)

#### Campos a MANTER (são usados):

1. **`sub` (account_id)** ✅
   - **Uso**: `get_current_account()` (linha 34) e `get_current_membership()` (linha 55)
   - **Necessário**: Sim (identificação do usuário)

2. **`tenant_id`** ✅
   - **Uso**: `get_current_membership()` (linha 56) e middleware (linha 37)
   - **Necessário**: Sim (contexto multi-tenant)

3. **`iat`, `exp`, `iss`** ✅
   - **Uso**: Validação padrão JWT (expiração, issuer) em `verify_token()`
   - **Necessário**: Sim (segurança do token)

#### Checklist de Remoção:

- [x] Remover `email` de `create_access_token()` em `app/auth/jwt.py`
- [x] Remover `name` de `create_access_token()` em `app/auth/jwt.py`
- [x] Remover `role` de `create_access_token()` em `app/auth/jwt.py`
- [x] Remover `membership_id` de `create_access_token()` em `app/auth/jwt.py` (já é opcional, mas remover completamente)
- [x] Atualizar assinatura de `create_access_token()`:
  - Remover parâmetros: `email: str`, `name: str`, `role: str`
  - Manter apenas: `account_id`, `tenant_id`
  - Remover `membership_id` opcional
- [x] Atualizar função `_issue_token_for_membership()` em `app/api/auth.py` (linha 206):
  - Remover passagem de `email`, `name`, `role` para `create_access_token()`
  - Remover passagem de `membership_id`
  - Manter apenas: `account_id=account.id`, `tenant_id=membership.tenant_id`
- [x] Atualizar todas as chamadas diretas a `create_access_token()`:
  - `auth_google_select_tenant()` (linha 353): Remover `role`, `email`, `name`, `membership_id`
  - `switch_tenant()` (linha 572): Remover `role`, `email`, `name`, `membership_id`
  - Total: 3 chamadas (1 via `_issue_token_for_membership`, 2 diretas)
- [x] Atualizar middleware `tenant_context_middleware()` em `app/middleware/tenant.py`:
  - Remover extração de `role` (linha 38)
  - Remover extração de `membership_id` (linha 39)
  - Remover `request.state.role` (linha 47)
  - Remover `request.state.membership_id` (linha 49)
- [ ] **Teste**: JWT funciona corretamente sem esses campos
- [ ] **Teste**: Validação de role continua funcionando (via banco)
- [ ] **Teste**: Autenticação funciona normalmente
- [ ] **Teste**: Multi-tenant isolation continua funcionando

### 3.1 Atualizar JWT Token (se necessário após limpeza)
- [ ] **NOTA**: Após limpeza (Fase 3.0), `name` não será mais incluído no JWT
- [ ] **Decisão revisada**: Como `name` não é usado do JWT em nenhum lugar, **NÃO precisa incluir `membership.name`**
- [ ] **Decisão original (#4)**: Era incluir `membership.name` com fallback, mas descobriu-se que não é necessário
- [ ] **Ação**: Remover `name` do JWT (já feito na limpeza)
- [ ] **Teste**: JWT funciona sem campo `name`

### 3.2 Atualizar endpoint `/me`
- [x] Em `app/api/route.py`, função `get_me()`:
  - Retornar ambos `account_name` e `membership_name`
  - `account_name`: `account.name`
  - `membership_name`: `membership.name` (pode ser NULL)
- [ ] **Teste**: Endpoint retorna ambos os campos

### 3.3 Atualizar `invite_to_tenant()`
- [x] Em `app/api/route.py`, função `invite_to_tenant()`:
  - Aceitar `name` no body (opcional)
  - Se `name` fornecido, salvar em `membership.name` (não em `account.name`)
  - Se criar novo account, usar `name` do body ou email como fallback para `account.name`
- [ ] **Teste**: Criar convite com `name` → `membership.name` preenchido

### 3.4 Atualizar `list_memberships()`
- [x] Em `app/api/route.py`, função `list_memberships()`:
  - Retornar `membership.name` em vez de `account.name` no campo `account_name`
  - Ou criar campo separado `membership_name` e manter `account_name` para compatibilidade
  - **Decisão**: Usar campo `membership_name` e manter `account_name` apenas para compatibilidade (deprecar depois)
- [ ] **Teste**: Listagem retorna `membership.name` correto

### 3.5 Criar/Atualizar `PUT /membership/{id}`
- [x] Criar ou atualizar endpoint para editar membership
- [x] Permitir editar `membership.name` (apenas admin)
- [x] Validar que `account.name` nunca é editado via este endpoint
- [ ] **Teste**: Admin pode editar `membership.name`

---

## Fase 4: Backend - Email e Auditoria

### 4.1 Atualizar email de convite
- [ ] Em `app/api/route.py`, função `send_membership_invite_email()`:
  - Usar `membership.name` se existir, senão usar email
  - Atualizar chamada para `send_professional_invite()`:
    - `professional_name = membership.name or account.email`
- [ ] **Teste**: Email usa `membership.name` se disponível

### 4.2 Atualizar AuditLog
- [ ] Em todos os lugares que criam `AuditLog`:
  - Registrar `membership.name` com fallback para email se NULL
  - Campo `data` deve incluir `membership_name` (ou `account_email` se NULL)
- [ ] **Teste**: Logs de auditoria contêm nome correto

---

## Fase 5: Frontend - Tipos e Interfaces

### 5.1 Atualizar tipos TypeScript
- [ ] Em `frontend/types/api.ts`:
  - Adicionar `membership_name?: string` em `MembershipResponse`
  - Atualizar `AccountResponse` para incluir `membership_name` (se necessário)
  - Atualizar `AuthResponse` ou criar tipo para `/me` com ambos os campos
- [ ] **Teste**: Tipos compilam sem erros

### 5.2 Atualizar endpoint `/me`
- [ ] Em `frontend/app/api/me/route.ts` ou similar:
  - Tratar resposta com `account_name` e `membership_name`
- [ ] **Teste**: Frontend recebe ambos os campos

---

## Fase 6: Frontend - Componentes e Páginas

### 6.1 Atualizar Header
- [ ] Em `frontend/components/Header.tsx`:
  - Usar `membership.name` (ou `account.name` se NULL) para exibição
  - Priorizar `membership_name` se disponível
- [ ] **Teste**: Header mostra nome correto

### 6.2 Atualizar página de Accounts
- [ ] Em `frontend/app/(protected)/account/page.tsx`:
  - **NOTA IMPORTANTE**: Atualmente mostra `account.name`
  - **FUTURO**: Este painel terá regras de acesso restritas
  - Por enquanto manter como está, mas documentar que será restringido
  - Adicionar comentário no código: `// TODO: Restringir acesso - account.name é privado`
- [ ] **Teste**: Página funciona (mesmo comportamento atual)

### 6.3 Atualizar página de Memberships
- [ ] Em `frontend/app/(protected)/membership/page.tsx`:
  - Mostrar `membership.name` em vez de `account.name`
  - Usar fallback para email se `membership.name` for NULL
- [ ] **Teste**: Listagem mostra `membership.name` correto

### 6.4 Atualizar formulário de convite
- [ ] Se houver formulário de criação de convite:
  - Permitir campo `name` (opcional)
  - Salvar em `membership.name` (não em `account.name`)
- [ ] **Teste**: Criar convite com nome funciona

---

## Fase 7: Validações e Testes

### 7.1 Validações de Privacidade
- [ ] Garantir que `account.name` nunca é atualizado a partir de `membership.name`
- [ ] Garantir que usuário só vê seu próprio `account.name`
- [ ] Garantir que admin não vê `account.name` de outros (exceto no painel de Accounts que será restringido)
- [ ] **Teste**: Privacidade respeitada

### 7.2 Validações de Atualização Automática
- [ ] `membership.name` é atualizado apenas se NULL
- [ ] `account.name` é atualizado apenas se NULL/vazio
- [ ] Edições manuais não são sobrescritas
- [ ] **Teste**: Atualizações automáticas funcionam corretamente

### 7.3 Testes de Integração
- [ ] Cenário: Criar convite com nome → Aceitar convite → Verificar `membership.name`
- [ ] Cenário: Login com account existente → Verificar atualização de `account.name` e `membership.name`
- [ ] Cenário: Editar `membership.name` manualmente → Login não sobrescreve
- [ ] Cenário: Múltiplos tenants → Nomes diferentes por tenant funcionam

---

## Notas Importantes

1. **Privacidade**: `Account.name` é privado - apenas o próprio usuário vê
2. **Futuro**: Painel de Accounts terá regras de acesso restritas (anotado no código)
3. **Migração**: Dados existentes serão copiados de `account.name` para `membership.name`
4. **Compatibilidade**: Manter `account_name` em respostas por enquanto (deprecar depois)

---

## Ordem de Implementação Recomendada

1. **Fase 1**: Modelo e migração (base)
2. **Fase 2**: Autenticação (lógica core)
3. **Fase 3.0**: Limpeza do JWT - remover campos não utilizados (opcional, mas recomendado)
4. **Fase 3**: JWT e endpoints (dados)
5. **Fase 4**: Email e auditoria (complementos)
6. **Fase 5**: Frontend tipos (preparação)
7. **Fase 6**: Frontend componentes (UI)
8. **Fase 7**: Testes e validações (garantia)

---

## Resumo da Análise do JWT

### Campos Atuais no JWT
```json
{
  "sub": "123",              // ✅ USADO (account_id)
  "email": "...",            // ❌ NÃO USADO
  "name": "...",             // ❌ NÃO USADO
  "tenant_id": 5,            // ✅ USADO
  "role": "admin",           // ⚠️ COLOCADO EM request.state mas NUNCA LIDO
  "membership_id": 42,       // ⚠️ COLOCADO EM request.state mas NUNCA LIDO
  "iat": 1234567890,         // ✅ USADO (validação JWT)
  "exp": 1234593690,         // ✅ USADO (validação JWT)
  "iss": "turna"             // ✅ USADO (validação JWT)
}
```

### Campos Mínimos Necessários (após limpeza)
```json
{
  "sub": "123",              // account_id
  "tenant_id": 5,            // tenant atual
  "iat": 1234567890,         // issued at
  "exp": 1234593690,         // expiration
  "iss": "turna"             // issuer
}
```

### Benefícios da Limpeza
- ✅ **JWT menor**: Redução de ~40-50% no tamanho do token
- ✅ **Menos confusão**: Não há dúvida sobre qual nome/email está no token
- ✅ **Fonte da verdade**: Dados sempre vêm do banco (mais confiável)
- ✅ **Privacidade**: Dados sensíveis não ficam expostos no token
- ✅ **Manutenibilidade**: Menos campos = menos complexidade
- ✅ **Performance**: Token menor = menos bytes em cada requisição

### Observações Importantes
1. **Validação sempre via banco**: O sistema já valida tudo no banco (`get_current_membership()`), então não há perda de segurança
2. **Frontend não decodifica**: Frontend sempre chama `/api/me` para obter dados, nunca lê o JWT diretamente
3. **Compatibilidade**: Tokens antigos continuarão funcionando até expirar (8 horas)
4. **Migração**: Não precisa migrar tokens existentes, apenas novos tokens terão menos campos

---

## Análise de Campos JWT - Campos Não Utilizados

### Campos que podem ser removidos (não são lidos em nenhum lugar):

1. **`email`** ❌
   - **Status**: Não usado
   - **Evidência**: Nenhum código faz `payload.get("email")` ou `payload["email"]`
   - **Motivo**: Email vem do banco via `get_current_account().email`
   - **Impacto**: Nenhum (dados sempre vêm do banco)

2. **`name`** ❌
   - **Status**: Não usado
   - **Evidência**: Nenhum código faz `payload.get("name")` ou `payload["name"]`
   - **Motivo**: Nome vem do banco via endpoint `/me`
   - **Impacto**: Nenhum (frontend sempre chama `/api/me`)

3. **`role`** ⚠️
   - **Status**: Colocado em `request.state.role` mas nunca lido
   - **Evidência**:
     - Middleware coloca em `request.state.role` (linha 47)
     - Nenhum código lê `request.state.role`
     - `require_role()` valida via banco (`get_current_membership().role`)
   - **Motivo**: Validação de role sempre consulta banco, não confia no JWT
   - **Impacto**: Nenhum (validação sempre via banco)

4. **`membership_id`** ⚠️
   - **Status**: Colocado em `request.state.membership_id` mas nunca lido
   - **Evidência**:
     - Middleware coloca em `request.state.membership_id` (linha 49)
     - Nenhum código lê `request.state.membership_id`
   - **Motivo**: Membership é buscado do banco via `get_current_membership()`
   - **Impacto**: Nenhum (membership sempre vem do banco)

### Campos que devem ser mantidos (são usados):

1. **`sub` (account_id)** ✅
   - **Uso**: `get_current_account()` e `get_current_membership()`
   - **Necessário**: Sim (identificação do usuário)

2. **`tenant_id`** ✅
   - **Uso**: `get_current_membership()` e middleware
   - **Necessário**: Sim (contexto multi-tenant)

3. **`iat`, `exp`, `iss`** ✅
   - **Uso**: Validação padrão JWT (expiração, issuer)
   - **Necessário**: Sim (segurança do token)

---

## Resumo da Limpeza do JWT

**Antes** (campos no JWT):
```json
{
  "sub": "123",
  "email": "usuario@exemplo.com",  // ❌ Não usado
  "name": "Carlos Silva",           // ❌ Não usado
  "tenant_id": 5,
  "role": "admin",                  // ⚠️ Não usado (validação via banco)
  "membership_id": 42,              // ⚠️ Não usado
  "iat": 1234567890,
  "exp": 1234593690,
  "iss": "turna"
}
```

**Depois** (campos mínimos necessários):
```json
{
  "sub": "123",           // account_id
  "tenant_id": 5,         // tenant atual
  "iat": 1234567890,      // issued at
  "exp": 1234593690,      // expiration
  "iss": "turna"          // issuer
}
```

**Benefícios**:
- ✅ JWT menor (menos dados)
- ✅ Menos confusão sobre qual nome/email está no token
- ✅ Fonte da verdade sempre é o banco
- ✅ Privacidade: dados sensíveis não ficam no token
