# Plano de refatoração: tenant.label, member.label e hospital.label

Este documento descreve os passos necessários para implementar a refatoração de forma gradativa, permitindo testar e validar cada fase. Alinhado a `CHECKLIST.md`, `DIRECTIVES.md`, `SECURITY.md` e `STACK.md`.

---

## Visão geral

| Objetivo | Descrição |
|----------|-----------|
| 1 | Renomear `tenant.slug` para `tenant.label` |
| 2 | Tornar `tenant.label` opcional (nullable) |
| 3 | Avaliar necessidade de `default` em label; preferir vazio quando possível |
| 4 | Criar `member.label` e `hospital.label` (opcionais, sem duplicação no tenant) |
| 5 | Adicionar campo label nos painéis de edição (tenant, member, hospital) |
| 6 | Em demandas e escalas: usar label com fallback para name |
| 7 | Adicionar coluna label nos relatórios respectivos |

---

## Fase 0: Preparação e migrações (backend)

**Objetivo**: Schema e modelos prontos no backend; migrações aplicadas.

### 0.1 Migração: tornar slug opcional

- **Arquivo**: `0134vw901240_make_tenant_slug_optional.py` (já existe)
- **Ação**: Executar `alembic upgrade head`
- **Validação**: `tenant.slug` aceita NULL no banco

### 0.2 Migração: slug → label + member/hospital.label

- **Arquivo**: `0134uv901240_tenant_slug_to_label_member_hospital_label.py` (já existe)
- **Ação**: Revisar e executar a migração
- **Resultado esperado**:
  - `tenant`: coluna `label` (nullable), índice único parcial `WHERE label IS NOT NULL`
  - `member`: coluna `label` (nullable), `UNIQUE(tenant_id, label) WHERE label IS NOT NULL`
  - `hospital`: coluna `label` (nullable), `UNIQUE(tenant_id, label) WHERE label IS NOT NULL`

### 0.3 Atualizar modelos Python

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/model/tenant.py` | `slug` → `label: str \| None` com `Field(nullable=True)`, remover unique/index do slug, adicionar `UniqueConstraint` parcial via `__table_args__` se necessário |
| `backend/app/model/member.py` | Adicionar `label: str \| None = Field(default=None, nullable=True)` e constraint único (tenant_id, label) |
| `backend/app/model/hospital.py` | Adicionar `label: str \| None = Field(default=None, nullable=True)` e constraint único (tenant_id, label) |

### 0.4 Default no label

- **Tenant**: Na criação automática de clínica (`POST /auth/google/create-tenant`), hoje gera `slug = f"clinica-{timestamp}"`. Com label opcional, pode deixar `label=None`; não é obrigatório preencher.
- **Tenant "default"** (auth.py `_get_or_create_default_tenant`): Este tenant especial usa `slug == "default"` para lookup. Após renomear para `label`, manter `label="default"` neste caso específico para compatibilidade. Para demais tenants, label pode ficar vazio.

**Validação**: Criação de tenant sem label não deve falhar; relatórios e telas devem tratar `label` vazio.

---

## Fase 1: API backend – tenant

### 1.1 Schemas e endpoints de tenant

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | `TenantCreate`, `TenantUpdate`, `TenantResponse`, `TenantListResponse`: trocar `slug` por `label` (opcional) |
| `backend/app/api/route.py` | Validação: ao criar/atualizar, se `label` informado, verificar unicidade; permitir `label` vazio/NULL |
| `backend/app/api/route.py` | Relatório: `rows = [(t.name, t.label or "")]` |

### 1.2 Auth e tenant service

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/auth.py` | `TenantOption`, `InviteOption`: `slug` → `label` |
| `backend/app/api/auth.py` | `_get_or_create_default_tenant`: `Tenant.slug == "default"` → `Tenant.label == "default"`; criar com `label="default"` |
| `backend/app/api/auth.py` | `create_tenant` (create-tenant): passar `label=None` ou `label` se gerado; remover geração obrigatória de slug |
| `backend/app/services/tenant_service.py` | Parâmetro `slug` → `label` (opcional) |

### 1.3 Testes

- Criar tenant com label vazio
- Criar tenant com label preenchido; verificar unicidade
- Relatório de clínicas inclui coluna label (vazia ou preenchida)
- Select-tenant e auth retornam `label` em vez de `slug`

---

## Fase 2: API backend – member e hospital

### 2.1 Schemas member

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | `MemberCreate`, `MemberUpdate`, `MemberResponse`: adicionar `label: str \| None` |
| `backend/app/api/route.py` | Validação: ao criar/atualizar, se `label` informado, verificar unicidade em `(tenant_id, label)`; permitir vazio |

### 2.2 Schemas hospital

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | `HospitalCreate`, `HospitalUpdate`, `HospitalResponse`: adicionar `label: str \| None` |
| `backend/app/api/route.py` | Validação: ao criar/atualizar, se `label` informado, verificar unicidade em `(tenant_id, label)`; permitir vazio |

### 2.3 Relatórios member e hospital

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/report/pdf_list.py` | `render_member_list_pdf`: adicionar coluna "Rótulo" (label); `headers` e `data` com nova coluna |
| `backend/app/report/pdf_list.py` | `render_hospital_list_pdf`: adicionar coluna "Rótulo" (label); `headers` e `data` com nova coluna |
| `backend/app/api/route.py` | Endpoints `/member/report` e `/hospital/report`: incluir `label` nos `rows` passados ao PDF |

---

## Fase 3: Demandas e escalas – label com fallback para name

### 3.1 Relatório de demandas (PDF)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/report/pdf_demand.py` | `member_dict[m.id]`: usar `(m.label or m.name or "").strip() or f"Member {m.id}"` |
| `backend/app/report/pdf_demand.py` | `hospital_dict[h.id]`: usar `h.label or h.name or f"Hospital {h.id}"` |

