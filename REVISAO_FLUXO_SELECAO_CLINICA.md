# Revisão do Fluxo de Seleção/Criação de Clínica

## 1. FLUXO ATUAL (Como funciona hoje)

### 1.1 Backend - Endpoints e Lógica

#### POST `/auth/google` (Login)
- **Localização**: `app/api/auth.py:216`
- **Comportamento atual**:
  1. Verifica se account existe (404 se não existir)
  2. Busca tenants ACTIVE e invites PENDING via `get_account_memberships()`
  3. **Se `tenants == []`**: retorna 403 (sem acesso)
  4. **Se `len(tenants) > 1 OU len(invites) > 0`**: retorna `requires_tenant_selection=True` com listas
  5. **Se `len(tenants) == 1 E len(invites) == 0`**: emite token direto (entra no dashboard)

#### POST `/auth/google/register` (Cadastro)
- **Localização**: `app/api/auth.py:259`
- **Comportamento atual**:
  1. Se account não existe: cria account + membership ACTIVE no tenant "default"
  2. Se account já existe: chama `auth_google()` (mesmo comportamento do login)

#### POST `/auth/google/select-tenant`
- **Localização**: `app/api/auth.py:312`
- **Comportamento**: Emite JWT para tenant escolhido (valida membership ACTIVE ou PENDING)

#### POST `/auth/switch-tenant`
- **Localização**: `app/api/auth.py:538`
- **Comportamento**: Emite novo JWT para outro tenant (sem Google OAuth, apenas cookie)

#### GET `/auth/tenant/list`
- **Localização**: `app/api/auth.py:425`
- **Comportamento**: Retorna lista de tenants ACTIVE e invites PENDING

#### POST `/auth/invites/{membership_id}/accept`
- **Localização**: `app/api/auth.py:450`
- **Comportamento**: Atualiza membership PENDING → ACTIVE

#### POST `/auth/invites/{membership_id}/reject`
- **Localização**: `app/api/auth.py:495`
- **Comportamento**: Atualiza membership PENDING → REJECTED

#### POST `/tenant` (Criar tenant)
- **Localização**: `app/api/route.py:578`
- **Comportamento**: Cria tenant + membership ADMIN/ACTIVE para o criador
- **Requer**: Autenticação (JWT válido)

### 1.2 Frontend - Fluxo de Navegação

#### Página de Login (`frontend/app/(auth)/login/page.tsx`)
- **Fluxo após OAuth**:
  1. Chama `/api/auth/google/login` (handler Next.js)
  2. Handler chama backend `/auth/google`
  3. **Se `requires_tenant_selection == true`**:
     - Salva dados no `sessionStorage`
     - Redireciona para `/select-tenant`
  4. **Se `access_token` presente**:
     - Cookie é gravado pelo handler
     - Redireciona para `/dashboard`

#### Página de Seleção (`frontend/app/(auth)/select-tenant/page.tsx`)
- **Carregamento inicial**:
  1. Tenta buscar `/api/auth/tenant/list` (requer autenticação)
  2. Se falhar, usa dados do `sessionStorage` (fallback)
  3. **SEMPRE mostra a tela**, mesmo se `ACTIVE == 1` e `PENDING == 0`

- **Ações disponíveis**:
  - **Selecionar tenant ACTIVE**: chama `/api/auth/google/select-tenant` ou `/api/auth/switch-tenant`
  - **Aceitar convite**:
    1. Obtém token (via select-tenant/switch-tenant)
    2. Chama `/api/auth/invites/{id}/accept`
    3. Obtém token final para o tenant aceito
    4. Redireciona para `/dashboard`
  - **Rejeitar convite**:
    1. Obtém token (precisa de tenant ACTIVE)
    2. Chama `/api/auth/invites/{id}/reject`
    3. **Se após rejeitar: `tenants.length == 1` e `invites.length == 0`**: entra automaticamente
    4. **Senão**: apenas remove da lista (fica na tela)

- **Problemas identificados**:
  - Não há botão "Criar clínica" na tela de seleção
  - Não redireciona automaticamente quando `ACTIVE == 1` e `PENDING == 0`
  - Não redireciona para criar clínica quando `ACTIVE == 0` e `PENDING == 0`
  - Após rejeitar, não recarrega snapshot completo (não reapresenta opções corretamente)

### 1.3 Estados Possíveis Atuais

| ACTIVE | PENDING | Comportamento Atual |
|--------|---------|---------------------|
| 0 | 0 | ❌ 403 (sem acesso) - **DIVERGE**: deveria ir para criar clínica |
| 0 | 1 | ✅ Mostra tela de seleção com convite |
| 0 | >1 | ✅ Mostra tela de seleção com convites |
| 1 | 0 | ❌ Mostra tela de seleção - **DIVERGE**: deveria entrar direto |
| 1 | 1 | ✅ Mostra tela de seleção com clínica + convite |
| 1 | >1 | ✅ Mostra tela de seleção com clínica + convites |
| >1 | 0 | ✅ Mostra tela de seleção com lista de clínicas |
| >1 | 1 | ✅ Mostra tela de seleção com clínicas + convite |
| >1 | >1 | ✅ Mostra tela de seleção com clínicas + convites |

