"""Script para verificar conexão com o banco de dados."""
import os
import sys

try:
    import psycopg2 as psycopg
    # psycopg2 usa connect() diretamente, não precisa de adaptação
except ImportError:
    try:
        import psycopg
    except ImportError:
        print("ERRO: psycopg ou psycopg2 nao instalado. Execute: pip install psycopg2-binary")
        sys.exit(1)

# Configuração do banco
# Usa 127.0.0.1 ao invés de localhost para evitar problemas com IPv6
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "turna")
DB_USER = os.getenv("DB_USER", "turna")
DB_PASSWORD = os.getenv("DB_PASSWORD", "turna")

print(f"Conectando ao banco: postgresql://{DB_USER}:***@{DB_HOST}:{DB_PORT}/{DB_NAME}")

try:
    # psycopg2 e psycopg3 têm APIs compatíveis para connect()
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    with conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print("OK: Conexao bem-sucedida!")
        print(f"   PostgreSQL: {version.split(',')[0]}")

        # Verifica se o banco 'turna' existe
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"   Banco atual: {db_name}")

        # Lista tabelas existentes
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]

        if tables:
            print(f"   Tabelas existentes: {', '.join(tables)}")
        else:
            print("   AVISO: Nenhuma tabela encontrada (execute 'alembic upgrade head')")

    conn.close()

except Exception as e:
    print(f"ERRO ao conectar: {e}")
    print("\nDica: Certifique-se de que:")
    print("  1. PostgreSQL está rodando: docker-compose ps")
    print("  2. O serviço 'postgres' está com status 'healthy'")
    sys.exit(1)
