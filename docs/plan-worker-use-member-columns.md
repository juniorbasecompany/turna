# Plano: Migrar worker para usar colunas diretas de member

Objetivo: alterar o worker de geração de escala para usar diretamente as colunas `member.can_peds`, `member.sequence` e `member.vacation`, em vez de ler do campo JSON `member.attribute`.

---

## Contexto

Atualmente, o worker (`backend/app/worker/job.py`) carrega profissionais para o cálculo da escala usando o campo JSON `member.attribute`:

```python
attr = m.attribute or {}
pros.append({
    "sequence": int(attr.get("sequence", 0)),
    "can_peds": bool(attr.get("can_peds", False)),
    "vacation": attr.get("vacation", []),
    ...
})
```

Com a refatoração do modelo Member (ver `plan-member-refactor.md`), as colunas `can_peds`, `sequence` e `vacation` já existem diretamente na tabela `member`. O worker deve passar a usá-las.

---

## Diferença de formato: vacation

| Fonte | Formato | Exemplo |
|-------|---------|---------|
| `member.attribute.vacation` (antigo) | Dias inteiros relativos | `[[1, 5], [10, 15]]` |
| `member.vacation` (coluna) | ISO datetime strings | `[["2025-01-01T00:00:00Z", "2025-01-15T23:59:59Z"]]` |

O solver espera dias inteiros relativos ao período da escala. É necessário converter o formato ISO para dias inteiros.

---

## Etapa 1: Criar função auxiliar para converter vacation

Objetivo: converter vacation de ISO datetime strings para dias inteiros relativos ao período da escala.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | Criar função `_parse_vacation_for_solver(vacation_iso: list[list[str]], period_start_date: date) -> list[tuple[int, int]]` que converte cada par `[datetime_iso_início, datetime_iso_fim]` para `(dia_início, dia_fim)` relativos ao `period_start_date`. |

Implementação sugerida:

```python
from datetime import date, datetime

def _parse_vacation_for_solver(
    vacation_iso: list[list[str]],
    period_start_date: date,
) -> list[tuple[int, int]]:
    """
    Converte vacation de ISO datetime strings para dias inteiros relativos ao período.

    Args:
        vacation_iso: Lista de pares [início, fim] em ISO datetime (ex.: "2025-01-01T00:00:00Z")
        period_start_date: Data de início do período da escala

    Returns:
        Lista de tuplas (dia_início, dia_fim) com dias inteiros (1 = primeiro dia do período)
    """
    result: list[tuple[int, int]] = []
    for pair in vacation_iso or []:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        try:
            start_dt = datetime.fromisoformat(str(pair[0]).replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(str(pair[1]).replace("Z", "+00:00"))
            start_day = (start_dt.date() - period_start_date).days + 1
            end_day = (end_dt.date() - period_start_date).days + 1
            # Incluir apenas se houver interseção com o período (dia >= 1)
            if end_day >= 1:
                result.append((max(1, start_day), end_day))
        except (ValueError, TypeError, AttributeError):
            continue
    return result
```

---

## Etapa 2: Simplificar ou remover `_validate_pro_attribute`

Objetivo: a validação não é mais necessária porque as colunas diretas têm defaults garantidos pelo banco.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | Remover a função `_validate_pro_attribute` (linhas 123–142) ou mantê-la apenas para logs de debug. |

Justificativa:
- `can_peds` → `BOOLEAN NOT NULL DEFAULT FALSE`
- `sequence` → `INTEGER NOT NULL DEFAULT 0`
- `vacation` → `JSON NOT NULL DEFAULT '[]'`

O banco garante valores válidos; não há mais risco de `attribute` com estrutura inválida.

---

## Etapa 3: Alterar `_load_pros_from_member_table`

Objetivo: usar diretamente as colunas `m.can_peds`, `m.sequence`, `m.vacation`.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | Função `_load_pros_from_member_table`: substituir leitura de `attr = m.attribute or {}` por leitura direta das colunas. |

### Código atual (linhas 145–195):

```python
def _load_pros_from_member_table(session: Session, tenant_id: int) -> list[dict]:
    ...
    for m in rows:
        attr = m.attribute or {}
        if not _validate_pro_attribute(attr):
            skipped += 1
            continue
        vacation_raw = attr.get("vacation", [])
        vacation = [tuple(int(x) for x in v) for v in vacation_raw]
        pros.append({
            "sequence": int(attr.get("sequence", 0)),
            "can_peds": bool(attr.get("can_peds", False)),
            "vacation": vacation,
            ...
        })
```

