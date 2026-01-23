# ✅ Checklist de Refatoração dos Painéis

Este checklist deve ser usado para acompanhar o progresso da refatoração dos painéis para usar componentes reutilizáveis.

---

## 📋 Fase 1: Preparação (Sem Breaking Changes)

### Componentes Base
- [ ] ✅ `FilterPanel.tsx` criado e testado
- [ ] ✅ `EntityCard.tsx` criado e testado
- [ ] ✅ `useEntityFilters.ts` criado e testado
- [ ] ✅ Documentação criada (`REFACTORING_STRATEGY.md`)
- [ ] ✅ Exemplo de migração criado (`MIGRATION_EXAMPLE.md`)

### Testes dos Componentes
- [ ] Testar `FilterPanel` em isolamento
- [ ] Testar `EntityCard` em isolamento
- [ ] Testar `useEntityFilters` em isolamento
- [ ] Validar que os componentes seguem padrões visuais existentes
- [ ] Criar página de teste (`/test-entity-page`) se necessário

**Status da Fase 1:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

## 📋 Fase 2: Migração Gradual

### 2.1 Migração do Painel Hospital

**Prioridade:** Alta (mais simples, já usa `useEntityPage`)

#### Preparação
- [ ] Revisar código atual do painel Hospital
- [ ] Identificar o que já está usando componentes reutilizáveis
- [ ] Identificar o que precisa ser migrado

#### Migração
- [ ] Substituir estrutura de filtros por `FilterPanel` (se aplicável)
- [ ] Substituir cards por `EntityCard` (se necessário)
- [ ] Validar que `useActionBarButtons` está sendo usado corretamente
- [ ] Validar que `getActionBarErrorProps` está sendo usado corretamente

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

**Status do Hospital:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

### 2.2 Migração do Painel Member

**Prioridade:** Alta (padrão para outros painéis)

#### Preparação
- [ ] Revisar código atual do painel Member
- [ ] Identificar todas as áreas de código repetido
- [ ] Criar branch: `refactor/member-page`

#### Migração - Lógica de Botões
- [ ] Adicionar import: `useActionBarButtons`
- [ ] Substituir lógica manual de botões (linhas 747-777)
- [ ] Ajustar para suportar `sendInvite` (customização necessária)
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [ ] Adicionar import: `getActionBarErrorProps`
- [ ] Substituir lógica manual de erro (linhas 714-746)
- [ ] Ajustar para suportar `emailMessage` e `emailMessageType`
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [ ] Adicionar imports: `FilterPanel`, `useEntityFilters`
- [ ] Substituir estado manual de filtros por `useEntityFilters`
- [ ] Substituir estrutura de filtros (linhas 611-633) por `FilterPanel`
- [ ] Atualizar `FilterButtons` para usar hooks
- [ ] Testar filtros funcionam corretamente

#### Migração - Cards (Opcional)
- [ ] Adicionar import: `EntityCard`
- [ ] Substituir estrutura manual de cards por `EntityCard`
- [ ] Manter customização visual (ícone, badges)
- [ ] Testar cards renderizam corretamente

#### Migração - Paginação
- [ ] Verificar se está usando `paginationHandlers` do hook
- [ ] Se não, migrar para usar `paginationHandlers`
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
- [ ] Revisar código atual do painel Demand
- [ ] Identificar todas as áreas de código repetido
- [ ] Criar branch: `refactor/demand-page`

#### Migração - Lógica de Botões
- [ ] Adicionar import: `useActionBarButtons`
- [ ] Substituir lógica manual de botões (linhas 735-767)
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [ ] Adicionar import: `getActionBarErrorProps`
- [ ] Substituir lógica manual de erro (linhas 680-710)
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [ ] Verificar se Demand tem filtros
- [ ] Se sim, migrar para `FilterPanel` e `useEntityFilters`
- [ ] Testar filtros funcionam corretamente

#### Migração - Cards (Opcional)
- [ ] Adicionar import: `EntityCard`
- [ ] Substituir estrutura manual de cards por `EntityCard`
- [ ] Manter customização visual
- [ ] Testar cards renderizam corretamente

#### Migração - Paginação
- [ ] Verificar se está usando `paginationHandlers`
- [ ] Se não, migrar para usar `paginationHandlers`
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

**Status do Demand:** ⬜ Não iniciado / 🟡 Em progresso / ✅ Completo

---

### 2.4 Migração do Painel File

**Prioridade:** Baixa (mais complexo, pode manter estrutura customizada)

#### Preparação
- [ ] Revisar código atual do painel File
- [ ] Identificar o que pode ser migrado
- [ ] Identificar o que deve permanecer customizado
- [ ] Criar branch: `refactor/file-page`

#### Migração - Lógica de Botões
- [ ] Adicionar import: `useActionBarButtons`
- [ ] Substituir lógica manual de botões (linhas 1768-1791)
- [ ] Ajustar para suportar `showEditArea` e `selectedFilesForReading`
- [ ] Testar botões aparecem corretamente

#### Migração - Lógica de Erro
- [ ] Adicionar import: `getActionBarErrorProps`
- [ ] Substituir lógica manual de erro (linhas 1747-1767)
- [ ] Ajustar para suportar `showEditArea`
- [ ] Testar mensagens de erro aparecem corretamente

#### Migração - Filtros
- [ ] Adicionar imports: `FilterPanel`, `useEntityFilters`
- [ ] Substituir estrutura de filtros (linhas 1349-1415) por `FilterPanel`
- [ ] Migrar filtros de status para `useEntityFilters`
- [ ] Manter filtros de data e hospital (customizados)
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

**Progresso Total:** ⬜ 0% / 🟡 25% / 🟡 50% / 🟡 75% / ✅ 100%

**Painéis Migrados:** 0 / 4

**Componentes Criados:** ✅ 3 / 3

**Documentação:** ✅ Completa

---

## 🔗 Links Úteis

- [Estratégia de Refatoração](./REFACTORING_STRATEGY.md)
- [Exemplo de Migração](./MIGRATION_EXAMPLE.md)
- [Componentes Reutilizáveis](../components/)

---

**Dica:** Marque os itens como concluídos usando `- [x]` e atualize o status geral regularmente.
