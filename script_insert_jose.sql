-- Script para inserir usuário jose e criar convite para o usuário atual
-- Execute este script no banco de dados PostgreSQL
--
-- Este script:
-- 1. Cria o account do jose (jose@empresa.com)
-- 2. Cria o tenant do jose
-- 3. Cria o membership ACTIVE do jose no tenant dele (como admin)
-- 4. Cria o membership PENDING do usuário atual no tenant do jose (convite)

DO $$
DECLARE
    current_account_id INTEGER;
    jose_account_id INTEGER;
    jose_tenant_id INTEGER;
    ts_now TIMESTAMP WITH TIME ZONE := NOW();
BEGIN
    -- Obter o account_id do usuário atual (primeiro account que não seja jose)
    -- Como você disse que há apenas um registro, este será o seu account
    SELECT id INTO current_account_id
    FROM account
    WHERE email != 'jose@empresa.com'
    ORDER BY id
    LIMIT 1;

    IF current_account_id IS NULL THEN
        RAISE EXCEPTION 'Não foi possível encontrar o account do usuário atual. Verifique se há registros na tabela account.';
    END IF;

    -- Inserir account do jose
    INSERT INTO account (email, name, role, auth_provider, created_at, updated_at)
    VALUES ('jose@empresa.com', 'jose', 'account', 'google', ts_now, ts_now)
    RETURNING id INTO jose_account_id;

    -- Inserir tenant do jose
    INSERT INTO tenant (name, slug, timezone, created_at, updated_at)
    VALUES ('Empresa do jose', 'empresa-jose', 'America/Sao_Paulo', ts_now, ts_now)
    RETURNING id INTO jose_tenant_id;

    -- Inserir membership ACTIVE do jose no tenant dele (como admin)
    INSERT INTO membership (tenant_id, account_id, role, status, created_at, updated_at)
    VALUES (jose_tenant_id, jose_account_id, 'admin', 'ACTIVE', ts_now, ts_now);

    -- Inserir membership PENDING do usuário atual no tenant do jose (convite)
    INSERT INTO membership (tenant_id, account_id, role, status, created_at, updated_at)
    VALUES (jose_tenant_id, current_account_id, 'account', 'PENDING', ts_now, ts_now);

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Usuário jose criado com sucesso!';
    RAISE NOTICE 'Account ID do jose: %', jose_account_id;
    RAISE NOTICE 'Tenant ID do jose: %', jose_tenant_id;
    RAISE NOTICE 'Account ID do usuário atual: %', current_account_id;
    RAISE NOTICE 'Convite PENDING criado para o usuário atual no tenant do jose';
    RAISE NOTICE '========================================';
END $$;
