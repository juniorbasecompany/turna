# Plano: Fragmentação de Resultado em Registros Individuais de Schedule

## Contexto Atual

Atualmente, quando uma escala é gerada, o resultado completo é armazenado em um único registro na tabela `schedule` (modelo `ScheduleVersion`), no campo `result_data`. A estrutura atual é:

```json
{
  "allocation_mode": "greedy",
  "days": 30,
  "total_cost": 1000,
  "per_day": [
    {
      "day_number": 1,
      "pros_for_day": [
        {"id": "B", "name": "Joaquim", "can_peds": true, "vacation": [], ...}
      ],
      "assigned_demands_by_pro": {
        "B": [
          {
            "id": "B",
            "day": 1,
            "start": 6,
            "end": 11,
            "is_pediatric": false,
            "source": {...}
          }
        ]
      },
      "demands_day": [...],
      "assigned_pids": [...]
    }
  ]
}
```

## Objetivo

Transformar cada alocação individual (profissional + demanda) em um registro separado na tabela `schedule`, onde cada registro terá em `result_data` um objeto JSON representando uma única alocação, no formato:

```json
{
  "professional": "Joaquim",
  "id": "B",
  "day": 1,
  "start": 6,
  "end": 11,
  "is_pediatric": false,
  "source": {
    "id": "B",
    "start": 6,
    "end": 11,
    "is_pediatric": false
  }
}
```

## Análise da Estrutura Atual

### Localização do Código Principal
- **Arquivo**: `backend/app/worker/job.py`
- **Função**: `generate_schedule_job()` (linha ~292)
- **Ponto de modificação**: Após a linha 443, onde `solve_greedy()` retorna `per_day` e `total_cost`

### Estrutura de Dados do Solver
O solver retorna `per_day`, que é uma lista onde cada item contém:
- `day_number`: número do dia (1..N)
- `pros_for_day`: lista de profissionais disponíveis no dia (contém `id`, `name`, `can_peds`, `vacation`, etc.)
- `assigned_demands_by_pro`: dicionário `{prof_id: [lista_de_demandas_alocadas]}`
- `demands_day`: todas as demandas do dia
- `assigned_pids`: lista paralela indicando qual profissional foi alocado para cada demanda

### Dados Necessários para Cada Registro
Para criar cada registro individual, precisamos:
1. **Nome do profissional**: obtido de `pros_for_day` (campo `name` ou `id` como fallback)
2. **Dados da demanda**: obtidos de `assigned_demands_by_pro[prof_id]`
3. **Dia**: obtido de `day_number`
4. **Metadados**: `allocation_mode`, `total_cost`, etc. (podem ser mantidos no primeiro registro ou distribuídos)

## Plano de Implementação

### Fase 1: Análise e Preparação

#### 1.1 Mapear Estrutura de Transformação
- [ ] Documentar exatamente como extrair cada alocação de `per_day`
- [ ] Definir formato exato do JSON em `result_data` de cada registro
- [ ] Identificar se precisamos manter algum registro "mestre" com metadados

#### 1.2 Verificar Dependências
- [ ] Verificar onde `ScheduleVersion.result_data` é lido/consumido
- [ ] Identificar impactos em:
  - `backend/app/api/schedule.py` (função `_day_schedules_from_result`)
  - Frontend (se houver consumo direto)
  - Geração de PDF
  - Outras APIs que consultam schedule

### Fase 2: Modificação do Modelo (se necessário)

#### 2.1 Avaliar Necessidade de Campos Adicionais
- [ ] Verificar se precisamos de campos para relacionar registros fragmentados
  - Exemplo: `parent_schedule_id` ou `schedule_group_id`
  - Exemplo: `sequence_number` para ordenação
- [ ] Decidir se mantemos um registro "mestre" com metadados gerais

#### 2.2 Migração de Banco de Dados
- [ ] Criar migration Alembic se necessário (campos adicionais)
- [ ] Planejar estratégia de migração de dados existentes (se houver)

### Fase 3: Modificação da Lógica de Gravação

#### 3.1 Função de Transformação
Criar função auxiliar para transformar `per_day` em lista de objetos individuais:

```python
def _extract_individual_allocations(
    per_day: list[dict],
    pros_by_sequence: list[dict]
) -> list[dict]:
    """
    Extrai alocações individuais do resultado do solver.
    
    Retorna lista de dicts, cada um representando uma alocação:
    {
        "professional": str,  # nome do profissional
        "id": str,            # ID da demanda
        "day": int,           # dia (1..N)
        "start": float,       # hora início
        "end": float,         # hora fim
        "is_pediatric": bool,
        "source": dict        # dados originais da demanda
    }
    """
    allocations = []
    
    for day_item in per_day:
        day_number = day_item.get("day_number", 0)
        pros_for_day = day_item.get("pros_for_day", [])
        assigned_demands_by_pro = day_item.get("assigned_demands_by_pro", {})
        
        # Criar mapa profissional_id -> nome
        pro_id_to_name = {}
        for pro in pros_for_day:
            pro_id = pro.get("id")
            pro_name = pro.get("name") or pro_id  # fallback para id se name ausente
            if pro_id:
                pro_id_to_name[pro_id] = pro_name
        
        # Iterar sobre alocações por profissional
        for pro_id, demands in assigned_demands_by_pro.items():
            professional_name = pro_id_to_name.get(pro_id, pro_id)
            
            for demand in demands:
                allocation = {
                    "professional": professional_name,
                    "id": demand.get("id"),
                    "day": day_number,
                    "start": demand.get("start"),
                    "end": demand.get("end"),
                    "is_pediatric": demand.get("is_pediatric", False),
                    "source": demand.get("source", {})
                }
                allocations.append(allocation)
    
    return allocations
```

