import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import UploadFile
from sqlmodel import Session
from app.storage.client import S3Client
from app.storage.config import S3Config
from app.model.file import File


class StorageService:
    """Serviço de storage que combina S3Client com modelos do banco."""

    def __init__(self, config: Optional[S3Config] = None):
        self.config = config or S3Config()
        self.client = S3Client(self.config)

    def _generate_s3_key(
        self, tenant_id: int, file_type: str, filename: str
    ) -> str:
        """
        Gera chave S3 seguindo padrão: {tenant_id}/{file_type}/{filename}

        Args:
            tenant_id: ID do tenant
            file_type: Tipo de arquivo (ex: "import", "pdf", "schedule")
            filename: Nome do arquivo

        Returns:
            Chave S3 (ex: "1/import/demanda.pdf")
        """
        # Sanitizar filename (remover caracteres problemáticos)
        safe_filename = filename.replace(" ", "_")
        # Adicionar UUID para evitar colisões
        name, ext = os.path.splitext(safe_filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"

        return f"{tenant_id}/{file_type}/{unique_filename}"

    def upload_imported_file(
        self, session: Session, tenant_id: int, hospital_id: int, file: UploadFile, filename: Optional[str] = None
    ) -> File:
        """
        Faz upload de arquivo importado (PDF, XLSX, etc) e cria registro File.

        Args:
            session: Sessão do banco
            tenant_id: ID do tenant
            hospital_id: ID do hospital (obrigatório)
            file: Arquivo do FastAPI UploadFile
            filename: Nome do arquivo (opcional, usa file.filename se não fornecido)

        Returns:
            Modelo File criado
        """
        filename = filename or file.filename or "unknown"
        content_type = file.content_type or "application/octet-stream"

        # Ler conteúdo do arquivo
        file_content = file.file.read()
        file_size = len(file_content)

        # Resetar ponteiro do arquivo (caso seja necessário ler novamente)
        file.file.seek(0)

        # Gerar chave S3
        s3_key = self._generate_s3_key(tenant_id, "import", filename)

        # Upload para S3
        import io
        file_obj = io.BytesIO(file_content)
        file_obj.seek(0)  # Garantir que o ponteiro está no início
        s3_url = self.client.upload_fileobj(
            file_obj, s3_key, content_type=content_type
        )

        # Criar registro no banco
        file_model = File(
            tenant_id=tenant_id,
            hospital_id=hospital_id,
            filename=filename,
            content_type=content_type,
            s3_key=s3_key,
            s3_url=s3_url,
            file_size=file_size,
        )

        try:
            session.add(file_model)
            session.commit()
            session.refresh(file_model)
        except Exception as db_error:
            session.rollback()
            # Verificar se é erro de tabela não existente
            error_msg = str(db_error).lower()
            if "does not exist" in error_msg or "relation" in error_msg or "table" in error_msg:
                raise Exception(
                    f"Tabela 'file' não existe no banco. "
                    f"Execute a migração: alembic upgrade head"
                ) from db_error
            raise Exception(f"Erro ao salvar arquivo no banco: {db_error}") from db_error

        return file_model

    def upload_schedule_pdf(
        self, session: Session, tenant_id: int, schedule_id: int, pdf_bytes: bytes
    ) -> File:
        """
        Faz upload de PDF de escala e cria registro File.

        Args:
            session: Sessão do banco
            tenant_id: ID do tenant
            schedule_id: ID da escala
            pdf_bytes: Bytes do PDF

        Returns:
            Modelo File criado
        """
        filename = f"schedule_{schedule_id}.pdf"
        content_type = "application/pdf"
        file_size = len(pdf_bytes)

        # Gerar chave S3
        s3_key = self._generate_s3_key(tenant_id, "schedule", filename)

        # Upload para S3
        import io
        file_obj = io.BytesIO(pdf_bytes)
        s3_url = self.client.upload_fileobj(
            file_obj, s3_key, content_type=content_type
        )

        # Criar registro no banco
        file_model = File(
            tenant_id=tenant_id,
            filename=filename,
            content_type=content_type,
            s3_key=s3_key,
            s3_url=s3_url,
            file_size=file_size,
        )

        try:
            session.add(file_model)
            session.commit()
            session.refresh(file_model)
        except Exception as db_error:
            session.rollback()
            # Verificar se é erro de tabela não existente
            error_msg = str(db_error).lower()
            if "does not exist" in error_msg or "relation" in error_msg or "table" in error_msg:
                raise Exception(
                    f"Tabela 'file' não existe no banco. "
                    f"Execute a migração: alembic upgrade head"
                ) from db_error
            raise Exception(f"Erro ao salvar arquivo no banco: {db_error}") from db_error

        return file_model

    def get_file_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Retorna URL presignada (temporária) para acesso ao arquivo.

        Args:
            s3_key: Chave S3 do arquivo
            expiration: Tempo de expiração em segundos (padrão: 1 hora)

        Returns:
            URL presignada
        """
        return self.client.get_presigned_url(s3_key, expiration=expiration)

    def delete_file(self, s3_key: str) -> None:
        """
        Exclui arquivo do S3/MinIO.

        Args:
            s3_key: Chave S3 do arquivo a ser excluído
        """
        self.client.delete_file(s3_key)
