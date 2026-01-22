# Padrões de Segurança e Validação Multi-Tenant

Este documento descreve os padrões de segurança implementados no sistema, com foco em isolamento multi-tenant e validação de acesso.

## Princípios Fundamentais

### 1. Isolamento Multi-Tenant
- **Nunca confiar em dados do cliente**: `tenant_id` nunca vem do body, querystring ou path parameters (exceto endpoints específicos de admin)
- **Sempre validar via JWT**: `tenant_id` é extraído do token JWT via `get_current_member()`
- **Filtrar todas as queries**: Todas as queries ao banco devem filtrar por `tenant_id` do member

### 2. Validação de Acesso
- **Dependency `get_current_member()`**: Valida que o usuário tem member ACTIVE no tenant do JWT
- **Verificação explícita**: Ao acessar recursos específicos, sempre verificar `resource.tenant_id == member.tenant_id`
- **HTTP 403 para acesso negado**: Retornar `403 Forbidden` quando tenant_id não corresponde

## Padrões de Implementação

### Endpoints que Acessam Recursos do Tenant

Todos os endpoints que acessam recursos (Job, File, ScheduleVersion, etc.) devem seguir este padrão:

```python
@router.get("/resource/{resource_id}")
def get_resource(
    resource_id: int,
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    # 1. Buscar recurso
    resource = session.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")

    # 2. Validar tenant_id
    if resource.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # 3. Retornar recurso
    return resource
```

### Endpoints de Listagem

Endpoints que listam recursos devem sempre filtrar por `tenant_id`:

```python
@router.get("/resource/list")
def list_resources(
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    # Query sempre filtra por tenant_id
    query = select(Resource).where(Resource.tenant_id == member.tenant_id)
    items = session.exec(query).all()
    return items
```

### Endpoints de Criação

Endpoints que criam recursos devem usar `member.tenant_id` (nunca aceitar do body):

```python
@router.post("/resource")
def create_resource(
    body: ResourceCreate,
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    # Usar tenant_id do member, nunca do body
    resource = Resource(
        tenant_id=member.tenant_id,  # ✅ Correto
        # ... outros campos do body
    )
    session.add(resource)
    session.commit()
    return resource
```

### Endpoints de Atualização

Endpoints que atualizam recursos devem validar `tenant_id` e não permitir alteração:

```python
@router.put("/resource/{resource_id}")
def update_resource(
    resource_id: int,
    body: ResourceUpdate,
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    resource = session.get(Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Recurso não encontrado")

    # Validar tenant_id
    if resource.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Atualizar campos (NUNCA permitir alterar tenant_id)
    resource.name = body.name  # ✅ Campos permitidos
    # resource.tenant_id = body.tenant_id  # ❌ NUNCA fazer isso

    session.add(resource)
    session.commit()
    return resource
```

## Dependencies de Segurança

### `get_current_member()`
- **O que faz**: Valida JWT, busca member ACTIVE para (account_id, tenant_id)
- **Quando usar**: Em todos os endpoints que acessam recursos do tenant
- **Retorna**: Objeto `member` ou levanta `HTTPException 401/403`

### `get_current_account()`
- **O que faz**: Valida JWT, busca Account por account_id
- **Quando usar**: Quando precisa apenas do Account (sem validação de tenant)
- **Exemplo**: `POST /tenant` (criação de tenant)

### `require_role(role: str)`
- **O que faz**: Factory que retorna dependency que valida role do member
- **Quando usar**: Endpoints que requerem role específica (ex: admin)
- **Exemplo**: `POST /tenant/{tenant_id}/invite` (requer admin)

## Endpoints Especiais

### Endpoints de Autenticação
Endpoints em `/auth/*` não validam tenant_id porque:
- Criam/validam Accounts (sem tenant_id)
- Gerenciam members (que já têm tenant_id)
- Emitem JWT com tenant_id
- **Convites**: `POST /tenant/{tenant_id}/invite` cria member PENDING com `account_id=NULL` e `email` preenchido (não cria Account)
- **Aceite**: `POST /auth/invites/{member_id}/accept` vincula Account ao member pelo email e sincroniza `member.email` se vazio ✅
- **Login**: `POST /auth/google` busca e vincula automaticamente members PENDING pelo email e sincroniza `member.email` se vazio ✅
- **Criação de member**: `POST /member` permite criar member com `email` e `name` públicos, sem `account_id` obrigatório ✅
- **Edição de member**: `PUT /member/{id}` permite editar `member.email` e `member.name` livremente (campos públicos) ✅
- **Privacidade**: `Account.email` e `Account.name` não são expostos em endpoints de tenant; apenas `member.email` e `member.name` são retornados ✅

