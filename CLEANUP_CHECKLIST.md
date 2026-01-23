# Checklist de Limpeza de Código

Este documento lista trechos de código que podem ser removidos com segurança:
- Código não utilizado
- Código obsoleto
- Logs de debug utilizados para resolver problemas anteriores

---

## 1. Logs de Debug no Frontend

### 1.1. Logs de Thumbnail (Frontend)
- [ ] **Arquivo:** `frontend/app/(protected)/file/page.tsx`
- [ ] **Linhas:** 305, 315, 319, 328, 338, 344, 367, 381

**Logs:**
- `console.log('[THUMBNAIL] Thumbnail disponível para file_id=...')`
- `console.log('[THUMBNAIL] Thumbnail não encontrado para file_id=..., retryCount=...')`
- `console.log('[THUMBNAIL] Máximo de tentativas atingido para file_id=...')`
- `console.log('[THUMBNAIL] Agendando retry em ...ms para file_id=...')`
- `console.error('[THUMBNAIL] Erro ao verificar thumbnail para file_id=...: status=...')`
- `console.error('[THUMBNAIL] Erro ao verificar thumbnail para file_id=...:')`
- `console.log('[THUMBNAIL] Thumbnail carregado com sucesso para file_id=...')`
- `console.log('[THUMBNAIL] Erro ao carregar imagem para file_id=...')`

**Motivo:** Logs de debug adicionados para rastrear o processo de carregamento de thumbnails. O sistema já está funcionando e esses logs não são necessários em produção.

---

### 1.2. Logs de Thumbnail (API Route)
- [ ] **Arquivo:** `frontend/app/api/file/[id]/thumbnail/route.ts`
- [ ] **Linhas:** 27, 38, 42, 65

**Logs:**
- `console.log('[THUMBNAIL-FRONTEND] Buscando thumbnail para file_id=..., hasToken=...')`
- `console.log('[THUMBNAIL-FRONTEND] Response status: ..., contentType: ...')`
- `console.error('[THUMBNAIL-FRONTEND] Erro ao obter thumbnail: status=..., body=...')`
- `console.error('Erro ao fazer proxy do thumbnail:', error)`

**Motivo:** Logs de debug para rastrear o proxy de thumbnails. O endpoint já está funcionando corretamente.

---

### 1.3. Logs de Debug em lib/api.ts
- [ ] **Arquivo:** `frontend/lib/api.ts`
- [ ] **Linhas:** 34, 59, 208, 212, 216, 220, 228

**Logs:**
- `console.log('Error data received:', JSON.stringify(data, null, 2))` (linha 34)
- `console.warn('Could not extract error message from:', data)` (linha 59)
- `console.log('Parsed error data:', errorData)` (linha 208)
- `console.warn('Failed to parse error response as JSON:', parseError, 'Text:', text)` (linha 212)
- `console.warn('Empty error response body')` (linha 216)
- `console.warn('Failed to read error response text:', textError)` (linha 220)
- `console.log('Extracted error message:', errorMessage)` (linha 228)

**Motivo:** Todos esses logs estão dentro de blocos `if (process.env.NODE_ENV === 'development')`, mas ainda são logs de debug para entender o formato de erros. Podem ser removidos se o tratamento de erros já está estável.

---

### 1.4. Logs de Debug em ActionBar
- [ ] **Arquivo:** `frontend/components/ActionBar.tsx`
- [ ] **Linha:** 92

**Log:**
- `console.log('[ACTIONBAR-COMPONENT] message:', message, 'messageType:', messageType, 'error:', error, 'buttons:', buttons.length)`

**Motivo:** Log de debug para rastrear mudanças de estado do ActionBar. Não é necessário em produção.

---

### 1.5. Logs de Debug em Member Page
- [ ] **Arquivo:** `frontend/app/(protected)/member/page.tsx`
- [ ] **Linhas:** 279, 290, 295, 726

**Logs:**
- `console.log('[INVITE-UI] Iniciando envio de convite para member ID=...')`
- `console.log('[EMAIL-MESSAGE] Definindo mensagem de sucesso:', successMsg)`
- `console.error('[INVITE-UI] ❌ FALHA - Erro ao enviar convite para member ID=...:')`
- `console.log('[ACTIONBAR] Mensagem de email presente, não mostrando erro genérico')`

**Motivo:** Logs de debug para rastrear o fluxo de envio de convites e mensagens de email. O sistema já está funcionando.

---

