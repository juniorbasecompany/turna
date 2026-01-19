"""
Serviço de envio de emails.
Por enquanto, apenas loga o email. Pode ser expandido para usar SMTP, SendGrid, AWS SES, etc.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def send_professional_invite(
    to_email: str,
    professional_name: str,
    tenant_name: str,
    app_url: Optional[str] = None,
) -> bool:
    """
    Envia email de convite para um profissional se juntar à clínica.

    Args:
        to_email: Email do destinatário
        professional_name: Nome do profissional
        tenant_name: Nome da clínica/tenant
        app_url: URL do aplicativo (opcional, pega de env var se não fornecido)

    Returns:
        True se o email foi enviado com sucesso, False caso contrário
    """
    try:
        app_url = app_url or os.getenv("APP_URL", "http://localhost:3000")

        subject = f"Convite para se juntar à {tenant_name}"

        body = f"""
Olá {professional_name},

Você foi convidado(a) para fazer parte da clínica {tenant_name} no sistema Turna.

Para acessar o aplicativo e começar a usar o sistema, acesse:
{app_url}

Se você já possui uma conta, faça login normalmente.
Se ainda não possui uma conta, você poderá criar uma usando seu email: {to_email}

Bem-vindo(a)!

Equipe {tenant_name}
        """.strip()

        # Por enquanto, apenas loga o email
        # TODO: Implementar envio real via SMTP, SendGrid, AWS SES, etc.
        logger.info(f"Email de convite enviado para {to_email}")
        logger.info(f"Assunto: {subject}")
        logger.info(f"Corpo:\n{body}")

        # Em produção, aqui você faria o envio real:
        # - Usar smtplib para SMTP
        # - Usar boto3 para AWS SES
        # - Usar sendgrid para SendGrid
        # - etc.

        return True
    except Exception as e:
        logger.error(f"Erro ao enviar email de convite para {to_email}: {e}", exc_info=True)
        return False
