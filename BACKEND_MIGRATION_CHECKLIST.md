# Checklist: Migração para pasta `backend/`

Este documento descreve os passos para mover o código do backend para a pasta `backend/` com segurança, garantindo conformidade com **CHECKLIST.md**, **DIRECTIVES.md**, **SECURITY.md** e **STACK.md**, e evitando quebrar o código existente.

## Conformidade

- **CHECKLIST.md**: Manter `app.py` legado funcionando; não quebrar Docker Compose, migrações Alembic, jobs Arq, endpoints.
- **DIRECTIVES.md**: Frontend e backend continuam independentes (comunicação apenas via API HTTP); código em inglês, comentários em português; nomes no singular; scripts com prefixo `script_`.
- **SECURITY.md**: Nenhuma alteração de lógica de segurança (tenant_id do JWT, `get_current_member()`, validações). Apenas mudança de layout de pastas.
- **STACK.md**: Manter FastAPI, SQLModel, Alembic, Arq, Redis, PostgreSQL, MinIO, etc. Sem troca de tecnologias.

---

## Fase 0: Pré-requisitos

- [ ] Criar branch dedicada (ex.: `feat/backend-folder`) para a migração.
- [ ] Garantir que a stack atual sobe e responde:
  - [ ] `docker compose up -d --build`
  - [ ] `GET http://localhost:8000/health` → `{"status":"ok"}`
  - [ ] Frontend em `npm run dev` acessível; login e uma página protegida funcionando.
- [ ] Fazer backup ou commit de referência antes de mover arquivos.
- [ ] Ler os trechos relevantes de **CHECKLIST.md** (Etapas 0–7, Validação Final, Fase 6, “Não quebrar app.py”).
- [ ] Confirmar que a pasta `backend/` existe na raiz do repositório (ou criá-la).

---

## Fase 1: Inventário — O que move e o que fica

### Move para `backend/`

| Item | Observação |
|------|------------|
| `app/` | Pacote principal da API, worker, modelos, auth, storage, etc. |
| `alembic/` | Inclui `env.py`, `versions/`, `script.py.mako` |
| `alembic.ini` | Configuração do Alembic |
| `demand/` | Extração de demandas (IA) |
| `output/` | Geração de PDF (console, day) |
| `strategy/` | Solvers (greedy, cd_sat) |
| `static/` | `login.html` e outros estáticos servidos pela API |
| `requirements.txt` | Dependências Python do backend |
| `Dockerfile` | Build da imagem API/worker |
| `app.py` | Código legado — **manter funcionando** (CHECKLIST) |
| `turna.py` | Entrypoint legado que importa `app.py` |
| `login.py` | Login legado (se ainda usado) |
| `diagnose.py` | Script de diagnóstico |
| Pastas `test/`, `data/` | Se existirem e forem usadas por `app.py`, worker ou scripts |

### Permanece na raiz

| Item | Observação |
|------|------------|
| `frontend/` | Projeto Next.js; não mexe. |
| `docker-compose.yml` | Será ajustado para build/volumes do backend. |
| `README.md`, `CHECKLIST.md`, `DIRECTIVES.md`, `SECURITY.md`, `STACK.md`, etc. | Documentação. |
| `.gitignore`, `.cursor/` | Configuração do repo/IDE. |
| `.env` | Pode ficar na raiz ou ser referenciado via `backend/.env`; definir na Fase 3. |

---

## Fase 2: Migração de arquivos

Executar na raiz do repositório. Ordem sugerida para evitar conflitos:

- [ ] Criar `backend/` se ainda não existir.
- [ ] Mover (ou copiar e depois remover da raiz para não duplicar):
  - [ ] `app/` → `backend/app/`
  - [ ] `alembic/` → `backend/alembic/`
  - [ ] `alembic.ini` → `backend/alembic.ini`
  - [ ] `demand/` → `backend/demand/`
  - [ ] `output/` → `backend/output/`
  - [ ] `strategy/` → `backend/strategy/`
  - [ ] `static/` → `backend/static/`
  - [ ] `requirements.txt` → `backend/requirements.txt`
  - [ ] `Dockerfile` → `backend/Dockerfile`
  - [ ] `app.py` → `backend/app.py`
  - [ ] `turna.py` → `backend/turna.py`
  - [ ] `login.py` → `backend/login.py`
  - [ ] `diagnose.py` → `backend/diagnose.py`
- [ ] Se existirem `test/` e `data/` usados pelo backend, mover para `backend/test/` e `backend/data/`.
- [ ] **Não** mover `frontend/`, `docker-compose.yml`, documentação ou config de IDE.

---

## Fase 3: Ajuste de paths (raiz = `backend/`)

Após a migração, a **raiz do backend** passa a ser `backend/`. Todos os `project_root` e caminhos derivados de `Path(__file__)` devem apontar para `backend/` (ou `backend/test/`, `backend/static/`, etc.).

### 3.1 `backend/alembic/env.py`