### 1.6. Logs de Debug em API Routes (Frontend)
- [ ] **Arquivos:** 
  - `frontend/app/api/tenant/route.ts` (linhas 11, 30, 35, 38)
  - `frontend/app/api/tenant/[id]/route.ts` (linhas 14, 33, 41, 47, 72, 89, 96, 101)
  - `frontend/app/api/tenant/list/route.ts` (linhas 11, 28, 33, 36)
  - `frontend/app/api/member/route.ts` (linhas 11, 38, 43, 46)
  - `frontend/app/api/member/[id]/invite/route.ts` (linha 14)
  - `frontend/app/api/tenant/[id]/invite/route.ts` (linha 14)
  - `frontend/app/api/account/route.ts` (linhas 11, 30, 35, 38)
  - `frontend/app/api/account/[id]/route.ts` (linhas 14, 33, 41, 47, 72, 89, 96, 101)

**Logs:**
- `console.log('[TENANT-FRONTEND] ...')`
- `console.log('[MEMBER-FRONTEND] ...')`
- `console.log('[ACCOUNT-FRONTEND] ...')`
- `console.log('[INVITE-FRONTEND] ...')`
- `console.error('[TENANT-FRONTEND] ❌ FALHA - ...')`
- `console.error('[MEMBER-FRONTEND] ❌ FALHA - ...')`
- `console.error('[ACCOUNT-FRONTEND] ❌ FALHA - ...')`

**Motivo:** Logs de debug com prefixos específicos adicionados para rastrear fluxos de criação/atualização. O sistema já está funcionando e esses logs não são necessários.

---

### 1.7. Logs de Debug em Auth Context
- [ ] **Arquivo:** `frontend/lib/context/auth-context.tsx`
- [ ] **Linhas:** 43, 64, 87

**Logs:**
- `console.debug('Erro ao carregar account:', error)`
- `console.debug('Erro ao carregar tenant:', error)`
- `console.debug('Auth check failed:', error)`

**Motivo:** Logs de debug para falhas silenciosas de autenticação (esperadas quando não autenticado). Podem ser removidos se não forem mais necessários para troubleshooting.

---

## 2. Logs de Debug no Backend

### 2.1. Logs Verbosos de Hospital (Backend)
- [ ] **Arquivo:** `app/api/route.py`
- [ ] **Linhas:** 2006, 2014, 2194

**Logs:**
- `logger.info(f"Valor do prompt após validação Pydantic: {body.prompt}")` (linha 2006)
- `logger.info(f"Objeto Hospital criado: tenant_id={hospital.tenant_id}, name={hospital.name}, prompt={hospital.prompt}")` (linha 2014)
- `logger.info(f"Objeto Hospital antes do commit: tenant_id={hospital.tenant_id}, name={hospital.name}, prompt={hospital.prompt}")` (linha 2194)

**Motivo:** Logs de debug adicionados para rastrear o fluxo de criação/atualização de hospitais, especialmente para verificar se o prompt estava sendo persistido corretamente. O problema já foi resolvido.

---

### 2.2. Logs Verbosos de Thumbnail (Backend)
- [ ] **Arquivo:** `app/api/route.py`
- [ ] **Linhas:** 1709, 1718, 1725, 1734

**Logs:**
- `logger.info(f"[THUMBNAIL] Buscando thumbnail para file_id={file_id}, s3_key={file_model.s3_key}, thumbnail_key={thumbnail_key}")`
- `logger.info(f"[THUMBNAIL] Thumbnail existe? {exists} (key={thumbnail_key})")`
- `logger.info(f"[THUMBNAIL] Retornando thumbnail para file_id={file_id}")`
- `logger.warning(f"[THUMBNAIL] Thumbnail não encontrado (key={thumbnail_key})")`

**Motivo:** Logs de debug para rastrear o processo de busca de thumbnails. O sistema já está funcionando.

---

### 2.3. Logs Verbosos de Thumbnail (Worker)
- [ ] **Arquivo:** `app/worker/job.py`
- [ ] **Linhas:** 394, 398, 454, 455, 459, 476, 507, 517, 528, 534, 538, 575, 581, 643, 668

