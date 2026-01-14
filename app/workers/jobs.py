from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.db.session import engine
from app.models.base import utc_now
from app.models.job import Job, JobStatus


async def ping_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Job fake para validar fila/worker.
    Atualiza status no banco e grava um payload simples em result_data.
    """
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            return {"ok": False, "error": "job_not_found", "job_id": job_id}

        job.status = JobStatus.RUNNING
        session.add(job)
        session.commit()

        try:
            job.result_data = {"pong": True}
            job.status = JobStatus.COMPLETED
            job.completed_at = utc_now()
            session.add(job)
            session.commit()
            session.refresh(job)
            return {"ok": True, "job_id": job.id}
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = utc_now()
            session.add(job)
            session.commit()
            return {"ok": False, "error": str(e), "job_id": job.id}

