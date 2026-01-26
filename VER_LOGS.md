# Como Ver os Logs de Diagnóstico

## 1. Ver logs do Worker (onde roda a geração de escala)

### PowerShell - Ver logs em tempo real (sem filtro):
```powershell
docker-compose logs -f worker
```

### PowerShell - Ver apenas logs recentes (últimas 100 linhas):
```powershell
docker-compose logs --tail=100 worker
```

### PowerShell - Filtrar logs relacionados à geração de escala:
```powershell
docker-compose logs -f worker | Select-String "GENERATE_SCHEDULE"
```

### PowerShell - Filtrar logs de extração de alocações:
```powershell
docker-compose logs -f worker | Select-String "EXTRACT_ALLOCATIONS"
```

### PowerShell - Filtrar ambos (GENERATE_SCHEDULE ou EXTRACT_ALLOCATIONS):
```powershell
docker-compose logs -f worker | Select-String "GENERATE_SCHEDULE|EXTRACT_ALLOCATIONS"
```

### PowerShell - Ver logs e salvar em arquivo:
```powershell
docker-compose logs worker | Select-String "GENERATE_SCHEDULE|EXTRACT_ALLOCATIONS" | Out-File -FilePath worker_logs.txt
```

## 2. Aumentar nível de detalhe dos logs

Por padrão, os logs estão em nível `INFO`. Para ver logs `DEBUG` (mais detalhados):

### Opção A: Via docker-compose.yml (temporário)
Edite `docker-compose.yml` na seção `worker`, linha ~125:
```yaml
LOG_LEVEL: "DEBUG"
```

Depois reinicie:
```powershell
docker-compose restart worker
```

### Opção B: Via variável de ambiente no .env
Adicione no `backend/.env`:
```
LOG_LEVEL=DEBUG
```

Depois reinicie:
```powershell
docker-compose restart worker
```

## 3. Ver logs após gerar uma escala

1. Gere uma escala pelo frontend ou API
2. Execute imediatamente:
```powershell
docker-compose logs --tail=200 worker | Select-String "GENERATE_SCHEDULE|EXTRACT_ALLOCATIONS"
```

## 4. Logs importantes para verificar

Procure por estas mensagens nos logs:

- `[GENERATE_SCHEDULE] Iniciando extração de alocações individuais` - Início da extração
- `[GENERATE_SCHEDULE] Dia X: assigned_demands_by_pro tem Y profissionais` - Estrutura encontrada
- `[EXTRACT_ALLOCATIONS] Profissional X: Y demandas` - Alocações por profissional
- `[GENERATE_SCHEDULE] Extraídas X alocações individuais` - Total extraído
- `[GENERATE_SCHEDULE] Criados X registros individuais de schedule` - Registros criados
- `[GENERATE_SCHEDULE] Verificação pós-commit: X registros individuais encontrados` - Confirmação no banco

## 5. Ver logs da API também (se necessário)

```powershell
docker-compose logs -f api
```

## 6. Ver todos os logs de uma vez

```powershell
docker-compose logs -f
```

## 7. Salvar logs em arquivo (PowerShell)

```powershell
docker-compose logs worker | Select-String "GENERATE_SCHEDULE|EXTRACT_ALLOCATIONS" | Out-File -FilePath worker_logs.txt
```

Depois abra o arquivo `worker_logs.txt` e procure pelas mensagens de diagnóstico.

## 8. Comando rápido para diagnóstico completo

Execute este comando para ver tudo relacionado à geração de escala:

```powershell
docker-compose logs --tail=500 worker | Select-String "GENERATE_SCHEDULE|EXTRACT_ALLOCATIONS|schedule"
```
