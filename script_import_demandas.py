#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para importar demandas do arquivo test/demandas.json para a tabela demand.

Uso:
    python script_import_demandas.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List

# Adiciona o diretório raiz ao path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from sqlmodel import Session, select
from app.db.session import engine, get_session
from app.model.demand import Demand
from app.model.tenant import Tenant
from app.model.hospital import Hospital


def get_or_create_tenant(session: Session) -> Tenant:
    """Obtém ou cria um tenant padrão."""
    # Tenta encontrar um tenant existente
    statement = select(Tenant)
    tenant = session.exec(statement).first()
    
    if not tenant:
        # Cria um tenant padrão se não existir
        tenant = Tenant(
            name="Tenant Padrão",
            slug="default",
            timezone="America/Sao_Paulo",
            locale="pt-BR",
            currency="BRL"
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        print(f"[OK] Tenant criado: {tenant.name} (ID: {tenant.id})")
    else:
        print(f"[OK] Tenant encontrado: {tenant.name} (ID: {tenant.id})")
    
    return tenant


def get_or_create_hospital(session: Session, tenant_id: int, hospital_key: str) -> Hospital:
    """Obtém ou cria um hospital baseado na chave do JSON."""
    # Tenta encontrar hospital existente com esse nome
    statement = select(Hospital).where(
        Hospital.tenant_id == tenant_id,
        Hospital.name == f"Hospital {hospital_key}"
    )
    hospital = session.exec(statement).first()
    
    if not hospital:
        # Cria um hospital se não existir
        hospital = Hospital(
            tenant_id=tenant_id,
            name=f"Hospital {hospital_key}",
            prompt=None,
            color=None
        )
        session.add(hospital)
        session.commit()
        session.refresh(hospital)
        print(f"  [OK] Hospital criado: {hospital.name} (ID: {hospital.id})")
    else:
        print(f"  [OK] Hospital encontrado: {hospital.name} (ID: {hospital.id})")
    
    return hospital


def convert_hour_to_datetime(hour: int, base_date: datetime) -> datetime:
    """Converte uma hora (0-23) para datetime usando a data base."""
    return base_date.replace(hour=hour, minute=0, second=0, microsecond=0)


def load_demandas_json(file_path: Path) -> Dict[str, List[Dict]]:
    """Carrega o arquivo JSON de demandas."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def clear_demand_table(session: Session):
    """Esvazia a tabela demand."""
    demands = session.exec(select(Demand)).all()
    deleted_count = len(demands)
    
    if deleted_count > 0:
        for demand in demands:
            session.delete(demand)
        session.commit()
        print(f"[OK] Tabela 'demand' esvaziada: {deleted_count} registros removidos")
    else:
        print("[OK] Tabela 'demand' ja esta vazia")


def import_demandas(session: Session, tenant: Tenant, demandas_data: Dict[str, List[Dict]], base_date: datetime):
    """Importa as demandas do JSON para o banco."""
    created_count = 0
    hospital_cache: Dict[str, Hospital] = {}
    
    # Itera sobre cada chave (hospital_id) no JSON
    for hospital_key, demandas_list in demandas_data.items():
        # Obtém ou cria o hospital
        if hospital_key not in hospital_cache:
            hospital = get_or_create_hospital(session, tenant.id, hospital_key)
            hospital_cache[hospital_key] = hospital
        else:
            hospital = hospital_cache[hospital_key]
        
        # Cria cada demanda
        for demanda_json in demandas_list:
            start_hour = demanda_json.get("start", 0)
            end_hour = demanda_json.get("end", 0)
            procedure_id = demanda_json.get("id", "")
            is_pediatric = demanda_json.get("is_pediatric", False)
            
            # Converte horas para datetime
            start_time = convert_hour_to_datetime(start_hour, base_date)
            end_time = convert_hour_to_datetime(end_hour, base_date)
            
            # Se end_time for menor que start_time, assume que é no dia seguinte
            if end_time <= start_time:
                end_time = end_time + timedelta(days=1)
            
            # Cria o registro de demanda
            demand = Demand(
                tenant_id=tenant.id,
                hospital_id=hospital.id,
                job_id=None,
                room=None,
                start_time=start_time,
                end_time=end_time,
                procedure=procedure_id,
                anesthesia_type=None,
                complexity=None,
                skills=None,
                priority=None,
                is_pediatric=is_pediatric,
                notes=None,
                source=demanda_json  # Guarda o JSON original
            )
            
            session.add(demand)
            created_count += 1
    
    # Commit em lote
    session.commit()
    print(f"[OK] {created_count} demandas criadas com sucesso")
    
    return created_count


def main():
    """Função principal."""
    print("=" * 60)
    print("Script de Importação de Demandas")
    print("=" * 60)
    
    # Caminho do arquivo JSON
    json_file = project_root / "test" / "demandas.json"
    
    if not json_file.exists():
        print(f"[ERRO] Arquivo nao encontrado: {json_file}")
        sys.exit(1)
    
    print(f"[OK] Arquivo encontrado: {json_file}")
    
    # Carrega o JSON
    try:
        demandas_data = load_demandas_json(json_file)
        print(f"[OK] JSON carregado: {len(demandas_data)} hospitais encontrados")
    except Exception as e:
        print(f"[ERRO] Erro ao carregar JSON: {e}")
        sys.exit(1)
    
    # Define data base (hoje)
    base_date = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0,
        tzinfo=timezone(timedelta(hours=-3))  # America/Sao_Paulo UTC-3
    )
    print(f"[OK] Data base: {base_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Conecta ao banco e executa importação
    with Session(engine) as session:
        try:
            # Obtém ou cria tenant
            tenant = get_or_create_tenant(session)
            
            # Esvazia a tabela demand
            clear_demand_table(session)
            
            # Importa as demandas
            created_count = import_demandas(session, tenant, demandas_data, base_date)
            
            print("=" * 60)
            print("[OK] Importacao concluida com sucesso!")
            print(f"  Total de demandas importadas: {created_count}")
            print("=" * 60)
            
        except Exception as e:
            session.rollback()
            print(f"[ERRO] Erro durante importacao: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
