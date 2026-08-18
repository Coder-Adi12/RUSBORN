-- Migration: Campaign Management System
-- Description: Adds tables and columns for the new outbound campaign orchestrator.

-- 1. Create campaigns table
CREATE TABLE IF NOT EXISTS public.campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    objective TEXT,
    voice_agent_instructions TEXT,
    timezone TEXT NOT NULL,
    max_concurrent_calls INTEGER NOT NULL DEFAULT 1,
    max_attempts_per_customer INTEGER NOT NULL DEFAULT 1,
    retry_delay_minutes INTEGER NOT NULL DEFAULT 30,
    scheduled_start_at TIMESTAMPTZ NULL,
    started_at TIMESTAMPTZ NULL,
    paused_at TIMESTAMPTZ NULL,
    stopped_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Create campaign_contacts table
CREATE TABLE IF NOT EXISTS public.campaign_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    priority INTEGER DEFAULT 0,
    attempt_count INTEGER DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NULL,
    last_attempt_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    last_outcome TEXT NULL,
    last_error TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campaign_id, customer_id)
);

-- 3. Create campaign_call_attempts table
CREATE TABLE IF NOT EXISTS public.campaign_call_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
    campaign_contact_id UUID NOT NULL REFERENCES public.campaign_contacts(id) ON DELETE CASCADE,
    call_id UUID NULL REFERENCES public.calls(id) ON DELETE SET NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    outcome TEXT NULL,
    started_at TIMESTAMPTZ NULL,
    ended_at TIMESTAMPTZ NULL,
    error_message TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Create campaign_activity table
CREATE TABLE IF NOT EXISTS public.campaign_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES public.campaigns(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    message TEXT,
    campaign_contact_id UUID NULL REFERENCES public.campaign_contacts(id) ON DELETE CASCADE,
    campaign_call_attempt_id UUID NULL REFERENCES public.campaign_call_attempts(id) ON DELETE CASCADE,
    metadata JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 5. Modify calls table to add campaign_id
ALTER TABLE public.calls ADD COLUMN IF NOT EXISTS campaign_id UUID NULL REFERENCES public.campaigns(id) ON DELETE SET NULL;

-- 6. Modify customers table to add do_not_call
ALTER TABLE public.customers ADD COLUMN IF NOT EXISTS do_not_call BOOLEAN NOT NULL DEFAULT FALSE;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_calls_campaign_id ON public.calls(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_contacts_campaign_id ON public.campaign_contacts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_contacts_customer_id ON public.campaign_contacts(customer_id);
CREATE INDEX IF NOT EXISTS idx_campaign_contacts_status ON public.campaign_contacts(status);
CREATE INDEX IF NOT EXISTS idx_campaign_contacts_next_attempt_at ON public.campaign_contacts(next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_campaign_call_attempts_campaign_id ON public.campaign_call_attempts(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_call_attempts_call_id ON public.campaign_call_attempts(call_id);
CREATE INDEX IF NOT EXISTS idx_campaign_activity_campaign_id ON public.campaign_activity(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_activity_created_at ON public.campaign_activity(created_at);
