-- Migration: 20260818170000_knowledge_base_rpc.sql
-- Description: Create a robust natural language search function for the knowledge base

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
BEGIN
  RETURN QUERY
  SELECT 
    kb.id, kb.title, kb.category, kb.content, kb.keywords, kb.access_level, kb.is_active, kb.priority
  FROM public.knowledge_base kb
  WHERE kb.is_active = true
    AND (category_filter IS NULL OR lower(kb.category) = lower(category_filter))
    AND (
      -- Primary search: websearch_to_tsquery allows natural query logic
      (search_query IS NOT NULL AND search_query <> '' AND kb.fts @@ websearch_to_tsquery('english', search_query))
      OR
      -- Fallback search: ILIKE on title for exact substring matches
      (search_query IS NOT NULL AND search_query <> '' AND kb.title ILIKE '%' || search_query || '%')
    )
  ORDER BY 
    -- Sort by ts_rank matching the search query, then fallback to priority
    ts_rank(kb.fts, websearch_to_tsquery('english', COALESCE(search_query, ''))) DESC,
    kb.priority DESC
  LIMIT max_limit;
END;
$$ LANGUAGE plpgsql;
