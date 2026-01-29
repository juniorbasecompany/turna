# Checklist: Botão de Relatório e PDFs

Objetivo: ter um **botão de relatório** reutilizável em todos os painéis que possuem relatório e gerar os PDFs descritos abaixo.

---

## 1. Botão de relatório reutilizável

- **Onde colocar**: O botão de relatório deve ficar no **ActionBar** (barra de ações), junto aos demais botões do painel (Cancelar, Excluir, Salvar, etc.).
- **Como encaixar**: Usar o mesmo padrão dos outros botões do ActionBar — por exemplo, via `customActions` do `useActionBarButtons`, que já alimenta o `ActionBar` com a prop `buttons`.
- **Componente ou hook**: Criar algo reutilizável para todos os painéis (Tenant, Member, Hospital, Arquivos, Demandas, Escala). O botão chama uma ação (abrir/baixar o PDF do painel atual).
- **Comportamento**: Ao clicar, disparar a requisição ao backend que gera/retorna o PDF (ou abrir em nova aba / iniciar download), e opcionalmente mostrar loading/erro.

---

## 2. Backend: endpoints de relatório em PDF

Cada relatório pode ser um endpoint GET (ou POST se precisar de filtros no body) que retorna `application/pdf`. O frontend só precisa chamar esse endpoint e tratar o blob (download ou nova aba).

- **Tenant**: Lista em PDF com **nome** e **slug** da clínica.
- **Member**: Lista em PDF com **nome**, **email** e **situação** (status) do associado.
- **Hospital**: Lista em PDF com **nome** dos hospitais.
- **Arquivos (File)**: Lista em PDF com **nome do hospital**, **nome do arquivo** e **data de cadastro** (created_at).
- **Demandas**: Relatório em tabela/grade:
  - Uma coluna com o **nome do hospital**.
  - Colunas de horário de **00:00 até 23:59** (ou 24:00).
  - Em cada linha (hospital), um quadro mostrando a demanda: **início** e **fim** do horário (blocos no intervalo correspondente), no estilo do `test/escala_dia1.pdf`.
  - **Cada dia em uma nova página** (quebrar por dia).
- **Escala**: Relatório no mesmo formato visual do `test/escala_dia1.pdf` (grade de horários, profissionais/linhas, blocos por horário). **Cada dia em uma nova página.**

Implementação no backend: usar ReportLab (já usado em `output/day.py`) para gerar os PDFs. Para listas simples (Tenant, Member, Hospital, Arquivos), tabelas com texto; para Demandas e Escala, reutilizar ou adaptar a lógica de `output/day.py` (grade, quebra de página por dia).

---

## 3. Frontend: botão no ActionBar por painel

O botão “Relatório” deve ser adicionado ao **ActionBar** de cada painel (via `customActions` em `useActionBarButtons` ou equivalente), apontando para o endpoint de PDF do painel:

- **Tenant**: Botão “Relatório” no ActionBar → endpoint de PDF de clínicas (nome + slug).
- **Member**: Botão “Relatório” no ActionBar → PDF de associados (nome, email, situação).
- **Hospital**: Botão “Relatório” no ActionBar → PDF de hospitais (nome).
- **Arquivos**: Botão “Relatório” no ActionBar → PDF de arquivos (hospital, nome do arquivo, data de cadastro).
- **Demandas**: Botão “Relatório” no ActionBar → PDF de demandas (grade por hospital/horário, um dia por página).
- **Escala (schedule)**: Botão “Relatório” no ActionBar → PDF no formato escala_dia1, um dia por página.

Em todos os casos, o mesmo padrão visual/comportamento (reutilizável), apenas o endpoint muda por painel.

---

## 4. Resumo por tipo de relatório

| Painel   | Conteúdo do PDF                                                                 | Quebra de página      |
|----------|----------------------------------------------------------------------------------|------------------------|
| Tenant   | Nome, slug                                                                       | Uma lista, sem regra   |
| Member   | Nome, email, situação                                                            | Uma lista, sem regra   |
| Hospital | Nome                                                                             | Uma lista, sem regra   |
| Arquivos | Nome do hospital, nome do arquivo, data de cadastro                              | Uma lista, sem regra   |
| Demandas | Coluna hospital + colunas 00:00–23:59; na linha, blocos início–fim da demanda   | Um dia = uma página    |
| Escala   | Igual ao escala_dia1.pdf (grade de horários, linhas por profissional/evento)     | Um dia = uma página    |

---

## 5. Ordem sugerida de implementação

1. **Backend**: Endpoints de PDF para listas simples (Tenant, Member, Hospital, Arquivos) — mais rápidos de implementar e validar.
2. **Frontend**: Componente/hook do botão de relatório e uso no **ActionBar** dos painéis Tenant, Member, Hospital e Arquivos.
3. **Backend**: Endpoint de PDF de Demandas (grade por hospital/horário, um dia por página).
4. **Backend**: Endpoint de PDF de Escala (reaproveitar/adaptar `output/day.py`, um dia por página).
5. **Frontend**: Botão de relatório no **ActionBar** dos painéis Demandas e Escala.

---

## 6. Observações

- **Autenticação e tenant**: Todos os endpoints de relatório devem respeitar o tenant do usuário logado (listar apenas dados do tenant atual).
- **Idioma**: Código em inglês; comentários e mensagens ao usuário em português, conforme regras do projeto.
- **Reuso**: Ao mudar o botão ou o fluxo de relatório em um painel, verificar se faz sentido aplicar o mesmo em todos os outros (regra dos painéis).