---

## 2. DIVERGÊNCIAS vs REGRAS DA MATRIZ

### 2.1 Navegação Inicial (Snapshot)

| Regra da Matriz | Comportamento Atual | Status |
|-----------------|---------------------|--------|
| `ACTIVE == 1` e `PENDING == 0` → entrar direto no dashboard | Sempre mostra tela de seleção | ❌ **DIVERGE** |
| `ACTIVE == 0` e `PENDING == 0` → ir para criar clínica | Retorna 403 (sem acesso) | ❌ **DIVERGE** |
| Caso contrário → mostrar tela de seleção | ✅ Funciona | ✅ OK |

### 2.2 Tela de Seleção

| Regra da Matriz | Comportamento Atual | Status |
|-----------------|---------------------|--------|
| Botão "Criar clínica" APENAS se `ACTIVE == 0` | Não existe botão | ❌ **FALTA** |
| Lista de clínicas ACTIVE (se `ACTIVE > 0`) | ✅ Funciona | ✅ OK |
| Lista de convites PENDING (se `PENDING > 0`) | ✅ Funciona | ✅ OK |

### 2.3 Ações Após Decisões

#### A) Escolher Clínica ACTIVE
| Regra da Matriz | Comportamento Atual | Status |
|-----------------|---------------------|--------|
| Se `ACTIVE == 0`: criar tenant + membership + entrar | Não há fluxo para isso | ❌ **FALTA** |
| Se `ACTIVE >= 1`: switch-tenant + entrar | ✅ Funciona | ✅ OK |

#### B) Aceitar Convite PENDING
| Regra da Matriz | Comportamento Atual | Status |
|-----------------|---------------------|--------|
| Atualizar APENAS o convite selecionado | ✅ Funciona | ✅ OK |
| switch-tenant para tenant aceito + entrar | ✅ Funciona | ✅ OK |

#### C) Rejeitar Convite PENDING
| Regra da Matriz | Comportamento Atual | Status |
|-----------------|---------------------|--------|
| Atualizar APENAS o convite selecionado | ✅ Funciona | ✅ OK |
| Recarregar snapshot e aplicar regras de navegação inicial | ❌ Apenas remove da lista local | ❌ **DIVERGE** |
| Se `ACTIVE == 1` e `PENDING == 0` → entrar direto | ❌ Não acontece | ❌ **DIVERGE** |
| Se `ACTIVE == 0` e `PENDING == 0` → ir para criar clínica | ❌ Não acontece | ❌ **DIVERGE** |

---

## 3. PROPOSTA DE AJUSTE MINIMALISTA

### 3.1 Princípio: Função Única de Decisão de Navegação

Criar uma função utilitária no frontend que decide a navegação baseada em `ACTIVE` e `PENDING`:
- Reutilizável após login, após rejeitar convite, após qualquer mudança de estado
- Centraliza a lógica (sem duplicação)

### 3.2 Arquivos a Modificar

#### Backend (`app/api/auth.py`)

**1. Ajustar `auth_google()` (linha 216)**
- **Mudança**: Quando `tenants == []` e `invites == []`, retornar `requires_tenant_selection=True` com listas vazias (em vez de 403)
- **Motivo**: Permite que o frontend decida se vai para criar clínica ou mostra tela vazia

**2. Ajustar `auth_google_register()` (linha 259)**
- **Mudança**: Se account já existe e não tem tenants/invites, retornar `requires_tenant_selection=True` com listas vazias
- **Motivo**: Consistência com login

#### Frontend (`frontend/app/(auth)/select-tenant/page.tsx`)

**1. Criar função utilitária `decideNavigation()`**
- **Localização**: No topo do arquivo (antes do componente)
- **Lógica**:
  ```typescript
  function decideNavigation(tenants: TenantOption[], invites: InviteOption[]): 'dashboard' | 'create-tenant' | 'select' {
    const activeCount = tenants.length
    const pendingCount = invites.length

    if (activeCount === 1 && pendingCount === 0) {
      return 'dashboard'
    }
    if (activeCount === 0 && pendingCount === 0) {
      return 'create-tenant'
    }
    return 'select'
  }
  ```

**2. Ajustar `useEffect` de carregamento inicial**
- **Mudança**: Após carregar tenants/invites, chamar `decideNavigation()`
- **Se `'dashboard'`**: redirecionar para `/dashboard` (com tenant único)
- **Se `'create-tenant'`**: chamar `handleCreateTenant()` automaticamente (criação automática)
- **Se `'select'`**: mostrar tela de seleção

