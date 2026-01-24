import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from typing import Optional
from app.storage.config import S3Config


class S3Client:
    """Cliente S3/MinIO usando boto3."""

    def __init__(self, config: Optional[S3Config] = None):
        self.config = config or S3Config()
        self._client = None
        self._ensure_client()

    def _ensure_client(self):
        """Cria cliente boto3 se ainda não existe."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key_id,
                aws_secret_access_key=self.config.secret_access_key,
                region_name=self.config.region,
                use_ssl=self.config.use_ssl,
                config=Config(signature_version="s3v4"),
            )

    def ensure_bucket_exists(self) -> bool:
        """Cria bucket se não existir. Retorna True se criado ou já existia."""
        try:
            self._client.head_bucket(Bucket=self.config.bucket_name)
            return True  # Bucket já existe
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                # Bucket não existe, criar
                try:
                    # Para MinIO, não precisa especificar LocationConstraint
                    # Para S3 real, pode ser necessário
                    if "minio" in self.config.endpoint_url.lower() or not self.config.use_ssl:
                        # MinIO ou S3 local
                        self._client.create_bucket(Bucket=self.config.bucket_name)
                    else:
                        # S3 real - pode precisar de LocationConstraint
                        self._client.create_bucket(
                            Bucket=self.config.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.config.region
                            } if self.config.region != "us-east-1" else {}
                        )
                    return True
                except ClientError as create_error:
                    raise Exception(
                        f"Erro ao criar bucket '{self.config.bucket_name}': {create_error}. "
                        f"Verifique se o MinIO está rodando e acessível em {self.config.endpoint_url}"
                    )
            else:
                raise Exception(
                    f"Erro ao verificar bucket '{self.config.bucket_name}': {e}. "
                    f"Verifique se o MinIO está rodando e acessível em {self.config.endpoint_url}"
                )

    def upload_file(
        self, file_path: str, s3_key: str, content_type: Optional[str] = None
    ) -> str:
        """
        Faz upload de arquivo para S3/MinIO.

        Args:
            file_path: Caminho local do arquivo
            s3_key: Chave S3 (ex: "1/import/arquivo.pdf")
            content_type: MIME type (opcional)

        Returns:
            URL completa do arquivo no S3
        """
        self.ensure_bucket_exists()

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self._client.upload_file(
            file_path, self.config.bucket_name, s3_key, ExtraArgs=extra_args
        )

        # Construir URL
        if self.config.endpoint_url:
            url = f"{self.config.endpoint_url}/{self.config.bucket_name}/{s3_key}"
        else:
            url = f"s3://{self.config.bucket_name}/{s3_key}"

        return url

    def upload_fileobj(
        self, file_obj, s3_key: str, content_type: Optional[str] = None
    ) -> str:
        """
        Faz upload de objeto de arquivo (BytesIO, etc) para S3/MinIO.

        Args:
            file_obj: Objeto de arquivo (BytesIO, file handle, etc)
            s3_key: Chave S3 (ex: "1/import/arquivo.pdf")
            content_type: MIME type (opcional)

        Returns:
            URL completa do arquivo no S3
        """
        self.ensure_bucket_exists()

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        self._client.upload_fileobj(
            file_obj, self.config.bucket_name, s3_key, ExtraArgs=extra_args
        )

        # Construir URL
        if self.config.endpoint_url:
            url = f"{self.config.endpoint_url}/{self.config.bucket_name}/{s3_key}"
        else:
            url = f"s3://{self.config.bucket_name}/{s3_key}"

        return url

    def download_file(self, s3_key: str, local_path: str) -> None:
        """
        Faz download de arquivo do S3/MinIO para arquivo local.

        Args:
            s3_key: Chave S3
            local_path: Caminho local onde salvar o arquivo
        """
        self._client.download_file(self.config.bucket_name, s3_key, local_path)

    def get_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Gera URL presignada (temporária) para acesso ao arquivo.

        Args:
            s3_key: Chave S3
            expiration: Tempo de expiração em segundos (padrão: 1 hora)

        Returns:
            URL presignada
        """
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.config.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            raise Exception(f"Erro ao gerar URL presignada: {e}")

    def delete_file(self, s3_key: str) -> None:
        """
        Exclui arquivo do S3/MinIO.

        Args:
            s3_key: Chave S3 do arquivo a ser excluído
        """
        try:
            self._client.delete_object(
                Bucket=self.config.bucket_name,
                Key=s3_key,
            )
        except ClientError as e:
            raise Exception(f"Erro ao excluir arquivo do S3: {e}")

    def file_exists(self, s3_key: str) -> bool:
        """
        Verifica se um arquivo existe no S3/MinIO.

        Args:
            s3_key: Chave S3 do arquivo

        Returns:
            True se o arquivo existe, False caso contrário
        """
        try:
            self._client.head_object(
                Bucket=self.config.bucket_name,
                Key=s3_key,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                return False
            # Outros erros são propagados
            raise Exception(f"Erro ao verificar existência do arquivo: {e}")

    def get_file_stream(self, s3_key: str):
        """
        Obtém stream do arquivo do S3/MinIO.

        Args:
            s3_key: Chave S3 do arquivo

        Returns:
            Stream do arquivo (Body do response)
        """
        try:
            response = self._client.get_object(
                Bucket=self.config.bucket_name,
                Key=s3_key,
            )
            return response['Body']
        except ClientError as e:
            raise Exception(f"Erro ao obter arquivo do S3: {e}")