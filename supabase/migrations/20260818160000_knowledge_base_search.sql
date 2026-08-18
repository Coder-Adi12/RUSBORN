-- 1. Create table if not exists
CREATE TABLE IF NOT EXISTS public.knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    keywords TEXT,
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Add columns if table already existed (with 'active' instead of 'is_active')
ALTER TABLE public.knowledge_base ADD COLUMN IF NOT EXISTS keywords TEXT;
ALTER TABLE public.knowledge_base ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE public.knowledge_base ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100;

-- 3. Add generated tsvector for full-text search
ALTER TABLE public.knowledge_base ADD COLUMN IF NOT EXISTS fts tsvector GENERATED ALWAYS AS (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '') || ' ' || coalesce(keywords, ''))) STORED;

-- 4. Create indexes
CREATE INDEX IF NOT EXISTS knowledge_base_fts_idx ON public.knowledge_base USING GIN (fts);
CREATE INDEX IF NOT EXISTS knowledge_base_category_idx ON public.knowledge_base (category);
CREATE INDEX IF NOT EXISTS knowledge_base_is_active_idx ON public.knowledge_base (is_active);

-- 5. Insert Seed Data
-- We don't have a unique constraint on title by default, but we don't want duplicates if the script runs twice.
-- The simplest way is to truncate if it's currently empty, or just insert.
-- Since it's currently empty (we checked), we'll just insert. 
-- In a real prod environment we'd use a robust upsert, but INSERT is fine for a fresh table.
INSERT INTO public.knowledge_base (category, title, content, keywords, priority)
VALUES 
('engineering_design', 'Engineering Design and Product Development', 'RUSBORN provides comprehensive engineering design services including mechanical design, product design, industrial design, CAD modeling, engineering drawings, technical documentation, prototyping, and design optimization.', 'engineering design, product development, mechanical design, CAD, prototyping', 100),
('cad_training', 'CAD/CAE Training', 'RUSBORN offers specialized training in SolidWorks, CATIA, AutoCAD, and ANSYS, focusing on CAD modeling, simulation, and engineering design practices.', 'SolidWorks, CATIA, AutoCAD, ANSYS, CAD modeling, simulation', 100),
('project_support', 'Research and Project Support', 'RUSBORN provides support for final-year projects and research including topic selection, project planning, analysis, technical development, paper development, journal selection, and publication guidance.', 'final-year projects, research support, publication guidance, paper development', 100),
('customized_training', 'Customized Technical Training', 'RUSBORN provides customized technical training for students, professionals, researchers, faculty, and organizations. Training covers relevant industry practices and topics related to ISO, BIS, ASME, API, and ASTM standards.', 'technical training, students, professionals, ISO, BIS, ASME', 100),
('pricing_policy', 'Pricing and Estimates', 'RUSBORN requires a detailed discussion to determine accurate pricing, duration, and schedules. We do not provide standard course fees, discounts, or guarantees without consulting the team.', 'price, cost, fees, discount, guarantee, duration', 10);
