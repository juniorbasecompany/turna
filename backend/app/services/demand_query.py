"""
Query compartilhada para Demand: única fonte de verdade para listagem e relatório.
List usa com limit/offset; relatório (build_demand_day_schedules) usa sem paginação.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select
from sqlalchemy import func

from app.model.demand import Demand


def get_demand_list_queries(
    session: Session,
    tenant_id: int,
    *,
    hospital_id: Optional[int] = None,
    job_id: Optional[int] = None,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    procedure: Optional[str] = None,
    is_pediatric: Optional[bool] = None,
    priority: Optional[str] = None,
):
    """
    Retorna (query, count_query) para Demand com os filtros aplicados.
    Mesmo canal de dados: list usa com .limit().offset(), relatório usa sem paginação.
    Validação (hospital/job existem, start_at <= end_at) fica a cargo do chamador.
    """
    query = select(Demand).where(Demand.tenant_id == tenant_id)
    count_query = select(func.count(Demand.id)).where(Demand.tenant_id == tenant_id)

    if hospital_id is not None:
        query = query.where(Demand.hospital_id == hospital_id)
        count_query = count_query.where(Demand.hospital_id == hospital_id)
    if job_id is not None:
        query = query.where(Demand.job_id == job_id)
        count_query = count_query.where(Demand.job_id == job_id)
    if start_at is not None:
        query = query.where(Demand.start_time >= start_at)
        count_query = count_query.where(Demand.start_time >= start_at)
    if end_at is not None:
        query = query.where(Demand.end_time <= end_at)
        count_query = count_query.where(Demand.end_time <= end_at)
    if procedure and procedure.strip():
        term = f"%{procedure.strip()}%"
        query = query.where(Demand.procedure.ilike(term))
        count_query = count_query.where(Demand.procedure.ilike(term))
    if is_pediatric is not None:
        query = query.where(Demand.is_pediatric == is_pediatric)
        count_query = count_query.where(Demand.is_pediatric == is_pediatric)
    if priority is not None:
        query = query.where(Demand.priority == priority)
        count_query = count_query.where(Demand.priority == priority)

    query = query.order_by(Demand.start_time.asc())
    return query, count_query