### 3.2 Relatório de escalas (PDF)

- Mesmo módulo `pdf_demand.py`, grupo `group_by="member"`: já usa `member_dict`; aplicar o mesmo fallback.
- Linhas por hospital: já usa `hospital_dict`; aplicar o mesmo fallback.

### 3.3 Worker (GENERATE_SCHEDULE)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | `LOAD_PROFESSIONALS`: `name = (m.label or m.name or pro_id).strip()` |

### 3.4 API de schedule

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/schedule.py` | Onde usar `hospital.name`: trocar para `(hospital.label or hospital.name) if hospital else "Geral"` |

### 3.5 Outros usos

- Verificar rotas de demand, file e demais referências a `member.name` ou `hospital.name` em contextos de exibição; aplicar `label or name`.

---

## Fase 4: Frontend – painéis e tipos

### 4.1 Tipos e API

| Arquivo | Alteração |
|---------|-----------|
| `frontend/types/api.ts` | `TenantResponse`, `TenantCreateRequest`, `TenantUpdateRequest`: `slug` → `label` (opcional) |
| `frontend/types/api.ts` | `TenantOption`, `InviteOption`: `slug` → `label` |
| `frontend/types/api.ts` | `MemberResponse`, `MemberCreateRequest`, `MemberUpdateRequest`: adicionar `label?: string \| null` |
| `frontend/types/api.ts` | `HospitalResponse`, `HospitalCreateRequest`, `HospitalUpdateRequest`: adicionar `label?: string \| null` |

### 4.2 Painel de Clínicas (tenant)

| Arquivo | Alteração |
|---------|-----------|
| `frontend/app/(protected)/tenant/page.tsx` | FormData e mapeamentos: `slug` → `label` |
| | Campo "Rótulo": tornar opcional; remover `required`; remover auto-conversão para minúsculas/hífens (label é display, não identificador técnico) |
| | Validação: remover obrigatoriedade de label |
| | Card: exibir `tenant.label` (ou vazio) em vez de `tenant.slug` |
| | `select-tenant`: usar `label` em vez de `slug` |

### 4.3 Painel de Associados (member)

| Arquivo | Alteração |
|---------|-----------|
| `frontend/app/(protected)/member/page.tsx` | Adicionar `label` em `MemberFormData` |
| | Adicionar campo "Rótulo" no formulário (opcional) |
| | Mapear `label` em `mapEntityToFormData`, `mapFormDataToCreateRequest`, `mapFormDataToUpdateRequest` |
| | Card: exibir label (se houver) além do nome |

### 4.4 Painel de Hospitais (hospital)

| Arquivo | Alteração |
|---------|-----------|
| `frontend/app/(protected)/hospital/page.tsx` | Adicionar `label` em `HospitalFormData` |
| | Adicionar campo "Rótulo" no formulário (opcional) |
| | Mapear `label` nos request/response |
| | Card: exibir label (se houver) além do nome |

### 4.5 Select-tenant

| Arquivo | Alteração |
|---------|-----------|
| `frontend/app/(auth)/select-tenant/page.tsx` | Trocar `slug` por `label` em `TenantOption`/`InviteOption`; exibir label quando existir, senão nome |

---

## Fase 5: Validação final

### Checklist

- [x] Migrações aplicadas; rollback testado
- [x] Tenant: criar/editar com label vazio e preenchido; unicidade de label
- [x] Member: criar/editar com label; unicidade por tenant
- [x] Hospital: criar/editar com label; unicidade por tenant
- [x] Relatórios PDF: tenant, member, hospital com coluna label
- [x] Demandas e escalas: exibição usa label com fallback para name
- [x] Frontend: todos os painéis mostram e editam label
- [x] Select-tenant e auth funcionam com label
- [ ] Padrões de segurança (SECURITY.md): validação de tenant_id, sem vazamento entre tenants
- [ ] Docker Compose e migrações Alembic OK

---

## Ordem sugerida de execução

1. **Fase 0** – Migrações e modelos
2. **Fase 1** – API tenant (slug → label)
3. **Fase 4.1 + 4.2 + 4.5** – Frontend tenant e select-tenant (para não quebrar a UI)
4. **Fase 2** – API member e hospital
5. **Fase 4.3 + 4.4** – Frontend member e hospital
6. **Fase 3** – Demandas, escalas e worker
7. **Fase 5** – Validação final

---

## Notas de compatibilidade

- **TenantOption/InviteOption**: Após a troca, clients antigos que esperam `slug` deixarão de funcionar. Se houver integrações externas, considerar manter `slug` como alias depreciado temporariamente ou anunciar breaking change.
- **Relatório de clínicas**: Hoje usa "Nome" e "Rótulo" (slug). Com a refatoração, "Rótulo" passa a ser `tenant.label` (pode ser vazio).
- **Default tenant**: O tenant criado por `_get_or_create_default_tenant` deve manter `label="default"` para o lookup continuar funcionando. Para novos tenants criados pelo usuário, `label` pode ser vazio.
