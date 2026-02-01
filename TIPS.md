# Turna
<!-- Pressiona CTRL+SHIFT+V para ver formatado. -->

Todos os comandos abaixo são executados a partir da **raiz do repositório**, exceto quando indicado.

## Ativação rápida
Para iniciar infra + backend (Docker) e frontend (Next.js):
  - **Via script** (recomendado):
    ```
    .\start.bat
    ```
  - **Via comandos** (alternativa):
    ```
    cd backend; docker compose up -d; cd ../frontend; npm run dev
    ```

## Atualizar o banco de dados - Alembic
- **Via Docker** (recomendado): `docker compose exec api alembic upgrade head`
- **Local** (com CWD em `backend/`): `alembic upgrade head`

## Auth Platform
Console para administrar a forma de autenticação

- **Clients**
  - Clique [`aqui`](https://console.cloud.google.com/auth/clients/1049570929300-f43333081hhvtpampiu18v4klmtel1a0.apps.googleusercontent.com?project=turna-483304) para acessar a página e administrar ou adicionar endereços que têm acesso ao sistema.


# BACKEND

O backend está em `backend/`. Docker Compose sobe API, worker, Postgres, Redis e MinIO. Use `backend/.env` para variáveis (Docker carrega via `env_file`).

## APIs
- **Primeira vez / após ligar o computador**
  - Na raiz do repo: `docker compose up -d`

- **Reiniciar apenas a API** (se os containers já estiverem rodando): `docker compose restart api`

- **Reiniciar o worker**: `docker compose restart worker`


# FRONTEND
  ```
  cd frontend
  ```
  (a partir da raiz do repositório)

## NEXT.js

- **Ativação para desenvolvimento**
  - Para ativar o Next.js e iniciar as portas 3000 ou 3001
  ```
  npm run dev
  ```

- **Ativação em produção**
  - Para ativar o Next.js otimizado e sem debug
  ```
  npm run build; npm start
  ```

## MinIO

- **Visualizar arquivos**
  - Usuário: minio
  - Senha: minio12345
  ```
  http://localhost:9001
  ```

## NGROK - Acesso pelo Celular em desenvolvimento
Precisa estar na mesma rede WiFi:

- **Ativar**
   ```
   ngrok http 3001
   ```
   A URL do ngork muda sempre que reiniciar (plano free)

- **Atualizar a URL do ngrok no [`console do Google`](https://console.cloud.google.com/auth/clients/1049570929300-f43333081hhvtpampiu18v4klmtel1a0.apps.googleusercontent.com?project=turna-483304)**

- **Acessar no celular**

- **Configuração inicial - apenas na primeira vez**
  ```
  ngrok config add-authtoken 37oTHeaR4VGIwnTLu7wPXGSCAZu_4Vb1QZ3sFCf5P8u5KEcNb
  ```