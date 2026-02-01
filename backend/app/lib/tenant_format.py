"""
Formatação de datas conforme locale do tenant (região).

Reutilizar sempre que uma data for apresentada em relatórios ou respostas da API.
Evita acoplamento ao formato ISO; o usuário vê a data no formato da região (ex: pt-BR → DD/MM/YYYY).
"""

from datetime import date, datetime

# Mapeamento BCP 47 (locale) -> strftime para data curta (apenas dia/mês/ano).
# Formato por região: pt-BR DD/MM/YYYY, en-US MM/DD/YYYY, etc.
# Fallback: ISO %Y-%m-%d.
_DATE_FORMAT_BY_LOCALE: dict[str, str] = {
    "pt-BR": "%d/%m/%Y",
    "pt": "%d/%m/%Y",
    "en-US": "%m/%d/%Y",
    "en-GB": "%d/%m/%Y",
    "en": "%d/%m/%Y",
    "es": "%d/%m/%Y",
    "es-ES": "%d/%m/%Y",
    "fr": "%d/%m/%Y",
    "fr-FR": "%d/%m/%Y",
    "de": "%d.%m.%Y",
    "de-DE": "%d.%m.%Y",
    "it": "%d/%m/%Y",
    "it-IT": "%d/%m/%Y",
}


def _format_for_locale(d: date, locale: str) -> str:
    """Retorna a string strftime para o locale; fallback para ISO."""
    if not locale or not locale.strip():
        return d.strftime("%Y-%m-%d")
    locale = locale.strip()
    fmt = _DATE_FORMAT_BY_LOCALE.get(locale)
    if not fmt:
        # Tentar só a parte da língua (ex: pt de pt-BR)
        lang = locale.split("-")[0].lower() if "-" in locale else locale.lower()
        fmt = _DATE_FORMAT_BY_LOCALE.get(lang)
    if not fmt:
        return d.strftime("%Y-%m-%d")
    return d.strftime(fmt)


def format_date_for_tenant(d: date, locale: str) -> str:
    """
    Formata uma data no formato da região do tenant.

    Reutilizar sempre que uma data for apresentada (relatórios PDF, títulos, API).

    :param d: Data (date) a formatar.
    :param locale: Locale BCP 47 do tenant (ex: "pt-BR", "en-US").
    :return: String formatada (ex: "01/02/2026" para pt-BR, "02/01/2026" para en-US).
    """
    return _format_for_locale(d, locale or "")


def format_datetime_for_tenant(dt: datetime, locale: str, include_time: bool = True) -> str:
    """
    Formata data/hora no formato da região do tenant.

    :param dt: datetime a formatar (com ou sem timezone).
    :param locale: Locale BCP 47 do tenant.
    :param include_time: Se True, inclui hora:minuto; senão só data.
    :return: String formatada.
    """
    d = dt.date() if hasattr(dt, "date") else dt
    date_str = _format_for_locale(d, locale or "")
    if not include_time:
        return date_str
    # Hora: usar formato 24h para pt-BR e similares; 12h para en-US se quiser (por simplicidade 24h para todos)
    time_str = dt.strftime("%H:%M") if hasattr(dt, "strftime") else ""
    return f"{date_str} {time_str}".strip()
