# Plano: Relatório de Escalas — Capa Platypus + Corpo Canvas + Merge

## Objetivo

Fazer o relatório de escalas (e o de demandas, quando usar o mesmo fluxo) usar **capa em Platypus** e **corpo em Canvas**, unidos por **merge**, de forma a:

- **Preservar o aspect ratio** da grade (sem compressão só na vertical).
- **Quebra de página dentro do mesmo dia** quando houver muitos médicos (parte na primeira página, resto na seguinte, depois próximo dia).
- **Capa no topo da primeira página** e **corpo na mesma página**, logo abaixo da capa (não “capa = página 1 inteira, corpo a partir da página 2”).

## Contexto técnico

- **Capa (Platypus):** cabeçalho Turna, título do relatório e seção de filtros — já existem (`build_report_cover_only`).
- **Corpo (Canvas):** grade de horário por dia, com paginação por linha em `_render_pdf_to_canvas` (já faz `showPage()` quando não cabe mais uma linha).
- **Merge:** hoje `merge_pdf_with_cover(cover_bytes, content_bytes)` concatena capa (1 página) + corpo (N páginas), ou seja, corpo começa na **página 2**. Para ter capa no topo e corpo na **mesma** primeira página, é necessário uma estratégia diferente (ver abaixo).

O relatório atual usa `build_report_with_schedule_body` (tudo em Platypus com `DayGridFlowable`), o que não quebra dentro do dia e altera o aspect ratio. A solução é trocar para o fluxo capa + corpo Canvas + merge, com primeira página composta (capa em cima, corpo embaixo).

---

## Estratégia: primeira página com capa + corpo

Para que **(1)** a capa fique no topo da primeira página e **(2)** o corpo comece na **mesma** página logo a seguir, o merge simples “capa = página 1, corpo = página 2 em diante” não serve. É preciso uma das abordagens abaixo.

### Opção A — Um único Canvas

- **Página 1:** desenhar a capa no topo; em seguida desenhar o corpo a partir de um `content_top_y` (altura da página menos altura da capa).
- Quando o corpo não couber mais na primeira página, `showPage()` e continuar o corpo nas páginas 2, 3… (páginas só de corpo).
- **Prós:** um único fluxo, controle total.  
- **Contras:** exige ter a capa desenhada em Canvas (réplica do layout da capa) ou alguma forma de compor a capa nesse Canvas.

### Opção B — Capa Platypus + corpo Canvas + merge “composite”

- Gerar a **capa** (1 página) em Platypus.
- Gerar o **corpo** em Canvas com **primeira página “parcial”**: `content_top_y = altura_da_página - margem - altura_da_capa`, para reservar o topo para a capa.
- Fazer um **merge customizado** (em vez de só concatenar): a **página 1** do PDF final = página da capa desenhada no topo + conteúdo da primeira página do corpo desenhado logo abaixo; as páginas 2, 3… = restantes páginas do corpo.
- Isso pode ser feito com PyMuPDF (fitz) compondo a primeira página: desenhar a página da capa no topo da primeira página e o conteúdo da primeira página do corpo abaixo.
- **Prós:** reaproveita a capa Platypus e o corpo Canvas existente.  
- **Contras:** lógica de merge mais elaborada (composite na primeira página).

Escolher A ou B conforme preferência (manter capa em Platypus sugere B; simplificar stack sugere A).

---

## Etapas de implementação

### 1. Corpo PDF em Canvas (lista de dias, com quebra no mesmo dia)

- **Onde:** `backend/output/day.py`.
- **O que:** Garantir que existe uma função que recebe `list[DaySchedule]` e gera os bytes do PDF do **corpo** (sem capa), usando **apenas** Canvas, com `_render_pdf_to_canvas` para cada dia.
  - Essa função já existe em essência: `render_multi_day_pdf_body_bytes(schedules)`. Ela itera os dias e chama `_render_pdf_to_canvas`; dentro de `_render_pdf_to_canvas` já há a lógica de `showPage()` quando `y - row_h < margin + 6`.
- **Se for Opção B:** expor/ajustar uma variante que aceite `content_top_y` na **primeira** página do corpo (ex.: primeiro dia usa `content_top_y = page_h - margin - capa_height`; demais páginas continuam com topo completo).
- **Verificar:** Que o corpo é gerado com **landscape A4** e que não há escala (desenho em tamanho natural), para preservar aspect ratio.

### 2. Merge com primeira página composta (capa + corpo)

- **Onde:** `backend/app/report/pdf_layout.py` (ou módulo dedicado).
- **O que:** Implementar a função de merge que produz:
  - **Página 1:** capa no topo + conteúdo da primeira página do corpo logo abaixo (Opção B: usar PyMuPDF para compor; Opção A: já está em um único Canvas).
  - **Páginas 2, 3, …:** restantes páginas do corpo.
