-- Migration: Security and Constraints
-- Description: Adds partial unique index for appointment slots to prevent double bookings.

-- Prevent double-booking for active appointments
CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_active_slot 
ON public.appointments(appointment_date, start_time) 
WHERE status IN ('booked', 'confirmed');

-- Ensure customer emails are unique if provided
CREATE UNIQUE INDEX IF NOT EXISTS idx_customers_email 
ON public.customers(email) 
WHERE email IS NOT NULL;
