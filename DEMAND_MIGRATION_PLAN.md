# 📋 Plano de Migração: Demand para `useEntityPage`

## Resumo

Migrar o painel Demand de carregamento manual para `useEntityPage`, mantendo todas as funcionalidades existentes.

---

## ✅ O que já está compatível

1. ✅ **Tipos existentes**: `DemandFormData`, `DemandCreateRequest`, `DemandUpdateRequest` já existem
2. ✅ **Estrutura de formulário**: Já usa `EditForm` separado
3. ✅ **Componentes**: Já usa `EntityCard`, `CardFooter`, `FilterPanel`
4. ✅ **Hooks auxiliares**: Já usa `useActionBarButtons`, `usePagination`
5. ✅ **Validações**: Lógica de validação já implementada

---

## 🔧 Ajustes Necessários

### 1. **Remover Estado Manual de Carregamento**

**Remover:**
```typescript
// ❌ REMOVER
const [demands, setDemands] = useState<DemandResponse[]>([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState<string | null>(null)
const loadDemands = async () => { ... }
useEffect(() => {
    loadDemands()
}, [pagination])
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    items: demands,  // Substitui demands
    loading,         // Substitui loading
    error,           // Substitui error
    setError,        // Substitui setError
    // ... outros retornos do hook
} = useEntityPage({...})
```

---

### 2. **Remover Estado Manual de Formulário**

**Remover:**
```typescript
// ❌ REMOVER
const [formData, setFormData] = useState<DemandFormData>({...})
const [originalFormData, setOriginalFormData] = useState<DemandFormData>({...})
const [editingDemand, setEditingDemand] = useState<DemandResponse | null>(null)
const [showEditArea, setShowEditArea] = useState(false)
const [submitting, setSubmitting] = useState(false)
const isEditing = showEditArea
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    formData,           // Substitui formData
    setFormData,        // Substitui setFormData
    editingItem: editingDemand,  // Substitui editingDemand
    isEditing,          // Substitui isEditing
    submitting,         // Substitui submitting
    // ... outros retornos
} = useEntityPage({...})
```

---

### 3. **Remover Estado Manual de Seleção**

**Remover:**
```typescript
// ❌ REMOVER
const [selectedDemands, setSelectedDemands] = useState<Set<number>>(new Set())
const toggleDemandSelection = (demandId: number) => { ... }
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    selectedItems: selectedDemands,  // Substitui selectedDemands
    toggleSelection: toggleDemandSelection,  // Substitui toggleDemandSelection
    selectedCount: selectedDemandsCount,    // Substitui selectedDemands.size
    // ... outros retornos
} = useEntityPage({...})
```

---

### 4. **Remover Handlers Manuais**

**Remover:**
```typescript
// ❌ REMOVER
const handleCreateClick = () => { ... }
const handleEditClick = (demand: DemandResponse) => { ... }
const handleCancel = () => { ... }
const handleSave = async () => { ... }
const handleDeleteSelected = async () => { ... }
const hasChanges = () => { ... }
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    handleCreateClick,      // Substitui handleCreateClick
    handleEditClick,        // Substitui handleEditClick (mas precisa customizar)
    handleCancel,          // Substitui handleCancel (mas precisa customizar)
    handleSave,            // Substitui handleSave
    handleDeleteSelected,  // Substitui handleDeleteSelected
    hasChanges,            // Substitui hasChanges
    // ... outros retornos
} = useEntityPage({...})
```

**Nota**: `handleEditClick` e `handleCancel` precisam de customização para lidar com `skillsInput`.

---

### 5. **Implementar Mapeamentos**

