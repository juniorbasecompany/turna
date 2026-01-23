from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from app.db.session import engine
from app.model.base import utc_now
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.schedule_version import ScheduleStatus, ScheduleVersion
from app.storage.client import S3Client

from demand.read import extract_demand
from strategy.greedy.solve import solve_greedy


_MAX_STALE_WINDOW = timedelta(hours=1)


def _stale_window_for(session: Session, *, tenant_id: int, job_type: JobType) -> timedelta:
    """
    Janela dinâmica:
      - 10x a média de duração dos últimos 10 jobs COMPLETED do mesmo tipo (tenant + job_type)
      - fallback: 1h se não existir média
      - teto: 1h em qualquer situação
    """
    rows = session.exec(
        select(Job)
        .where(
            Job.tenant_id == tenant_id,
            Job.job_type == job_type,
            Job.status == JobStatus.COMPLETED,
            Job.started_at.is_not(None),  # type: ignore[attr-defined]
            Job.completed_at.is_not(None),
        )
        .order_by(Job.completed_at.desc())  # type: ignore[union-attr]
        .limit(10)
    ).all()

    durations: list[float] = []
    for j in rows:
        if not j.started_at or not j.completed_at:
            continue
        durations.append((j.completed_at - j.started_at).total_seconds())

    if not durations:
        return _MAX_STALE_WINDOW

    avg_seconds = sum(durations) / len(durations)
    window = timedelta(seconds=avg_seconds * 10)
    return min(window, _MAX_STALE_WINDOW)


async def ping_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Job fake para validar fila/worker.
    Atualiza status no banco e grava um payload simples em result_data.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        try:
            job.result_data = {"pong": True}
            job.status = JobStatus.COMPLETED
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": str(e), "job_id": job.id}


def _safe_error_message(e: Exception, max_len: int = 500) -> str:
    msg = f"{type(e).__name__}: {str(e)}".strip()
    return msg[:max_len]


def _load_pros_from_repo_test() -> list[dict]:
    """
    Fallback de DEV: usa `test/profissionais.json` (mesmo formato do `app.py`).
    Em produção, o ideal é ter modelo/tabela de profissionais.
    """
    from pathlib import Path
    import json

    project_root = Path(__file__).resolve().parents[2]
    path = project_root / "test" / "profissionais.json"
    pros_json = json.loads(path.read_text(encoding="utf-8"))
    pros = [{**p, "vacation": [tuple(v) for v in p.get("vacation", [])]} for p in pros_json]
    return sorted(pros, key=lambda p: p.get("sequence", 0))


def _demands_from_extract_result(result_data: dict, *, period_start_at, period_end_at) -> tuple[list[dict], int]:
    """
    Converte `result_data` do EXTRACT_DEMAND para o formato esperado pelos solvers:
      - day: 1..N
      - start/end: horas em float (ex.: 9.5 = 09:30)
      - is_pediatric: bool (default False)
    """
    from datetime import datetime

    demands_raw = (result_data or {}).get("demands") or []
    if not isinstance(demands_raw, list):
        raise RuntimeError("result_data.demands inválido")

    # Assume timestamps com offset/Z (diretiva).
    start_date = period_start_at.date()
    end_date = period_end_at.date()
    days = (end_date - start_date).days
    if days <= 0:
        raise RuntimeError("Período inválido: period_end_at deve ser maior que period_start_at")

    def parse_dt(s: str) -> datetime:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    out: list[dict] = []
    for i, d in enumerate(demands_raw):
        if not isinstance(d, dict):
            continue
        st = parse_dt(str(d.get("start_time")))
        en = parse_dt(str(d.get("end_time")))
        if en <= st:
            continue

        # Dia relativo ao period_start_at (mesma data do start_time).
        day_idx = (st.date() - start_date).days + 1
        if day_idx < 1 or day_idx > days:
            continue

        start_h = st.hour + (st.minute / 60.0)
        end_h = en.hour + (en.minute / 60.0)
        did = str(d.get("room") or f"D{i+1}")
        out.append(
            {
                "id": did,
                "day": int(day_idx),
                "start": float(start_h),
                "end": float(end_h),
                "is_pediatric": bool(d.get("is_pediatric") or False),
                "source": d.get("source"),
            }
        )

    return out, days


