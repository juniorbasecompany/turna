# Plano: Reutilização de Código para Edição de Campos String

## Objetivo
Reutilizar o código e comportamento que funciona perfeitamente para campos numéricos vazios (null) e aplicar o mesmo padrão para campos string vazios, garantindo que ambos funcionem de forma idêntica.

## Análise do Comportamento Atual (Campos Numéricos)

### O que funciona:
1. **Detecção de valores vazios**: Campos com `null` ou `undefined` são detectados corretamente
2. **Placeholder tracejado**: Aparece corretamente com texto "Clique para editar"
3. **Edição inline**: Ao clicar, transforma em input editável
4. **Salvamento correto**: O valor digitado é salvo no lugar certo do JSON
5. **Re-renderização**: Após salvar, o valor aparece corretamente ao lado do título

### Componentes envolvidos:
- `JsonView.Null` - Para valores `null`
- `JsonView.Undefined` - Para valores `undefined`
- `JsonView.Int` - Para números inteiros
- `JsonView.Float` - Para números decimais

## Problema Identificado (Campos String)

### Situação atual:
- Campos string vazios (`""`) não estão mostrando placeholder tracejado
- A lógica de detecção de valores vazios pode não estar funcionando corretamente
- O salvamento pode estar deslocando valores para o final do objeto

## Tarefas a Implementar

### 1. Análise e Diagnóstico
- [ ] Verificar como o JsonView renderiza strings vazias (`""`)
- [ ] Confirmar se `JsonView.String` é chamado para strings vazias
- [ ] Verificar se há diferença no `path` (keys) passado para String vs Int/Null
- [ ] Testar se o problema é na detecção (`isEmpty`) ou no salvamento (`updateValueInObject`)
- [ ] Comparar o comportamento de `JsonView.String` com `JsonView.Null` quando ambos têm valores vazios

### 2. Unificação da Lógica de Detecção de Valores Vazios
- [ ] Criar função auxiliar `isValueEmpty(value)` que detecta:
  - `null`
  - `undefined`
  - String vazia (`""`)
  - String com apenas espaços (opcional)
- [ ] Aplicar a mesma função em todos os componentes (String, Int, Float, Null, Undefined)
- [ ] Garantir que a detecção seja consistente entre todos os tipos

### 3. Unificação da Lógica de Placeholder
- [ ] Extrair o componente de placeholder para uma função reutilizável
- [ ] Criar componente `EmptyValuePlaceholder` que recebe:
  - `pathKey`: identificador único do campo
  - `onClick`: handler para iniciar edição
  - `is_disabled`: flag de desabilitado
- [ ] Aplicar o mesmo placeholder em String, Int, Float, Null, Undefined
- [ ] Garantir que o texto "Clique para editar" apareça em todos

### 4. Unificação da Lógica de Edição
- [ ] Extrair o componente de input de edição para uma função reutilizável
- [ ] Criar componente `EditableInput` que recebe:
  - `type`: 'text' | 'number'
  - `value`: valor atual sendo editado
  - `onChange`: handler de mudança
  - `onBlur`: handler de saída (salvamento)
  - `onKeyDown`: handler de teclas (Enter/Escape)
  - `keys`: caminho do campo no JSON
  - `is_disabled`: flag de desabilitado
- [ ] Aplicar o mesmo componente em String, Int, Float, Null, Undefined
- [ ] Garantir que o salvamento use a mesma lógica (`updateValueInObject`)

### 5. Correção da Lógica de Salvamento para Strings
- [ ] Verificar se `updateValueInObject` funciona corretamente para strings
- [ ] Garantir que o `path` (keys) seja tratado da mesma forma para strings e números
- [ ] Testar salvamento de strings em diferentes níveis de aninhamento:
  - Nível raiz: `{"field": ""}`
  - Nível 1: `{"obj": {"field": ""}}`
  - Nível 2+: `{"obj": {"nested": {"field": ""}}}`
