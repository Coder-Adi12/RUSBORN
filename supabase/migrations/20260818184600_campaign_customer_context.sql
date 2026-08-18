-- Add customer_context to campaign_contacts table

ALTER TABLE campaign_contacts 
ADD COLUMN IF NOT EXISTS customer_context TEXT;

-- Update RLS policies to include the new column (not strictly necessary if policies are blanket for the table)
-- But ensuring no issues exist.
