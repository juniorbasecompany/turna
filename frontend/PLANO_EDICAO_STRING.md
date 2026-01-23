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

## Problema Identificado (Campos String e Arrays)

### Situação atual:
- Campos string vazios (`""`) não estão mostrando placeholder tracejado
- A lógica de detecção de valores vazios pode não estar funcionando corretamente
- **CRÍTICO**: O salvamento está deslocando valores para o final quando o campo está dentro de um array (ex: `demands[0].room`)
- A função `updateValueInObject` não trata arrays corretamente - ela converte arrays em objetos quando navega pelo path

### Problema Técnico Identificado:
A função `updateValueInObject` (linha 64-98) tem um bug crítico:
- Na linha 85, há uma verificação que exclui arrays: `!Array.isArray(current[key])`
- Quando o path contém um índice de array (ex: `['demands', 0, 'room']`), ao chegar em `demands[0]`, a função detecta que é um array e vai para o `else`, que cria um objeto vazio `{}` em vez de manter o array
- Isso corrompe a estrutura do JSON, convertendo arrays em objetos
- O tipo `Record<string, unknown>` não permite acessar arrays por índice numérico corretamente

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

### 5. Correção da Lógica de Salvamento (CRÍTICO - Arrays)
- [ ] **PRIORIDADE ALTA**: Corrigir `updateValueInObject` para tratar arrays corretamente
  - [ ] Mudar o tipo de retorno para aceitar tanto objetos quanto arrays na raiz
  - [ ] Detectar quando um elemento do path é um índice de array (número)
  - [ ] Manter arrays como arrays durante a navegação do path
  - [ ] Não converter arrays em objetos quando encontrar um índice numérico
  - [ ] Garantir que arrays sejam acessados por índice numérico, não por string
- [ ] Verificar se `updateValueInObject` funciona corretamente para strings
- [ ] Garantir que o `path` (keys) seja tratado da mesma forma para strings e números
- [ ] Testar salvamento em diferentes estruturas:
  - Nível raiz: `{"field": ""}`
  - Nível 1: `{"obj": {"field": ""}}`
  - Nível 2+: `{"obj": {"nested": {"field": ""}}}`
  - **Array nível 1**: `{"demands": [{"room": ""}]}` ← CASO PROBLEMÁTICO
  - **Array nível 2+**: `{"data": {"items": [{"field": ""}]}}`
- [ ] Verificar se valores estão sendo salvos no lugar correto (não deslocando para o final)
- [ ] Testar especificamente o caso `demands[0].room` que está falhando

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
- [ ] **PRIORIDADE ALTA**: Testar edição dentro de arrays:
  - [ ] `demands[0].room` (caso reportado pelo usuário)
  - [ ] `demands[1].room` (outros índices)
  - [ ] Arrays aninhados em múltiplos níveis
- [ ] Testar que o valor aparece no lugar correto após salvar (especialmente em arrays)
- [ ] Testar que o placeholder aparece corretamente para strings vazias
- [ ] Comparar comportamento lado a lado: string vazia vs número null
- [ ] Verificar que não há regressão no comportamento de números
- [ ] Verificar que arrays não são convertidos em objetos após edição

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
5. **`updateValueInObject(obj: unknown, path: (string | number)[], newValue: unknown): unknown`** - **REESCREVER COMPLETAMENTE**
   - Mudar tipo de entrada de `Record<string, unknown>` para `unknown`
   - Mudar tipo de retorno de `Record<string, unknown>` para `unknown`
   - Detectar se um elemento do path é número (índice de array) ou string (chave de objeto)
   - Manter arrays como arrays durante navegação
   - Acessar arrays por índice numérico: `array[index]` não `array[String(index)]`
   - Acessar objetos por chave string: `obj[key]`
   - Criar arrays quando necessário: `[]` não `{}`
   - Criar objetos quando necessário: `{}`

### Componentes a Unificar:
- `JsonView.String` - Usar funções auxiliares
- `JsonView.Int` - Usar funções auxiliares
- `JsonView.Float` - Usar funções auxiliares
- `JsonView.Null` - Usar funções auxiliares
- `JsonView.Undefined` - Usar funções auxiliares

## Ordem de Implementação Sugerida (ATUALIZADA)

1. **Fase 0 - Correção Crítica de Arrays**: Tarefa 5 (corrigir `updateValueInObject` para arrays) ← **FAZER PRIMEIRO**
2. **Fase 1 - Diagnóstico**: Tarefas 1 e 2 (análise e unificação de detecção)
3. **Fase 2 - Extração**: Tarefas 3 e 4 (criar componentes reutilizáveis)
4. **Fase 3 - Correção**: Tarefas 5 (restante) e 6 (corrigir salvamento e sincronização)
5. **Fase 4 - Refatoração**: Tarefas 7 e 9 (aplicar funções auxiliares e limpar código)
6. **Fase 5 - Validação**: Tarefas 8 e 10 (testes e casos especiais)

## Notas Importantes

- O comportamento de números está funcionando perfeitamente, então deve ser usado como referência
- **CRÍTICO**: A lógica de `updateValueInObject` tem um bug que corrompe arrays - precisa ser corrigida primeiro
- O `path` (keys) pode conter números (índices de array) e strings (chaves de objeto) - ambos devem ser tratados corretamente
- Quando o path contém um número, significa que estamos acessando um array, não um objeto
- A função atual usa `Record<string, unknown>` que não é adequada para arrays - precisa aceitar `unknown` ou um tipo union
- A sincronização de estado (`editingPath`, `editingValue`) deve ser consistente
- O re-render após salvar depende de `handleChange` atualizar `internalValue` corretamente
- O JsonView passa `keys` como `(string | number)[]` - números indicam índices de array

## Detalhes Técnicos da Correção de Arrays

### Problema na Linha 85:
```typescript
if (typeof current[key] === 'object' && current[key] !== null && !Array.isArray(current[key])) {
    current = current[key] as Record<string, unknown>
} else {
    current[key] = {}  // ← BUG: Cria objeto mesmo quando deveria ser array
    current = current[key] as Record<string, unknown>
}
```

### Solução Proposta:
1. Detectar se o próximo elemento do path é número ou string
2. Se for número e o elemento atual não for array, criar array: `[]`
3. Se for string e o elemento atual não for objeto, criar objeto: `{}`
4. Manter o tipo correto durante toda a navegação
5. Acessar arrays por índice numérico: `arr[0]` não `arr['0']`
6. Acessar objetos por chave string: `obj['key']`

### Pseudocódigo da Correção:
```
function updateValueInObject(obj, path, newValue):
    result = deepCopy(obj)
    
    if path is empty: return result
    
    current = result
    
    for i in 0..path.length-2:  // Todos exceto o último
        key = path[i]
        nextKey = path[i+1]
        
        if current[key] is undefined:
            // Criar estrutura baseada no próximo elemento
            if nextKey is number:
                current[key] = []  // Array
            else:
                current[key] = {}  // Objeto
        
        if nextKey is number:
            // Próximo é índice de array
            if current[key] is not array:
                current[key] = []  // Converter para array
            current = current[key]  // Navegar no array
        else:
            // Próximo é chave de objeto
            if current[key] is not object or is array:
                current[key] = {}  // Converter para objeto
            current = current[key]  // Navegar no objeto
    
    // Atualizar valor final
    finalKey = path[path.length-1]
    if finalKey is number:
        // Acessar array por índice
        if current is not array:
            current = []  // Converter para array
        current[finalKey] = newValue
    else:
        // Acessar objeto por chave
        if current is not object or is array:
            current = {}  // Converter para objeto
        current[finalKey] = newValue
    
    return result
```
