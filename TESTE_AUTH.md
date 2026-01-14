# Como Testar Autenticação Google OAuth

## Opção 1: Usar a Página de Login (Recomendado)

1. **Acesse a página de login:**
   ```
   http://localhost:8001/login
   ```

2. **Clique no botão "Entrar com Google"** ou **"Cadastrar-se com Google"**

3. **Escolha sua conta Google** na janela de autenticação

4. **Após autenticar**, você verá uma mensagem de sucesso e o token será exibido no console do navegador

5. **Copie o token** e use no Swagger UI ou em requisições

## Opção 2: Testar via Swagger UI

1. **Acesse:** `http://localhost:8001/docs`

2. **Para obter um token do Google:**
   - Abra o console do navegador (F12)
   - Execute este código JavaScript:
   ```javascript
   // Substitua pelo seu GOOGLE_CLIENT_ID
   const CLIENT_ID = "1049570929300-f43333081hhvtpampiu18v4klmtel1a0.apps.googleusercontent.com";
   
   // Carrega a biblioteca do Google
   const script = document.createElement('script');
   script.src = 'https://accounts.google.com/gsi/client';
   script.onload = () => {
     window.google.accounts.id.initialize({
       client_id: CLIENT_ID,
       callback: (response) => {
         console.log('ID Token:', response.credential);
         alert('Token copiado! Veja o console (F12)');
       }
     });
     window.google.accounts.id.prompt();
   };
   document.head.appendChild(script);
   ```

3. **Copie o token** do console e cole no Swagger UI em `POST /auth/google`

## Opção 3: Usar o Endpoint de Registro (Mais Fácil)

Se você ainda não tem usuário criado:

1. **Acesse:** `http://localhost:8001/login`
2. **Clique em "Cadastrar-se com Google"**
3. Isso criará o usuário automaticamente e retornará o token

## Endpoints Disponíveis

- `POST /auth/google` - Login (usuário deve existir)
- `POST /auth/google/register` - Registro (cria usuário se não existir)
- `GET /me` - Dados do usuário (requer Bearer token no header)

## Exemplo de Resposta

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## Usar o Token

No Swagger UI, clique no botão **"Authorize"** (cadeado no topo) e cole o `access_token` no campo.

Ou use no header das requisições:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
