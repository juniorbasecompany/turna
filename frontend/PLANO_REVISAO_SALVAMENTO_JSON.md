# Plano: Revisão do Fluxo de Salvamento do JSON

## Objetivo
Garantir que o componente `JsonEditor` devolva o JSON corretamente quando o botão "Salvar" é clicado, permitindo que o valor seja gravado como qualquer outro campo do formulário.

## Análise do Fluxo Atual

### 1. Estado e Inicialização
- **Estado `jsonContent`**: String JSON (linha 693)
- **Estado `originalJsonContent`**: String JSON para comparação (linha 694)
- **Carregamento inicial**: `fetchFileJson` retorna string JSON formatada (linha 849-851)

### 2. Uso do JsonEditor
- **Linha 1451-1465**: JsonEditor é renderizado
- **Prop `value`**: Objeto JSON (parse de `jsonContent`)
- **Prop `on_change`**: Callback que recebe objeto e converte para string JSON
  ```typescript
  on_change={(value) => {
      setJsonContent(JSON.stringify(value, null, 2))
  }}
  ```

### 3. Fluxo de Salvamento (handleSave)
- **Linha 870-917**: Função `handleSave`
- **Validação**: Parse de `jsonContent` (string) para objeto (linha 879)
- **Envio**: Envia `parsedJson` (objeto) para API (linha 896)
- **Atualização**: Atualiza `originalJsonContent` com `jsonContent` (linha 901)

## Problemas Potenciais Identificados

### 1. Sincronização de Estado
- **Problema**: O `JsonEditor` mantém estado interno (`internalValue`)
- **Risco**: Pode haver dessincronização entre o estado interno do componente e o estado `jsonContent` do pai
- **Cenário**: Usuário edita no JsonEditor, mas o estado `jsonContent` não é atualizado antes do clique em "Salvar"

### 2. Timing do Callback `on_change`
- **Problema**: O `on_change` é chamado a cada edição individual de campo
- **Risco**: Se o usuário editar rapidamente e clicar em "Salvar", pode haver race condition
- **Cenário**: Última edição ainda não atualizou `jsonContent` quando `handleSave` é executado

### 3. Formatação do JSON
- **Problema**: `JSON.stringify(value, null, 2)` sempre formata com indentação
- **Risco**: Pode alterar a formatação original, mesmo que o conteúdo seja o mesmo
- **Cenário**: Comparação `jsonContent !== originalJsonContent` pode falhar por diferença de formatação

### 4. Validação de JSON
- **Problema**: Validação só acontece no `handleSave`
- **Risco**: Se o JSON estiver inválido, o usuário só descobre ao tentar salvar
- **Cenário**: Usuário edita e cria JSON inválido, tenta salvar, recebe erro

### 5. Estado Interno do JsonEditor
- **Problema**: `JsonEditor` mantém `internalValue` que pode divergir do `value` prop
- **Risco**: Se o `value` prop mudar externamente, o `internalValue` pode não refletir a mudança
- **Cenário**: Outro código atualiza `jsonContent`, mas `JsonEditor` não reflete a mudança

## Tarefas de Revisão

### 1. Verificar Sincronização de Estado
- [ ] Confirmar que `on_change` é chamado imediatamente após cada edição
- [ ] Verificar se há delay ou debounce no callback
- [ ] Testar edição rápida seguida de clique em "Salvar"
- [ ] Garantir que o estado `jsonContent` está sempre atualizado

### 2. Revisar Callback `on_change`
- [ ] Verificar se o callback está sendo chamado corretamente
- [ ] Confirmar que o valor retornado é o objeto completo atualizado
- [ ] Testar se edições múltiplas são capturadas corretamente
- [ ] Verificar se não há perda de dados entre edições

### 3. Garantir Valor no Momento do Salvamento
- [ ] Opção A: Usar `useRef` para manter referência ao valor mais recente
- [ ] Opção B: Forçar atualização do estado antes de salvar
- [ ] Opção C: Obter valor diretamente do JsonEditor via ref
- [ ] Implementar a solução escolhida

### 4. Melhorar Validação
- [ ] Validar JSON em tempo real durante edição
- [ ] Mostrar indicador visual de JSON inválido
- [ ] Desabilitar botão "Salvar" se JSON estiver inválido
- [ ] Mostrar mensagem de erro específica sobre o problema no JSON