**Adicionar:**
```typescript
// ✅ ADICIONAR
const mapEntityToFormData = (demand: DemandResponse): DemandFormData => {
    return {
        hospital_id: demand.hospital_id,
        job_id: demand.job_id,
        room: demand.room || '',
        start_time: demand.start_time ? new Date(demand.start_time) : null,
        end_time: demand.end_time ? new Date(demand.end_time) : null,
        procedure: demand.procedure,
        anesthesia_type: demand.anesthesia_type || '',
        complexity: demand.complexity || '',
        skills: demand.skills || [],
        priority: demand.priority,
        is_pediatric: demand.is_pediatric,
        notes: demand.notes || '',
        source: demand.source,
    }
}

const mapFormDataToCreateRequest = (formData: DemandFormData): DemandCreateRequest => {
    const startIso = formData.start_time?.toISOString()
    const endIso = formData.end_time?.toISOString()
    
    return {
        hospital_id: formData.hospital_id,
        job_id: formData.job_id,
        room: formData.room.trim() || null,
        start_time: startIso!,
        end_time: endIso!,
        procedure: formData.procedure.trim(),
        anesthesia_type: formData.anesthesia_type.trim() || null,
        complexity: formData.complexity.trim() || null,
        skills: formData.skills.length > 0 ? formData.skills : null,
        priority: formData.priority || null,
        is_pediatric: formData.is_pediatric,
        notes: formData.notes.trim() || null,
        source: formData.source,
    }
}

const mapFormDataToUpdateRequest = (formData: DemandFormData): DemandUpdateRequest => {
    const startIso = formData.start_time?.toISOString()
    const endIso = formData.end_time?.toISOString()
    
    return {
        hospital_id: formData.hospital_id,
        job_id: formData.job_id,
        room: formData.room.trim() || null,
        start_time: startIso!,
        end_time: endIso!,
        procedure: formData.procedure.trim(),
        anesthesia_type: formData.anesthesia_type.trim() || null,
        complexity: formData.complexity.trim() || null,
        skills: formData.skills.length > 0 ? formData.skills : null,
        priority: formData.priority || null,
        is_pediatric: formData.is_pediatric,
        notes: formData.notes.trim() || null,
        source: formData.source,
    }
}
```

---

### 6. **Implementar Validação**

**Adicionar:**
```typescript
// ✅ ADICIONAR
const validateFormData = (formData: DemandFormData): string | null => {
    if (!formData.procedure.trim()) {
        return 'Procedimento é obrigatório'
    }
    
    if (!formData.start_time || !formData.end_time) {
        return 'Data/hora de início e fim são obrigatórias'
    }
    
    if (formData.end_time <= formData.start_time) {
        return 'Data/hora de fim deve ser maior que a de início'
    }
    
    return null
}
```

---

### 7. **Implementar isEmptyCheck**

**Adicionar:**
```typescript
// ✅ ADICIONAR
const isEmptyCheck = (formData: DemandFormData): boolean => {
    return (
        formData.procedure.trim() === '' &&
        formData.start_time === null &&
        formData.end_time === null &&
        formData.hospital_id === null &&
        formData.room.trim() === ''
    )
}
```

---

### 8. **Lidar com Filtro de Procedimento**

**Opção A: Filtro no Frontend (Recomendado para início)**
```typescript
// ✅ MANTER filtro no frontend
const filteredDemands = useMemo(() => {
    if (!procedureFilter.trim()) {
        return demands  // demands vem do useEntityPage
    }
    const filterLower = procedureFilter.toLowerCase().trim()
    return demands.filter((demand) => 
        demand.procedure.toLowerCase().includes(filterLower)
    )
}, [demands, procedureFilter])
```

**Opção B: Filtro no Backend (Futuro)**
```typescript
// ⚠️ FUTURO: Mover filtro para backend
const { items: demands } = useEntityPage({
    // ...
    additionalListParams: procedureFilter 
        ? { procedure: procedureFilter } 
        : undefined,
})
```

**Recomendação**: Começar com Opção A (filtro no frontend), depois migrar para Opção B se necessário.

---

### 9. **Manter Carregamento de Hospitais Separado**

