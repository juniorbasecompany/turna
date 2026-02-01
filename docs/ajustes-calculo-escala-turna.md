# Ajustes no Cálculo da Escala para Alinhar com turna.py

**Fonte de verdade:** `backend/turna.py` (via `app.py`)

Este documento lista as modificações objetivas necessárias no processo de cálculo da escala (job `generate_schedule_job`) para obter o mesmo resultado que o `turna.py`.

---

## 1. Vacation (férias/folgas) — Prioridade alta

### Problema

- **turna.py** (profissionais.json): `vacation` usa **horas** `(hora_início, hora_fim)` em cada dia.
  - Ex.: `[[13, 17]]` = indisponível das 13h às 17h em todos os dias.
  - Ex.: `[[0, 24]]` = dia inteiro bloqueado.

- **Worker atual** (`_parse_vacation_for_solver`): converte `member.vacation` (ISO datetime) para **(dia_início, dia_fim)** do período.
  - Ex.: `(13, 17)` = dias 13 a 17 do período.

- **Solver** (`strategy/core.py`): `is_available` trata `vacation` como **(hora_início, hora_fim)** e compara com `(start, end)` das demandas em horas.

**Efeito:** O solver interpreta `(13, 17)` como 13h–17h em vez de dias 13–17, gerando alocações incorretas.

### Ajuste necessário

Tratar corretamente a vacation baseada em **datas** (member) no solver:

1. **Em `job.py` (`_load_pros_from_member_table`)**  
   Guardar vacation por datas em campo separado:
   - `vacation`: reservado para blocos horários `(hora_início, hora_fim)` (compatível com turna).
   - `vacation_days`: lista de `(dia_início, dia_fim)` relativos ao período (1 = primeiro dia).

2. **Em `strategy/greedy/solve.py`**  
   Para cada dia `day_num`:
   - Filtrar `pros_for_day`: remover profissionais cujo `day_num` esteja em `vacation_days`.
   - Usar `vacation` (blocos horários) só para quem não está em férias naquele dia.

3. **Compatibilidade com turna**  
   - turna usa apenas `vacation` em horas; `vacation_days` fica vazio.
   - Quando `vacation_days` estiver vazio, manter o comportamento atual (usar só `vacation`).

**Arquivos afetados:** `backend/app/worker/job.py`, `backend/strategy/greedy/solve.py`, `backend/strategy/core.py` (se necessário, para ler `vacation_days`).

---

## 2. Suporte a vacation em horas no Member (opcional)

### Contexto

Em turna, vacation é sempre em **horas**, por exemplo: `[[7, 12]]`, `[[0, 24]]`. Hoje o member aceita apenas intervalos em ISO datetime.

### Ajuste necessário (se quiser armazenar férias em horas)

- Definir um formato para vacation em horas no member (ex.: pares numéricos ou estrutura específica).
- No `_load_pros_from_member_table`, detectar o formato:
  - Se for ISO datetime → converter para `vacation_days` (e `vacation = []`).
  - Se for par numérico em `[0, 24]` → tratar como `vacation` em horas (e `vacation_days = []`).
- Garantir que o solver use `vacation` em horas quando existir, e `vacation_days` quando houver datas.

---

## 3. Formato de entrada para o solver

### Garantir equivalência com turna

O solver espera:

**Demandas (por demanda):**
- `day`: int (1..N)
- `start`: float (hora, ex.: 9.5)
- `end`: float (hora)
- `is_pediatric`: bool
- `id`: str (identificador)

**Profissionais (por pro):**
- `id`: str
- `name`: str
- `sequence`: int
- `can_peds`: bool
- `vacation`: `list[tuple[float, float]]` — blocos horários `(hora_início, hora_fim)`
- `vacation_days` (novo): `list[tuple[int, int]]` — blocos de dias `(dia_início, dia_fim)`

O job já preenche corretamente demandas e profissionais, exceto `vacation`/`vacation_days` conforme o item 1.

---

## 4. Resumo das alterações por arquivo

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/worker/job.py` | Em `_load_pros_from_member_table`: preencher `vacation_days` com o resultado de `_parse_vacation_for_solver` e manter `vacation = []` para vacation baseada em datas. |
| `backend/strategy/greedy/solve.py` | Ao montar `pros_for_day`, excluir profissionais cujo `day_num` esteja em `vacation_days`. Tratar `vacation_days` ausente como lista vazia (compatível com turna). |
| `backend/strategy/core.py` | Sem mudança; `is_available` continua usando apenas `vacation` em horas. |

---

## 5. Parâmetros do solver

O job já chama `solve_greedy` com os mesmos parâmetros usados em turna:

- `unassigned_penalty=1000`
- `ped_unassigned_extra_penalty=1000`
- `base_shift=0`

Não há ajuste necessário nesses valores.

---

## 6. Validação

Para validar:

1. Carregar demandas e profissionais equivalentes a `demandas.json` e `profissionais.json` no banco.
2. Rodar `py turna.py` e registrar o resultado (alocações por dia, custo total).
3. Rodar o cálculo via API (job de escala) para o mesmo período e mesmas demandas/profissionais.
4. Comparar as alocações dia a dia e o custo total.

Os resultados devem ser idênticos após aplicar os ajustes acima.
