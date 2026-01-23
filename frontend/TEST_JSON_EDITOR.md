# Checklist de Teste - JsonEditor

Este documento contém o checklist de testes manuais para a funcionalidade de substituição do textarea por Tree Editor JSON usando `@uiw/react-json-view`.

## 1. Instalação e Build

- [ ] Executar `npm install` no diretório `frontend`
- [ ] Verificar se não há erros de build
- [ ] Verificar se a dependência `@uiw/react-json-view@^2.0.0-alpha.41` foi instalada corretamente
- [ ] Executar `npm run build` e verificar se compila sem erros
- [ ] Executar `npm run dev` e verificar se o servidor inicia corretamente

## 2. Visualização Básica

- [ ] Abrir a página de Members (`/member`)
- [ ] Clicar em "Criar" ou "Editar" um member existente
- [ ] Verificar se o editor em árvore aparece no lugar do textarea antigo
- [ ] Verificar se o JSON é exibido corretamente em formato árvore
- [ ] Verificar se é possível expandir nós clicando nas setas
- [ ] Verificar se é possível colapsar nós clicando nas setas
- [ ] Verificar se os tipos de dados são exibidos corretamente (string, int, float, boolean, null, etc.)
- [ ] Verificar se o tamanho dos objetos/arrays é exibido corretamente

## 3. Funcionalidades do Editor

- [ ] Verificar se o botão "Voltar" aparece acima do editor
- [ ] Verificar se o botão "Limpar" aparece acima do editor
- [ ] Verificar se o indicador "Alterações não salvas" aparece quando há mudanças
- [ ] Verificar se o indicador desaparece quando não há mudanças

## 4. Botões de Ação

### Botão "Voltar"
- [ ] Fazer alterações no JSON (via edição manual do objeto, se disponível)
- [ ] Clicar em "Voltar"
- [ ] Verificar se o valor volta ao estado inicial (vindo do backend)
- [ ] Verificar se o botão "Voltar" fica desabilitado quando não há mudanças
- [ ] Verificar se o botão "Voltar" fica desabilitado quando `is_disabled=true`

### Botão "Limpar"
- [ ] Clicar em "Limpar"
- [ ] Verificar se o valor é definido como `{}` (objeto vazio)
- [ ] Verificar se o botão "Limpar" fica desabilitado quando `is_disabled=true`
- [ ] Verificar se o indicador "Alterações não salvas" aparece após limpar

## 5. Validação

- [ ] Tentar salvar com objeto vazio `{}` (deve validar e permitir, já que é um objeto válido)
- [ ] Verificar se mensagens de erro aparecem corretamente quando necessário
- [ ] Verificar se o salvamento funciona com objeto válido
- [ ] Verificar se a validação impede salvar com `null` ou `undefined` como attribute
- [ ] Verificar se a validação impede salvar com array no lugar de objeto

## 6. Compatibilidade de Dados

### Objeto Vazio
- [ ] Criar um novo member com attribute `{}`
- [ ] Salvar e verificar se foi salvo corretamente
- [ ] Editar o member e verificar se o objeto vazio é exibido corretamente

### Arrays Aninhados
- [ ] Criar/editar member com attribute contendo arrays:
  ```json
  {
    "skill_list": ["skill1", "skill2", "skill3"]
  }
  ```
- [ ] Verificar se o array é exibido corretamente
- [ ] Verificar se é possível expandir/colapsar o array
- [ ] Salvar e verificar se foi salvo corretamente

### Objetos Aninhados
- [ ] Criar/editar member com attribute contendo objetos aninhados:
  ```json
  {
    "restriction": {
      "no_obstetric": true,
      "max_complexity": 3
    }
  }
  ```
- [ ] Verificar se o objeto aninhado é exibido corretamente
- [ ] Verificar se é possível expandir/colapsar o objeto aninhado
- [ ] Salvar e verificar se foi salvo corretamente

### Diferentes Tipos de Dados
- [ ] Testar com string: `{"name": "teste"}`
- [ ] Testar com number: `{"age": 30}`
- [ ] Testar com boolean: `{"active": true}`
- [ ] Testar com null: `{"value": null}`
- [ ] Testar com combinação: `{"name": "teste", "age": 30, "active": true, "value": null}`
- [ ] Verificar se todos os tipos são exibidos e salvos corretamente