**Manter:**
```typescript
// ✅ MANTER (não afeta useEntityPage)
const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
const [loadingHospitals, setLoadingHospitals] = useState(true)

const loadHospitals = async () => {
    // ... código existente
}

useEffect(() => {
    loadHospitals()
}, [])
```

**Razão**: Hospitais são uma lista auxiliar, não a entidade principal gerenciada pelo `useEntityPage`.

---

### 10. **Customizar handleEditClick para skillsInput**

**Problema**: `useEntityPage` não gerencia `skillsInput` (estado local para input de skills)

**Solução**: Criar wrapper customizado
```typescript
// ✅ ADICIONAR
const [skillsInput, setSkillsInput] = useState('')

// Wrapper customizado para handleEditClick
const handleEditClickCustom = (demand: DemandResponse) => {
    handleEditClick(demand)  // Chama o handleEditClick do useEntityPage
    setSkillsInput((demand.skills || []).join(', '))  // Atualiza skillsInput
}

// Wrapper customizado para handleCancel
const handleCancelCustom = () => {
    handleCancel()  // Chama o handleCancel do useEntityPage
    setSkillsInput('')  // Limpa skillsInput
}
```

---

### 11. **Customizar handleCreateClick para skillsInput**

**Problema**: `useEntityPage` não gerencia `skillsInput`

**Solução**: Criar wrapper customizado
```typescript
// ✅ ADICIONAR
const handleCreateClickCustom = () => {
    handleCreateClick()  // Chama o handleCreateClick do useEntityPage
    setSkillsInput('')  // Limpa skillsInput
}
```

---

### 12. **Atualizar updateSkills**

**Manter:**
```typescript
// ✅ MANTER (não muda)
const updateSkills = (input: string) => {
    setSkillsInput(input)
    const skillsArray = input
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
    setFormData({ ...formData, skills: skillsArray })
}
```

**Nota**: `formData` agora vem do `useEntityPage`, mas o comportamento é o mesmo.

---

### 13. **Remover usePagination Manual**

**Remover:**
```typescript
// ❌ REMOVER
const { pagination, setPagination, total, setTotal, paginationHandlers } = usePagination(20)
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    pagination,
    total,
    paginationHandlers,
    // ... outros retornos
} = useEntityPage({...})
```

**Nota**: `useEntityPage` usa `usePagination` internamente, então não precisa importar separadamente.

---

### 14. **Remover useActionBarButtons Manual**

**Remover:**
```typescript
// ❌ REMOVER
const actionBarButtons = useActionBarButtons({
    isEditing,
    selectedCount: selectedDemands.size,
    hasChanges: hasChanges(),
    submitting,
    deleting,
    onCancel: handleCancel,
    onDelete: handleDeleteSelected,
    onSave: handleSave,
})
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    actionBarButtons,  // Já vem do useEntityPage
    // ... outros retornos
} = useEntityPage({...})
```

**Nota**: Mas precisa customizar para usar `handleCancelCustom` e `handleCreateClickCustom`.

**Solução**: Usar `actionBarButtons` do hook, mas sobrescrever `onCancel` e `onCreate` se necessário, OU criar wrapper.

---

### 15. **Remover getActionBarErrorProps Manual**

**Remover:**
```typescript
// ❌ REMOVER
const actionBarErrorProps = getActionBarErrorProps(
    error,
    isEditing,
    selectedDemands.size
)
```

**Substituir por:**
```typescript
// ✅ USAR useEntityPage
const {
    actionBarErrorProps,  // Já vem do useEntityPage
    // ... outros retornos
} = useEntityPage({...})
```

---

### 16. **Atualizar Referências no JSX**

**Mudanças necessárias:**

1. **totalCount no CardPanel:**
```typescript
// ❌ ANTES
totalCount={filteredDemands.length}

// ✅ DEPOIS
totalCount={filteredDemands.length}  // Mantém (filtro no frontend)
// OU
totalCount={total}  // Se mover filtro para backend
```