### Endpoints Públicos
- `GET /health`: Não requer autenticação
- `POST /auth/google`: Não requer autenticação (cria autenticação)

### Endpoints Admin
Alguns endpoints requerem role ADMIN:
- `POST /tenant/{tenant_id}/invite`: Requer admin no tenant
- `POST /job/{job_id}/requeue`: Requer admin no tenant

## Checklist de Validação

Ao implementar um novo endpoint, verificar:

- [ ] Endpoint usa `get_current_member()` se acessa recursos do tenant?
- [ ] Queries filtram por `tenant_id` do member?
- [ ] Endpoints de criação usam `member.tenant_id` (não aceitam do body)?
- [ ] Endpoints de atualização validam `tenant_id` e não permitem alteração?
- [ ] Endpoints de leitura validam `tenant_id` antes de retornar?
- [ ] Retorna HTTP 403 quando `tenant_id` não corresponde?
- [ ] Retorna HTTP 404 quando recurso não existe (antes de validar tenant)?

## Exemplos de Implementação Correta

### ✅ Correto: GET /job/{job_id}
```python
@router.get("/job/{job_id}")
def get_job(
    job_id: int,
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    if job.tenant_id != member.tenant_id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return job
```

### ✅ Correto: GET /job/list
```python
@router.get("/job/list")
def list_jobs(
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    query = select(Job).where(Job.tenant_id == member.tenant_id)
    items = session.exec(query).all()
    return items
```

### ✅ Correto: POST /job/ping
```python
@router.post("/job/ping")
def create_ping_job(
    member: member = Depends(get_current_member),
    session: Session = Depends(get_session),
):
    job = Job(
        tenant_id=member.tenant_id,  # ✅ Do member, não do body
        job_type=JobType.PING,
        status=JobStatus.PENDING,
    )
    session.add(job)
    session.commit()
    return job
```

### ❌ Incorreto: Aceitar tenant_id do body
```python
@router.post("/job/ping")
def create_ping_job(
    body: JobCreate,  # ❌ body contém tenant_id
    session: Session = Depends(get_session),
):
    job = Job(
        tenant_id=body.tenant_id,  # ❌ NUNCA fazer isso
        # ...
    )
```

### ❌ Incorreto: Não validar tenant_id
```python
@router.get("/job/{job_id}")
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
):
    job = session.get(Job, job_id)
    return job  # ❌ Não valida tenant_id
```

## Auditoria

Eventos de segurança são registrados na tabela `audit_log`:
- `member_invited`: Convite criado
- `member_status_changed`: Status de member alterado
- `tenant_switched`: Usuário trocou de tenant

## Status Codes Padrão

- **200 OK**: Operação bem-sucedida
- **201 Created**: Recurso criado
- **400 Bad Request**: Dados inválidos
- **401 Unauthorized**: Token ausente/inválido
- **403 Forbidden**: Acesso negado (tenant_id não corresponde ou sem permissão)
- **404 Not Found**: Recurso não encontrado
- **409 Conflict**: Conflito (ex: member duplicado)
- **500 Internal Server Error**: Erro interno do servidor

## Notas Importantes

1. **Middleware não valida DB**: O middleware apenas extrai `tenant_id` do JWT para `request.state`. A validação real acontece em `get_current_member()` que consulta o banco.

2. **JWT contém apenas dados mínimos**: O token JWT contém apenas `sub` (account_id), `tenant_id`, `iat`, `exp`, `iss`. Dados como email, name, role são obtidos do banco via endpoints (`/me`, `get_current_member()`). Isso mantém o token menor e mais seguro.

3. **member é a fonte da verdade**: Role e status vêm do member, não do Account. Um Account pode ter múltiplos members (um por tenant).

4. **Convites pendentes**: `member.account_id` pode ser `NULL` para convites pendentes. O campo `email` identifica o convite até o usuário aceitar. Account é criado quando o usuário faz login/registro via Google OAuth pela primeira vez (sem precisar de convite). Ao aceitar um convite, o Account é vinculado ao member pelo email (se o Account já existir) ou criado se ainda não existir.

5. **Soft-delete em members**: members não são deletados, apenas marcados como REMOVED. Isso mantém histórico e permite auditoria.
