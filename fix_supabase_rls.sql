-- =============================================================================
-- FIX SICUREZZA SUPABASE (gestionale-birra) — ZERO PERDITA DI DATI
-- Risolve:
--   1. rls_disabled_in_public ("Table publicly accessible")
--   2. sensitive_columns_exposed ("Sensitive data publicly accessible")
--
-- Questo script NON elimina né modifica alcun dato esistente.
-- Abilita il Row-Level Security (RLS) su tutte le tabelle dello schema public
-- e revoca i permessi alle API pubbliche di Supabase (ruoli anon e authenticated),
-- lasciando intatto l'accesso completo per il backend FastAPI (ruolo postgres).
-- =============================================================================

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        -- 1. Abilita Row-Level Security sulla tabella
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', r.tablename);

        -- 2. Revoca accesso tramite API REST pubblica (PostgREST)
        BEGIN
            EXECUTE format('REVOKE ALL ON TABLE public.%I FROM anon, authenticated;', r.tablename);
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;

        -- 3. Crea policy esplicita per il ruolo del backend (postgres / service_role)
        EXECUTE format('DROP POLICY IF EXISTS "backend_full_access" ON public.%I;', r.tablename);
        EXECUTE format(
            'CREATE POLICY "backend_full_access" ON public.%I FOR ALL TO CURRENT_USER USING (true) WITH CHECK (true);',
            r.tablename
        );
    END LOOP;
END $$;