## 7. Estados e Comportamento

### Estado Desabilitado
- [ ] Verificar se o editor fica desabilitado durante `submitting=true`
- [ ] Verificar se os botões ficam desabilitados durante `submitting=true`
- [ ] Verificar se a aparência visual indica estado desabilitado (opacity, cursor)

### Preservação de Estado
- [ ] Fazer alterações no attribute
- [ ] Clicar em "Cancelar" (sem salvar)
- [ ] Verificar se o estado volta ao valor original
- [ ] Abrir novamente a edição e verificar se o valor original é exibido

### Reset Após Salvar
- [ ] Fazer alterações e salvar com sucesso
- [ ] Verificar se o estado é resetado após salvar
- [ ] Verificar se o indicador "Alterações não salvas" desaparece após salvar
- [ ] Verificar se o valor inicial é atualizado após salvar

## 8. Acessibilidade

- [ ] Verificar se o `id` do campo é aplicado corretamente
- [ ] Verificar se o label está associado ao campo (via `htmlFor` ou `aria-labelledby`)
- [ ] Verificar se os botões têm labels descritivos
- [ ] Testar navegação por teclado (Tab, Enter, etc.)
- [ ] Verificar se há feedback visual adequado para estados (disabled, hover, focus)

## 9. Integração com Backend

### Criação
- [ ] Criar um novo member com attribute JSON válido
- [ ] Verificar se o objeto é enviado corretamente ao backend (não como string)
- [ ] Verificar se o backend recebe e salva corretamente
- [ ] Verificar se após salvar, o valor é exibido corretamente ao editar

### Edição
- [ ] Editar um member existente com attribute
- [ ] Modificar o attribute
- [ ] Salvar e verificar se as mudanças foram persistidas
- [ ] Recarregar a página e verificar se o valor salvo é exibido corretamente

### Compatibilidade com Dados Existentes
- [ ] Verificar se members existentes (criados com textarea) são exibidos corretamente
- [ ] Verificar se é possível editar members antigos sem problemas
- [ ] Verificar se não há quebra de dados ao migrar do formato antigo

## 10. Casos Extremos

- [ ] Testar com objeto muito grande (muitas propriedades)
- [ ] Testar com objetos muito profundos (muitos níveis de aninhamento)
- [ ] Testar com strings muito longas
- [ ] Testar com caracteres especiais em chaves e valores
- [ ] Testar com valores numéricos muito grandes
- [ ] Testar com valores numéricos negativos
- [ ] Testar com valores decimais

## 11. Performance

- [ ] Verificar se não há lag ao expandir/colapsar nós
- [ ] Verificar se não há lag ao fazer mudanças
- [ ] Verificar se não há memory leaks ao abrir/fechar o formulário várias vezes
- [ ] Verificar se o componente não causa re-renders desnecessários

## 12. Responsividade

- [ ] Testar em diferentes tamanhos de tela (mobile, tablet, desktop)
- [ ] Verificar se o editor se adapta ao tamanho da tela
- [ ] Verificar se a altura configurada (400px) é respeitada
- [ ] Verificar se há scroll quando o conteúdo é maior que a altura

## 13. Erros e Edge Cases

- [ ] Verificar tratamento de erro quando o backend retorna attribute inválido
- [ ] Verificar tratamento de erro quando há problema de rede ao salvar
- [ ] Verificar se mensagens de erro são exibidas corretamente
- [ ] Verificar se o estado não fica corrompido após um erro

## Notas

- A funcionalidade de edição inline ainda está em desenvolvimento na biblioteca `@uiw/react-json-view` v2
- Atualmente, o componente oferece visualização em árvore com botões de ação (Voltar/Limpar)
- Quando a edição inline estiver disponível na biblioteca, será necessário atualizar o componente para suportá-la

## Resultado Esperado

Após todos os testes, o JsonEditor deve:
- Substituir completamente o textarea antigo
- Oferecer melhor UX com visualização em árvore
- Manter compatibilidade com dados existentes
- Funcionar corretamente em todos os cenários de uso
- Ser acessível e responsivo
