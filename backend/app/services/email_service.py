"""
Serviço de envio de emails usando Resend.
Faz fallback para modo "log" quando RESEND_API_KEY não está configurado (desenvolvimento).
"""
import logging
import os
import re
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Tentar importar Resend, mas não falhar se não estiver instalado
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("Resend não está instalado. Emails serão apenas logados.")


def _get_email_template_html(
    member_name: str,
    tenant_name: str,
    app_url: str,
    to_email: str,
) -> str:
    """
    Gera template HTML para email de convite.
    """
    return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Convite - {tenant_name}</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h1 style="color: #2c3e50; margin-top: 0;">Bem-vindo(a) à {tenant_name}!</h1>
    </div>

    <div style="padding: 20px 0;">
        <p>Olá <strong>{member_name}</strong>,</p>

        <p>Você foi convidado(a) para fazer parte da clínica <strong>{tenant_name}</strong> no sistema Turna.</p>

        <p>Para acessar o aplicativo e começar a usar o sistema, clique no botão abaixo:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{app_url}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                Acessar Aplicativo
            </a>
        </div>

        <p>Ou copie e cole este link no seu navegador:</p>
        <p style="word-break: break-all; color: #007bff;">{app_url}</p>

        <div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0;"><strong>Instruções:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Se você já possui uma conta, faça login normalmente.</li>
                <li>Se ainda não possui uma conta, você poderá criar uma usando seu email: <strong>{to_email}</strong></li>
            </ul>
        </div>

        <p>Bem-vindo(a)!</p>

        <p style="margin-top: 30px;">
            Atenciosamente,<br>
            <strong>Equipe {tenant_name}</strong>
        </p>
    </div>

    <div style="border-top: 1px solid #dee2e6; padding-top: 20px; margin-top: 30px; font-size: 12px; color: #6c757d;">
        <p style="margin: 0;">Este é um email automático do sistema Turna. Por favor, não responda este email.</p>
    </div>
</body>
</html>
    """.strip()


def _get_email_template_text(
    member_name: str,
    tenant_name: str,
    app_url: str,
    to_email: str,
) -> str:
    """
    Gera versão texto simples do email de convite.
    """
    return f"""
Olá {member_name},

Você foi convidado(a) para fazer parte da clínica {tenant_name} no sistema Turna.

Para acessar o aplicativo e começar a usar o sistema, acesse:
{app_url}

Instruções:
- Se você já possui uma conta, faça login normalmente.
- Se ainda não possui uma conta, você poderá criar uma usando seu email: {to_email}

Bem-vindo(a)!

Atenciosamente,
Equipe {tenant_name}

