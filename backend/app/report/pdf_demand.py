"""
Geração de PDF de relatório de demandas: grade por hospital e horário (00:00–23:59), um dia por página.

Mesma fonte de dados do painel: usa get_demand_list_queries (start_at/end_at).
Cada demanda vira um quadrinho na linha, posicionado por start/end; cada dia em uma página.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.model.demand import Demand
from app.model.hospital import Hospital
from app.model.member import Member
from app.model.tenant import Tenant
from app.services.demand_query import get_demand_list_queries


def build_demand_day_schedules(
    session: Session,
    tenant_id: int,
    *,
    start_at: Optional[datetime] = None,
    end_at: Optional[datetime] = None,
    hospital_id: Optional[int] = None,
    procedure: Optional[str] = None,
    job_id: Optional[int] = None,
    is_pediatric: Optional[bool] = None,
    priority: Optional[str] = None,
) -> list:
    """
    Usa a mesma query do painel (get_demand_list_queries): start_time >= start_at, end_time <= end_at.
    Agrupa demandas por dia (timezone do tenant) e por hospital; retorna lista de DaySchedule
    para render_multi_day_pdf_bytes (cada demanda = um quadrinho na linha, posicionado por start/end).
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado")
    tz = ZoneInfo(tenant.timezone)

    query, _ = get_demand_list_queries(
        session,
        tenant_id,
        start_at=start_at,
        end_at=end_at,
        hospital_id=hospital_id,
        procedure=procedure,
        job_id=job_id,
        is_pediatric=is_pediatric,
        priority=priority,
    )
    demands = session.exec(query).all()
    return demands_to_day_schedules(demands, session, tenant_id, title_prefix="Demandas")


