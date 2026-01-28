# Checklist: Migrar Profissionais de JSON para Tabela Member

Este checklist detalha as tarefas para deixar de usar `test/profissionais.json` e passar a usar a tabela `member` com os dados em `member.attribute` ao calcular escalas.

## Status da implementação

**Concluído** (jan/2026). O worker carrega profissionais da tabela `member` do tenant. Fallback para arquivo JSON removido. Pasta `test/` mantida inalterada.

## Contexto

**Estado anterior:**
- O worker usava `_load_pros_from_repo_test()` como fallback, lendo `test/profissionais.json`.

**Estado atual:**
- O worker carrega profissionais da tabela `member` do tenant (`_load_pros_from_member_table`).
- Dados em `member.attribute`: `id`, `sequence`, `can_peds`, `vacation`.
- Se `pros_by_sequence` vier no `input_data`, continua sendo usado (payload explícito tem prioridade).

## Pré-requisitos

- [x] Tabela `member` já possui campo `attribute` (JSONB)
- [x] Script SQL para inserir profissionais com `attribute` (`test/script_insert_profissionais.sql`)
- [x] Dados inseridos no banco para o tenant de teste
- **Não alterar, remover nem mover arquivos na pasta `test/`**

---

## FASE 1: Backend - Função para Carregar Profissionais do Banco

### 1.1 Criar função para carregar profissionais

- [x] Criar função `_load_pros_from_member_table(session, tenant_id)` em `backend/app/worker/job.py`
- [x] Implementar a função:
  - [x] Filtrar por `tenant_id`
  - [x] Filtrar por `status = ACTIVE`
  - [x] Usar apenas members com `attribute` válido (via `_validate_pro_attribute`)
  - [x] Extrair de `member.attribute`: `id`, `name`, `sequence`, `can_peds`, `vacation` (listas → tuplas)
  - [x] Ordenar por `sequence`
  - [x] Retornar lista de dicts

### 1.2 Atualizar o job de geração de escala

- [x] Em `generate_schedule_job()`, carregar profissionais do banco quando `pros_by_sequence` ausente
- [x] Validação: `RuntimeError("Nenhum profissional encontrado para o tenant")` se lista vazia

### 1.3 Remover fallback para arquivo JSON

- [x] Remover função `_load_pros_from_repo_test()` do backend
- [x] Atualizar comentários que referenciam o arquivo JSON
- **Não alterar, remover nem mover arquivos na pasta `test/`**

---

## FASE 2: Validações e Tratamento de Erros

### 2.1 Validar estrutura do attribute

- [x] Criar `_validate_pro_attribute(attribute: dict) -> bool` em `job.py`
- [x] Exigir `sequence` numérico, `can_peds` bool, `vacation` lista (itens com 2 elementos)
- [x] Logar warning para members com attribute inválido

### 2.2 Tratamento de erros

- [x] Log ao iniciar carregamento e com quantidade carregada/ignorada
- [x] Mensagem "Nenhum profissional encontrado para o tenant"
- [x] Mensagem "Member id=… name=… ignorado: attribute inválido"

---

## FASE 3: API - Endpoint para Listar Profissionais (Opcional)

### 3.1 Criar endpoint GET /member/professionals

- [ ] Criar endpoint em `backend/app/api/route.py`
- [ ] Schema `ProfessionalResponse` (id, name, sequence, can_peds, vacation)

### 3.2 Usar endpoint no frontend (opcional)

- [ ] Handler `frontend/app/api/member/professionals/route.ts`
- [ ] Exibir lista de profissionais no painel de schedule (se desejado)

---

## FASE 4: Testes e Validação

### 4.1 Testes manuais

- [ ] Inserir profissionais no banco via SQL
- [ ] Verificar logs `[LOAD_PROFESSIONALS]` do worker
- [ ] Gerar escala e conferir profissionais usados
- [ ] Testar tenant sem profissionais (erro claro)

### 4.2 Validação de comportamento

- [ ] Profissionais filtrados por `tenant_id`
- [ ] Apenas members `ACTIVE` considerados
- [ ] Ordenação por `sequence`
- [ ] `vacation` convertida corretamente para tuplas

---

## FASE 5: Documentação e Limpeza

### 5.1 Documentação

- [x] Atualizar `CHECKLIST.md` (seção 4.4 Job GENERATE_SCHEDULE)
- [x] Formato esperado do `member.attribute`:

```json
{
  "id": "string (opcional; usa member.name ou member.id se ausente)",
  "sequence": "int (ordem de prioridade)",
  "can_peds": "bool (pode atender pediatria)",
  "vacation": "list[list[int]] (ex.: [[13, 17]], [[7, 12]])"
}
```

### 5.2 Limpeza

- [x] Sem imports não utilizados no backend
- **Não mexer na pasta `test/`** (manter `profissionais.json` e `script_insert_profissionais.sql`)

---

## Considerações de Segurança

- [x] `tenant_id` do job (nunca do payload)
- [x] Query filtrada por `tenant_id`
- [x] Sem exposição de dados de outros tenants

## Considerações de Arquitetura

- [x] Código em inglês, comentários em português
- [x] Multi-tenant por `tenant_id`
- [x] Profissionais vêm do banco (tabela `member`), não de arquivos

---

## Ordem de execução (já aplicada)

1. Fase 1.1 → 1.2 → 1.3, Fase 2.1 → 2.2, Fase 5.1 → 5.2
2. Fase 4 (testes manuais) e Fase 3 (opcional) conforme necessidade

---

## Notas

- O `attribute` deve ser compatível com o formato esperado pelo solver.
- **Não mexer na pasta `test/`**; arquivos lá permanecem inalterados.
- O campo `attribute` é JSON/JSONB; pode ser consultado no banco se necessário.

**Última atualização**: Janeiro/2026