- Se for **Opção B:** nova função (ex.: `merge_pdf_cover_with_body_first_page(cover_bytes, body_bytes, capa_height)`) que monta a primeira página composta e depois anexa as páginas 2 em diante do corpo.
- Se for **Opção A:** o Canvas único já desenha capa + corpo na primeira página; não há “merge” de dois PDFs, só um PDF gerado em um fluxo.

### 3. Integração no relatório de escalas (capa + corpo + merge)

- **Onde:** `backend/app/api/schedule.py` (endpoint do relatório de escalas).
- **O que:** Em vez de `build_report_with_schedule_body(...)`:
  1. Gerar a **capa** com `build_report_cover_only(report_title="Relatório de escalas", filters=filters_parts, pagesize=landscape(A4))`.
  2. Gerar o **corpo** com a função de `day.py` que retorna bytes do PDF das grades (ex.: `render_multi_day_pdf_body_bytes(all_schedules)` ou equivalente que aceite `content_top_y` na primeira página, se Opção B).
  3. Obter o PDF final com a função de merge que respeita “capa no topo + corpo na mesma primeira página” (etapa 2).
- **Imports:** incluir `build_report_cover_only`, a nova função de merge, e a função de body de `output.day`.

### 4. Relatório de demandas (mesmo padrão)

- **Onde:** `backend/app/api/route.py` (endpoint do relatório de demandas).
- **O que:** Aplicar o mesmo padrão: capa com `build_report_cover_only`, corpo com a mesma função Canvas de `day.py`, resposta com a função de merge que compõe a primeira página. Ajustar título e filtros para “Relatório de demandas”.

### 5. Dados de teste (forçar quebra de página no mesmo dia)

- **Problema:** Com poucos registros por dia (ex.: ~10 médicos), a grade cabe em uma página e a quebra dentro do mesmo dia não aparece.
- **Solução (apenas para teste):** Depois de montar a lista de `DaySchedule` (ex.: `demands_to_day_schedules`), **em ambiente de teste ou via flag**, expandir os dados para simular mais linhas por dia: por exemplo, **replicar 3 linhas por member** (cada médico aparece 3 vezes no mesmo dia), aumentando o número de linhas da grade e forçando quebra de página.
- **Onde:** Pode ser um passo opcional no pipeline de construção de `schedules` (ex.: em `schedule.py` ou em `pdf_demand.py`), ativado só quando necessário para teste (variável de ambiente, flag ou comentário explícito “apenas para teste”).
- **Forma simples:** Para cada `DaySchedule`, para cada `Row` em `schedule.rows`, adicionar duas cópias da mesma `Row` (ou criar 3 linhas por member com o mesmo nome/dados). Assim, 10 médicos viram 30 linhas e a segunda página do mesmo dia passa a ser usada.

### 6. Verificação final

- Gerar o relatório de escalas com período que tenha vários dias e, com o truque de 3 linhas por member, vários médicos por dia.
- **Verificar:**
  1. **Capa no topo da primeira página.**
  2. **Corpo na mesma primeira página**, logo a seguir da capa.
  3. **Quebra de página no meio de um dia:** parte dos médicos numa página, resto na seguinte.
  4. **Próximo dia na página seguinte.**
  5. **Proporção da grade mantida** (sem achatamento vertical).
- Opcional: remover ou desativar o “triplicar linhas por member” depois que os testes estiverem ok, ou deixar documentado como opção de teste.

---

## Resumo

| Item | Ação |
|------|------|
| Aspect ratio | Corpo 100% em Canvas, sem escala; preservado. |
| Quebra no mesmo dia | Já implementada em `_render_pdf_to_canvas`; basta usar esse corpo no relatório. |
| Capa | `build_report_cover_only` (Platypus). |
| Primeira página | Capa no topo + corpo logo abaixo na **mesma** página (merge composite ou Canvas único). |
| Teste com muitas linhas | Replicar 3 linhas por member nos dados de schedule (só para teste). |

---

## Arquivos envolvidos (implementado)

- `backend/output/day.py` — `render_multi_day_pdf_body_bytes(first_page_content_top_y=...)`; `expand_schedule_rows_for_test(schedules, factor=3)`.
- `backend/app/report/pdf_layout.py` — `COVER_HEIGHT_PT`; `merge_pdf_cover_with_body_first_page(cover_bytes, body_bytes, capa_height_pt)`.
- `backend/app/api/schedule.py` — relatório de escalas: capa + corpo + merge; expand para teste quando `TURNA_TEST_TRIPLE_SCHEDULE_ROWS=1`.
- `backend/app/api/route.py` — relatório de demandas: mesmo fluxo.
- Dados de teste — `TURNA_TEST_TRIPLE_SCHEDULE_ROWS=1` ativa 3 linhas por member para forçar quebra de página.
