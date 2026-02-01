from sqlmodel import Session, select
from app.model.hospital import Hospital


def create_default_hospital_for_tenant(session: Session, tenant_id: int) -> None:
    """
    Cria o hospital default para um tenant (idempotente).

    Garante que todo tenant tenha exatamente 1 hospital default chamado "Hospital".
    Se já existir, não cria duplicado.
    """
    # Verifica se já existe hospital default para este tenant
    existing = session.exec(
        select(Hospital).where(
            Hospital.tenant_id == tenant_id,
            Hospital.name == "Hospital",
        )
    ).first()

    if existing:
        return  # Já existe, não precisa criar

    default_prompt = """Extraia as demandas cirúrgicas do documento.
Regras:
- Responda APENAS JSON.
- O JSON DEVE conter as chaves: meta, demands.
- demands é uma lista de objetos com:
  - room (string ou null)
  - start_time (ISO datetime com timezone, ex: "2026-01-12T09:30:00-03:00")
  - end_time (ISO datetime com timezone, ex: "2026-01-12T12:00:00-03:00")
  - procedure (string)
  - anesthesia_type (string ou null)
  - skills (lista; se não houver, [])
  - priority ("Urgente" | "Emergência" | null)  # extrair de notes quando houver "Prioridade: ..."
  - complexity (string ou null)  # se existir como complexidade do caso (Baixa/Média/Alta)
  - members (lista; se não houver, [])
  - notes (string ou null)
- Não invente dados que não estejam no documento.
"""
    default_hospital = Hospital(
        tenant_id=tenant_id,
        name="Hospital",
        prompt=default_prompt,
    )
    session.add(default_hospital)
    session.commit()