**3. Adicionar função `handleCreateTenant()`**
- **Lógica**: Criar tenant automaticamente com dados default:
  - `name`: "Clínica"
  - `slug`: gerar automaticamente (ex: "clinica-{timestamp}" ou "clinica-{account_id}")
  - `timezone`: "America/Sao_Paulo" (default)
  - `locale`: "pt-BR" (default)
  - `currency`: "BRL" (default)
- **Fluxo**:
  1. Chamar `/api/tenant` com dados default
  2. Após criar com sucesso, fazer switch-tenant para o novo tenant
  3. Redirecionar para `/dashboard`
- **Tratamento de erros**: Se slug já existir, tentar com sufixo único

**4. Adicionar botão "Criar clínica"**
- **Condição**: Mostrar APENAS se `tenants.length === 0`
- **Ação**: Chamar `handleCreateTenant()` diretamente (criação automática, sem formulário)
- **Estado**: Mostrar loading durante criação

**5. Ajustar `handleRejectInvite()`**
- **Mudança**: Após rejeitar, recarregar snapshot completo (`loadTenants()`)
- **Depois**: Chamar `decideNavigation()` e aplicar a mesma lógica do carregamento inicial
- **Se `'dashboard'`**: entrar automaticamente
- **Se `'create-tenant'`**: chamar `handleCreateTenant()` automaticamente (criação automática)
- **Se `'select'`**: reapresentar tela atualizada

**6. Ajustar `handleSelectTenant()` para caso especial**
- **Mudança**: Se `tenants.length === 0` (não deveria acontecer, mas por segurança), não permitir seleção

#### Frontend (`frontend/app/(auth)/login/page.tsx`)

**1. Ajustar tratamento de resposta**
- **Mudança**: Se `requires_tenant_selection == true` mas `tenants.length === 0` e `invites.length === 0`, redirecionar para `/select-tenant` (que vai decidir e criar automaticamente se necessário)

---

## 4. CHECKLIST INCREMENTAL E TESTÁVEL

### Fase 1: Backend - Ajustar Respostas de Login

- [x] **1.1** Modificar `auth_google()` em `app/api/auth.py:216`
  - [x] Quando `tenants == []` e `invites == []`, retornar `requires_tenant_selection=True` com listas vazias (em vez de 403)
  - [ ] **Teste**: Login com account sem tenants/invites → deve retornar `requires_tenant_selection=True`

- [x] **1.2** Modificar `auth_google_register()` em `app/api/auth.py:259`
  - [x] Se account já existe e não tem tenants/invites, retornar `requires_tenant_selection=True` com listas vazias (já implementado via chamada a `auth_google()`)
  - [ ] **Teste**: Register com account existente sem tenants/invites → deve retornar `requires_tenant_selection=True`

### Fase 2: Frontend - Função de Decisão e Navegação Inicial

- [x] **2.1** Criar função `decideNavigation()` em `frontend/app/(auth)/select-tenant/page.tsx`
  - [x] Implementar lógica: `ACTIVE==1 && PENDING==0` → `'dashboard'`, `ACTIVE==0 && PENDING==0` → `'create-tenant'`, senão → `'select'`
  - [ ] **Teste**: Testar função com diferentes combinações de tenants/invites

- [x] **2.2** Ajustar `loadTenants()` e adicionar `useEffect` para aplicar decisão após carregar
  - [x] Criado `useEffect` que aplica `decideNavigation()` após carregar tenants/invites
  - [x] Se `'dashboard'`: chamar `handleSelectTenant(tenants[0].tenant_id)` automaticamente
  - [x] Se `'create-tenant'`: chamar `handleCreateTenant()` automaticamente (criação automática)
  - [x] Se `'select'`: mostrar tela normalmente
  - [ ] **Teste**:
    - `ACTIVE=1, PENDING=0` → deve entrar direto no dashboard (sem mostrar tela)
    - `ACTIVE=0, PENDING=0` → deve criar clínica automaticamente e entrar no dashboard
    - `ACTIVE>1 ou PENDING>0` → deve mostrar tela de seleção

### Fase 3: Frontend - Criação Automática de Clínica

- [x] **3.1** Criar função `handleCreateTenant()` em `frontend/app/(auth)/select-tenant/page.tsx`
  - [x] Criado endpoint backend `POST /auth/google/create-tenant` que gera slug único automaticamente
  - [x] Função chama `/api/auth/google/create-tenant` com `id_token`
  - [x] Endpoint backend cria tenant com dados default:
    - `name`: "Clínica"
    - `slug`: gerado automaticamente (`clinica-{timestamp}`)
    - `timezone`: "America/Sao_Paulo"
    - `locale`: "pt-BR"
    - `currency`: "BRL"
  - [x] Backend trata erro de slug duplicado (tenta com sufixo aleatório)
  - [x] Endpoint retorna JWT diretamente (não precisa fazer switch-tenant separado)
  - [x] Redirecionar para `/dashboard` após criar
  - [ ] **Teste**: Criar tenant → deve entrar no dashboard do novo tenant automaticamente

