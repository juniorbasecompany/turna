import os
from typing import Optional
from pathlib import Path


class S3Config:
    """Configuração S3/MinIO lida de variáveis de ambiente."""

    def __init__(self):
        endpoint_url = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")

        # Validar que não é um placeholder
        if "SEU_S3" in endpoint_url.upper() or endpoint_url.startswith("https://SEU"):
            project_root = Path(__file__).resolve().parent.parent.parent
            env_file = project_root / ".env"
            raise ValueError(
                f"Variável S3_ENDPOINT_URL contém placeholder inválido: {endpoint_url}\n\n"
                f"SOLUÇÃO: Edite o arquivo backend/.env ({env_file}) e configure:\n"
                f"  S3_ENDPOINT_URL=http://localhost:9000\n"
                f"  S3_ACCESS_KEY_ID=minio\n"
                f"  S3_SECRET_ACCESS_KEY=minio12345\n"
                f"  S3_BUCKET_NAME=turna\n"
                f"  S3_REGION=us-east-1\n"
                f"  S3_USE_SSL=false\n\n"
                f"Ou defina essas variáveis no seu ambiente antes de rodar a aplicação."
            )

        self.endpoint_url: str = endpoint_url
        self.access_key_id: str = os.getenv("S3_ACCESS_KEY_ID", "minio")
        self.secret_access_key: str = os.getenv("S3_SECRET_ACCESS_KEY", "minio12345")
        self.bucket_name: str = os.getenv("S3_BUCKET_NAME", "turna")
        self.region: str = os.getenv("S3_REGION", "us-east-1")
        self.use_ssl: bool = os.getenv("S3_USE_SSL", "false").lower() == "true"
