"""
Modulo SaaS (Fase 1): multi-tenancy, piani di abbonamento, paywall, Stripe Billing, PWA.

Integrazione NON distruttiva: il core (ricette, cotte, BeerXML, magazzino) non viene modificato.
L'isolamento dei dati per birrificio (tenant) avviene a livello ORM tramite eventi SQLAlchemy
che aggiungono automaticamente il filtro `tenant_id` a ogni query e lo valorizzano su ogni insert.
"""