### Código novo:

```python
def _load_pros_from_member_table(
    session: Session,
    tenant_id: int,
    period_start_date: date | None = None,
) -> list[dict]:
    """
    Carrega profissionais da tabela member para o tenant.
    Usa diretamente as colunas can_peds, sequence, vacation do model Member.

    Args:
        session: Sessão do banco
        tenant_id: ID do tenant
        period_start_date: Data de início do período (para converter vacation para dias relativos).
                           Se None, vacation será lista vazia.
    """
    logger.info(f"[LOAD_PROFESSIONALS] Carregando profissionais do tenant_id={tenant_id}")
    rows = session.exec(
        select(Member)
        .where(
            Member.tenant_id == tenant_id,
            Member.status == MemberStatus.ACTIVE,
        )
    ).all()

    pros: list[dict] = []
    for m in rows:
        pro_id = str(m.id)
        name = (m.name or pro_id).strip()

        # Converter vacation de ISO para dias inteiros
        if period_start_date is not None:
            vacation = _parse_vacation_for_solver(m.vacation, period_start_date)
        else:
            vacation = []

        pros.append({
            "id": pro_id,
            "name": name,
            "sequence": m.sequence,       # ← coluna direta
            "can_peds": m.can_peds,       # ← coluna direta
            "vacation": vacation,          # ← coluna direta (convertida)
            "member_db_id": m.id,
        })

    pros.sort(key=lambda p: p["sequence"])
    logger.info(f"[LOAD_PROFESSIONALS] {len(pros)} profissionais carregados")
    return pros
```

---

## Etapa 4: Atualizar chamadas de `_load_pros_from_member_table`

Objetivo: passar `period_start_date` nas chamadas existentes.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | Na função `generate_schedule_job`, reorganizar para obter `period_start_at` **antes** de carregar profissionais, e então passar `period_start_date`. |

**Implementado**: O código foi reorganizado para:
1. Primeiro parsear `period_start_at` e `period_end_at` do `input_data`
2. Obter o tenant e seu timezone
3. Calcular `period_start_date = period_start_at.astimezone(tenant_tz).date()`
4. Então chamar `_load_pros_from_member_table(session, job.tenant_id, period_start_date)`

Isso removeu código duplicado de parsing de datas nos blocos `from_demands` e `from_extract`.

---

## Resumo das alterações

| Arquivo | Função/Linha | Alteração |
|---------|--------------|-----------|
| `backend/app/worker/job.py` | Nova função | Criar `_parse_vacation_for_solver` |
| `backend/app/worker/job.py` | `_validate_pro_attribute` (123–142) | Remover |
| `backend/app/worker/job.py` | `_load_pros_from_member_table` (145–195) | Usar colunas diretas; adicionar parâmetro `period_start_date` |
| `backend/app/worker/job.py` | `generate_schedule_job` (~528, ~532) | Passar `period_start_date` ao chamar `_load_pros_from_member_table` |

---

## Checklist de validação

- [x] Função `_parse_vacation_for_solver` criada e testada com diferentes formatos de entrada.
- [x] `_validate_pro_attribute` removida.
- [x] `_load_pros_from_member_table` usa `m.can_peds`, `m.sequence`, `m.vacation`.
- [x] Chamadas de `_load_pros_from_member_table` passam `period_start_date`.
- [ ] Gerar escala com profissionais que possuem `vacation` preenchido; verificar que férias aparecem corretamente no resultado.
- [ ] Gerar escala com profissionais sem vacation (lista vazia); verificar que não há erro.
- [ ] Verificar que a ordenação por `sequence` continua funcionando.
- [x] Campo `member.attribute` pode ser ignorado (não precisa remover ainda; mantém compatibilidade retroativa).

---

## Observações

1. **Retrocompatibilidade**: o campo `member.attribute` continuará existindo no banco, mas não será mais lido pelo worker. Dados antigos em `attribute` serão ignorados.

2. **Migração de dados**: se houver dados em `attribute` que precisam ser migrados para as colunas diretas, criar script de migração separado (fora do escopo deste plano).

3. **Dependência**: este plano assume que a migração `0132rs901238_add_member_can_peds_sequence_vacation.py` já foi executada e as colunas existem no banco.