**Logs:**
- `logger.info(f"[THUMBNAIL] Iniciando job (job_id={job_id})")`
- `logger.info(f"[THUMBNAIL] Processando file_id={file_id}")`
- `logger.info(f"[THUMBNAIL] file_id={file_id}, mime={mime}, ext={ext}, is_image={is_image}, is_pdf={is_pdf}, is_excel={is_excel}")`
- `logger.info(f"[THUMBNAIL] Detalhes detecção: mime='{mime}', ext='{ext}', mime in excel_mime_types={mime in excel_mime_types}, ext in excel_exts={ext in {'.xls', '.xlsx'}}")` (ver item 3.1 sobre bug)
- `logger.warning(f"[THUMBNAIL] Tipo não suportado para file_id={file_id}: mime={mime}, ext={ext}")`
- `logger.info(f"[THUMBNAIL] Tipo suportado detectado: is_image={is_image}, is_pdf={is_pdf}, is_excel={is_excel}")`
- `logger.info(f"[THUMBNAIL] Processando Excel: file_id={file_id}, ext={ext}")`
- `logger.info(f"[THUMBNAIL] Lendo Excel com engine apropriado: ext={ext}")`
- `logger.warning(f"[THUMBNAIL] Erro com openpyxl, tentando xlrd: {e1}")`
- `logger.info(f"[THUMBNAIL] Excel lido: {len(df)} linhas, {len(df.columns)} colunas")`
- `logger.warning(f"[THUMBNAIL] Planilha Excel vazia para file_id={file_id}")`
- `logger.info(f"[THUMBNAIL] Criando figura matplotlib")`
- `logger.info(f"[THUMBNAIL] Convertendo figura para PIL Image")`
- `logger.info(f"[THUMBNAIL] Excel convertido para imagem: {image.size}")`
- `logger.info(f"[THUMBNAIL] Thumbnail gerado com sucesso (job_id={job.id}, file_id={file_id}, thumbnail_key={thumbnail_key})")`
- `logger.info(f"[THUMBNAIL] Finalizando job (job_id={job_id}, file_id={file_id})")`

**Motivo:** Logs extremamente verbosos de debug para rastrear cada etapa do processo de geração de thumbnails. O sistema já está funcionando e esses logs geram muito ruído.

---

### 2.4. Logs Verbosos de Email Service
- [ ] **Arquivo:** `app/services/email_service.py`
- [ ] **Linhas:** 144, 166, 167, 168, 176, 177, 178, 193, 203, 207, 210, 216, 219

**Logs:**
- `logger.debug(f"Configurações: APP_URL={app_url}, EMAIL_FROM={'***' if email_from else 'NÃO CONFIGURADO'}, RESEND_API_KEY={'***' if resend_api_key else 'NÃO CONFIGURADO'}")`
- `logger.info(f"[EMAIL] Assunto: {subject}")`
- `logger.info(f"[EMAIL] Corpo (texto):\n{text_body}")`
- `logger.info(f"[EMAIL] Processo concluído (modo log) - Email NÃO enviado para {to_email}")`
- `logger.info(f"[EMAIL] Tentando enviar email via Resend para {to_email}...")`
- `logger.debug(f"[EMAIL] Resposta do Resend recebida: {type(email_response)}")`
- `logger.info(f"[EMAIL] ✅ SUCESSO - Email de convite enviado com sucesso para {to_email} (Resend ID: {email_response['id']})")`
- `logger.info(f"[EMAIL] Processo concluído com SUCESSO - Email enviado para {to_email}")`

**Motivo:** Logs muito verbosos de debug para rastrear o envio de emails. Alguns são úteis (erros), mas os de sucesso e detalhes de configuração podem ser reduzidos.

---

## 3. Código com Problemas ou Referências Incorretas

### 3.1. Referência a Variável Inexistente em Log
- [ ] **Arquivo:** `app/worker/job.py`
- [ ] **Linha:** 455

**Código:**
```python
logger.info(f"[THUMBNAIL] Detalhes detecção: mime='{mime}', ext='{ext}', mime in excel_mime_types={mime in excel_mime_types}, ext in excel_exts={ext in {'.xls', '.xlsx'}}")
```

**Problema:** O log menciona `excel_exts` no texto, mas essa variável não existe no código. O valor correto é calculado como `ext in {'.xls', '.xlsx'}`. A referência `excel_exts` no texto do log é enganosa.

**Motivo:** O log foi criado para debug e contém uma referência incorreta a uma variável que não existe. Pode ser removido ou corrigido.

---

### 3.2. Imports Duplicados de Logging
- [ ] **Arquivo:** `app/worker/job.py`
- [ ] **Linhas:** 392-393, 452-453, 505-506, 646-647, 665-666

