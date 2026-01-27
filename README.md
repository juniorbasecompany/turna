# Turna

Sistema inteligente para geração automática de escalas cirúrgicas otimizadas.

## Visão Geral

O Turna é um SaaS multi-tenant para clínicas gerarem escalas e relatórios (PDF), com:
- **Web (admin)**: cadastros, importação, geração/publicação de escalas, relatórios
- **Mobile (profissionais)**: consulta de escalas publicadas (futuro)

## Estrutura do Repositório

```
turna/
├── backend/           # API FastAPI, worker Arq, modelos, Alembic
│   ├── app/           # Código principal (api, auth, model, services, worker, storage)
│   ├── alembic/       # Migrações de banco de dados
│   ├── demand/        # Extração de demandas (IA/OpenAI)
│   ├── output/        # Geração de PDFs (ReportLab)
│   └── strategy/      # Algoritmos de alocação (Greedy, CP-SAT)
├── frontend/          # Next.js (App Router) - comunica via API HTTP
├── docker-compose.yml # Orquestra Postgres, Redis, MinIO, API e worker
└── *.md               # Documentação do projeto
```

## Funcionalidades Implementadas

- **Autenticação**: OAuth Google + JWT + multi-tenant
- **Hospitais**: CRUD com prompt customizável para extração IA
- **Arquivos**: Upload de PDF/imagens, extração automática de demandas via IA
- **Demandas**: CRUD completo de demandas cirúrgicas
- **Escalas**: Geração automática com solver Greedy, publicação em PDF
- **Jobs**: Sistema de jobs assíncronos (Arq/Redis) para processamento pesado
- **Membros**: Gestão de usuários com convites por email (Resend)
- **Clínicas**: Multi-tenant com isolamento de dados

## Execução Rápida

```bash
# Na raiz do repositório
docker compose up -d --build    # Sobe infra + backend
cd frontend && npm run dev      # Sobe frontend em http://localhost:3001
```

- **API**: `http://localhost:8000` (health: `GET /health`)
- **MinIO Console**: `http://localhost:9001` (minio / minio12345)
- **Frontend**: `http://localhost:3001`

## Configuração

### Backend (`backend/.env`)
O Docker Compose usa `env_file: backend/.env`. Variáveis principais:
- `DATABASE_URL`, `REDIS_URL` - conexões (Docker usa valores internos)
- `JWT_SECRET`, `JWT_ISSUER` - autenticação
- `GOOGLE_OAUTH_CLIENT_ID` - login Google
- `S3_*` - storage (MinIO em dev)
- `OPENAI_API_KEY` - extração de demandas via IA
- `RESEND_API_KEY`, `EMAIL_FROM` - envio de emails

### Frontend (`frontend/.env.local`)
Copie de `frontend/env.example`:
- `NEXT_PUBLIC_API_URL=http://localhost:8000`
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID=<seu Client ID>`

### Google OAuth
1. Crie projeto no [Google Cloud Console](https://console.cloud.google.com/)
2. Em **APIs e Serviços → Credenciais**, crie ID de cliente OAuth 2.0
3. Em **Origens JavaScript autorizadas**, adicione `http://localhost:3001`

## Comandos Úteis

```bash
# Alembic (migrações)
docker compose exec api alembic upgrade head
docker compose exec api alembic revision --autogenerate -m "descrição"

# Logs
docker compose logs -f api      # Logs da API
docker compose logs -f worker   # Logs do worker

# Reiniciar serviços
docker compose restart api
docker compose restart worker
```

## Documentação

### Arquivos Principais
| Arquivo | Descrição |
|---------|-----------|
| [`DIRECTIVES.md`](DIRECTIVES.md) | Diretivas do projeto (fonte da verdade) |
| [`STACK.md`](STACK.md) | Stack tecnológico (ferramentas e bibliotecas) |
| [`SECURITY.md`](SECURITY.md) | Padrões de segurança e validação multi-tenant |
| [`CHECKLIST.md`](CHECKLIST.md) | Checklist de implementação com status |
| [`PRESENTATION.md`](PRESENTATION.md) | Apresentação e funcionalidades do produto |
| [`TIPS.md`](TIPS.md) | Dicas rápidas (comandos, MinIO, ngrok) |

### Arquivos de Planejamento
| Arquivo | Descrição |
|---------|-----------|
| [`PLANO_GERACAO_ESCALA_FROM_DEMANDS.md`](PLANO_GERACAO_ESCALA_FROM_DEMANDS.md) | Plano de geração de escalas |
| [`PLANO_FRAGMENTACAO_SCHEDULE.md`](PLANO_FRAGMENTACAO_SCHEDULE.md) | Plano de fragmentação de schedules |
| [`DEMAND_VALIDATION_CHECKLIST.md`](DEMAND_VALIDATION_CHECKLIST.md) | Checklist de validação de demandas |

## Status do Projeto

**MVP Web Admin**: ~90% implementado
- ✅ Autenticação, multi-tenant, hospitais, arquivos, demandas, escalas, jobs, membros
- 🔄 Página de listagem de escalas no frontend (em progresso)
- 📋 App mobile React Native (futuro)
- 📋 Solver CP-SAT otimizado (futuro)
