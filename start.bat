@echo off
cls
cd /d "%~dp0"
cd backend && docker compose up -d && cd ..\frontend && npm run dev
