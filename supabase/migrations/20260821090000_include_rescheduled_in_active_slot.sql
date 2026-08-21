-- Migration: Include 'rescheduled' in the active-slot unique index
-- Description:
--   The original partial unique index (idx_appointments_active_slot) only
--   guarded slots in status ('booked','confirmed'). A rescheduled appointment
--   keeps status = 'rescheduled' but still physically occupies its new
--   (appointment_date, start_time). Without 'rescheduled' in the predicate,
--   two appointments could be rescheduled/booked into the same slot without
--   the DB raising a unique-constraint violation.
--
--   A partial index predicate cannot be altered in place, so we drop and
--   recreate it. The application layer (appointment_service.check_availability)
--   is updated in the same change to include 'rescheduled' in its slot-occupancy
--   filters so both layers agree.

DROP INDEX IF EXISTS idx_appointments_active_slot;

CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_active_slot
ON public.appointments(appointment_date, start_time)
WHERE status IN ('booked', 'confirmed', 'rescheduled');
