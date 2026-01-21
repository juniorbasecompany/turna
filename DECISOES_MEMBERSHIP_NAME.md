# Decisões: Separação Account.name (privado) vs Membership.name (público)

## Contexto

**Problema identificado:**
1. Admin pode cadastrar usuário com nome errado no convite
2. Admin pode ver nome do usuário mesmo antes do consentimento (privacidade)
3. Nome não é atualizado automaticamente quando usuário faz login via Google

**Solução proposta:**
- `Account.name`: **PRIVADO** - apenas o próprio usuário vê
- `Membership.name`: **PÚBLICO** - nome na clínica, visível para admins do tenant

---

## Decisões Tomadas

### 1. Quando atualizar `Membership.name` automaticamente?
**Decisão: C** - Apenas se `membership.name` estiver NULL/vazio
- Preenche na primeira vez (ao aceitar convite ou primeiro login)
- Depois não sobrescreve edições manuais do admin
- Se admin apagar o nome, volta a atualizar automaticamente

### 2. O que fazer com `Account.name` ao fazer login via Google?
**Decisão: B** - Atualizar apenas se `account.name` estiver vazio/NULL
- **IMPORTANTE**: `Account.name` sempre vem do Google, nunca de `membership.name`
- Preenche na primeira vez, depois não atualiza automaticamente
- Usuário tem controle sobre seu nome privado

### 3. O que mostrar na listagem de Accounts (admin)?
**Decisão: Mostrar `account.name`**
- **NOTA IMPORTANTE**: Este painel terá regras de acesso restritas no futuro
- Por enquanto, admin pode ver `account.name` (será restringido depois)
- Anotado no checklist para implementação futura

### 4. O que incluir no JWT Token?
**Decisão: A** - `membership.name` com fallback para `account.name` se NULL
- JWT contém nome no contexto do tenant atual
- Se `membership.name` for NULL, usa `account.name` como fallback
- **⚠️ REVISÃO**: Análise posterior descobriu que `name` não é usado do JWT em nenhum lugar
- **Decisão revisada**: Remover `name` do JWT completamente (ver `CHECKLIST_MEMBERSHIP_NAME.md` Fase 3.0)

### 5. Endpoint `/me` — o que retornar?
**Decisão: C** - Retornar ambos (`account_name` e `membership_name`)
- Frontend decide qual usar em cada contexto
- `account_name`: nome privado do usuário
- `membership_name`: nome na clínica (pode ser NULL)

### 6. Migração de dados existentes
**Decisão: A** - Copiar `account.name` → `membership.name` para todos os memberships ACTIVE
- Dados imediatamente disponíveis após migração
- Script de migração copia nome existente

### 7. Campo `name` no body do convite — aceitar ou não?
**Decisão: C** - Aceitar `name` e salvar em `membership.name` como placeholder
- Admin pode colocar nome inicial
- Será sobrescrito quando usuário aceitar convite (se `membership.name` estiver NULL)
- Útil para identificação antes do consentimento

### 8. Email de convite — qual nome usar?
**Decisão: A** - `membership.name` se existir, senão email
- Usa nome da clínica se disponível
- Fallback para email se `membership.name` for NULL

### 9. Auditoria (AuditLog) — qual nome registrar?
**Decisão: A** - `membership.name` com fallback para email se NULL
- Registra nome no contexto do tenant
- Se `membership.name` for NULL, usa email como identificador

---

## Resumo das Regras

### Account.name (PRIVADO)
- **Visibilidade**: Apenas o próprio usuário
- **Fonte**: Sempre do Google OAuth (nunca de `membership.name`)
- **Atualização**: Apenas se NULL/vazio no login
- **Uso**: Nome pessoal do usuário

### Membership.name (PÚBLICO)
- **Visibilidade**: Admins do tenant podem ver
- **Fonte**:
  - Pode ser preenchido no convite (placeholder)
  - Atualizado do Google ao aceitar convite (se NULL)
  - Pode ser editado manualmente por admin
- **Atualização automática**: Apenas se NULL/vazio
- **Uso**: Nome do usuário no contexto da clínica

### JWT Token
- **REVISÃO**: Análise descobriu que `name` não é usado do JWT
- **Decisão revisada**: Remover `name` do JWT (não é necessário)
- **Campos mínimos**: `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`
- **Contexto**: Dados sempre vêm do banco via endpoints (`/me`, `get_current_membership()`, etc)

### Endpoint `/me`
- Retorna: `account_name` e `membership_name` (ambos)
- Frontend decide qual usar

### Listagem de Accounts
- **ATUALMENTE**: Mostra `account.name` (admin pode ver)
- **FUTURO**: Regras de acesso restritas (anotado no checklist)

---

## Notas de Implementação

1. **Migração**: Script Alembic para adicionar campo `name` em `Membership` e copiar `account.name` para `membership.name` em memberships ACTIVE
2. **Validação**: Garantir que `Account.name` nunca seja atualizado a partir de `Membership.name`
3. **Privacidade**: Endpoints de listagem devem respeitar regras de visibilidade
4. **Futuro**: Implementar regras de acesso restritas no painel de Accounts
