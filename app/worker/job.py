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