2. **selectedCount no CardPanel:**
```typescript
// ❌ ANTES
selectedCount={selectedDemands.size}

// ✅ DEPOIS
selectedCount={selectedDemandsCount}  // Vem do useEntityPage
```

3. **onClick no CreateCard:**
```typescript
// ❌ ANTES
onClick={handleCreateClick}

// ✅ DEPOIS
onClick={handleCreateClickCustom}  // Wrapper customizado
```

4. **onEdit no CardFooter:**
```typescript
// ❌ ANTES
onEdit={() => handleEditClick(demand)}

// ✅ DEPOIS
onEdit={() => handleEditClickCustom(demand)}  // Wrapper customizado
```

5. **onToggleSelection no CardFooter:**
```typescript
// ❌ ANTES
onToggleSelection={(e) => {
    e.stopPropagation()
    toggleDemandSelection(demand.id)
}}

// ✅ DEPOIS
onToggleSelection={(e) => {
    e.stopPropagation()
    toggleDemandSelection(demand.id)  // Vem do useEntityPage
}}
```

6. **isSelected:**
```typescript
// ❌ ANTES
const isSelected = selectedDemands.has(demand.id)

// ✅ DEPOIS
const isSelected = selectedDemands.has(demand.id)  // selectedDemands vem do useEntityPage
```

---

### 17. **Atualizar Imports**

**Remover:**
```typescript
// ❌ REMOVER
import { usePagination } from '@/hooks/usePagination'
import { useActionBarButtons } from '@/hooks/useActionBarButtons'
import { getActionBarErrorProps } from '@/lib/entityUtils'
```

**Adicionar:**
```typescript
// ✅ ADICIONAR
import { useEntityPage } from '@/hooks/useEntityPage'
```

---

## 📝 Checklist de Implementação

### Fase 1: Preparação
- [ ] Criar `initialFormData` constante
- [ ] Implementar `mapEntityToFormData`
- [ ] Implementar `mapFormDataToCreateRequest`
- [ ] Implementar `mapFormDataToUpdateRequest`
- [ ] Implementar `validateFormData`
- [ ] Implementar `isEmptyCheck`

### Fase 2: Migração do Hook
- [ ] Adicionar import de `useEntityPage`
- [ ] Remover imports não utilizados (`usePagination`, `useActionBarButtons`, `getActionBarErrorProps`)
- [ ] Substituir estado manual por `useEntityPage`
- [ ] Configurar `useEntityPage` com todas as opções

### Fase 3: Customizações
- [ ] Criar `handleCreateClickCustom` (wrapper para `skillsInput`)
- [ ] Criar `handleEditClickCustom` (wrapper para `skillsInput`)
- [ ] Criar `handleCancelCustom` (wrapper para `skillsInput`)
- [ ] Manter `updateSkills` funcionando com novo `formData`

### Fase 4: Atualização do JSX
- [ ] Atualizar `totalCount` no `CardPanel`
- [ ] Atualizar `selectedCount` no `CardPanel`
- [ ] Atualizar `onClick` no `CreateCard`
- [ ] Atualizar `onEdit` no `CardFooter`
- [ ] Atualizar `onToggleSelection` no `CardFooter`
- [ ] Atualizar referências a `isSelected`

### Fase 5: Filtro
- [ ] Manter filtro de procedimento no frontend (Opção A)
- [ ] OU implementar filtro no backend (Opção B - futuro)

### Fase 6: Testes
- [ ] Testar criação de demanda
- [ ] Testar edição de demanda
- [ ] Testar exclusão de demandas
- [ ] Testar filtro de procedimento
- [ ] Testar paginação
- [ ] Testar validações
- [ ] Testar campos complexos (skills, source)
- [ ] Testar datas (start_time, end_time)

### Fase 7: Limpeza
- [ ] Remover código não utilizado
- [ ] Verificar imports não utilizados
- [ ] Atualizar `PANEL_COMPARISON.md`
- [ ] Documentar mudanças

---

