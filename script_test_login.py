"""Script para testar se o login.html está sendo processado corretamente."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env
project_root = Path(__file__).resolve().parent
load_dotenv(project_root / ".env")

# Lê o HTML
html_path = project_root / "static" / "login.html"
if html_path.exists():
    html_content = html_path.read_text(encoding="utf-8")
    
    # Substitui o placeholder
    google_client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    print(f"GOOGLE_CLIENT_ID do .env: {google_client_id}")
    
    html_content_replaced = html_content.replace("COLE_AQUI_SEU_GOOGLE_CLIENT_ID", google_client_id)
    
    # Verifica se foi substituído
    if "COLE_AQUI_SEU_GOOGLE_CLIENT_ID" in html_content_replaced:
        print("ERRO: Placeholder não foi substituído!")
    else:
        print("OK: Placeholder foi substituído corretamente")
        
    # Verifica se o CLIENT_ID está no HTML
    if google_client_id and google_client_id in html_content_replaced:
        print(f"OK: CLIENT_ID encontrado no HTML processado")
        # Mostra a linha onde está
        for i, line in enumerate(html_content_replaced.split('\n'), 1):
            if 'CLIENT_ID' in line:
                print(f"Linha {i}: {line.strip()[:100]}")
    else:
        print("ERRO: CLIENT_ID não encontrado no HTML processado")
else:
    print(f"ERRO: Arquivo não encontrado: {html_path}")