---
Este é um email automático do sistema Turna. Por favor, não responda este email.
    """.strip()


def send_member_invite(
    to_email: str,
    member_name: str,
    tenant_name: str,
    app_url: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Envia email de convite para um associado se juntar à clínica usando Resend.
    Faz fallback para modo "log" quando RESEND_API_KEY não está configurado.

    Args:
        to_email: Email do destinatário
        member_name: Nome do associado
        tenant_name: Nome da clínica/tenant
        app_url: URL do aplicativo (opcional, pega de env var se não fornecido)

    Returns:
        Tupla (success: bool, error_message: str):
        - success: True se o email foi enviado com sucesso, False caso contrário
        - error_message: Mensagem de erro específica se falhou, string vazia se sucesso
    """
    logger.info(
        f"Iniciando envio de email de convite para {to_email} (associado: {member_name}, clínica: {tenant_name})"
    )
    try:
        app_url = app_url or os.getenv("APP_URL", "http://localhost:3000")
        resend_api_key = os.getenv("RESEND_API_KEY")
        email_from = os.getenv("EMAIL_FROM")

        subject = f"Convite para se juntar à {tenant_name}"

        # Gerar templates
        html_body = _get_email_template_html(
            member_name=member_name,
            tenant_name=tenant_name,
            app_url=app_url,
            to_email=to_email,
        )
        text_body = _get_email_template_text(
            member_name=member_name,
            tenant_name=tenant_name,
            app_url=app_url,
            to_email=to_email,
        )

        # Verificar se Resend está disponível e configurado
        if not RESEND_AVAILABLE:
            error_msg = "Resend não está instalado. Configure o serviço de email."
            logger.warning(
                f"[EMAIL] {error_msg} Email de convite apenas logado para {to_email}"
            )
            return False, error_msg

        if not resend_api_key:
            error_msg = "Chave de API do Resend não configurada. Configure RESEND_API_KEY no ambiente."
            logger.warning(
                f"[EMAIL] {error_msg} Email de convite apenas logado para {to_email}"
            )
            return False, error_msg

        if not email_from:
            error_msg = "Endereço de email remetente não configurado. Configure EMAIL_FROM no ambiente."
            logger.error(
                f"[EMAIL] {error_msg} Não é possível enviar email para {to_email}"
            )
            logger.error(f"[EMAIL] Processo FALHOU - Email NÃO enviado para {to_email}")
            return False, error_msg

        # Configurar Resend
        resend.api_key = resend_api_key

        # Enviar email via Resend
        try:
            params = {
                "from": email_from,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            }
            email_response = resend.Emails.send(params)

            # Resend retorna um objeto com 'id' quando bem-sucedido
            if email_response and isinstance(email_response, dict) and "id" in email_response:
                return True, ""
            elif email_response:
                # Pode retornar objeto com atributo id
                email_id = getattr(email_response, "id", None)
                if email_id:
                    return True, ""

            error_msg = f"Resposta inesperada do serviço de email: {email_response}"
            logger.error(f"[EMAIL] ❌ FALHA - {error_msg} para {to_email}")
            logger.error(f"[EMAIL] Processo FALHOU - Email NÃO enviado para {to_email}")
            return False, error_msg

        except Exception as resend_error:
            # Capturar exceções específicas do Resend sem expor API key
            error_msg_raw = str(resend_error)
            # Remover possíveis vazamentos de API key
            if resend_api_key and resend_api_key in error_msg_raw:
                error_msg_raw = error_msg_raw.replace(resend_api_key, "***REDACTED***")

            # Extrair mensagem de erro mais amigável
            # Detectar erro de domínio não verificado (mensagem específica do Resend)
            if "domain" in error_msg_raw.lower() and ("not verified" in error_msg_raw.lower() or "não verificado" in error_msg_raw.lower() or "unverified" in error_msg_raw.lower()):
                # Extrair o domínio da mensagem de erro se possível
                # Exemplo: "The basecompany.com.br domain is not verified"
                domain_pattern = r"\b([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"
                domain_match = re.search(domain_pattern, error_msg_raw)

                if domain_match:
                    domain = domain_match.group(0)
                    error_msg = f"Domínio '{domain}' não está verificado no Resend. Adicione e verifique o domínio em https://resend.com/domains"
                else:
                    error_msg = "Domínio de email não está verificado no Resend. Adicione e verifique o domínio em https://resend.com/domains"
            elif "domain" in error_msg_raw.lower() or "verificado" in error_msg_raw.lower() or "verified" in error_msg_raw.lower():
                error_msg = "Domínio de email não verificado no Resend. Verifique o domínio nas configurações."
            elif "invalid" in error_msg_raw.lower() or "inválido" in error_msg_raw.lower():
                error_msg = "Configuração de email inválida. Verifique EMAIL_FROM e RESEND_API_KEY."
            elif "unauthorized" in error_msg_raw.lower() or "401" in error_msg_raw:
                error_msg = "Chave de API do Resend inválida ou expirada. Verifique RESEND_API_KEY."
            elif "rate limit" in error_msg_raw.lower() or "quota" in error_msg_raw.lower():
                error_msg = "Limite de envio de emails excedido. Tente novamente mais tarde."
            else:
                error_msg = f"Erro ao enviar email: {error_msg_raw[:100]}"  # Limitar tamanho

            logger.error(
                f"[EMAIL] ❌ FALHA - Erro ao enviar email via Resend para {to_email}: {error_msg_raw}",
                exc_info=True,
            )
            logger.error(f"[EMAIL] Processo FALHOU - Email NÃO enviado para {to_email}")
            return False, error_msg

    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)[:100]}"
        logger.error(
            f"[EMAIL] ❌ FALHA - Erro inesperado ao processar envio de email de convite para {to_email}: {e}",
            exc_info=True,
        )
        logger.error(f"[EMAIL] Processo FALHOU - Email NÃO enviado para {to_email}")
        return False, error_msg
