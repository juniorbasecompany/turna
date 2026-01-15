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
from app.storage.client import S3Client

from demand.read import extract_demand


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

            # Executa extração (retorna dict JSON-serializável)
            result = extract_demand(tmp_path)
            if isinstance(result, dict):
                meta = result.setdefault("meta", {})
                meta.pop("pdf_path", None)
                meta["file_id"] = file_id
                meta["filename"] = filename

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