## 🎯 Código Final Esperado (Estrutura)

```typescript
export default function DemandPage() {
    const { settings } = useTenantSettings()
    
    // Estados auxiliares (não gerenciados por useEntityPage)
    const [hospitals, setHospitals] = useState<HospitalResponse[]>([])
    const [loadingHospitals, setLoadingHospitals] = useState(true)
    const [procedureFilter, setProcedureFilter] = useState('')
    const [skillsInput, setSkillsInput] = useState('')
    
    // Configuração inicial
    const initialFormData: DemandFormData = { ... }
    
    // useEntityPage
    const {
        items: demands,
        loading,
        error,
        setError,
        submitting,
        deleting,
        formData,
        setFormData,
        editingItem: editingDemand,
        isEditing,
        hasChanges,
        handleCreateClick,
        handleEditClick,
        handleCancel,
        selectedItems: selectedDemands,
        toggleSelection: toggleDemandSelection,
        selectedCount: selectedDemandsCount,
        pagination,
        total,
        paginationHandlers,
        handleSave,
        handleDeleteSelected,
        actionBarButtons,
        actionBarErrorProps,
    } = useEntityPage<DemandFormData, DemandResponse, DemandCreateRequest, DemandUpdateRequest>({
        endpoint: '/api/demand',
        entityName: 'demanda',
        initialFormData,
        isEmptyCheck,
        mapEntityToFormData,
        mapFormDataToCreateRequest,
        mapFormDataToUpdateRequest,
        validateFormData,
    })
    
    // Wrappers customizados para skillsInput
    const handleCreateClickCustom = () => {
        handleCreateClick()
        setSkillsInput('')
    }
    
    const handleEditClickCustom = (demand: DemandResponse) => {
        handleEditClick(demand)
        setSkillsInput((demand.skills || []).join(', '))
    }
    
    const handleCancelCustom = () => {
        handleCancel()
        setSkillsInput('')
    }
    
    // Filtro no frontend
    const filteredDemands = useMemo(() => {
        if (!procedureFilter.trim()) {
            return demands
        }
        const filterLower = procedureFilter.toLowerCase().trim()
        return demands.filter((demand) => 
            demand.procedure.toLowerCase().includes(filterLower)
        )
    }, [demands, procedureFilter])
    
    // Carregar hospitais (mantido separado)
    useEffect(() => {
        loadHospitals()
    }, [])
    
    // updateSkills (mantido)
    const updateSkills = (input: string) => {
        setSkillsInput(input)
        const skillsArray = input
            .split(',')
            .map((s) => s.trim())
            .filter((s) => s.length > 0)
        setFormData({ ...formData, skills: skillsArray })
    }
    
    // JSX...
}
```

---

## ⚠️ Pontos de Atenção

1. **skillsInput**: Estado local que precisa ser sincronizado com `formData.skills`
2. **Filtro de procedimento**: Manter no frontend inicialmente, pode migrar para backend depois
3. **Carregamento de hospitais**: Manter separado (não afeta `useEntityPage`)
4. **Validações**: Já implementadas, apenas mover para `validateFormData`
5. **Campos complexos**: `skills` (array) e `source` (object) já são suportados

---

## 📊 Estimativa de Esforço

- **Preparação**: 1-2 horas
- **Migração do Hook**: 1-2 horas
- **Customizações**: 1 hora
- **Atualização do JSX**: 1 hora
- **Testes**: 1-2 horas
- **Total**: 5-8 horas

---

## ✅ Benefícios da Migração

1. ✅ Código mais limpo e padronizado
2. ✅ Menos estado manual para gerenciar
3. ✅ Tratamento de erros padronizado
4. ✅ Paginação gerenciada automaticamente
5. ✅ Seleção gerenciada automaticamente
6. ✅ Formulário gerenciado automaticamente
7. ✅ Botões do ActionBar gerenciados automaticamente
8. ✅ Consistência com Hospital e Tenant
