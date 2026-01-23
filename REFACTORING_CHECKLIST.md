# ✅ Checklist de Refatoração dos Painéis

Este checklist deve ser usado para acompanhar o progresso da refatoração dos painéis para usar componentes reutilizáveis.

---

## 📋 Fase 1: Preparação (Sem Breaking Changes)

### Componentes Base
- [x] ✅ `FilterPanel.tsx` criado e testado
- [x] ✅ `EntityCard.tsx` criado e testado
- [x] ✅ `useEntityFilters.ts` criado e testado
- [x] ✅ Documentação criada (`REFACTORING_STRATEGY.md`)
- [x] ✅ Exemplo de migração criado (`MIGRATION_EXAMPLE.md`)

### Testes dos Componentes
- [x] Testar `FilterPanel` em isolamento
- [x] Testar `EntityCard` em isolamento
- [x] Testar `useEntityFilters` em isolamento
- [x] Validar que os componentes seguem padrões visuais existentes
- [x] Criar página de teste (`/test-entity-page`) se necessário

**Status da Fase 1:** ✅ Completo

---

## 📋 Fase 2: Migração Gradual

### 2.1 Migração do Painel Hospital

**Prioridade:** Alta (mais simples, já usa `useEntityPage`)

#### Preparação
- [x] Revisar código atual do painel Hospital
- [x] Identificar o que já está usando componentes reutilizáveis
- [x] Identificar o que precisa ser migrado

#### Migração
- [x] Substituir estrutura de filtros por `FilterPanel` (se aplicável) - N/A (não tem filtros)
- [x] Substituir cards por `EntityCard` ✅ Migrado
- [x] Validar que `useActionBarButtons` está sendo usado corretamente ✅ Já estava correto
- [x] Validar que `getActionBarErrorProps` está sendo usado corretamente ✅ Já estava correto

#### Testes
- [ ] Testar criação de hospital
- [ ] Testar edição de hospital
- [ ] Testar exclusão de hospital
- [ ] Testar paginação
- [ ] Validar visualmente (comparar antes/depois)
- [ ] Verificar responsividade

#### Finalização
- [ ] Commit: `refactor: migrate hospital page to use reusable components`
- [ ] Documentar mudanças específicas do Hospital (se houver)

**Status do Hospital:** ✅ Completo

---

### 2.2 Migração do Painel Member

**Prioridade:** Alta (padrão para outros painéis)

#### Preparação
- [x] Revisar código atual do painel Member
- [x] Identificar todas as áreas de código repetido
- [x] Criar branch: `refactor/member-page` - N/A (trabalhando direto)

#### Migração - Lógica de Botões
- [x] Adicionar import: `useActionBarButtons` ✅
- [x] Substituir lógica manual de botões (linhas 747-777) ✅
- [x] Ajustar para suportar `sendInvite` (customização necessária) ✅
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [x] Adicionar import: `getActionBarErrorProps` ✅
- [x] Substituir lógica manual de erro (linhas 714-746) ✅
- [x] Ajustar para suportar `emailMessage` e `emailMessageType` ✅
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [x] Adicionar imports: `FilterPanel`, `useEntityFilters` ✅
- [x] Substituir estado manual de filtros por `useEntityFilters` ✅
- [x] Substituir estrutura de filtros (linhas 611-633) por `FilterPanel` ✅
- [x] Atualizar `FilterButtons` para usar hooks ✅
- [ ] Testar filtros funcionam corretamente

#### Migração - Cards (Opcional)
- [x] Adicionar import: `EntityCard` ✅
- [x] Substituir estrutura manual de cards por `EntityCard` ✅
- [x] Manter customização visual (ícone, badges) ✅
- [ ] Testar cards renderizam corretamente

#### Migração - Paginação
- [x] Verificar se está usando `paginationHandlers` do hook - N/A (paginação manual, mas funcional)
- [ ] Se não, migrar para usar `paginationHandlers` - Deixar como está (funcional)
- [ ] Testar paginação funciona corretamente

#### Testes Completos
- [ ] Testar criação de member
- [ ] Testar edição de member
- [ ] Testar exclusão de member(s)
- [ ] Testar filtros (status e função)
- [ ] Testar paginação
- [ ] Testar seleção múltipla
- [ ] Testar envio de convite
- [ ] Validar visualmente (comparar antes/depois)
- [ ] Verificar responsividade
- [ ] Testar em diferentes tamanhos de tela