#### 3.2 Modificação em `generate_schedule_job()`
- [ ] Após obter `per_day` do solver (linha ~443)
- [ ] Chamar função de transformação para extrair alocações individuais
- [ ] Em vez de gravar um único `sv.result_data`, criar múltiplos registros `ScheduleVersion`:
  ```python
  # Criar registros individuais
  schedule_records = []
  for allocation in individual_allocations:
      sv_item = ScheduleVersion(
          tenant_id=sv.tenant_id,
          name=f"{sv.name} - {allocation['professional']} - Dia {allocation['day']}",
          period_start_at=sv.period_start_at,
          period_end_at=sv.period_end_at,
          status=ScheduleStatus.DRAFT,
          version_number=sv.version_number,
          job_id=job.id,
          result_data=allocation,  # objeto individual
          generated_at=now,
          updated_at=now,
      )
      schedule_records.append(sv_item)
  
  # Gravar todos os registros
  session.add_all(schedule_records)
  ```

#### 3.3 Decisão: Registro Mestre
- [ ] Decidir se mantemos o registro original `sv` com metadados:
  - Opção A: Manter `sv` com metadados (`total_cost`, `allocation_mode`, etc.) e criar registros filhos
  - Opção B: Deletar `sv` original e criar apenas registros individuais
  - Opção C: Criar um novo registro "mestre" com metadados e referenciar nos filhos

### Fase 4: Atualização de Código Consumidor

#### 4.1 API de Leitura (`backend/app/api/schedule.py`)
- [ ] Modificar `_day_schedules_from_result()` para:
  - Buscar múltiplos registros relacionados
  - Agrupar por dia/profissional conforme necessário
  - Reconstruir estrutura esperada pelo gerador de PDF

#### 4.2 Endpoints de API
- [ ] Verificar endpoints que retornam `ScheduleVersion`:
  - `GET /schedule/{id}` - pode precisar retornar lista ou grupo
  - `GET /schedule` - listagem pode precisar agrupar
- [ ] Atualizar response models se necessário

#### 4.3 Frontend
- [ ] Verificar consumo de `result_data` no frontend
- [ ] Atualizar para lidar com múltiplos registros ou estrutura fragmentada

### Fase 5: Estratégia de Agrupamento/Relacionamento

#### 5.1 Identificador de Grupo
- [ ] Decidir como relacionar registros da mesma geração:
  - Opção A: Campo `schedule_group_id` (novo campo)
  - Opção B: Usar `job_id` (já existe)
  - Opção C: Campo `parent_schedule_id` apontando para registro mestre

#### 5.2 Ordenação e Consulta
- [ ] Definir como consultar "uma escala completa":
  - Filtrar por `job_id`?
  - Filtrar por `period_start_at` + `period_end_at`?
  - Usar campo de agrupamento?

### Fase 6: Testes e Validação

#### 6.1 Testes Unitários
- [ ] Testar função de transformação `_extract_individual_allocations()`
- [ ] Testar criação de múltiplos registros
- [ ] Testar integridade dos dados

#### 6.2 Testes de Integração
- [ ] Testar fluxo completo: geração → gravação → leitura
- [ ] Testar geração de PDF com estrutura fragmentada
- [ ] Testar APIs de consulta

#### 6.3 Migração de Dados Existentes
- [ ] Se houver dados existentes, criar script de migração
- [ ] Transformar registros antigos em estrutura fragmentada (se necessário)

## Considerações Importantes

### Performance
- **Múltiplas inserções**: Gravar N registros pode ser mais lento que 1 registro
  - Considerar `session.add_all()` para inserção em lote
  - Avaliar uso de bulk insert se volume for muito grande

### Consistência
- **Transação**: Garantir que todos os registros sejam criados ou nenhum (rollback em caso de erro)
- **Validação**: Validar que todos os registros foram criados com sucesso

### Backward Compatibility
- **Dados antigos**: Decidir como lidar com registros na estrutura antiga
- **APIs**: Manter compatibilidade ou criar versão nova?

### Consultas Futuras
- **Agregações**: Como consultar estatísticas (total_cost, etc.) se dados estão fragmentados?
- **Filtros**: Como filtrar por profissional, dia, etc.?

## Estrutura Proposta do JSON Individual

```json
{
  "professional": "Joaquim",
  "professional_id": "B",
  "id": "B",
  "day": 1,
  "start": 6.0,
  "end": 11.0,
  "is_pediatric": false,
  "source": {
    "id": "B",
    "start": 6.0,
    "end": 11.0,
    "is_pediatric": false,
    "room": "Sala 1",
    "procedure": "Cirurgia X",
    "start_time": "2026-01-26T06:00:00Z",
    "end_time": "2026-01-26T11:00:00Z"
  },
  "metadata": {
    "allocation_mode": "greedy",
    "generated_at": "2026-01-26T10:00:00Z",
    "job_id": 123
  }
}
```

**Nota**: Incluir `metadata` opcional em cada registro pode facilitar consultas futuras sem precisar de registro mestre.

## Próximos Passos

1. Revisar e aprovar este plano
2. Decidir estratégia de agrupamento (campo adicional vs. usar `job_id`)
3. Decidir se mantemos registro mestre ou apenas fragmentados
4. Implementar função de transformação
5. Modificar `generate_schedule_job()`
6. Atualizar código consumidor
7. Testes e validação
8. Migração de dados (se necessário)
