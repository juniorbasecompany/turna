# Diretivas do Projeto (Fonte da Verdade)

Frontend e backend são projetos independentes no mesmo repositório, comunicando-se exclusivamente via API HTTP; nenhuma camada pode depender, acoplar ou assumir detalhes internos da outra.

Este documento concentra **diretivas que devem ser seguidas** durante a construção do projeto (código, sugestões, revisões e automações).

## Convenções de nomenclatura e idioma

- **Idioma do código**: todo o código-fonte (nomes de classes, arquivos, métodos, variáveis, atributos, etc.) deve ser escrito **em inglês**.
- **Idioma de comunicação**: todos os **comentários**, **documentação** e **mensagens exibidas ao usuário** devem ser escritos **em português**, tanto no **backend** quanto no **frontend**.
- **Singular**: utilize nomes no singular como padrão (ex.: `User`, `Invoice`, `Schedule`).
- **Plural**: evite o uso de nomes no plural, exceto quando estritamente necessário.
- **Listas e arrays**: utilize o sufixo `List` para indicar coleções (ex.: `userList`, `invoiceList`).
- **Exceções por convenção de ferramentas**: quando uma ferramenta ou framework adotar um padrão consolidado (ex.: `alembic/versions/`), preserve a convenção original e registre explicitamente a exceção na documentação do projeto.


## Datas e Horários
- **Tipo obrigatório**: todos os campos de data/hora devem ser `timestamptz` (PostgreSQL).
- **Proibição**: não usar `date`, `time` ou `timestamp without time zone`.
- **Convenção de nomes**: todo campo de data/hora termina com `_at` (`created_at`, `start_at`, `end_at`, `published_at`).
- **Formato da API**: entrada e saída sempre em ISO 8601 completo, com offset ou `Z`.
- **Validação**: timestamps sem fuso explícito são inválidos e devem ser rejeitados pela API.
- **Armazenamento**: todos os instantes são normalizados e armazenados em UTC.
- **Timezone do Tenant**: cada Tenant deve possuir um campo `timezone` no padrão IANA (ex.: `America/Sao_Paulo`).
- **Exibição**: conversão de fuso ocorre apenas no frontend ou camada de apresentação.
- **Períodos integrais**: “dia inteiro” deve ser modelado como intervalo `[start_at, end_at)`.
- **Jobs e relatórios**: sempre usam timestamps normalizados; nunca aplicam conversão de fuso internamente.

## Python

- **Preferência**: sempre prefira **Python** (evite PowerShell quando houver alternativa).
- **Estilo**: siga o padrão de formatação/indentação já usado nos arquivos similares do repositório.
- **Mudanças**: altere apenas o que estiver diretamente relacionado ao assunto que está sendo tratado (evite refatoração desnecessária).

## Banco / Alembic

- **Migrações**: toda mudança de schema deve vir acompanhada de migration Alembic.
- **Consistência**: mantenha nomes e padrões alinhados ao histórico das migrations existentes.

## Modelos e Multi-Tenant

- **Account**: modelo de pessoa física (login Google), email único global, sem `tenant_id`.
- **Membership**: vínculo Account↔Tenant com `role` e `status` (um Account pode ter múltiplos memberships).
- **Role e Status**: sempre usar do Membership, não do Account (Account.role é apenas legado/conveniência).
- **Tenant isolation**: todas as queries devem filtrar por `tenant_id` do JWT (via `get_current_membership()`).
- **Dependencies**: usar `get_current_membership()` para validar acesso ao tenant, não `get_current_account()` diretamente.
- **JWT**: `role` no token vem do Membership, não do Account.

## API / FastAPI

- **Contratos**: endpoints devem ter schemas claros de request/response.
- **Erros**: padronize respostas de erro (mensagens e status codes).

## Frontend / Autenticação

## Padrão de carregamento em páginas protegidas

- **Use `fetch()` diretamente**.
  Não use `api.get()` do `lib/api.ts` nem hooks de autenticação.
- **Seguir o padrão de `/dashboard`.**
- **Estrutura obrigatória**:
  - `try` externo para controle geral
  - `try` interno para chamada da API
  - `catch` interno **ignora erro** (rede/servidor)
- **Nunca redirecionar para `/login`** em erro de API.
- **Motivo**: evitar logout indevido ao pressionar F5 em falhas temporárias.

## F5 / Refresh

- Ao recarregar a página, **sempre tentar carregar os dados**.
- Se falhar:
  - Mostrar mensagem de erro
  - **Não redirecionar automaticamente para `/login`**
- Redirecionar para `/login` **somente em 401 real** (cookie inválido).

## Redirecionamento automático (`lib/api.ts`) - ⚠️ ATENÇÃO CRÍTICA

### Problema Identificado

O `AuthProvider` (usado no `RootLayout` via `Providers`) utiliza `api.get()` do `lib/api.ts` para verificar autenticação ao montar a aplicação. O `lib/api.ts` possui lógica que redireciona automaticamente para `/login` quando recebe 401, **exceto para páginas específicas listadas em exceções**.

