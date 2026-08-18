from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from services.knowledge_service import search_knowledge

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])

@router.get("/search", response_model=list[dict[str, Any]])
async def search_knowledge_endpoint(
    q: str = Query(..., description="The search query text"),
    category: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(3, description="Limit number of results")
) -> list[dict[str, Any]]:
    """Search the knowledge base for relevant RUSBORN business facts.
    
    Returns concise title, category, and content strictly for active records.
    """
    try:
        results = search_knowledge(query=q, category=category, limit=limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
