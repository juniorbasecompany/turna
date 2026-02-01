# Plano: Refatoração da tabela member (can_peds, sequence, vacation)

Objetivo: adicionar três novos campos na tabela `member` e permitir edição no painel de associados.

- **member.can_peds** (boolean): indica se o membro pode atender pediatria.
- **member.sequence** (inteiro): ordem/sequência do membro (ex.: para exibição ou prioridade).
- **member.vacation** (vetor de vetor): zero, um ou mais pares de datetime `[início, fim]` representando períodos de férias.

Formato de `vacation` na API e no banco: lista de pares, cada par = `[datetime_iso_início, datetime_iso_fim]`. Exemplo em JSON:  
`[["2025-01-01T00:00:00Z", "2025-01-15T23:59:59Z"], ["2025-07-01T00:00:00Z", "2025-07-15T23:59:59Z"]]`.

---

## Etapa 1: Backend – modelo e migração

Objetivo: definir os campos no modelo SQLModel e criar migração Alembic.

### 1.1 Modelo (member.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/model/member.py` | Adicionar `can_peds: bool = Field(default=False)` (ou `True`, conforme regra de negócio). |
| `backend/app/model/member.py` | Adicionar `sequence: int = Field(default=0)` (inteiro; definir se nullable ou default 0). |
| `backend/app/model/member.py` | Adicionar `vacation` como coluna JSON (lista de listas de 2 strings ISO datetime), por exemplo `vacation: list[list[str]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))` com `server_default="[]"` na migração. |

### 1.2 Migração Alembic

| Arquivo | Alteração |
|---------|-----------|
| Novo arquivo em `backend/alembic/versions/` | Criar revisão (ex.: `0132_add_member_can_peds_sequence_vacation.py`) que: (1) adiciona coluna `can_peds` BOOLEAN NOT NULL com `server_default='false'`; (2) adiciona coluna `sequence` INTEGER NOT NULL com `server_default='0'`; (3) adiciona coluna `vacation` JSON/JSONB NOT NULL com `server_default='[]'`. No downgrade, remover as três colunas. |
| `backend/alembic/versions/` | Revisão deve depender da última atual (ex.: `0131pq901237`). |

---

## Etapa 2: Backend – API (schemas e endpoints)

Objetivo: expor os novos campos nos schemas Pydantic e nos handlers de create/update/get/list.

### 2.1 Schemas Pydantic (route.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | **MemberCreate**: adicionar `can_peds: Optional[bool] = None`, `sequence: Optional[int] = None`, `vacation: Optional[list[list[str]]] = None`. Definir default na criação (ex.: False, 0, []). |
| `backend/app/api/route.py` | **MemberUpdate**: adicionar `can_peds: Optional[bool] = None`, `sequence: Optional[int] = None`, `vacation: Optional[list[list[str]]] = None`. |
| `backend/app/api/route.py` | **MemberResponse**: adicionar `can_peds: bool`, `sequence: int`, `vacation: list[list[str]]` (ou tipar como list de pares de datetime/string conforme serialização). |

Validadores sugeridos (opcional na Etapa 2):

- **sequence**: garantir inteiro (e, se desejado, >= 0).
- **vacation**: validar que cada elemento é uma lista de exatamente 2 strings que podem ser parseadas como datetime ISO (início <= fim por par).

### 2.2 Handlers de member (route.py)

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | **create_member**: ao instanciar `Member(...)`, preencher `can_peds=body.can_peds if body.can_peds is not None else False`, `sequence=body.sequence if body.sequence is not None else 0`, `vacation=body.vacation if body.vacation is not None else []`. |
| `backend/app/api/route.py` | **update_member**: adicionar `if body.can_peds is not None: member_obj.can_peds = body.can_peds`; idem para `sequence` e `vacation`. |
| `backend/app/api/route.py` | **get_member**, **list_members**, **create_member** (retorno), **update_member** (retorno): incluir `can_peds`, `sequence`, `vacation` em todos os `MemberResponse(...)` construídos. |

### 2.3 Ordenação: sequence, name (painel e relatório)