async def generate_schedule_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Gera escala a partir de um Job de extração (EXTRACT_DEMAND) e grava em ScheduleVersion.result_data.
    MVP: usa solver greedy.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        try:
            input_data = job.input_data or {}
            schedule_version_id = int(input_data.get("schedule_version_id"))
            extract_job_id = int(input_data.get("extract_job_id"))
            allocation_mode = str(input_data.get("allocation_mode") or "greedy").strip().lower()

            if allocation_mode != "greedy":
                raise RuntimeError("allocation_mode não suportado no MVP (apenas greedy)")

            sv = session.get(ScheduleVersion, schedule_version_id)
            if not sv:
                raise RuntimeError(f"ScheduleVersion não encontrado (id={schedule_version_id})")
            if sv.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            extract_job = session.get(Job, extract_job_id)
            if not extract_job:
                raise RuntimeError(f"Job de extração não encontrado (id={extract_job_id})")
            if extract_job.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")
            if extract_job.status != JobStatus.COMPLETED or not isinstance(extract_job.result_data, dict):
                raise RuntimeError("Job de extração não está COMPLETED (ou result_data ausente)")

            # Profissionais: payload > fallback dev
            pros_by_sequence = input_data.get("pros_by_sequence")
            if pros_by_sequence is None:
                pros_by_sequence = _load_pros_from_repo_test()
            if not isinstance(pros_by_sequence, list) or not pros_by_sequence:
                raise RuntimeError("pros_by_sequence ausente/ inválido")

            demands, days = _demands_from_extract_result(
                extract_job.result_data,
                period_start_at=sv.period_start_at,
                period_end_at=sv.period_end_at,
            )
            if not demands:
                raise RuntimeError("Nenhuma demanda dentro do período informado")

            per_day, total_cost = solve_greedy(
                demands=demands,
                pros_by_sequence=pros_by_sequence,
                days=days,
                unassigned_penalty=1000,
                ped_unassigned_extra_penalty=1000,
                base_shift=0,
            )

            sv.result_data = {
                "allocation_mode": "greedy",
                "days": days,
                "total_cost": total_cost,
                "per_day": per_day,
                "extract_job_id": extract_job_id,
            }
            sv.generated_at = now
            sv.updated_at = now
            sv.status = ScheduleStatus.DRAFT
            session.add(sv)

            job.status = JobStatus.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            job.result_data = {"schedule_version_id": sv.id, "total_cost": total_cost}
            job.error_message = None
            session.add(job)

            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id, "schedule_version_id": sv.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = _safe_error_message(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}

async def extract_demand_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Extrai demandas (OpenAI) a partir de um File (PDF/JPEG/PNG) já armazenado no S3/MinIO.
    Persistência:
      - `Job.result_data`: JSON com o resultado
      - `Job.status`: RUNNING -> COMPLETED/FAILED
      - `Job.completed_at`: UTC
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        tmp_path: str | None = None
        try:
            input_data = job.input_data or {}
            file_id = int(input_data.get("file_id"))

            file_model = session.get(File, file_id)
            if not file_model:
                raise RuntimeError(f"File não encontrado (file_id={file_id})")
            if file_model.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            # Carregar hospital via file.hospital_id
            from app.model.hospital import Hospital
            hospital = session.get(Hospital, file_model.hospital_id)
            if not hospital:
                raise RuntimeError(f"Hospital não encontrado (hospital_id={file_model.hospital_id})")
            if hospital.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (hospital tenant mismatch)")

            # Usar prompt do hospital
            hospital_prompt = hospital.prompt

            filename = file_model.filename or "file"
            _, ext = os.path.splitext(filename)
            ext = (ext or "").lower()
            if ext not in {".pdf", ".png", ".jpg", ".jpeg"}:
                # Fallback: o extractor suporta PDF/JPEG/PNG; assume PDF quando extensão desconhecida.
                ext = ".pdf"

            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = tmp.name

            # Download do S3/MinIO para arquivo temporário
            s3 = S3Client()
            s3.download_file(file_model.s3_key, tmp_path)

            # Executa extração usando prompt do hospital (retorna dict JSON-serializável)
            result = extract_demand(tmp_path, custom_user_prompt=hospital_prompt)
            if isinstance(result, dict):
                meta = result.setdefault("meta", {})
                meta.pop("pdf_path", None)
                meta["file_id"] = file_id
                meta["filename"] = filename
                meta["hospital_id"] = hospital.id
                meta["hospital_name"] = hospital.name

            job.result_data = result
            job.status = JobStatus.COMPLETED
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            job.error_message = None
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = _safe_error_message(e)
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


