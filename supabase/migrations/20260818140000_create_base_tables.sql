-- Migration: Create Base Tables
-- Description: Creates the core tables that were previously created manually via the dashboard, ensuring a fresh local/remote DB can run cleanly.

CREATE TABLE IF NOT EXISTS public.customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    phone TEXT,
    email TEXT,
    company TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES public.customers(id),
    direction TEXT NOT NULL,
    livekit_room_id TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    transcript TEXT,
    summary TEXT,
    outcome TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES public.customers(id),
    call_id UUID REFERENCES public.calls(id),
    appointment_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    timezone TEXT NOT NULL,
    status TEXT NOT NULL,
    meeting_details TEXT,
    cancelled_at TIMESTAMPTZ,
    rescheduled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    reschedule_reason TEXT,
    previous_appointment_date TEXT,
    previous_start_time TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    access_level TEXT NOT NULL DEFAULT 'PUBLIC',
    source_document TEXT,
    source_page TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 100,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
