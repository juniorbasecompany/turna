from __future__ import annotations

import logging
import os
import tempfile
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.db.session import engine
from app.model.base import utc_now
from app.model.demand import Demand
from app.model.file import File
from app.model.job import Job, JobStatus, JobType
from app.model.schedule_version import ScheduleStatus, ScheduleVersion
from app.model.tenant import Tenant
from app.storage.client import S3Client

from demand.read import extract_demand
from strategy.greedy.solve import solve_greedy

logger = logging.getLogger(__name__)


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


def _demands_from_database(
    session: Session,
    *,
    tenant_id: int,
    period_start_at,
    period_end_at,
) -> tuple[list[dict], int]:
    """
    Lê demandas do banco de dados (tabela demand) e converte para o formato esperado pelos solvers:
      - day: 1..N
      - start/end: horas em float (ex.: 9.5 = 09:30)
      - is_pediatric: bool (default False)

    Filtra por tenant_id e período (start_time dentro do intervalo).
    Usa o timezone da clínica para calcular dias e horas relativas.
    """
    from datetime import datetime

    logger.debug(f"[_demands_from_database] Iniciando - tenant_id={tenant_id}, period_start_at={period_start_at}, period_end_at={period_end_at}")

    # Buscar timezone do tenant
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise RuntimeError(f"Tenant não encontrado (id={tenant_id})")

    tenant_tz = ZoneInfo(tenant.timezone)
    logger.debug(f"[_demands_from_database] Timezone do tenant: {tenant.timezone}")

    # Converter períodos para timezone da clínica para cálculo de datas
    period_start_local = period_start_at.astimezone(tenant_tz)
    period_end_local = period_end_at.astimezone(tenant_tz)
    logger.debug(f"[_demands_from_database] Período no timezone local: {period_start_local} até {period_end_local}")

    # Validar período usando datas no timezone da clínica
    start_date = period_start_local.date()
    end_date = period_end_local.date()
    days = (end_date - start_date).days
    logger.debug(f"[_demands_from_database] start_date={start_date}, end_date={end_date}, days={days}")
    
    if days <= 0:
        raise RuntimeError(f"Período inválido: period_end_at deve ser maior que period_start_at (days={days})")

    # Buscar demandas do banco no período
    # Filtra por tenant_id (segurança multi-tenant) e start_time dentro do intervalo
    # As datas de comparação já estão em UTC (timestamptz), então a comparação direta funciona
    query = (
        select(Demand)
        .where(
            Demand.tenant_id == tenant_id,
            Demand.start_time >= period_start_at,
            Demand.start_time < period_end_at,
        )
        .order_by(Demand.start_time)
    )
    demands_db = session.exec(query).all()

    if not demands_db:
        raise RuntimeError("Nenhuma demanda encontrada no período informado")

    out: list[dict] = []
    logger.debug(f"[_demands_from_database] Processando {len(demands_db)} demandas do banco")
    
    for i, d in enumerate(demands_db):
        # Converter para timezone da clínica para cálculos de dia e hora
        st_local = d.start_time.astimezone(tenant_tz)
        en_local = d.end_time.astimezone(tenant_tz)

        if en_local <= st_local:
            logger.warning(f"[_demands_from_database] Demanda {i} ignorada: end_time <= start_time")
            continue

        # Dia relativo ao period_start_at usando data no timezone da clínica
        day_idx = (st_local.date() - start_date).days + 1
        logger.debug(f"[_demands_from_database] Demanda {i}: day_idx={day_idx} (st_local.date()={st_local.date()}, start_date={start_date})")
        
        if day_idx is None:
            raise RuntimeError(f"day_idx é None para demanda {i} (st_local.date()={st_local.date()}, start_date={start_date})")
        
        if day_idx < 1 or day_idx > days:
            logger.warning(f"[_demands_from_database] Demanda {i} ignorada: day_idx={day_idx} fora do intervalo [1, {days}]")
            continue

        # Converter para horas float usando hora no timezone da clínica (ex.: 9.5 = 09:30)
        start_h = st_local.hour + (st_local.minute / 60.0) + (st_local.second / 3600.0)
        end_h = en_local.hour + (en_local.minute / 60.0) + (en_local.second / 3600.0)

        # ID da demanda: usar room se disponível, senão usar procedure ou índice
        did = str(d.room or d.procedure or f"D{i+1}")

        try:
            day_int = int(day_idx)
        except (ValueError, TypeError) as e:
            raise RuntimeError(
                f"Erro ao converter day_idx para int: day_idx={day_idx} (tipo: {type(day_idx)}), "
                f"st_local.date()={st_local.date()}, start_date={start_date}, days={days}. "
                f"Erro: {str(e)}"
            ) from e

        out.append(
            {
                "id": did,
                "day": day_int,
                "start": float(start_h),
                "end": float(end_h),
                "is_pediatric": bool(d.is_pediatric),
                "source": d.source,  # Preservar source original
            }
        )

    logger.info(f"[_demands_from_database] Retornando {len(out)} demandas processadas em {days} dias")
    return out, days