async def generate_thumbnail_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Gera thumbnail WebP 500x500 para arquivo (PNG/JPEG/PDF).
    Thumbnail é salvo no MinIO com chave: {original_key}.thumbnail.webp
    Idempotente: se thumbnail já existe, não regenera.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        if job.status != JobStatus.PENDING:
            return {"ok": False, "error": "job_not_pending", "job_id": job_id, "status": job.status}

        now = utc_now()
        job.status = JobStatus.RUNNING
        job.started_at = now  # type: ignore[attr-defined]
        job.updated_at = now
        session.add(job)
        session.commit()

        tmp_path: str | None = None
        file_id: int | None = None
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[THUMBNAIL] Iniciando job (job_id={job_id})")

            input_data = job.input_data or {}
            file_id = int(input_data.get("file_id"))
            logger.info(f"[THUMBNAIL] Processando file_id={file_id}")

            file_model = session.get(File, file_id)
            if not file_model:
                raise RuntimeError(f"File não encontrado (file_id={file_id})")
            if file_model.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            # Calcular thumbnail_key: original_key + ".thumbnail.webp"
            original_key = file_model.s3_key
            thumbnail_key = original_key + ".thumbnail.webp"

            # Idempotência: verificar se thumbnail já existe
            s3 = S3Client()
            if s3.file_exists(thumbnail_key):
                # Thumbnail já existe, não regenerar
                job.status = JobStatus.COMPLETED
                job.completed_at = utc_now()
                job.updated_at = job.completed_at
                job.result_data = {
                    "file_id": file_id,
                    "original_key": original_key,
                    "thumbnail_key": thumbnail_key,
                    "skipped": True,
                    "reason": "thumbnail já existe",
                }
                job.error_message = None
                session.add(job)
                session.commit()
                session.refresh(job)
                return {"ok": True, "job_id": job.id, "skipped": True}

            # Detectar mime type
            mime = file_model.content_type or ""
            filename = file_model.filename or "file"
            _, ext = os.path.splitext(filename)
            ext = (ext or "").lower()

            # Determinar se é imagem, PDF ou Excel
            is_image = mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg"}
            is_pdf = mime == "application/pdf" or ext == ".pdf"
            # MIME types comuns para Excel
            excel_mime_types = {
                "application/vnd.ms-excel",  # XLS antigo
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
                "application/excel",  # Alternativo para XLS
                "application/x-excel",  # Alternativo para XLS
                "application/x-msexcel",  # Alternativo para XLS
            }
            is_excel = (
                mime in excel_mime_types
                or ext in {".xls", ".xlsx"}
            )

            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[THUMBNAIL] file_id={file_id}, mime={mime}, ext={ext}, is_image={is_image}, is_pdf={is_pdf}, is_excel={is_excel}")
            logger.info(f"[THUMBNAIL] Detalhes detecção: mime='{mime}', ext='{ext}', mime in excel_mime_types={mime in excel_mime_types}, ext in excel_exts={ext in {'.xls', '.xlsx'}}")

            if not (is_image or is_pdf or is_excel):
                # Outro tipo: não gerar thumbnail (frontend exibirá fallback)
                logger.warning(f"[THUMBNAIL] Tipo não suportado para file_id={file_id}: mime={mime}, ext={ext}")
                job.status = JobStatus.COMPLETED
                job.completed_at = utc_now()
                job.updated_at = job.completed_at
                job.result_data = {
                    "file_id": file_id,
                    "original_key": original_key,
                    "thumbnail_key": thumbnail_key,
                    "skipped": True,
                    "reason": f"tipo não suportado (mime={mime}, ext={ext})",
                }
                job.error_message = None
                session.add(job)
                session.commit()
                session.refresh(job)
                return {"ok": True, "job_id": job.id, "skipped": True}

            logger.info(f"[THUMBNAIL] Tipo suportado detectado: is_image={is_image}, is_pdf={is_pdf}, is_excel={is_excel}")

            # Download do arquivo original para arquivo temporário
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = tmp.name

            s3.download_file(original_key, tmp_path)

            # Gerar imagem base
            from PIL import Image
            image: Image.Image | None = None

            if is_pdf:
                # PDF: renderizar página 1 com PyMuPDF
                import fitz  # PyMuPDF
                pdf_doc = fitz.open(tmp_path)
                if len(pdf_doc) == 0:
                    raise RuntimeError("PDF vazio")
                page = pdf_doc[0]  # Primeira página
                # Renderizar em alta resolução (zoom 2.0 para melhor qualidade)
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                # Converter para PIL Image
                img_data = pix.tobytes("png")
                import io
                image = Image.open(io.BytesIO(img_data))
                pdf_doc.close()
            elif is_excel:
                # Excel (XLS/XLSX): renderizar primeira planilha como tabela
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"[THUMBNAIL] Processando Excel: file_id={file_id}, ext={ext}")

                import pandas as pd
                import matplotlib
                matplotlib.use('Agg')  # Backend sem GUI
                import matplotlib.pyplot as plt
                import io

                # Ler primeira planilha (limitado a 50 linhas para performance)
                try:
                    logger.info(f"[THUMBNAIL] Lendo Excel com engine apropriado: ext={ext}")
                    if ext == ".xls":
                        df = pd.read_excel(tmp_path, engine='xlrd', nrows=50)
                    else:
                        # XLSX ou extensão não reconhecida: tentar openpyxl primeiro
                        try:
                            df = pd.read_excel(tmp_path, engine='openpyxl', nrows=50)
                        except Exception as e1:
                            logger.warning(f"[THUMBNAIL] Erro com openpyxl, tentando xlrd: {e1}")
                            # Fallback para xlrd se openpyxl falhar
                            df = pd.read_excel(tmp_path, engine='xlrd', nrows=50)
                    logger.info(f"[THUMBNAIL] Excel lido: {len(df)} linhas, {len(df.columns)} colunas")
                except Exception as e:
                    logger.error(f"[THUMBNAIL] Erro ao ler Excel: {e}", exc_info=True)
                    raise RuntimeError(f"Erro ao ler Excel: {e}")

                if df.empty:
                    logger.warning(f"[THUMBNAIL] Planilha Excel vazia para file_id={file_id}")
                    raise RuntimeError("Planilha Excel vazia")

                # Criar figura matplotlib
                logger.info(f"[THUMBNAIL] Criando figura matplotlib")
                fig, ax = plt.subplots(figsize=(10, 8), dpi=100)
                ax.axis('tight')
                ax.axis('off')

                # Criar tabela (limitado a 20 colunas para não ficar muito largo)
                df_display = df.iloc[:, :20]  # Primeiras 20 colunas

                # Limitar número de linhas exibidas (máximo 30 para não ficar muito grande)
                df_display = df_display.iloc[:30]

                # Converter valores para string (matplotlib table precisa de strings)
                # Substituir NaN por string vazia e truncar valores muito longos
                def format_cell_value(val):
                    if pd.isna(val):
                        return ''
                    s = str(val)
                    # Truncar valores muito longos (máximo 50 caracteres)
                    if len(s) > 50:
                        return s[:47] + '...'
                    return s

                # Usar apply com função para cada célula (applymap está deprecated)
                df_display_str = df_display.map(format_cell_value)

                table = ax.table(
                    cellText=df_display_str.values.tolist(),
                    colLabels=[str(col)[:30] for col in df_display_str.columns.tolist()],  # Truncar nomes de colunas também
                    cellLoc='left',
                    loc='center',
                    bbox=[0, 0, 1, 1]
                )
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)

                # Converter figura para PIL Image
                logger.info(f"[THUMBNAIL] Convertendo figura para PIL Image")
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, pad_inches=0.1)
                buf.seek(0)
                image = Image.open(buf)
                plt.close(fig)
                logger.info(f"[THUMBNAIL] Excel convertido para imagem: {image.size}")
            elif is_image:
                # PNG/JPEG: abrir com Pillow
                image = Image.open(tmp_path)
                # Converter para RGB se necessário (WebP não suporta RGBA diretamente)
                if image.mode in ("RGBA", "LA", "P"):
                    # Criar fundo branco para imagens com transparência
                    rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        # Converter paleta para RGBA primeiro
                        image = image.convert("RGBA")
                    if image.mode in ("RGBA", "LA"):
                        # Usar canal alpha como máscara
                        rgb_image.paste(image, mask=image.split()[-1])
                    else:
                        # Sem transparência, apenas colar
                        rgb_image.paste(image)
                    image = rgb_image
                elif image.mode != "RGB":
                    image = image.convert("RGB")

            if not image:
                raise RuntimeError("Falha ao gerar imagem base")

            # Transformar para 500x500 (fit + fundo branco)
            target_size = (500, 500)
            # Calcular tamanho mantendo proporção (fit)
            image.thumbnail(target_size, Image.Resampling.LANCZOS)
            # Criar imagem 500x500 com fundo branco
            thumbnail = Image.new("RGB", target_size, (255, 255, 255))
            # Centralizar imagem original
            x_offset = (target_size[0] - image.size[0]) // 2
            y_offset = (target_size[1] - image.size[1]) // 2
            thumbnail.paste(image, (x_offset, y_offset))

            # Salvar thumbnail como WebP em BytesIO
            import io
            webp_buffer = io.BytesIO()
            thumbnail.save(webp_buffer, format="WEBP", quality=85)
            webp_buffer.seek(0)

            # Upload para MinIO
            s3.upload_fileobj(
                webp_buffer,
                thumbnail_key,
                content_type="image/webp",
            )

            # Sucesso
            job.status = JobStatus.COMPLETED
            job.completed_at = utc_now()
            job.updated_at = job.completed_at
            job.result_data = {
                "file_id": file_id,
                "original_key": original_key,
                "thumbnail_key": thumbnail_key,
                "skipped": False,
            }
            job.error_message = None
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info(f"[THUMBNAIL] Thumbnail gerado com sucesso (job_id={job.id}, file_id={file_id}, thumbnail_key={thumbnail_key})")
            return {"ok": True, "job_id": job.id, "thumbnail_key": thumbnail_key}
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_msg = _safe_error_message(e)
            logger.error(f"[THUMBNAIL] Erro ao gerar thumbnail (job_id={job_id}, file_id={file_id if file_id else 'N/A'}): {error_msg}", exc_info=True)

            job.status = JobStatus.FAILED
            job.error_message = error_msg
            now = utc_now()
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            return {"ok": False, "error": job.error_message, "job_id": job.id}
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            import logging
            logger = logging.getLogger(__name__)
            if file_id:
                logger.info(f"[THUMBNAIL] Finalizando job (job_id={job_id}, file_id={file_id})")


