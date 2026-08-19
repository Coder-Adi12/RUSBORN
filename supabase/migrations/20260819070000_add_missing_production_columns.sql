-- Migration: Add missing production-critical columns
-- Description: Adds do_not_call flag to customers and campaign_id to calls.
-- These columns are referenced in application code but were missing from schema.

-- 1. Add do_not_call column to customers (DNC compliance)
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS do_not_call BOOLEAN NOT NULL DEFAULT FALSE;

-- 2. Add campaign_id column to calls (campaign tracking)
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS campaign_id UUID REFERENCES public.campaigns(id);

-- 3. Index for DNC lookups during campaign validation
CREATE INDEX IF NOT EXISTS idx_customers_do_not_call ON public.customers(do_not_call) WHERE do_not_call = TRUE;

-- 4. Index for campaign call lookups
CREATE INDEX IF NOT EXISTS idx_calls_campaign_id ON public.calls(campaign_id) WHERE campaign_id IS NOT NULL;