- [ ] `project_root = Path(__file__).resolve().parent.parent` já resulta em `backend/` (pois `__file__` = `backend/alembic/env.py`). Verificar.
- [ ] `sys.path.insert(0, str(project_root))` — garante que `app`, `demand`, etc. sejam importáveis a partir de `backend/`.
- [ ] Nenhuma referência a pasta raiz do **repositório**; só à raiz do backend.

### 3.2 `backend/app/main.py`

- [ ] `project_root = Path(__file__).resolve().parent.parent` → `backend/`.
- [ ] `load_dotenv(project_root / ".env")` e, se houver, `load_dotenv(".env")`. Garantir que `.env` em `backend/` (ou raiz do repo, conforme decisão) seja carregado.
- [ ] `static_dir = Path(__file__).resolve().parent.parent / "static"` → `backend/static`. Verificar existência.

### 3.3 `backend/app/auth/jwt.py`

- [ ] `project_root = Path(__file__).resolve().parent.parent.parent` → `backend/` (auth → app → backend).
- [ ] `load_dotenv(project_root / ".env")` coerente com a estratégia de `.env`.

### 3.4 `backend/app/auth/oauth.py`

- [ ] Idem: `project_root = ... parent.parent.parent` → `backend/`.
- [ ] `load_dotenv(project_root / ".env")`.

### 3.5 `backend/app/storage/config.py`

- [ ] `project_root = Path(__file__).resolve().parent.parent.parent` → `backend/`.
- [ ] `env_file = project_root / ".env"`.

### 3.6 `backend/app/worker/run.py`

- [ ] `project_root = Path(__file__).resolve().parents[2]` → `backend/` (worker → app → backend).
- [ ] `sys.path.insert(0, str(project_root))` para execução via `python -m app.worker.run`.

### 3.7 `backend/app/worker/job.py`

- [ ] `project_root = Path(__file__).resolve().parents[2]` → `backend/`.
- [ ] Caminhos como `project_root / "test" / "profissionais.json"` passam a `backend/test/...`. Ajustar se `test/` tiver sido movido.

### 3.8 `backend/demand/read.py`

- [ ] `here = Path(__file__).resolve().parent` → `backend/demand/`.
- [ ] `project_root = here.parent` → `backend/`.
- [ ] `load_dotenv(project_root / ".env")` e `load_dotenv(".env")` conforme estratégia.
- [ ] Qualquer `project_root / config.DEFAULT_OUTPUT_PATH` ou similar apontando para `backend/`.

### 3.9 `backend/login.py`

- [ ] `project_root = Path(__file__).resolve().parent` → `backend/`.
- [ ] `ACCOUNT_FILE = project_root / "data" / "account.json"` e `html_path = ... / "static" / "login.html"` → `backend/data/`, `backend/static/`.

### 3.10 `backend/app.py`

- [ ] `Path(__file__).resolve().parent` → `backend/`.
- [ ] `test/`, `demandas.json`, `profissionais.json`, etc. em `backend/test/` (ou onde estiverem).

### 3.11 `backend/turna.py`

- [ ] `Path(__file__).parent / "app.py"` → continua correto se `app.py` estiver em `backend/`.

### 3.12 `.env`

- [ ] Decisão: `.env` na **raiz do repo** ou em `backend/`?
- [ ] Se na raiz: garantir que, ao rodar backend (Docker ou local), o `project_root` usado para `load_dotenv` aponte para a raiz do repo **ou** que variáveis sejam injetadas por `docker-compose` / ambiente. Documentar.
- [ ] Se em `backend/`: atualizar todos os `load_dotenv` para `backend/.env` e ajustar `.gitignore` se necessário.

---

## Fase 4: Docker e Docker Compose

### 4.1 `backend/Dockerfile`

- [ ] Manter `WORKDIR /app`.
- [ ] `COPY . /app` deve executar no **contexto** `backend/` (veja 4.2). Ou seja, conteúdo de `backend/` é copiado para `/app`.
- [ ] `COPY requirements.txt`, `RUN pip install ...` — caminhos relativos ao contexto (`backend/`).

### 4.2 `docker-compose.yml` (na raiz)

- [ ] Serviços `api` e `worker`:
  - [ ] `build.context` → `./backend`
  - [ ] `build.dockerfile` → `Dockerfile` (em `backend/`) ou `./backend/Dockerfile` conforme sintaxe.
- [ ] Volumes:
  - [ ] Trocar `./:/app` por `./backend:/app` para `api` e `worker`, de modo que edições em `backend/` reflitam no container (reload).
- [ ] Comandos **mantidos**:
  - [ ] API: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
  - [ ] Worker: `python -m app.worker.run`
- [ ] Variáveis de ambiente: sem mudança de nomes ou valores; continuam em `environment` dos serviços.

### 4.3 Portas e dependências

- [ ] API segue em `8000`; frontend e proxy continuam usando `NEXT_PUBLIC_API_URL` (ex.: `http://localhost:8000`). Nenhuma alteração no frontend.

---

## Fase 5: Alembic

- [ ] `alembic.ini` está em `backend/`. `script_location = alembic` relativo ao CWD de execução.
- [ ] Comandos sempre executados com CWD = `backend/` (ou `/app` dentro do container, que é o conteúdo de `backend/`):
  - [ ] `alembic upgrade head`
  - [ ] `alembic revision --autogenerate -m "..."`
