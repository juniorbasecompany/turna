# Turna

## Estrutura

- **`backend/`** — API FastAPI, worker Arq, modelos, alembic, demand, output, strategy. Docker usa `context: ./backend` e volume `./backend:/app`.
- **`frontend/`** — Next.js; comunica com a API apenas via HTTP (ver `DIRECTIVES.md`).

## Execução (Docker Compose)

Na raiz do repositório:

```bash
docker compose up -d --build
```

- API: `http://localhost:8000` — health: `GET /health`
- Comandos Alembic: `docker compose exec api alembic upgrade head` (ou `alembic` rodando em `backend/`)

## Como rodar (a partir do login)

1. **Subir a API e a infra** (na raiz):
   ```bash
   docker compose up -d --build
   ```
   Validar: `Invoke-RestMethod http://localhost:8000/health` (PowerShell) ou `curl -s http://localhost:8000/health`.

2. **Configurar o frontend** (`frontend/`):
   - Copie `env.example` para `.env.local` (se ainda não existir).
   - Em `.env.local`:
     - `NEXT_PUBLIC_API_URL=http://localhost:8000`
     - `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<seu Client ID do Google>`

3. **Google OAuth** (para o login funcionar):
   - Crie um projeto no [Google Cloud Console](https://console.cloud.google.com/).
   - Em **APIs e Serviços → Credenciais**, crie um **ID de cliente OAuth 2.0** (tipo "Aplicativo da Web").
   - Em **Origens JavaScript autorizadas**, adicione `http://localhost:3001`.
   - Use o **Client ID** em `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.

4. **Rodar o frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   O app sobe em **http://localhost:3001**.

5. **Acessar**: abra **http://localhost:3001/login**, faça login com Google e siga o fluxo (seleção de clínica, se houver).

## .env

- Pode ficar na **raiz** do repo ou em **`backend/`**. O código carrega `backend/.env` e, como fallback, `../.env` (raiz).
- Variáveis do Docker vêm do `environment` no `docker-compose.yml`; para dev local, use `backend/.env` ou raiz.

## Documentos

- **Fonte da verdade (diretivas)**: [`DIRECTIVES.md`](DIRECTIVES.md)
- **Checklist de execução/entrega**: [`CHECKLIST.md`](CHECKLIST.md)
- **Stack do projeto**: [`STACK.md`](STACK.md)
- **Segurança**: [`SECURITY.md`](SECURITY.md)
- **Apresentação do projeto**: [`PRESENTATION.md`](PRESENTATION.md)
- **Migração do backend para `backend/`**: [`BACKEND_MIGRATION_CHECKLIST.md`](BACKEND_MIGRATION_CHECKLIST.md)
