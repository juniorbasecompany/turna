# Turna
<!-- Pressiona CTRL+SHIFT+V para ver formatado. -->

## Ativação rápida
Use este comando para iniciar todos os serviços (backend + frontend):
  ```
  docker compose up -d; cd frontend; npm run dev
  ```

## Auth Platform
Console para administrar a forma de autenticação

- **Clients**
  - Clique [`aqui`](https://console.cloud.google.com/auth/clients/1049570929300-f43333081hhvtpampiu18v4klmtel1a0.apps.googleusercontent.com?project=turna-483304) para acessar a página e administrar ou adicionar endereços que têm acesso ao sistema.


# BACKEND

## APIs
- **Primeira vez / após ligar o computador**
  - Para iniciar todos os serviços (postgres, redis, minio, api, worker)
  ```
  docker compose up -d
  ```

- **Reiniciar apenas a API (se containers já estiverem rodando)**
  ```
  docker compose restart api
  ```


# FRONTEND
  ```
  cd frontend
  ```

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