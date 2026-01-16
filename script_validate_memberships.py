import sys
from pathlib import Path

import sqlalchemy as sa
from sqlmodel import Session, select

# Garante import do app/ a partir da raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.session import engine  # noqa: E402
from app.model.membership import Membership, MembershipStatus  # noqa: E402
from app.model.user import Account  # noqa: E402


def main() -> int:
    problems = 0
    with Session(engine) as session:
        # 1) Accounts sem membership
        accounts = session.exec(select(Account)).all()
        for a in accounts:
            count = session.exec(
                select(sa.func.count(Membership.id)).where(Membership.account_id == a.id)
            ).one()
            if int(count) <= 0:
                problems += 1
                print(f"[ERROR] account_id={a.id} email={a.email} sem memberships")

        # 2) Duplicatas (tenant_id, account_id)
        dup_rows = session.exec(
            sa.text(
                """
                SELECT tenant_id, account_id, COUNT(*) AS c
                FROM membership
                GROUP BY tenant_id, account_id
                HAVING COUNT(*) > 1
                """
            )
        ).all()
        for tenant_id, account_id, c in dup_rows:
            problems += 1
            print(f"[ERROR] duplicata membership tenant_id={tenant_id} account_id={account_id} count={c}")

        # 3) ACTIVE por account (sanity)
        active_rows = session.exec(
            select(Membership.account_id, sa.func.count(Membership.id))
            .where(Membership.status == MembershipStatus.ACTIVE)
            .group_by(Membership.account_id)
        ).all()
        for account_id, c in active_rows:
            if int(c) <= 0:
                continue

    if problems:
        print(f"problems={problems}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

