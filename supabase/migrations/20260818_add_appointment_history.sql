-- Add appointment history columns to track cancellation and rescheduling details
ALTER TABLE appointments
ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS cancellation_reason TEXT,
ADD COLUMN IF NOT EXISTS rescheduled_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS reschedule_reason TEXT,
ADD COLUMN IF NOT EXISTS previous_appointment_date DATE,
ADD COLUMN IF NOT EXISTS previous_start_time TIME WITHOUT TIME ZONE;