Tanto o painel quanto o relatório devem listar members ordenados por **member.sequence**, depois **member.name**.

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/api/route.py` | **_member_list_queries** (linha ~1073): trocar `query.order_by(Member.created_at.desc())` por `query.order_by(Member.sequence, Member.name.asc().nulls_last())` (ou equivalente: primeiro por sequence, depois por name, com nome nulo por último). Assim, a listagem (`list_members`) e o relatório (`report_member_pdf`) passam a usar a mesma ordenação. |

---

## Etapa 3: Frontend – tipos e painel

Objetivo: atualizar tipos da API e o painel de member para exibir e editar os três campos.

### 3.1 Tipos (api.ts)

| Arquivo | Alteração |
|---------|-----------|
| `frontend/types/api.ts` | **MemberResponse**: adicionar `can_peds: boolean`, `sequence: number`, `vacation: [string, string][]` (ou `string[][]` com convenção de par [início, fim] em ISO). |
| `frontend/types/api.ts` | **MemberUpdateRequest**: adicionar `can_peds?: boolean \| null`, `sequence?: number \| null`, `vacation?: [string, string][] \| null`. |
| `frontend/types/api.ts` | **MemberCreateRequest**: adicionar `can_peds?: boolean \| null`, `sequence?: number \| null`, `vacation?: [string, string][] \| null`. |

### 3.2 Painel de member (page.tsx)

| Arquivo | Alteração |
|---------|-----------|
| `frontend/app/(protected)/member/page.tsx` | **MemberFormData**: adicionar `can_peds: boolean`, `sequence: number`, `vacation: [string, string][]`. |
| `frontend/app/(protected)/member/page.tsx` | **initialFormData**: incluir `can_peds: false`, `sequence: 0`, `vacation: []`. |
| `frontend/app/(protected)/member/page.tsx` | **mapEntityToFormData**: mapear `member.can_peds`, `member.sequence`, `member.vacation ?? []`. |
| `frontend/app/(protected)/member/page.tsx` | **mapFormDataToCreateRequest** e **mapFormDataToUpdateRequest**: incluir `can_peds`, `sequence`, `vacation` nos objetos enviados à API. |
| `frontend/app/(protected)/member/page.tsx` | **Formulário (EditForm)**: adicionar campo de edição para **can_peds** (checkbox), **sequence** (input numérico) e **vacation** (lista editável de pares de datetime; pode ser um componente reutilizável ou lista com “Adicionar período” + dois inputs/datetime-picker por período, garantindo início e fim). |
| `frontend/app/(protected)/member/page.tsx` | **Ordenação**: a listagem do painel vem do endpoint `/api/member/list`, que já retornará ordenada por `sequence`, `name` (ver Etapa 2.3). Nenhuma ordenação extra no frontend necessária. |

Sugestão de UX para `vacation`:

- Lista de “períodos de férias”.
- Cada período: dois campos de data/hora (início e fim).
- Botão “Adicionar período”; opção de remover período.
- Validar no front (opcional): início <= fim; não sobrepor períodos (opcional).

---

## Etapa 4: Relatório PDF de associados

Objetivo: incluir os campos **can_peds**, **sequence** e **vacation** no relatório de associados e garantir que a ordem seja por **member.sequence**, **member.name** (já coberto na Etapa 2.3).

### 4.1 Estrutura das linhas e cabeçalhos do PDF

| Arquivo | Alteração |
|---------|-----------|
| `backend/app/report/pdf_list.py` | **render_member_list_pdf**: alterar assinatura de `rows: list[tuple[str, str, str]]` para uma tupla maior com os novos campos, por exemplo `rows: list[tuple[str, str, str, str, str, str]]` correspondente a (nome, email, situação, pode_pediatria, ordem, férias). Atualizar **headers** de `["Nome", "E-mail", "Situação"]` para incluir colunas para can_peds (ex.: "Pode pediatria?"), sequence (ex.: "Ordem") e vacation (ex.: "Férias"). Ajustar `data = [[str(r[0]), str(r[1]), str(r[2])], ...]` para incluir os novos índices. |
| `backend/app/api/route.py` | **report_member_pdf** (montagem de `rows`): em vez de `rows.append((name, email, member_obj.status.value))`, construir cada linha com: nome, email, situação, texto para can_peds (ex.: "Sim"/"Não"), sequence (ex.: str(member_obj.sequence)), e vacation formatado como string legível (ex.: listar cada par [início, fim] em formato de data local ou ISO abreviado; se vazio, "-"). Usar a mesma ordem de colunas definida em `render_member_list_pdf`. |

Sugestão de formatação para **vacation** no PDF: exibir cada período como "dd/mm/aaaa – dd/mm/aaaa"; múltiplos períodos separados por "; " ou quebra de linha. Valores vazios exibir como "-".

### 4.2 Ordenação do relatório

A ordenação do relatório é a mesma da listagem: **member.sequence**, **member.name**. O relatório usa `_member_list_queries`, que será alterado na Etapa 2.3; nenhuma alteração adicional no relatório para ordem.

---

## Etapa 5: Outros usos de member (opcional nesta refatoração)

Objetivo: garantir que relatórios ou outros pontos que leem `Member` estejam compatíveis.

| Arquivo | Observação |
|---------|------------|
| `backend/app/report/pdf_demand.py` | Já usa `Member` (nome). Se no futuro o relatório de escalas usar `vacation` para marcar férias no PDF, incluir leitura de `member.vacation` e repassar para `Row(..., vacations=...)` (já existe parâmetro `vacations` em `Row`). Pode ficar para um passo posterior. |

---

## Ordem sugerida de execução

1. Etapa 1 (modelo + migração); rodar migração e conferir tabela.
2. Etapa 2 (API + ordenação); testar create/update/get/list via API; conferir que list e report vêm ordenados por sequence, name.
3. Etapa 3 (frontend); testar criar e editar member no painel com os três novos campos; conferir que a lista do painel aparece ordenada por sequence, name.
4. Etapa 4 (relatório PDF); incluir can_peds, sequence, vacation no PDF e validar ordenação.
5. Etapa 5 (outros usos de member) conforme necessidade.

---

## Checklist de validação

- [ ] Migração sobe e desce sem erro.
- [ ] Criar member via API com e sem os novos campos; valores default aplicados.
- [ ] Atualizar member via API (can_peds, sequence, vacation).
- [ ] GET member e list retornam can_peds, sequence, vacation.
- [ ] Listagem (painel e API) ordenada por member.sequence, depois member.name (nome nulo por último).
- [ ] Frontend: formulário exibe e persiste can_peds, sequence e vacation.
- [ ] Frontend: vacation aceita zero, um ou vários períodos; datas em ISO.
- [ ] Relatório PDF de associados: inclui colunas can_peds, sequence, vacation; mesma ordenação (sequence, name).