- [ ] Verificar se strings estão sendo salvas no lugar correto (não deslocando para o final)

### 6. Sincronização de Estado
- [ ] Garantir que `editingValue` seja inicializado corretamente para strings vazias
- [ ] Verificar se `setEditingValue('')` funciona corretamente ao clicar em placeholder de string
- [ ] Garantir que o valor digitado seja preservado durante a edição
- [ ] Verificar se o estado é limpo corretamente após salvar ou cancelar

### 7. Tratamento de Tipos após Edição
- [ ] Quando editar um campo `null` e digitar um número, garantir que seja salvo como número
- [ ] Quando editar um campo `null` e digitar uma string, garantir que seja salvo como string
- [ ] Quando editar um campo string vazio (`""`), garantir que seja salvo como string
- [ ] Considerar conversão automática de tipo quando apropriado (ex: "123" → 123 para campos numéricos)

### 8. Testes e Validação
- [ ] Testar edição de string vazia no nível raiz
- [ ] Testar edição de string vazia em objeto aninhado
- [ ] Testar edição de string vazia em múltiplos níveis de aninhamento
- [ ] Testar que o valor aparece no lugar correto após salvar
- [ ] Testar que o placeholder aparece corretamente para strings vazias
- [ ] Comparar comportamento lado a lado: string vazia vs número null
- [ ] Verificar que não há regressão no comportamento de números

### 9. Refatoração e Limpeza
- [ ] Remover código duplicado entre String, Int, Float, Null, Undefined
- [ ] Consolidar lógica comum em funções auxiliares
- [ ] Garantir que todos os componentes usem as mesmas funções auxiliares
- [ ] Adicionar comentários explicativos sobre o fluxo de edição
- [ ] Documentar como o `path` (keys) funciona e é usado

### 10. Casos Especiais
- [ ] Tratar strings com apenas espaços em branco
- [ ] Tratar conversão de string para número quando apropriado
- [ ] Tratar valores que mudam de tipo (null → string, null → number)
- [ ] Garantir que arrays vazios também tenham placeholder (se necessário)
- [ ] Garantir que objetos vazios também tenham placeholder (se necessário)

## Estrutura Proposta de Refatoração

### Funções Auxiliares a Criar:
1. `isValueEmpty(value: unknown): boolean` - Detecta valores vazios
2. `EmptyValuePlaceholder(props)` - Componente de placeholder reutilizável
3. `EditableInput(props)` - Componente de input de edição reutilizável
4. `useFieldEditing(pathKey, keys, initialValue)` - Hook customizado para gerenciar estado de edição

### Componentes a Unificar:
- `JsonView.String` - Usar funções auxiliares
- `JsonView.Int` - Usar funções auxiliares
- `JsonView.Float` - Usar funções auxiliares
- `JsonView.Null` - Usar funções auxiliares
- `JsonView.Undefined` - Usar funções auxiliares

## Ordem de Implementação Sugerida

1. **Fase 1 - Diagnóstico**: Tarefas 1 e 2 (análise e unificação de detecção)
2. **Fase 2 - Extração**: Tarefas 3 e 4 (criar componentes reutilizáveis)
3. **Fase 3 - Correção**: Tarefas 5 e 6 (corrigir salvamento e sincronização)
4. **Fase 4 - Refatoração**: Tarefas 7 e 9 (aplicar funções auxiliares e limpar código)
5. **Fase 5 - Validação**: Tarefas 8 e 10 (testes e casos especiais)

## Notas Importantes

- O comportamento de números está funcionando perfeitamente, então deve ser usado como referência
- A lógica de `updateValueInObject` parece estar correta, mas precisa ser validada para strings
- O `path` (keys) é crítico - deve ser tratado de forma idêntica para todos os tipos
- A sincronização de estado (`editingPath`, `editingValue`) deve ser consistente
- O re-render após salvar depende de `handleChange` atualizar `internalValue` corretamente