async def reconcile_pending_orphans(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    Auto-fail de jobs órfãos/stale:
      - apenas `PENDING`
      - apenas quando `started_at IS NULL` (nunca virou RUNNING)
      - usa janela dinâmica (10x média últimos 10 COMPLETED do mesmo tipo), com teto 1h
    """
    now = utc_now()
    failed = 0
    scanned = 0

    with Session(engine) as session:
        pending = session.exec(
            select(Job).where(
                Job.status == JobStatus.PENDING,
                Job.started_at.is_(None),  # type: ignore[attr-defined]
            )
        ).all()

        window_cache: dict[tuple[int, JobType], timedelta] = {}
        for job in pending:
            scanned += 1
            key = (job.tenant_id, job.job_type)
            window = window_cache.get(key)
            if window is None:
                window = _stale_window_for(session, tenant_id=job.tenant_id, job_type=job.job_type)
                window_cache[key] = window

            if now - job.created_at <= window:
                continue

            job.status = JobStatus.FAILED
            job.error_message = (
                "orphan/stale: job permaneceu PENDING (started_at ausente) por tempo acima do esperado; "
                "requeue manual (admin)"
            )
            job.completed_at = now
            job.updated_at = now
            session.add(job)
            failed += 1

        if failed:
            session.commit()

    return {"ok": True, "scanned": scanned, "failed": failed}
