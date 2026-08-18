CREATE TABLE IF NOT EXISTS public.email_deliveries (
    id uuid primary key default gen_random_uuid(),
    customer_id uuid references public.customers(id),
    call_id uuid references public.calls(id),
    appointment_id uuid references public.appointments(id),
    email_type text not null,
    recipient_email text not null,
    subject text not null,
    status text not null,
    provider text not null,
    attempt_count int not null default 1,
    last_error text,
    sent_at timestamptz,
    created_at timestamptz not null default now()
);

-- Idempotency constraints
CREATE UNIQUE INDEX idx_email_deliveries_customer_confirmation 
ON public.email_deliveries(appointment_id, email_type) 
WHERE email_type = 'customer_confirmation';

CREATE UNIQUE INDEX idx_email_deliveries_sales_summary 
ON public.email_deliveries(call_id, email_type) 
WHERE email_type = 'sales_summary';

-- Useful indexes
CREATE INDEX idx_email_deliveries_customer_id ON public.email_deliveries(customer_id);
CREATE INDEX idx_email_deliveries_status ON public.email_deliveries(status);
