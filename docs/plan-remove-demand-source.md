# Plano: Remoção do campo demand.source

Objetivo: remover o campo `source` da tabela `demand`, que é redundante com colunas existentes e não é utilizado em lógica de negócio.

---

## Etapa 1: Remover dependências do campo demand.source

Objetivo: parar de ler, gravar e propagar `source`. A coluna permanece no banco; validamos que o sistema funciona sem utilizá-la.

### 1.1 Backend – API (route.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | **DemandCreate** (linha 2762): remover campo `source: dict \| None = None` |
| `backend/app/api/route.py` | **DemandUpdate** (linha 2810): remover campo `source: dict \| None = None` |
| `backend/app/api/route.py` | **DemandResponse** (linha 2853): remover campo `source: dict \| None` |
| `backend/app/api/route.py` | **create_demand** (linha 2918): remover `source=body.source` da criação do `Demand` |
| `backend/app/api/route.py` | **update_demand** (linhas 3183-3184): remover bloco `if body.source is not None: demand.source = body.source` |

### 1.2 Backend – Worker (job.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | **_demands_from_database** (linha 479): trocar `"source": d.source` por `"source": {}` |
| `backend/app/worker/job.py` | **_extract_allocations** (linha 304): trocar `"source": demand.get("source", {})` por `"source": {}` |
| `backend/app/worker/job.py` | **_demands_from_extract_result** (linha 362): trocar `"source": d.get("source")` por `"source": {}` |
| `backend/app/worker/job.py` | **Docstring** (linha 222): remover menção a `"source": dict` do retorno de _extract_allocations (opcional) |

### 1.3 Backend – Schedule (schedule.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/schedule.py` | Linha 283: trocar `"source": result_data.get("source", {})` por `"source": {}` |

### 1.4 Backend – Schema de extração (demand/schema.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/demand/schema.py` | **validate_and_normalize_result** (linha 252): trocar `"source": d.get("source") if isinstance(d.get("source"), dict) else {}` por `"source": {}` |
| `backend/demand/schema.py` | **extract_id** (linhas 181-188): manter por enquanto (usa `source.raw`; com `source={}` retorna `None` sem erro). Opcional: simplificar a docstring. |

### 1.5 Backend – Prompts (opcional na Etapa 1)

| Arquivo | Alteração |
|---------|-----------|
| `backend/demand/prompt.py` | Linha 33: remover `source (objeto livre; inclua page e qualquer raw útil)` da lista de campos |
| `backend/app/services/hospital_service.py` | Linha 38: idem no prompt padrão |

### 1.6 Frontend

| Arquivo | Alteração |
|---------|-----------|
| `frontend/types/api.ts` | **DemandResponse** (linha 277): remover `source: Record<string, unknown> \| null` |
| `frontend/types/api.ts` | **DemandCreateRequest** (linha 300): remover `source?: Record<string, unknown> \| null` |
| `frontend/types/api.ts` | **DemandUpdateRequest** (linha 316): remover `source?: Record<string, unknown> \| null` |
| `frontend/app/(protected)/demand/page.tsx` | **DemandFormData** (linha 44): remover `source: Record<string, unknown> \| null` |
| `frontend/app/(protected)/demand/page.tsx` | **initialFormData** (linha 115): remover `source: null` |
| `frontend/app/(protected)/demand/page.tsx` | **mapEntityToFormData** (linha 133): remover `source: demand.source` |
| `frontend/app/(protected)/demand/page.tsx` | **mapFormDataToCreateRequest** (linha 154): remover `source: formData.source` |
| `frontend/app/(protected)/demand/page.tsx` | **mapFormDataToUpdateRequest** (linha 175): remover `source: formData.source` |

### 1.7 Testes e validação

- [ ] Executar testes automatizados (se houver)
- [ ] Criar demanda via API – deve funcionar sem `source`
- [ ] Atualizar demanda via API – deve funcionar sem `source`
- [ ] Gerar escala a partir de demandas (from_demands) – deve funcionar
- [ ] Gerar escala a partir de extração (from_extract) – deve funcionar
- [ ] Gerar PDF da escala – deve funcionar
- [ ] Frontend: criar/editar demanda – deve funcionar sem erros

---

## Etapa 2: Remoção física e eliminação de vestígios

Objetivo: remover a coluna do banco, o campo do modelo e **eliminar qualquer referência a `source` no código** – nenhum vestígio deve permanecer.

### 2.1 Modelo (demand.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/model/demand.py` | Remover `source: Optional[dict] = Field(default=None, sa_column=Column(JSON))` |

### 2.2 Worker (job.py)

Remover a chave `"source"` dos dicts – não incluir mais essa chave.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | **_extract_allocations** (linha ~303): remover a linha `"source": {},` do dict `allocation` |
| `backend/app/worker/job.py` | **_demands_from_extract_result** (linha ~361): remover a linha `"source": {},` do dict de saída |
| `backend/app/worker/job.py` | **_demands_from_database** (linha ~478): remover a linha `"source": {},` do dict de saída |

### 2.3 Schedule (schedule.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/schedule.py` | Remover a linha `"source": {},` do `demand_data` (~linha 283) |

### 2.4 Schema de extração (demand/schema.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/demand/schema.py` | **extract_id**: remover o bloco que usa `source/raw` (linhas 181-188); remover docstring/comentário que menciona source; a função passa a usar apenas os campos explícitos de ID |
| `backend/demand/schema.py` | **validate_and_normalize_result**: remover `"source": {},` do dict `dd` (~linha 252) |

### 2.5 Migração Alembic

Criar nova migração para remover a coluna:

```python
# alembic/versions/XXXX_remove_demand_source_column.py
"""remove demand.source column

Revision ID: XXXX
Revises: 0129mn901235_add_member_id_to_demand
Create Date: ...

"""
def upgrade() -> None:
    op.drop_column("demand", "source")

def downgrade() -> None:
    op.add_column(
        "demand",
        sa.Column("source", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
```

### 2.6 Verificações finais

- [ ] Rodar migração em ambiente de desenvolvimento
- [ ] Rodar migração em ambiente de staging (se houver)
- [ ] Buscar por `source` no código (ex.: `rg -i "source" backend/ frontend/` excluindo package-lock, node_modules, etc.) – resultado deve estar vazio para arquivos de código
- [ ] Rodar testes end-to-end

---

## Ordem de execução sugerida

1. Etapa 1.1 a 1.4 (backend)
2. Etapa 1.6 (frontend)
3. Etapa 1.5 (prompts – opcional)
4. Etapa 1.7 (testes)
5. Se tudo ok: Etapa 2.1 a 2.5 (código primeiro), depois 2.6 (validação)

---

## Rollback

- **Etapa 1**: reverter os commits; nenhuma alteração de banco.
- **Etapa 2**: rodar `downgrade` da migração para recriar a coluna `source` (valores serão perdidos).