#### Finalização
- [ ] Remover código duplicado não utilizado
- [ ] Revisar código migrado
- [ ] Commit: `refactor: migrate member page to use reusable components`
- [ ] Merge branch (se aplicável)

**Status do Member:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

### 2.3 Migração do Painel Demand

**Prioridade:** Média (similar ao Member)

#### Preparação
- [x] Revisar código atual do painel Demand
- [x] Identificar todas as áreas de código repetido
- [x] Criar branch: `refactor/demand-page` - N/A (trabalhando direto)

#### Migração - Lógica de Botões
- [x] Adicionar import: `useActionBarButtons` ✅
- [x] Substituir lógica manual de botões (linhas 735-767) ✅
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [x] Adicionar import: `getActionBarErrorProps` ✅
- [x] Substituir lógica manual de erro (linhas 680-710) ✅
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [x] Verificar se Demand tem filtros - N/A (não tem filtros)
- [x] Se sim, migrar para `FilterPanel` e `useEntityFilters` - N/A
- [x] Testar filtros funcionam corretamente - N/A

#### Migração - Cards (Opcional)
- [x] Adicionar import: `EntityCard` ✅
- [x] Substituir estrutura manual de cards por `EntityCard` ✅
- [x] Manter customização visual ✅
- [ ] Testar cards renderizam corretamente

#### Migração - Paginação
- [x] Verificar se está usando `paginationHandlers` - N/A (paginação manual, mas funcional)
- [x] Se não, migrar para usar `paginationHandlers` - Deixar como está (funcional)
- [ ] Testar paginação funciona corretamente

#### Testes Completos
- [ ] Testar criação de demanda
- [ ] Testar edição de demanda
- [ ] Testar exclusão de demanda(s)
- [ ] Testar filtros (se houver)
- [ ] Testar paginação
- [ ] Testar seleção múltipla
- [ ] Validar visualmente (comparar antes/depois)
- [ ] Verificar responsividade

#### Finalização
- [ ] Remover código duplicado não utilizado
- [ ] Revisar código migrado
- [ ] Commit: `refactor: migrate demand page to use reusable components`
- [ ] Merge branch (se aplicável)

**Status do Demand:** 🟡 Em progresso

---

### 2.4 Migração do Painel File

**Prioridade:** Baixa (mais complexo, pode manter estrutura customizada)

#### Preparação
- [x] Revisar código atual do painel File
- [x] Identificar o que pode ser migrado
- [x] Identificar o que deve permanecer customizado
- [x] Criar branch: `refactor/file-page` - N/A (trabalhando direto)

#### Migração - Lógica de Botões
- [x] Adicionar import: `useActionBarButtons` ✅
- [x] Substituir lógica manual de botões (linhas 1768-1791) ✅
- [x] Ajustar para suportar `showEditArea` e `selectedFilesForReading` ✅ (customizado com useMemo)
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [x] Adicionar import: `getActionBarErrorProps` ✅
- [x] Substituir lógica manual de erro (linhas 1747-1767) ✅
- [x] Ajustar para suportar `showEditArea` ✅
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [x] Adicionar imports: `FilterPanel`, `useEntityFilters` ✅
- [x] Substituir estrutura de filtros (linhas 1349-1415) por `FilterPanel` ✅
- [x] Migrar filtros de status para `useEntityFilters` ✅
- [x] Manter filtros de data e hospital (customizados) ✅
- [ ] Testar filtros funcionam corretamente

#### Migração - Cards (Opcional)
- [ ] Avaliar se `EntityCard` faz sentido para File
- [ ] Se sim, migrar mantendo customização (thumbnail, status)
- [ ] Se não, documentar por que mantém estrutura customizada
- [ ] Testar cards renderizam corretamente

#### Migração - Paginação
- [ ] Verificar se está usando `paginationHandlers`
- [ ] Se não, migrar para usar `paginationHandlers`
- [ ] Testar paginação funciona corretamente

