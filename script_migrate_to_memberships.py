import argparse
import sys
from pathlib import Path

from sqlmodel import Session, select

# Garante import do app/ a partir da raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import engine  # noqa: E402
from app.model.membership import Membership, MembershipRole, MembershipStatus  # noqa: E402
from app.model.user import Account  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra accounts existentes para memberships (idempotente).")
    parser.add_argument("--dry-run", action="store_true", help="Não grava alterações no banco")
    args = parser.parse_args()

    created = 0
    skipped = 0

    with Session(engine) as session:
        accounts = session.exec(select(Account)).all()
        for account in accounts:
            if account.tenant_id is None:
                skipped += 1
                continue

            existing = session.exec(
                select(Membership).where(
                    Membership.account_id == account.id,
                    Membership.tenant_id == account.tenant_id,
                )
            ).first()
            if existing:
                skipped += 1
                continue

            role = MembershipRole.ADMIN if account.role == "admin" else MembershipRole.USER
            membership = Membership(
                tenant_id=account.tenant_id,
                account_id=account.id,
                role=role,
                status=MembershipStatus.ACTIVE,
                created_at=account.created_at,
                updated_at=account.updated_at,
            )
            session.add(membership)
            created += 1

        if args.dry_run:
            session.rollback()
        else:
            session.commit()

    print(f"created={created} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

