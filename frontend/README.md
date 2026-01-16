# Turna Frontend

Frontend web do Turna construído com Next.js (App Router), TypeScript e Tailwind CSS.

## Estrutura

- `app/` - Rotas e páginas (App Router)
- `components/` - Componentes React reutilizáveis
- `lib/` - Utilitários e helpers
- `types/` - Definições TypeScript
- `hooks/` - Custom React hooks

## Tecnologias

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS** (estilização)
- **ESLint** (linting)

## Desenvolvimento

```bash
# Instalar dependências
npm install

# Rodar em desenvolvimento
npm run dev

# Build para produção
npm run build

# Rodar produção
npm start
```

## Variáveis de Ambiente

Copie `env.example` para `.env.local` e configure:

- `NEXT_PUBLIC_API_URL` - URL da API backend (ex: `http://localhost:8000`)
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` - Client ID do Google OAuth

## Comunicação com Backend

O frontend se comunica exclusivamente via API HTTP. Nenhuma dependência direta de código Python.