- [x] **3.2** Adicionar botão "Criar clínica" em `frontend/app/(auth)/select-tenant/page.tsx`
  - [x] Mostrar APENAS se `tenants.length === 0`
  - [x] Ao clicar: chamar `handleCreateTenant()` diretamente (sem formulário)
  - [x] Mostrar loading durante criação (estado `creating`)
  - [ ] **Teste**: Com `ACTIVE=0`, botão deve aparecer; com `ACTIVE>0`, não deve aparecer

### Fase 4: Frontend - Ajustar Rejeição de Convite

- [x] **4.1** Modificar `handleRejectInvite()` em `frontend/app/(auth)/select-tenant/page.tsx`
  - [x] Após rejeitar com sucesso, chamar `loadTenants()` para recarregar snapshot
  - [x] Ajustado para permitir rejeitar mesmo sem tenant ativo (usa token temporário do invite)
  - [x] Após recarregar, `useEffect` aplica `decideNavigation()` automaticamente:
    - [x] Se `'dashboard'`: entrar automaticamente no único tenant
    - [x] Se `'create-tenant'`: chamar `handleCreateTenant()` automaticamente (criação automática)
    - [x] Se `'select'`: continuar na tela (já atualizada)
  - [ ] **Teste**:
    - `ACTIVE=1, PENDING=1` → rejeitar → deve entrar no dashboard
    - `ACTIVE=0, PENDING=1` → rejeitar → deve criar clínica automaticamente e entrar no dashboard
    - `ACTIVE>1, PENDING=1` → rejeitar → deve continuar na tela atualizada

### Fase 5: Frontend - Ajustar Login para Caso Especial

- [ ] **5.1** Modificar `handleGoogleSignIn()` em `frontend/app/(auth)/login/page.tsx`
  - [ ] Se `requires_tenant_selection == true` mas listas vazias, redirecionar para `/select-tenant` (que vai decidir e criar automaticamente se necessário)
  - [ ] **Teste**: Login sem tenants/invites → deve ir para `/select-tenant` que cria clínica automaticamente

### Fase 6: Testes de Integração

- [ ] **6.1** Teste completo: `ACTIVE=0, PENDING=0`
  - [ ] Login → redireciona para `/select-tenant`
  - [ ] `/select-tenant` detecta situação e cria clínica automaticamente
  - [ ] Entra no dashboard do novo tenant

- [ ] **6.2** Teste completo: `ACTIVE=1, PENDING=0`
  - [ ] Login → entra direto no dashboard (sem mostrar tela de seleção)

- [ ] **6.3** Teste completo: `ACTIVE=0, PENDING=1`
  - [ ] Login → mostra tela com convite + botão criar
  - [ ] Aceitar → entra no dashboard do tenant aceito
  - [ ] Rejeitar → cria clínica automaticamente e entra no dashboard

- [ ] **6.4** Teste completo: `ACTIVE=1, PENDING=1`
  - [ ] Login → mostra tela com clínica + convite
  - [ ] Rejeitar convite → entra no dashboard (único tenant restante)

- [ ] **6.5** Teste completo: `ACTIVE>1, PENDING>0`
  - [ ] Login → mostra tela com clínicas + convites
  - [ ] Rejeitar convite → continua na tela atualizada
  - [ ] Aceitar convite → entra no dashboard do tenant aceito

---

## 5. RESUMO DAS MUDANÇAS

### Arquivos a Modificar (Backend)
1. `app/api/auth.py` (2 funções: `auth_google`, `auth_google_register` + novo endpoint `auth_google_create_tenant`)

### Arquivos a Modificar (Frontend)
1. `frontend/app/(auth)/select-tenant/page.tsx` (função de decisão, navegação inicial, rejeição, função de criação automática, botão criar)
2. `frontend/app/(auth)/login/page.tsx` (já trata corretamente, sem mudanças necessárias)

### Arquivos a Criar (Frontend)
1. `frontend/app/api/auth/google/create-tenant/route.ts` (handler Next.js para criação automática)

### Total de Mudanças
- **Backend**: 2 funções ajustadas + 1 novo endpoint (mudanças mínimas)
- **Frontend**: 1 arquivo modificado + 1 arquivo novo (handler)
- **Complexidade**: Baixa (lógica centralizada, criação automática sem UI adicional)

---

**Status**: ✅ **Implementado** - Aguardando testes de validação.
