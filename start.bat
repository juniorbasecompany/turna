@echo off
cls
cd /d "%~dp0"

if /i "%~1"=="debug" (
  echo [DEBUG] Subindo apenas infraestrutura ^(postgres, redis, minio^). API e Worker rode pelo IDE.
  cd backend
  docker compose up -d postgres redis minio
  cd ..\frontend
  echo/
  echo Inicie no IDE: FastAPI e depois Worker ^(Arq^).
  npm run dev
) else (
  echo [NORMAL] Subindo todos os servicos ^(Docker + frontend^).
  cd backend
  docker compose up -d
  cd ..\frontend
  npm run dev
)
