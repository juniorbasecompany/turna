"""
Geração de PDF de relatório de demandas: grade por hospital e horário (00:00–23:59), um dia por página.

Constrói DaySchedule a partir de Demand (por dia, por hospital) e usa render_multi_day_pdf_bytes.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.model.demand import Demand
from app.model.hospital import Hospital
from app.model.tenant import Tenant


def build_demand_day_schedules(
    session: Session,
    tenant_id: int,
    start_time_from: datetime | None = None,
    start_time_to: datetime | None = None,
    hospital_id: int | None = None,
) -> list:
    """
    Agrupa demandas por dia (timezone do tenant) e por hospital; retorna lista de DaySchedule
    para render_multi_day_pdf_bytes (formato output.day).
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado")
    tz = ZoneInfo(tenant.timezone)

    query = select(Demand).where(Demand.tenant_id == tenant_id)
    if start_time_from is not None:
        query = query.where(Demand.start_time >= start_time_from)
    if start_time_to is not None:
        query = query.where(Demand.start_time <= start_time_to)
    if hospital_id is not None:
        query = query.where(Demand.hospital_id == hospital_id)
    query = query.order_by(Demand.start_time)
    demands = session.exec(query).all()

    # Agrupar por (data local, hospital_id)
    by_day_hospital: dict[tuple[str, int], list[Demand]] = defaultdict(list)
    for d in demands:
        if not d.start_time or not d.end_time:
            continue
        st_local = d.start_time.astimezone(tz)
        day_key = st_local.date().isoformat()
        hid = d.hospital_id or 0
        by_day_hospital[(day_key, hid)].append(d)

    hospital_ids = {hid for (_, hid) in by_day_hospital if hid}
    hospital_dict = {}
    if hospital_ids:
        for h in session.exec(select(Hospital).where(Hospital.id.in_(hospital_ids))).all():
            hospital_dict[h.id] = h.name

    from output.day import (
        DaySchedule,
        Event,
        Interval,
        Row,
        _pick_color_from_text,
    )

    schedules: list[DaySchedule] = []
    days_sorted = sorted({day for (day, _) in by_day_hospital})

    for day_str in days_sorted:
        # Meia-noite do dia no timezone do tenant (uma vez por dia)
        day_date = date.fromisoformat(day_str)
        day_start_dt = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=tz)
        rows: list[Row] = []
        hospitals_this_day = sorted({hid for (day, hid) in by_day_hospital if day == day_str and hid})
        for hid in hospitals_this_day:
            demands_row = by_day_hospital.get((day_str, hid), [])
            events: list[Event] = []
            for d in demands_row:
                st_local = d.start_time.astimezone(tz)
                en_local = d.end_time.astimezone(tz)
                start_min = int((st_local - day_start_dt).total_seconds() // 60)
                end_min = int((en_local - day_start_dt).total_seconds() // 60)
                start_min = max(0, min(24 * 60, start_min))
                end_min = max(0, min(24 * 60, end_min))
                if end_min <= start_min:
                    continue
                title = (d.procedure or "").strip() or "?"
                if d.is_pediatric:
                    title += " (PED)"
                events.append(
                    Event(
                        interval=Interval(start_min, end_min),
                        title=title,
                        subtitle=d.room.strip() if d.room else None,
                        color_rgb=_pick_color_from_text(title),
                    )
                )
            events.sort(key=lambda e: (e.interval.start_min, e.interval.end_min))
            name = hospital_dict.get(hid, f"Hospital {hid}")
            rows.append(Row(name=name, events=events, vacations=[]))

        if not rows:
            continue
        day_start_min = 0
        day_end_min = 24 * 60
        try:
            d = date.fromisoformat(day_str)
            title = f"Demandas - {d}"
        except Exception:
            title = f"Demandas - {day_str}"
        schedules.append(
            DaySchedule(
                title=title,
                day_start_min=day_start_min,
                day_end_min=day_end_min,
                rows=rows,
            )
        )

    return schedules
