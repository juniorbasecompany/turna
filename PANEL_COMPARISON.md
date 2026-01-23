# 📊 Diferenças entre os Painéis

Este documento lista apenas as **diferenças** entre os painéis. Todos os painéis já estão padronizados nos seguintes aspectos:
- ✅ `useEntityPage` para gerenciamento de estado e dados
- ✅ `EntityCard` + `CardFooter` para estrutura dos cards
- ✅ `EditForm` separado para edição
- ✅ `FilterPanel` para filtros
- ✅ `paginationHandlers` via `useEntityPage`
- ✅ Estrutura visual padronizada (Container `h-40 sm:h-48` com `border-blue-200` → Footer)
- ✅ Filtros vs Edição mutuamente exclusivos

---

## 🔍 Diferenças Identificadas

### 1. **Filtros**

| Painel | Tipo de Filtro |
|--------|----------------|
| **Hospital** | Texto (nome) |
| **Tenant** | Texto (nome) |
| **Member** | Seleção múltipla (`useEntityFilters`: Status + Role) |
| **Demand** | Texto (procedimento) |
| **File** | Seleção múltipla (`useEntityFilters`: Status) + Customizados (Hospital + Data) |

**Nota:** Member e File usam `additionalListParams` reativo no `useEntityPage` para suportar filtros dinâmicos.

---

### 2. **Botões do ActionBar**

| Painel | Implementação |
|--------|---------------|
| **Hospital** | Via `useEntityPage` (indireto) |
| **Tenant** | Via `useEntityPage` (indireto) |
| **Member** | `useActionBarButtons` (direto) |
| **Demand** | `useActionBarButtons` (direto) |
| **File** | `useActionBarButtons` (direto, com extensões para ações customizadas) |

**Nota:** Member, Demand e File usam `useActionBarButtons` diretamente porque precisam de customizações (Member: `sendInvite`, File: `selectedFilesForReading`).

---

### 3. **getActionBarErrorProps**

| Painel | Implementação |
|--------|---------------|
| **Hospital** | Via `useEntityPage` |
| **Tenant** | Via `useEntityPage` |
| **Member** | Via `useEntityPage` |
| **Demand** | Via `useEntityPage` |
| **File** | `getActionBarErrorProps` (direto) |

**Nota:** File usa diretamente porque precisa customizar para `showEditArea` e contagem de seleções duplas.

---

### 4. **Cor do Container do Card**

| Painel | Cor |
|--------|-----|
| **Hospital** | Cor dinâmica (`hospital.color`) |
| **Tenant** | Cor sólida azul (`bg-blue-50`) |
| **Member** | Cor sólida azul (`bg-blue-50`) |
| **Demand** | Cor dinâmica (`hospital.color`) |
| **File** | Cor dinâmica (`hospital.color`) |

**Padrão:** Todos usam `border-blue-200`. A cor de fundo pode ser dinâmica (baseada no hospital) ou sólida azul.

---

### 5. **Conteúdo Visual do Card**

| Painel | Ícone | Título | Badges/Status | Detalhes Adicionais |
|--------|-------|--------|---------------|---------------------|
| **Hospital** | SVG hospital | Nome do hospital | ❌ Não tem | ❌ Não tem |
| **Tenant** | SVG clínica | Nome da clínica | ❌ Não tem | Slug abaixo do nome |
| **Member** | SVG pessoas | Nome/email do member | ✅ Status + Role | Badges abaixo do nome |
| **Demand** | SVG documento | Procedimento | ✅ Pediátrica + Prioridade | Lista de detalhes (sala, datas, etc) |
| **File** | Thumbnail/ícone tipo arquivo | Nome do arquivo | ✅ Status com ícone + spinner | Topo (hospital + nome) + Thumbnail + Status + Metadados (data, tamanho) |

**Notas:**
- File usa thumbnail/ícone variável baseado no tipo de arquivo
- File tem estrutura mais complexa: topo com hospital + nome, thumbnail no meio, e status no final
- Member e Demand têm badges dentro do container
- Demand tem lista de detalhes adicionais fora do container principal

---

### 6. **Seleção Múltipla**

| Painel | Tipo |
|--------|------|
| **Hospital** | Exclusão apenas |
| **Tenant** | Exclusão apenas |
| **Member** | Exclusão apenas |
| **Demand** | Exclusão apenas |
| **File** | Exclusão + Leitura (seleção dupla) |

**Nota:** File tem duas seleções independentes:
- `selectedFiles` (via `useEntityPage`) para exclusão
- `selectedFilesForReading` (estado local) para leitura de conteúdo

---

### 7. **Ações Customizadas**

| Painel | Ações |
|--------|-------|
| **Hospital** | ❌ Não tem |
| **Tenant** | ❌ Não tem |
| **Member** | ✅ Enviar convite (checkbox no formulário) |
| **Demand** | ❌ Não tem |
| **File** | ✅ Ler conteúdo (botão no ActionBar) |

**Notas:**
- Member: Ação "Enviar convite" é um checkbox no formulário que dispara envio de email após salvar
- File: Ação "Ler conteúdo" aparece no ActionBar quando há arquivos selecionados para leitura

---

## 📝 Resumo das Diferenças

### Diferenças Justificadas (Mantidas)

1. **Cor do Container**: Hospital/Demand/File usam cor dinâmica (funcionalidade específica do hospital)
2. **Conteúdo do Card**: Cada painel tem informações específicas da entidade
3. **Filtros**: Cada painel tem filtros apropriados para sua entidade
4. **File**: Estrutura customizada mantida (thumbnail, status complexo, múltiplas seleções) - funcionalidade específica
5. **Member**: Ação "Enviar convite" - funcionalidade específica
6. **File**: Ação "Ler conteúdo" - funcionalidade específica

### Diferenças Técnicas (Implementação)

1. **useActionBarButtons**: Hospital/Tenant via `useEntityPage`, outros diretamente (devido a customizações)
2. **getActionBarErrorProps**: File usa diretamente (devido a `showEditArea` e seleções duplas)
3. **Filtros**: Member e File usam `additionalListParams` reativo para filtros dinâmicos

---

## ✅ Status de Padronização

Todos os painéis seguem o padrão base estabelecido. As diferenças listadas acima são:
- **Funcionalidades específicas** de cada entidade (justificadas)
- **Implementações técnicas** diferentes para suportar essas funcionalidades (necessárias)