- [ ] `env.py` já configurado para importar modelos de `app.model` e usar `DATABASE_URL`. Sem alteração de lógica.
- [ ] Garantir que não haja referências a caminhos fora de `backend/` (ex.: raiz do repo) nos scripts de migração.

---

## Fase 6: Validação

### 6.1 Build e serviços

- [ ] `docker compose build --no-cache` sem erros.
- [ ] `docker compose up -d`.
- [ ] `GET http://localhost:8000/health` → `{"status":"ok"}`.
- [ ] Logs da API e do worker sem tracebacks.

### 6.2 Migrações

- [ ] `docker compose exec api alembic upgrade head` (ou equivalente) aplica sem erro.
- [ ] Nenhuma migração pendente ou quebrada.

### 6.3 Autenticação e API

- [ ] Login via Google (ou fluxo configurado) funciona.
- [ ] `GET /me` ou `GET /auth/me` retorna dados corretos.
- [ ] Um endpoint protegido (ex.: `GET /hospital/list`) funciona com token válido.

### 6.4 Frontend

- [ ] `npm run dev` no `frontend/`; acessar app, login, dashboard e pelo menos uma página protegida (Hospitais, Demandas, etc.).
- [ ] Nenhum 401 inesperado ou quebra de fluxo ao dar F5 em página protegida (conforme DIRECTIVES).

### 6.5 Jobs (Arq)

- [ ] Enfileirar um job (ex.: PING ou EXTRACT_DEMAND) e checar que o worker processa e o status retornado pela API está correto.

### 6.6 Código legado

- [ ] Com CWD = `backend/`: `python app.py` ou `python turna.py` (conforme uso atual) executa sem erro e mantém o comportamento esperado (CHECKLIST: não quebrar `app.py`).

### 6.7 Segurança (SECURITY.md)

- [ ] Nenhuma alteração em validação de `tenant_id`, `get_current_member()`, ou regras de isolamento.
- [ ] Apenas paths e layout foram alterados; lógica de segurança intacta.

---

## Fase 7: Limpeza e documentação

- [ ] Remover da **raiz** cópias residuais: `app/`, `alembic/`, `demand/`, `output/`, `strategy/`, `static/`, `requirements.txt`, `Dockerfile`, `app.py`, `turna.py`, `login.py`, `diagnose.py`, `alembic.ini`. Se der "Access denied": feche o IDE, `docker compose down`, tente de novo. Ou execute `python script_cleanup_root_duplicates.py`.
- [ ] Se existir `backend/app/app/` (aninhado): faça `docker compose down`, depois `Remove-Item -Recurse -Force backend\app\app`.
- [ ] Atualizar `README.md` (ou documento de setup) com:
  - [ ] Indicação de que o backend está em `backend/`.
  - [ ] Comandos Docker e Alembic executados a partir da raiz, com contexto `backend/`.
  - [ ] Onde fica o `.env` e como é carregado.
- [ ] Adicionar ao **CHECKLIST.md** uma entrada referenciando este guia, por exemplo:
  - [ ] “Migração para `backend/`: ver `BACKEND_MIGRATION_CHECKLIST.md`.”
- [ ] Commitar em branch dedicada e abrir MR/PR; revisar diff com foco em paths e Docker.

---

## Rollback rápido

Se algo quebrar após a migração:

1. Reverter commits da branch de migração ou voltar ao backup/branch anterior.
2. Restaurar `docker-compose.yml` para `build.context: .` e volumes `./:/app`.
3. Garantir que `app/`, `alembic/`, etc. estejam de novo na raiz, se tiver revertido a movimentação de arquivos.
4. Rodar `docker compose up -d --build` e validar ` /health`, frontend e jobs.

---

## Resumo de conformidade

| Doc | Como é garantido |
|-----|-------------------|
| **CHECKLIST.md** | `app.py` e fluxos atuais preservados; Docker e Alembic validados; jobs e endpoints conferidos na Fase 6. |
| **DIRECTIVES.md** | Frontend inalterado; comunicação só via HTTP; mudanças mínimas e pontuais (paths e Docker). |
| **SECURITY.md** | Nenhuma mudança em regras de tenant, JWT ou endpoints; apenas reorganização de arquivos. |
| **STACK.md** | Mesma stack (FastAPI, SQLModel, Alembic, Arq, Redis, Postgres, MinIO, etc.). |

---

## Revisão / Pendências

- **`backend/app/app/`** (pasta aninhada): se ainda existir, remover manualmente após `docker compose down` — `Remove-Item -Recurse -Force backend\app\app`. Enquanto existir, o Docker usa `app.main` em `backend/app/`; a pasta aninhada é redundante.
- **Raiz**: não deve haver `app/`, `alembic/`, etc. Se houver, use `python script_cleanup_root_duplicates.py` (após `docker compose down`).

---

**Última atualização**: criado para guiar a migração do backend para `backend/` com segurança e conformidade aos documentos do projeto.
