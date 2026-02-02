"""
Geração de PDFs de listas (relatórios simples em tabela).

Usa o layout reutilizável (Turna + filtros + conteúdo) e ReportLab.
Cada função recebe os dados já carregados e o texto dos filtros utilizados.
"""

from __future__ import annotations

from app.report.pdf_layout import build_report_pdf


def render_tenant_list_pdf(
    rows: list[tuple[str, str]],
    filters: list[tuple[str, str]] | None = None,
    header_title: str | None = None,
) -> bytes:
    """Gera PDF com lista de clínicas: nome e rótulo."""
    headers = ["Nome", "Rótulo"]
    data = [[str(r[0]), str(r[1])] for r in rows]
    return build_report_pdf(
        report_title="Relatório de clínicas",
        filters=filters,
        headers=headers,
        rows=data,
        header_title=header_title,
    )


def render_member_list_pdf(
    rows: list[tuple[str, str, str, str, str, str]],
    filters: list[tuple[str, str]] | None = None,
    header_title: str | None = None,
) -> bytes:
    """Gera PDF com lista de associados: ordem, rótulo, nome, email, situação, pode pediatria."""
    headers = ["", "Rótulo", "Nome", "E-mail", "Situação", "Pode pediatria?"]
    data = [[str(r[0]), str(r[1]), str(r[2]), str(r[3]), str(r[4]), str(r[5])] for r in rows]
    col_widths = [0.06, 0.12, 0.20, 0.32, 0.15, 0.15]  # ordem, rótulo, nome, email, situação, pediatria
    return build_report_pdf(
        report_title="Relatório de associados",
        filters=filters,
        headers=headers,
        rows=data,
        header_title=header_title,
        col_widths=col_widths,
    )


def render_hospital_list_pdf(
    rows: list[tuple[str, str]],
    filters: list[tuple[str, str]] | None = None,
    header_title: str | None = None,
) -> bytes:
    """Gera PDF com lista de hospitais: nome e rótulo."""
    headers = ["Nome", "Rótulo"]
    data = [[str(r[0]), str(r[1])] for r in rows]
    return build_report_pdf(
        report_title="Relatório de hospitais",
        filters=filters,
        headers=headers,
        rows=data,
        header_title=header_title,
    )


def render_file_list_pdf(
    rows: list[tuple[str, str, str]],
    filters: list[tuple[str, str]] | None = None,
    header_title: str | None = None,
) -> bytes:
    """Gera PDF com lista de arquivos: nome do hospital, nome do arquivo, data de cadastro."""
    headers = ["Hospital", "Arquivo", "Data de cadastro"]
    data = [[str(r[0]), str(r[1]), str(r[2])] for r in rows]
    return build_report_pdf(
        report_title="Relatório de arquivos",
        filters=filters,
        headers=headers,
        rows=data,
        header_title=header_title,
    )
