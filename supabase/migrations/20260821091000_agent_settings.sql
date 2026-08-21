-- Migration: Agent Settings (editable appointment configuration)
-- Description:
--   Adds a singleton table holding the appointment-scheduling configuration
--   that was previously environment-only (APPOINTMENT_* env vars). This lets
--   the dashboard edit these values at runtime and have both the FastAPI
--   backend (availability/booking enforcement) and the LiveKit agent (spoken
--   awareness of business hours) read from a single shared source.
--
--   The table is a singleton: exactly one row with id = 1. The application
--   always reads/writes that row and falls back to the env-var defaults
--   (config.settings.appointment_*) if the row or a column is missing/invalid.

CREATE TABLE IF NOT EXISTS public.agent_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1,
    appointment_timezone TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    appointment_duration_minutes INTEGER NOT NULL DEFAULT 30,
    appointment_working_days TEXT NOT NULL DEFAULT '1,2,3,4,5',
    appointment_start_time TEXT NOT NULL DEFAULT '09:00',
    appointment_end_time TEXT NOT NULL DEFAULT '18:00',
    updated_at TIMESTAMPTZ DEFAULT now(),
    updated_by TEXT NULL,
    CONSTRAINT agent_settings_singleton CHECK (id = 1),
    CONSTRAINT agent_settings_duration_positive CHECK (appointment_duration_minutes BETWEEN 5 AND 480)
);

-- Seed the singleton row with defaults (no-op if it already exists).
INSERT INTO public.agent_settings (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;