### 5. Revisar Comparação de Mudanças
- [ ] Normalizar JSON antes de comparar (remover espaços/formatação)
- [ ] Usar comparação profunda de objetos em vez de strings
- [ ] Garantir que `hasChanges()` funcione corretamente

### 6. Testar Casos Especiais
- [ ] Editar campo dentro de array (ex: `demands[0].room`)
- [ ] Editar múltiplos campos rapidamente
- [ ] Salvar imediatamente após edição
- [ ] Cancelar e reabrir edição (deve manter valores)
- [ ] Editar, fechar sem salvar, reabrir (deve restaurar original)

### 7. Revisar Componente JsonEditor
- [ ] Verificar se `handleChange` está sendo chamado corretamente
- [ ] Confirmar que `on_change` prop recebe o valor atualizado
- [ ] Verificar sincronização entre `internalValue` e `value` prop
- [ ] Garantir que mudanças externas ao `value` prop são refletidas

### 8. Documentar Fluxo de Dados
- [ ] Documentar como o valor flui do JsonEditor para o estado
- [ ] Documentar como o valor é enviado para a API
- [ ] Criar diagrama de fluxo de dados
- [ ] Adicionar comentários explicativos no código

## Soluções Propostas

### Solução 1: Usar Ref para Acesso Direto ao Valor
```typescript
const jsonEditorRef = useRef<{ getValue: () => unknown } | null>(null)

// No JsonEditor, expor método getValue via ref
// No handleSave, obter valor diretamente: const currentValue = jsonEditorRef.current?.getValue()
```

**Vantagens**: Acesso direto ao valor mais recente, sem depender de estado
**Desvantagens**: Requer modificação do JsonEditor para expor método

### Solução 2: Forçar Atualização Antes de Salvar
```typescript
const handleSave = async () => {
    // Aguardar um tick para garantir que todos os callbacks foram processados
    await new Promise(resolve => setTimeout(resolve, 0))
    
    // Agora usar jsonContent que deve estar atualizado
    // ...
}
```

**Vantagens**: Simples, não requer mudanças no JsonEditor
**Desvantagens**: Hacky, pode não funcionar em todos os casos

### Solução 3: Usar useRef para Valor Mais Recente
```typescript
const jsonContentRef = useRef<string>('')

// Atualizar ref sempre que jsonContent mudar
useEffect(() => {
    jsonContentRef.current = jsonContent
}, [jsonContent])

// No handleSave, usar jsonContentRef.current
```

**Vantagens**: Sempre tem o valor mais recente, mesmo se houver race condition
**Desvantagens**: Pode mascarar problemas de sincronização

### Solução 4: Melhorar JsonEditor para Garantir Sincronização
- Adicionar `useEffect` para sincronizar `internalValue` com `value` prop
- Garantir que `on_change` é chamado de forma síncrona
- Adicionar método `getValue()` para acesso direto ao valor

**Vantagens**: Solução mais robusta e reutilizável
**Desvantagens**: Requer mais trabalho de implementação

## Ordem de Implementação Sugerida

1. **Fase 1 - Diagnóstico**: Tarefas 1, 2, 7 (verificar sincronização e callbacks)
2. **Fase 2 - Correção Imediata**: Tarefa 3 (garantir valor no salvamento) - usar Solução 3 (useRef)
3. **Fase 3 - Melhorias**: Tarefas 4, 5 (validação e comparação)
4. **Fase 4 - Testes**: Tarefa 6 (testar casos especiais)
5. **Fase 5 - Refatoração**: Tarefa 8 (documentação) e considerar Solução 4 (melhorar JsonEditor)

## Notas Importantes

- O `JsonEditor` usa `internalValue` que pode divergir do `value` prop
- O callback `on_change` é chamado a cada edição individual, não apenas no blur
- A comparação de mudanças usa strings, o que pode ser afetado por formatação
- O estado `jsonContent` é uma string, enquanto o JsonEditor trabalha com objetos
- A conversão objeto → string acontece no callback `on_change`
- A conversão string → objeto acontece no `handleSave` e na prop `value`

## Questões a Responder

1. O `on_change` está sendo chamado imediatamente após cada edição?
2. Há algum delay ou debounce que pode causar perda de dados?
3. O estado `jsonContent` está sempre sincronizado com as edições?
4. A comparação de mudanças está funcionando corretamente?
5. O valor enviado para a API é o valor mais recente editado?
6. Há algum caso onde o JSON pode estar inválido sem o usuário saber?