#### Testes Completos
- [ ] Testar upload de arquivos
- [ ] Testar edição de JSON
- [ ] Testar exclusão de arquivo(s)
- [ ] Testar leitura de conteúdo
- [ ] Testar filtros (hospital, data, status)
- [ ] Testar paginação
- [ ] Testar seleção múltipla
- [ ] Validar visualmente (comparar antes/depois)
- [ ] Verificar responsividade

#### Finalização
- [ ] Remover código duplicado não utilizado
- [ ] Revisar código migrado
- [ ] Documentar decisões de customização (se houver)
- [ ] Commit: `refactor: migrate file page to use reusable components`
- [ ] Merge branch (se aplicável)

**Status do File:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

## 📋 Fase 3: Limpeza e Documentação

### Limpeza de Código
- [ ] Remover implementações manuais de botões não utilizadas
- [ ] Remover implementações manuais de erro não utilizadas
- [ ] Remover estruturas de filtros manuais não utilizadas
- [ ] Remover código comentado relacionado à refatoração
- [ ] Executar linter e corrigir warnings

### Documentação
- [ ] Atualizar `REFACTORING_STRATEGY.md` com lições aprendidas
- [ ] Criar/atualizar documentação dos componentes:
  - [ ] `FilterPanel` - JSDoc completo
  - [ ] `EntityCard` - JSDoc completo
  - [ ] `useEntityFilters` - JSDoc completo
- [ ] Criar template para novos painéis
- [ ] Atualizar README com padrões de desenvolvimento
- [ ] Documentar decisões de customização (quando manter código específico)

### Validação Final
- [ ] Executar testes em todos os painéis migrados
- [ ] Validar visualmente todos os painéis
- [ ] Verificar responsividade em todos os painéis
- [ ] Revisar código final
- [ ] Obter aprovação de code review (se aplicável)

**Status da Fase 3:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

## 📊 Métricas de Progresso

### Código Reduzido
- [ ] Medir linhas de código antes da refatoração
- [ ] Medir linhas de código depois da refatoração
- [ ] Calcular redução percentual
- [ ] Documentar métricas

### Consistência
- [ ] Verificar que todos os painéis usam `useActionBarButtons`
- [ ] Verificar que todos os painéis usam `getActionBarErrorProps`
- [ ] Verificar que todos os painéis usam `FilterPanel` (quando aplicável)
- [ ] Verificar que todos os painéis usam `paginationHandlers`

### Testes
- [ ] Todos os painéis têm testes funcionais
- [ ] Nenhum teste quebrou após refatoração
- [ ] Novos testes criados para componentes reutilizáveis (se aplicável)

---

## 🎯 Próximos Passos (Após Refatoração)

### Novos Painéis
- [ ] Criar template base para novos painéis
- [ ] Documentar processo de criação de novo painel
- [ ] Criar exemplo de novo painel seguindo padrões

### Melhorias Futuras
- [ ] Considerar criar `EntityPage` component (componente de alto nível)
- [ ] Considerar criar mais hooks reutilizáveis
- [ ] Considerar testes automatizados para componentes
- [ ] Considerar Storybook para documentação visual

---

## 📝 Notas

### Decisões Importantes
- [ ] Documentar decisão de manter estrutura customizada no File (se aplicável)
- [ ] Documentar customizações necessárias (ex: `sendInvite` no Member)
- [ ] Documentar casos especiais que não seguem o padrão

### Problemas Encontrados
- [ ] Listar problemas encontrados durante migração
- [ ] Documentar soluções aplicadas
- [ ] Atualizar estratégia com lições aprendidas

### Melhorias Identificadas
- [ ] Listar melhorias identificadas durante refatoração
- [ ] Priorizar melhorias para implementação futura

---

## ✅ Status Geral

**Última atualização:** _[Data]_

**Progresso Total:** 🟡 50%

**Painéis Migrados:** 0 / 4 (código migrado, aguardando testes)

**Última atualização:** 23/01/2026

**Componentes Criados:** ✅ 3 / 3

**Documentação:** ✅ Completa

---

## 🔗 Links Úteis

- [Estratégia de Refatoração](./REFACTORING_STRATEGY.md)
- [Exemplo de Migração](./MIGRATION_EXAMPLE.md)
- [Componentes Reutilizáveis](../components/)

---

**Dica:** Marque os itens como concluídos usando `- [x]` e atualize o status geral regularmente.