**Código:**
```python
import logging
logger = logging.getLogger(__name__)
```

**Problema:** O módulo `logging` é importado múltiplas vezes dentro da mesma função (dentro de blocos try/except diferentes). O import deveria ser feito uma vez no início da função ou no nível do módulo.

**Motivo:** Código redundante. O import de `logging` deveria ser feito uma vez no início da função `process_thumbnail_job` ou no nível do módulo.

---

### 3.3. Imports Inline de Logging e Traceback
- [ ] **Arquivo:** `app/api/route.py`
- [ ] **Linhas:** 1453, 1683, 1769, 1773, 1785, 1794-1795

**Código:**
```python
import logging
import traceback
```

**Problema:** Imports de `logging` e `traceback` feitos dentro de funções/endpoints, quando já existe `import logging` no nível do módulo (linha 2) e `logger` já está definido.

**Motivo:** Código redundante. O `logging` já está importado no nível do módulo. O `traceback` pode ser importado no nível do módulo se necessário, ou removido se não for mais usado.

---

## 4. Comentários Obsoletos

### 4.1. Comentário sobre Compatibilidade com login.py
- [ ] **Arquivo:** `app/auth/jwt.py`
- [ ] **Linha:** 18

**Código:**
```python
# Aceita JWT_SECRET ou APP_JWT_SECRET (compatibilidade com login.py)
```

**Motivo:** O comentário menciona compatibilidade com `login.py`, que é código legado. Se `login.py` não for mais usado, o comentário pode ser atualizado ou removido. O suporte a `APP_JWT_SECRET` ainda é funcional e pode ser mantido para compatibilidade, mas o comentário pode ser simplificado.

---

## 5. Logs Operacionais Excessivamente Verbosos

### 5.1. Logs de Auditoria Muito Detalhados
- [ ] **Arquivo:** `app/api/route.py`
- [ ] **Múltiplas linhas com padrão:**
  - `logger.info(f"Criando account: email={body.email}, tenant_id={member.tenant_id}")`
  - `logger.info(f"Account criado com sucesso: id={account.id}")`
  - `logger.info(f"Listando accounts para tenant_id={member.tenant_id}, limit={limit}, offset={offset}")`
  - `logger.info(f"Encontrados {total} accounts, retornando {len(accounts)}")`
  - E similares para Tenant, Hospital, Member, Demand

**Motivo:** Logs operacionais são úteis, mas muitos deles são muito verbosos. Logs de sucesso (ex: "Account criado com sucesso") podem ser reduzidos ou removidos, mantendo apenas logs de erro e operações críticas. Logs de listagem com detalhes de paginação podem ser simplificados.

**Recomendação:** Manter apenas:
- Logs de erro (`logger.error`, `logger.warning`)
- Logs de operações críticas (ex: criação de tenant, exclusão de dados)
- Remover logs de sucesso rotineiros
- Simplificar logs de listagem

---

## Resumo

### Total de Itens Encontrados:
- **Frontend:** ~50+ logs de debug
- **Backend:** ~100+ logs de debug/verbosos
- **Código com problemas:** 3 casos (referência incorreta, imports duplicados)
- **Comentários obsoletos:** 1 caso

### Prioridade de Remoção:
1. **Alta:** Logs de debug com prefixos `[THUMBNAIL]`, `[TENANT-FRONTEND]`, `[MEMBER-FRONTEND]`, etc.
2. **Média:** Logs verbosos de sucesso no backend (ex: "Account criado com sucesso")
3. **Baixa:** Logs de debug condicionais em desenvolvimento (ex: `if (process.env.NODE_ENV === 'development')`)
4. **Correção:** Imports duplicados e referências incorretas em logs

### Observações:
- Alguns `console.error` em catch blocks podem ser mantidos para produção, mas muitos são redundantes se houver tratamento centralizado de erros.
- Logs de debug condicionais a `NODE_ENV === 'development'` são menos críticos, mas ainda podem ser removidos para limpeza.
- Logs operacionais no backend podem ser reduzidos mantendo apenas erros e operações críticas.

### Progresso:
- [ ] Seção 1: Logs de Debug no Frontend (7 itens)
- [ ] Seção 2: Logs de Debug no Backend (4 itens)
- [ ] Seção 3: Código com Problemas (3 itens)
- [ ] Seção 4: Comentários Obsoletos (1 item)
- [ ] Seção 5: Logs Operacionais Verbosos (1 item)

**Total: 16 itens principais**