async def generate_schedule_job(ctx: dict[str, Any], job_id: int) -> dict[str, Any]:
    """
    Gera escala e grava em ScheduleVersion.result_data.

    Suporta dois modos:
    - "from_extract": Lê demandas de um Job de extração (EXTRACT_DEMAND) - modo original
    - "from_demands": Lê demandas diretamente da tabela demand - novo modo

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
            logger.info(f"[GENERATE_SCHEDULE] Iniciando job_id={job_id}, tenant_id={job.tenant_id}")
            input_data = job.input_data or {}
            logger.debug(f"[GENERATE_SCHEDULE] input_data keys: {list(input_data.keys()) if input_data else 'None'}")
            logger.debug(f"[GENERATE_SCHEDULE] input_data completo: {input_data}")
            
            # Validar e obter schedule_version_id com logs detalhados
            schedule_version_id_raw = input_data.get("schedule_version_id")
            logger.debug(f"[GENERATE_SCHEDULE] schedule_version_id_raw: {schedule_version_id_raw} (tipo: {type(schedule_version_id_raw)})")
            
            if schedule_version_id_raw is None:
                error_msg = (
                    f"schedule_version_id ausente no input_data. "
                    f"input_data keys: {list(input_data.keys()) if input_data else 'None'}, "
                    f"input_data completo: {input_data}"
                )
                logger.error(f"[GENERATE_SCHEDULE] {error_msg}")
                raise RuntimeError(error_msg)
            
            try:
                schedule_version_id = int(schedule_version_id_raw)
                logger.debug(f"[GENERATE_SCHEDULE] schedule_version_id convertido: {schedule_version_id}")
            except (ValueError, TypeError) as e:
                error_msg = (
                    f"schedule_version_id inválido: {schedule_version_id_raw} (tipo: {type(schedule_version_id_raw)}). "
                    f"Erro: {str(e)}"
                )
                logger.error(f"[GENERATE_SCHEDULE] {error_msg}")
                raise RuntimeError(error_msg) from e
            
            mode = str(input_data.get("mode") or "from_extract").strip().lower()
            allocation_mode = str(input_data.get("allocation_mode") or "greedy").strip().lower()
            logger.debug(f"[GENERATE_SCHEDULE] mode={mode}, allocation_mode={allocation_mode}")

            if allocation_mode != "greedy":
                raise RuntimeError("allocation_mode não suportado no MVP (apenas greedy)")

            sv = session.get(ScheduleVersion, schedule_version_id)
            if not sv:
                raise RuntimeError(f"ScheduleVersion não encontrado (id={schedule_version_id})")
            if sv.tenant_id != job.tenant_id:
                raise RuntimeError("Acesso negado (tenant mismatch)")

            # Profissionais: payload > fallback dev
            pros_by_sequence = input_data.get("pros_by_sequence")
            if pros_by_sequence is None:
                pros_by_sequence = _load_pros_from_repo_test()
            if not isinstance(pros_by_sequence, list) or not pros_by_sequence:
                raise RuntimeError("pros_by_sequence ausente/ inválido")

            # Carregar demandas conforme o modo
            if mode == "from_demands":
                logger.info(f"[GENERATE_SCHEDULE] Modo 'from_demands' - lendo demandas do banco")
                # Modo novo: ler do banco de dados
                from datetime import datetime

                # Obter período do input_data ou do ScheduleVersion
                period_start_at = input_data.get("period_start_at")
                period_end_at = input_data.get("period_end_at")
                logger.debug(f"[GENERATE_SCHEDULE] period_start_at do input_data: {period_start_at} (tipo: {type(period_start_at)})")
                logger.debug(f"[GENERATE_SCHEDULE] period_end_at do input_data: {period_end_at} (tipo: {type(period_end_at)})")

                if period_start_at:
                    if isinstance(period_start_at, str):
                        period_start_at = datetime.fromisoformat(period_start_at.replace("Z", "+00:00"))
                        logger.debug(f"[GENERATE_SCHEDULE] period_start_at convertido de string: {period_start_at}")
                else:
                    period_start_at = sv.period_start_at
                    logger.debug(f"[GENERATE_SCHEDULE] period_start_at do ScheduleVersion: {period_start_at}")

                if period_end_at:
                    if isinstance(period_end_at, str):
                        period_end_at = datetime.fromisoformat(period_end_at.replace("Z", "+00:00"))
                        logger.debug(f"[GENERATE_SCHEDULE] period_end_at convertido de string: {period_end_at}")
                else:
                    period_end_at = sv.period_end_at
                    logger.debug(f"[GENERATE_SCHEDULE] period_end_at do ScheduleVersion: {period_end_at}")

                logger.info(f"[GENERATE_SCHEDULE] Chamando _demands_from_database com período: {period_start_at} até {period_end_at}")
                demands, days = _demands_from_database(
                    session,
                    tenant_id=job.tenant_id,
                    period_start_at=period_start_at,
                    period_end_at=period_end_at,
                )
                logger.info(f"[GENERATE_SCHEDULE] Encontradas {len(demands)} demandas em {days} dias")
                extract_job_id = None
            else:
                # Modo original: ler de job de extração
                extract_job_id_raw = input_data.get("extract_job_id")
                if extract_job_id_raw is None:
                    error_msg = f"extract_job_id ausente no input_data para modo 'from_extract'"
                    logger.error(f"[GENERATE_SCHEDULE] {error_msg}")
                    raise RuntimeError(error_msg)
                try:
                    extract_job_id = int(extract_job_id_raw)
                    logger.debug(f"[GENERATE_SCHEDULE] extract_job_id: {extract_job_id}")
                except (ValueError, TypeError) as e:
                    error_msg = f"extract_job_id inválido: {extract_job_id_raw} (tipo: {type(extract_job_id_raw)}). Erro: {str(e)}"
                    logger.error(f"[GENERATE_SCHEDULE] {error_msg}")
                    raise RuntimeError(error_msg) from e

                extract_job = session.get(Job, extract_job_id)
                if not extract_job:
                    raise RuntimeError(f"Job de extração não encontrado (id={extract_job_id})")
                if extract_job.tenant_id != job.tenant_id:
                    raise RuntimeError("Acesso negado (tenant mismatch)")
                if extract_job.status != JobStatus.COMPLETED or not isinstance(extract_job.result_data, dict):
                    raise RuntimeError("Job de extração não está COMPLETED (ou result_data ausente)")

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

            result_data: dict[str, Any] = {
                "allocation_mode": "greedy",
                "days": days,
                "total_cost": total_cost,
                "per_day": per_day,
                "mode": mode,
            }
            if extract_job_id is not None:
                result_data["extract_job_id"] = extract_job_id

            sv.result_data = result_data
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

            input_data = job.input_data or {}
            file_id = int(input_data.get("file_id"))

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

                import pandas as pd
                import matplotlib
                matplotlib.use('Agg')  # Backend sem GUI
                import matplotlib.pyplot as plt
                import io

                # Ler primeira planilha (limitado a 50 linhas para performance)
                try:
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
                buf = io.BytesIO()
                fig.savefig(buf, format='png', bbox_inches='tight', dpi=100, pad_inches=0.1)
                buf.seek(0)
                image = Image.open(buf)
                plt.close(fig)
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
            return {"ok": True, "job_id": job.id, "thumbnail_key": thumbnail_key}
        except Exception as e:
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