def demands_to_day_schedules(
    demands: list,
    session: Session,
    tenant_id: int,
    *,
    title_prefix: str = "Demandas",
    group_by: Literal["hospital", "member"] = "hospital",
) -> list:
    """
    Agrupa demandas por dia (dia = demand.start_time no timezone do tenant).
    - group_by="hospital": uma linha por hospital (relatório de demandas).
    - group_by="member": uma linha por member/profissional (relatório de escalas).
    Cada demanda vira um quadrinho na linha, posicionado por start_time/end_time.
    """
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado")
    tz = ZoneInfo(tenant.timezone)

    from output.day import (
        DaySchedule,
        Event,
        Interval,
        Row,
        _hex_to_rgb,
    )

    def _color_rgb_for_demand(d, title: str, hospital_color_by_id: dict) -> tuple[float, float, float] | None:
        """Cor do quadro: hospital.color se existir; se estiver sem cor, retorna None (quadro sem cor)."""
        hid = getattr(d, "hospital_id", None)
        if hid and hid in hospital_color_by_id and hospital_color_by_id[hid]:
            try:
                return _hex_to_rgb(hospital_color_by_id[hid])
            except (ValueError, TypeError):
                pass
        return None

    def _color_rgb_for_hospital_row(
        hid: int,
        hospital_dict: dict,
        hospital_color_by_id: dict,
        hex_to_rgb,
    ) -> tuple[float, float, float] | None:
        """Cor única da linha (relatório por hospital): hospital.color se existir; sem cor retorna None."""
        if hid in hospital_color_by_id and hospital_color_by_id[hid]:
            try:
                return hex_to_rgb(hospital_color_by_id[hid])
            except (ValueError, TypeError):
                pass
        return None

    if group_by == "member":
        # Relatório de escalas: agrupar por dia e member_id (uma linha por profissional)
        by_day_member: dict[tuple[str, Optional[int]], list] = defaultdict(list)
        for d in demands:
            if not d.start_time or not d.end_time:
                continue
            st_local = d.start_time.astimezone(tz)
            day_key = st_local.date().isoformat()
            mid = getattr(d, "member_id", None)
            by_day_member[(day_key, mid)].append(d)

        member_ids = {mid for (_, mid) in by_day_member if mid}
        member_dict: dict[int, str] = {}
        member_sequence: dict[int, int] = {}
        if member_ids:
            for m in session.exec(select(Member).where(Member.id.in_(member_ids))).all():
                member_dict[m.id] = (m.name or "").strip() or f"Member {m.id}"
                member_sequence[m.id] = getattr(m, "sequence", 0) or 0

        # Ordem rotacionada (como turna/solver): carregar todos members com sequence > 0
        pros_by_sequence: list[int] = []
        for m in session.exec(
            select(Member).where(Member.tenant_id == tenant_id, Member.sequence > 0).order_by(Member.sequence)
        ).all():
            pros_by_sequence.append(m.id)
        base_shift = 0

        hospital_ids_member = {d.hospital_id for d in demands if getattr(d, "hospital_id", None)}
        hospital_color_by_id: dict[int, Optional[str]] = {}
        if hospital_ids_member:
            for h in session.exec(select(Hospital).where(Hospital.id.in_(hospital_ids_member))).all():
                hospital_color_by_id[h.id] = h.color if getattr(h, "color", None) else None

        schedules = []
        days_sorted = sorted({day for (day, _) in by_day_member})
        n_pros = len(pros_by_sequence)
        for day_index, day_str in enumerate(days_sorted):
            day_date = date.fromisoformat(day_str)
            day_start_dt = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=tz)
            rows = []
            # Ordenar pela rotação do turna: dia N → start_idx = (base_shift + N) % n_pros
            start_idx = (base_shift + day_index) % n_pros if n_pros else 0
            rotated_order = pros_by_sequence[start_idx:] + pros_by_sequence[:start_idx]
            mid_to_rotated_pos = {mid: i for i, mid in enumerate(rotated_order)}
            members_this_day = sorted(
                {mid for (day, mid) in by_day_member if day == day_str},
                key=lambda x: (
                    x is None,
                    mid_to_rotated_pos.get(x, 999) if x is not None else 999,
                    member_dict.get(x, f"Member {x}") if x is not None else "Sem alocação",
                ),
            )
            for mid in members_this_day:
                demands_row = by_day_member.get((day_str, mid), [])
                events = []
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
                            color_rgb=_color_rgb_for_demand(d, title, hospital_color_by_id),
                        )
                    )
                events.sort(key=lambda e: (e.interval.start_min, e.interval.end_min))
                name = "Sem alocação" if mid is None else member_dict.get(mid, f"Member {mid}")
                rows.append(Row(name=name, events=events, vacations=[]))
            if not rows:
                continue
            try:
                d = date.fromisoformat(day_str)
                title = f"{title_prefix} - {d}"
            except Exception:
                title = f"{title_prefix} - {day_str}"
            schedules.append(
                DaySchedule(
                    title=title,
                    day_start_min=0,
                    day_end_min=24 * 60,
                    rows=rows,
                )
            )
        return schedules

    # Relatório de demandas: agrupar por dia e hospital (uma linha por hospital)
    by_day_hospital: dict[tuple[str, int], list] = defaultdict(list)
    for d in demands:
        if not d.start_time or not d.end_time:
            continue
        st_local = d.start_time.astimezone(tz)
        day_key = st_local.date().isoformat()
        hid = d.hospital_id or 0
        by_day_hospital[(day_key, hid)].append(d)

    hospital_ids = {hid for (_, hid) in by_day_hospital if hid}
    hospital_dict: dict[int, str] = {}
    hospital_color_by_id = {}
    if hospital_ids:
        for h in session.exec(select(Hospital).where(Hospital.id.in_(hospital_ids))).all():
            hospital_dict[h.id] = h.name or f"Hospital {h.id}"
            hospital_color_by_id[h.id] = h.color if getattr(h, "color", None) else None

    schedules = []
    days_sorted = sorted({day for (day, _) in by_day_hospital})
    for day_str in days_sorted:
        day_date = date.fromisoformat(day_str)
        day_start_dt = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0, tzinfo=tz)
        rows = []
        hospitals_this_day = sorted({hid for (day, hid) in by_day_hospital if day == day_str and hid})
        for hid in hospitals_this_day:
            demands_row = by_day_hospital.get((day_str, hid), [])
            # Uma linha = um hospital: todos os quadros da linha usam a mesma cor (hospital.color; sem cor = None)
            row_color_rgb = _color_rgb_for_hospital_row(hid, hospital_dict, hospital_color_by_id, _hex_to_rgb)
            events = []
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
                        color_rgb=row_color_rgb,
                    )
                )
            events.sort(key=lambda e: (e.interval.start_min, e.interval.end_min))
            name = hospital_dict.get(hid, f"Hospital {hid}")
            rows.append(Row(name=name, events=events, vacations=[]))
        if not rows:
            continue
        try:
            d = date.fromisoformat(day_str)
            title = f"{title_prefix} - {d}"
        except Exception:
            title = f"{title_prefix} - {day_str}"
        schedules.append(
            DaySchedule(
                title=title,
                day_start_min=0,
                day_end_min=24 * 60,
                rows=rows,
            )
        )
    return schedules
