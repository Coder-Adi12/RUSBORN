-- Migration: 20260818170500_knowledge_base_rpc_fix.sql
CREATE OR REPLACE FUNCTION search_knowledge_v1(
    search_query text, 
    category_filter text DEFAULT NULL,
    max_limit int DEFAULT 4
)
RETURNS TABLE (
  id uuid,
  title text,
  category text,
  content text,
  keywords text,
  access_level text,
  is_active boolean,
  priority integer
) AS $$
DECLARE
  -- Replace spaces with ' OR ' for websearch_to_tsquery to match ANY word
  or_query text := replace(trim(search_query), ' ', ' OR ');
BEGIN
  RETURN QUERY
  SELECT 
    kb.id, kb.title, kb.category, kb.content, kb.keywords, kb.access_level, kb.is_active, kb.priority
  FROM public.knowledge_base kb
  WHERE kb.is_active = true
    AND (category_filter IS NULL OR lower(kb.category) = lower(category_filter))
    AND (
      -- Primary search: Match ANY word using OR
      (search_query IS NOT NULL AND search_query <> '' AND kb.fts @@ websearch_to_tsquery('english', or_query))
      OR
      -- Fallback search: ILIKE on title
      (search_query IS NOT NULL AND search_query <> '' AND kb.title ILIKE '%' || search_query || '%')
    )
  ORDER BY 
    ts_rank(kb.fts, websearch_to_tsquery('english', COALESCE(or_query, ''))) DESC,
    kb.priority DESC
  LIMIT max_limit;
END;
$$ LANGUAGE plpgsql;