### Quando o Problema Ocorre

- Ao criar uma **nova página protegida** que usa `fetch()` direto (correto)
- O `AuthProvider` tenta carregar autenticação usando `api.get()` (que usa `lib/api.ts`)
- Se houver 401 durante essa verificação, `lib/api.ts` redireciona para `/login` **mesmo que a página use `fetch()` direto**
- **Resultado**: Ao pressionar F5 na nova página, o usuário é redirecionado para `/login` indevidamente

### Solução OBRIGATÓRIA

**Ao criar uma nova página protegida que segue o padrão (usa `fetch()` direto e NÃO redireciona em 401):**

1. **Adicionar o caminho da página à lista de exceções no `lib/api.ts`**
2. Localizar a verificação de 401 no `lib/api.ts` (função `apiRequest`)
3. Adicionar a exceção: `!path.startsWith('/sua-pagina')` na condição de redirecionamento
4. **Páginas atualmente na lista de exceções:**
   - `/login`
   - `/select-tenant`
   - `/dashboard`
   - `/file`

### Exemplo de Correção

```typescript
// Em frontend/lib/api.ts, função apiRequest, após linha ~67
if (response.status === 401) {
    if (typeof window !== 'undefined') {
        const path = window.location.pathname
        if (!path.startsWith('/login') &&
            !path.startsWith('/select-tenant') &&
            !path.startsWith('/dashboard') &&
            !path.startsWith('/file') &&
            !path.startsWith('/sua-nova-pagina')) {  // ← ADICIONAR AQUI
            window.location.href = '/login'
        }
    }
    throw new ApiError('Não autenticado', 401)
}
```

### Checklist ao Criar Nova Página Protegida

- [ ] Página usa `fetch()` direto (não `api.get()`)
- [ ] Página segue padrão try/catch interno/externo (catch interno ignora erro)
- [ ] Página NÃO redireciona para `/login` em 401
- [ ] **Página adicionada à lista de exceções no `lib/api.ts`** ← CRÍTICO
- [ ] Testado pressionando F5 - não deve redirecionar para `/login`

### Motivo Técnico

O `AuthProvider` é montado no `RootLayout` e executa em **todas as páginas**, incluindo páginas protegidas. Ele usa `api.get()` que por sua vez usa `lib/api.ts`. Mesmo que sua página use `fetch()` direto e trate 401 corretamente, o `AuthProvider` pode causar redirecionamento se não estiver na lista de exceções.

## Referência

- Padrão implementado em:
  - `/select-tenant`
  - `/dashboard`

## Execução (Dev): Docker vs Local

- **Padrão (recomendado)**: rodar via **Docker Compose** (API + worker + Postgres + Redis + MinIO).
- **Local (exceção)**: rodar no venv apenas para depuração pontual (scripts/diagnóstico), não como modo “oficial”.
- **Comandos úteis (Docker Compose)**:
  - **Subir stack**: `docker compose up -d --build`
  - **Logs worker**: `docker compose logs -f worker`
  - **Logs API**: `docker compose logs -f api`
- **Comandos úteis (Local / exceção)**:
  - **Rodar worker local**: `python .\app\worker\run.py`
- **Portas**:
  - **Docker Compose**: API em `http://localhost:8000`
  - **Local**: a porta pode variar (ex.: `8001`) e isso impacta integrações.
- **Hosts de serviços (env vars)**:
  - **Dentro do Docker**: usar nomes de service (`REDIS_URL=redis://redis:6379/0`, `DATABASE_URL=...@postgres...`)
  - **Rodando local com infra no Docker**: usar `localhost` (`REDIS_URL=redis://localhost:6379/0`, `DATABASE_URL=...@localhost:5433...`)
- **OAuth (Google)**: o **origin** depende de host/porta; ao trocar (ex. `8001` → `8000`) é necessário atualizar **Authorized JavaScript origins** no Google Console para evitar `origin_mismatch`.

## Estilo / Formatters

- **Consistência**: priorize consistência com o código existente (imports, nomes, organização de módulos).
- **Legibilidade**: prefira código simples e explícito a "mágica".

## Scripts

- **Nome**: quando criar um script Python, use o prefixo **`script_`** no nome do arquivo.
- **Isolamento**: scripts devem ser executáveis e não devem introduzir efeitos colaterais indesejados ao serem importados.

## Dependências

- **Atualidade**: ao adicionar dependências, prefira versões atuais/seguras.
- **Justificativa**: toda dependência nova deve ter um motivo claro.
- **Requisitos**: mantenha o arquivo requirements.txt atualizado.

## Segurança

- **Segredos**: nunca commitar credenciais/chaves/tokens; use variáveis de ambiente e arquivos ignorados.
- **Dados sensíveis**: evite logar informações sensíveis (tokens, headers, PII).

## Consulta à Web (quando aplicável)

- **Atualidade**: ao consultar a web, priorize fontes atuais e verificáveis; se não houver, sinalize que pode não ser confiável.

