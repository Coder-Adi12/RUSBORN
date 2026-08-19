-- Migration: Customer ID idempotency and constraints
-- Description: Adds a unique index to the customers table for the phone column to ensure safe concurrent upserts.

CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_phone 
ON public.customers(phone) 
WHERE phone IS NOT NULL;
