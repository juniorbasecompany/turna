# Padrões de Segurança e Validação Multi-Tenant

Este documento descreve os padrões de segurança **implementados** no sistema: isolamento multi-tenant e validação de acesso. O código da API está em `backend/` (ver `README.md` e `STACK.md`).

## Princípios

### Isolamento multi-tenant
- **Nunca confiar em dados do cliente**: `tenant_id` não vem do body, querystring ou path (exceto endpoints específicos de admin).
- **Sempre validar via JWT**: `tenant_id` é extraído do token via `get_current_member()`.
- **Filtrar todas as queries**: Todas as queries ao banco filtram por `tenant_id` do member.

### Validação de acesso
- **Dependency `get_current_member()`**: Valida que o usuário tem member ACTIVE no tenant do JWT.
- **Verificação explícita**: Ao acessar recurso específico, verificar `resource.tenant_id == member.tenant_id`.
- **HTTP 403**: Retornar `403 Forbidden` quando `tenant_id` não corresponde.

## Padrões de implementação

### Endpoints que acessam recursos
- Buscar recurso; se não existir → 404.
- Validar `resource.tenant_id == member.tenant_id`; se não → 403.
- Retornar recurso.

### Endpoints de listagem
- Sempre filtrar por `tenant_id` do member (ex.: `Resource.tenant_id == member.tenant_id`).

### Endpoints de criação
- Usar `member.tenant_id`; nunca aceitar `tenant_id` do body.

### Endpoints de atualização
- Validar `tenant_id` antes de atualizar; nunca permitir alterar `tenant_id`.

## Dependencies de segurança

- **`get_current_member()`**: Valida JWT, busca member ACTIVE para (account_id, tenant_id). Usar em todos os endpoints que acessam recursos do tenant. Retorna member ou levanta 401/403.
- **`get_current_account()`**: Valida JWT, busca Account. Usar quando não for necessário validar tenant (ex.: `POST /tenant`).
- **`require_role(role: str)`**: Dependency que valida role do member. Usar em endpoints que exigem role específica (ex.: admin).

## Endpoints por recurso

### Autenticação (`/auth/*`)
- Não validam tenant_id: criam/validam Account, gerenciam members, emitem JWT.
- Convites: `POST /tenant/{tenant_id}/invite` cria member PENDING com `account_id=NULL` e `email`.
- Aceite/login: vinculam Account ao member pelo email; sincronizam `member.email` se vazio.
- Criação/edição de member: `POST /member` e `PUT /member/{id}` usam `email` e `name` públicos.
- Privacidade: `Account.email` e `Account.name` não são expostos em endpoints de tenant; apenas `member.email` e `member.name`.
- Endpoints de Account (`/account/*`): admin-only; expõem dados privados; usar com cuidado.

### Públicos
- `GET /health`: sem autenticação.
- `POST /auth/google`: sem autenticação (cria autenticação).

### Admin (role ADMIN)
- Tenant: POST/GET/PUT/DELETE `/tenant`, `POST /tenant/{tenant_id}/invite`.
- Member: POST/GET/PUT/DELETE `/member`, `POST /member/{member_id}/invite`.
- Account: POST/GET/PUT/DELETE `/account`.
- Hospital: POST/PUT/DELETE `/hospital`.
- Job: `POST /job/{job_id}/requeue` (admin no tenant).

### Recursos do tenant (requerem member ativo)
- **Hospital**: `GET /hospital/list`, `GET /hospital/{id}` (leitura para todos).
- **File**: POST/GET/DELETE `/file/upload`, `/file/list`, `/file/{id}`, `/file/{id}/download`, `/file/{id}/thumbnail`.
- **Demand**: POST/GET/PUT/DELETE `/demand`, `POST /demand/{id}/publish`, `GET /demand/{id}/pdf`. Geração em lote: endpoint cria Job; worker atualiza Demand(s).
- **Escala (alias sobre Demand, id = demand_id)**: `GET /schedule/list`, `POST /schedule`, `GET /schedule/{id}`, `POST /schedule/{id}/publish`, `GET /schedule/{id}/pdf`, `DELETE /schedule/{id}`.
- **Job**: POST/GET `/job/ping`, `/job/extract`, `/job/list`, `/job/{id}`, `/job/{id}/stream`, POST/DELETE `/job/{id}/cancel`, `/job/{id}`.

## Checklist ao implementar novo endpoint

- [ ] Endpoint usa `get_current_member()` se acessa recursos do tenant?
- [ ] Queries filtram por `tenant_id` do member?
- [ ] Criação usa `member.tenant_id` (não aceita do body)?
- [ ] Atualização valida `tenant_id` e não permite alteração?
- [ ] Leitura valida `tenant_id` antes de retornar?
- [ ] Retorna 403 quando `tenant_id` não corresponde?
- [ ] Retorna 404 quando recurso não existe (antes de validar tenant)?

## Exemplos

### Correto: GET /job/{job_id}
Buscar job; se não existir → 404; se `job.tenant_id != member.tenant_id` → 403; retornar job.

### Correto: GET /job/list
`select(Job).where(Job.tenant_id == member.tenant_id)`.

### Correto: POST /job/ping
Criar Job com `tenant_id=member.tenant_id` (nunca do body).

### Incorreto
- Aceitar `tenant_id` do body em criação.
- Não validar `tenant_id` antes de retornar recurso.

## Auditoria

Eventos registrados em `audit_log`: `member_invited`, `member_status_changed`, `tenant_switched`.

## Status codes

- 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 500 Internal Server Error.

## Notas

1. **Middleware**: Apenas extrai `tenant_id` do JWT para `request.state`. Validação real em `get_current_member()` (consulta ao banco).
2. **JWT**: Contém apenas `sub`, `tenant_id`, `iat`, `exp`, `iss`. Email, name e role vêm do banco via endpoints.
3. **Member é a fonte da verdade**: Role e status vêm do member; um Account pode ter múltiplos members.
4. **Convites pendentes**: `member.account_id` pode ser NULL; `email` identifica o convite. Account é criado no primeiro login ou ao aceitar convite.
5. **Soft-delete em members**: members são marcados como REMOVED; não são deletados fisicamente (histórico e auditoria).
