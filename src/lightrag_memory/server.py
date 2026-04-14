"""LightRAG Memory MCP Server — 29 tools, verified against LightRAG source code."""

import json
from mcp.server.fastmcp import FastMCP
from .client import request, stream_request, LightRAGError

mcp = FastMCP("LightRAG Memory")


def _err(e: Exception) -> str:
    """Format any exception as a readable error string."""
    return f"❌ {type(e).__name__}: {e}"


# ─── QUERY ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def query_memory(
    query: str,
    mode: str = "hybrid",
    top_k: int = 60,
    response_type: str = "",
) -> str:
    """
    Search the knowledge graph and generate an answer.

    Args:
        query: Your question or search query
        mode: naive | local | global | hybrid (default) | mix | bypass
        top_k: Number of top items to retrieve (default 60)
        response_type: Output format hint e.g. "Multiple Paragraphs", "Single Sentence"
    """
    payload: dict = {"query": query, "mode": mode, "top_k": top_k}
    if response_type:
        payload["response_type"] = response_type
    try:
        data = await request("POST", "/query", json=payload, timeout=90)
        if isinstance(data, dict):
            return data.get("response", json.dumps(data, ensure_ascii=False))
        return str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def query_memory_with_citations(query: str, mode: str = "hybrid") -> str:
    """
    Search the knowledge graph — answer WITH source references.

    Args:
        query: Your question or search query
        mode: naive | local | global | hybrid (default) | mix
    """
    try:
        data = await request(
            "POST", "/query",
            json={"query": query, "mode": mode, "include_references": True},
            timeout=90,
        )
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def query_context_only(query: str, mode: str = "hybrid") -> str:
    """
    Get raw context chunks WITHOUT LLM answer generation.
    Useful to inspect what's actually stored on a topic.

    Args:
        query: Topic or question
        mode: naive | local | global | hybrid (default) | mix
    """
    try:
        data = await request(
            "POST", "/query",
            json={"query": query, "mode": mode, "only_need_context": True},
            timeout=60,
        )
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def query_raw_data(
    query: str,
    mode: str = "hybrid",
    top_k: int = 10,
) -> str:
    """
    Get structured RAG data WITHOUT LLM generation.
    Returns entities, relationships, chunks, and references as structured JSON.
    Perfect for debugging retrieval, data analysis, or custom processing.

    Args:
        query: Your query
        mode: naive | local | global | hybrid (default) | mix
        top_k: Number of results (default 10)
    """
    try:
        data = await request(
            "POST", "/query/data",
            json={"query": query, "mode": mode, "top_k": top_k},
            timeout=60,
        )
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def query_with_conversation(
    query: str,
    history: list[dict],
    mode: str = "hybrid",
) -> str:
    """
    Query memory with conversation history for multi-turn dialogue.

    Args:
        query: Current user message
        history: Previous messages as list of {"role": "user"|"assistant", "content": "..."}
        mode: naive | local | global | hybrid (default) | mix
    """
    try:
        data = await request(
            "POST", "/query",
            json={"query": query, "mode": mode, "conversation_history": history},
            timeout=90,
        )
        if isinstance(data, dict):
            return data.get("response", json.dumps(data, ensure_ascii=False))
        return str(data)
    except LightRAGError as e:
        return _err(e)


# ─── DOCUMENTS: INSERT ────────────────────────────────────────────────────────

@mcp.tool()
async def save_to_memory(text: str, file_source: str = "") -> str:
    """
    Save text or knowledge to the LightRAG memory graph.
    Use this for facts, decisions, project context, or any important info.

    Args:
        text: The text content to save
        file_source: Document label/name — e.g. "project-x-architecture" or "user-profile"
    """
    payload: dict = {"text": text}
    if file_source:
        payload["file_source"] = file_source
    try:
        await request("POST", "/documents/text", json=payload, timeout=120)
        label = f" as '{file_source}'" if file_source else ""
        return f"✅ Saved to memory{label}"
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def save_multiple_to_memory(
    texts: list[str],
    file_sources: list[str] | None = None,
) -> str:
    """
    Save multiple texts to memory in one batch operation.
    More efficient than calling save_to_memory multiple times.

    Args:
        texts: List of text strings to save
        file_sources: Optional list of labels (same length as texts)
                      e.g. ["doc-1", "doc-2"]
    """
    payload: dict = {"texts": texts}
    if file_sources:
        payload["file_sources"] = file_sources
    try:
        data = await request("POST", "/documents/texts", json=payload, timeout=300)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def upload_file_to_memory(file_path: str) -> str:
    """
    Upload a file (PDF, TXT, MD, DOCX, PPTX, XLSX) into the memory graph.

    Args:
        file_path: Absolute path to the file on the local machine
    """
    import os
    if not os.path.exists(file_path):
        return f"❌ File not found: {file_path}"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            data = await request("POST", "/documents/upload", files=files, timeout=300)
        return f"✅ File uploaded: {os.path.basename(file_path)}" + (
            f" (track_id: {data.get('track_id')})" if isinstance(data, dict) and data.get("track_id") else ""
        )
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def scan_input_folder() -> str:
    """
    Trigger scanning of the /inputs folder on the LightRAG server.
    Use to index files manually placed in the server's input directory.
    """
    try:
        data = await request("POST", "/documents/scan", timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


# ─── DOCUMENTS: VIEW & DELETE ────────────────────────────────────────────────

@mcp.tool()
async def list_memory_documents(
    page: int = 1,
    page_size: int = 20,
    status_filter: str = "",
    sort_field: str = "updated_at",
    sort_direction: str = "desc",
) -> str:
    """
    List documents in memory with their processing status (paginated).

    Args:
        page: Page number (default: 1)
        page_size: Results per page, min 10, max 200 (default: 20)
        status_filter: Filter by status: PENDING, PROCESSING, PROCESSED, FAILED (empty = all)
        sort_field: Sort by: created_at, updated_at (default), id, file_path
        sort_direction: asc or desc (default)
    """
    # API enforces min=10, max=200
    page_size = max(10, min(page_size, 200))
    payload: dict = {
        "page": page,
        "page_size": page_size,
        "sort_field": sort_field,
        "sort_direction": sort_direction,
    }
    if status_filter:
        payload["status_filter"] = status_filter.lower()
    try:
        data = await request("POST", "/documents/paginated", json=payload, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def get_document_status_counts() -> str:
    """
    Get a quick summary: how many documents are completed / failed / pending / processing.
    """
    try:
        data = await request("GET", "/documents/status_counts", timeout=15)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def delete_memory_document(
    document_id: str,
    delete_file: bool = False,
    delete_llm_cache: bool = False,
) -> str:
    """
    Delete a specific document from memory by its ID.
    Get document IDs from list_memory_documents().

    Args:
        document_id: Document ID (e.g. doc-abc123...)
        delete_file: Also delete the source file from the upload directory
        delete_llm_cache: Also delete cached LLM extraction results for this document
    """
    try:
        await request(
            "DELETE", "/documents/delete_document",
            json={
                "doc_ids": [document_id],
                "delete_file": delete_file,
                "delete_llm_cache": delete_llm_cache,
            },
            timeout=30,
        )
        return f"✅ Document {document_id} deleted"
    except LightRAGError as e:
        return _err(e)


# ─── PIPELINE CONTROL ────────────────────────────────────────────────────────

@mcp.tool()
async def get_pipeline_status() -> str:
    """
    Check the current document processing pipeline status.
    """
    try:
        data = await request("GET", "/documents/pipeline_status", timeout=15)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def reprocess_failed_documents() -> str:
    """
    Retry all documents that previously failed processing (e.g. due to 503/429 errors).
    Use this after Gemini API temporary outages or rate limit issues.
    """
    try:
        data = await request("POST", "/documents/reprocess_failed", timeout=30)
        return f"✅ Reprocessing started: {json.dumps(data, ensure_ascii=False)}"
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def cancel_pipeline() -> str:
    """
    Cancel the currently running document processing pipeline.
    Use this if processing is stuck or you need to stop a long-running batch.
    """
    try:
        await request("POST", "/documents/cancel_pipeline", timeout=15)
        return "✅ Pipeline cancelled"
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def track_operation_status(track_id: str) -> str:
    """
    Track the status of a specific async operation by its track ID.

    Args:
        track_id: Operation tracking ID returned by insert/upload operations
    """
    try:
        data = await request("GET", f"/documents/track_status/{track_id}", timeout=15)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def clear_memory_cache() -> str:
    """
    Clear the LightRAG LLM response cache.
    Use this if you notice stale or outdated query responses.
    Note: clears ALL cache (server does not support partial cache clearing).
    """
    try:
        # ClearCacheRequest is an empty model — server clears all cache regardless
        await request("POST", "/documents/clear_cache", json={}, timeout=15)
        return "✅ Cache cleared"
    except LightRAGError as e:
        return _err(e)


# ─── KNOWLEDGE GRAPH: VIEW ────────────────────────────────────────────────────

@mcp.tool()
async def get_graph_labels(limit: int = 50) -> str:
    """
    Get the most common entity types and relationship types in the graph.

    Args:
        limit: Max number of labels to return (default: 50)
    """
    try:
        data = await request("GET", f"/graph/label/popular?limit={limit}", timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def search_graph_labels(query: str) -> str:
    """
    Search for entity types or relation types by name pattern.

    Args:
        query: Search term to match against label names
    """
    try:
        # Verified: API uses ?q= (not ?query=)
        data = await request("GET", "/graph/label/search", params={"q": query}, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def get_graph_stats() -> str:
    """
    Get knowledge graph statistics: total node count and edge count.
    """
    try:
        data = await request("GET", "/graphs", params={"label": "*", "max_depth": 1, "max_nodes": 5}, timeout=30)
        if isinstance(data, dict):
            return json.dumps({
                "node_count": len(data.get("nodes", [])),
                "edge_count": len(data.get("edges", [])),
            }, ensure_ascii=False)
        return str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def check_entity_exists(entity_name: str) -> str:
    """
    Check if a specific entity exists in the knowledge graph.

    Args:
        entity_name: The entity name to look up
    """
    try:
        # Verified: LightRAG uses ?name= query parameter (not ?entity_name=)
        data = await request("GET", "/graph/entity/exists", params={"name": entity_name}, timeout=15)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


# ─── KNOWLEDGE GRAPH: EDIT ────────────────────────────────────────────────────

@mcp.tool()
async def create_graph_entity(
    entity_name: str,
    entity_type: str,
    description: str = "",
) -> str:
    """
    Manually create a new entity in the knowledge graph.

    Args:
        entity_name: Unique name for the entity (e.g. "PostgreSQL", "Sergei")
        entity_type: Category (e.g. "TECHNOLOGY", "PERSON", "PROJECT", "ORGANIZATION")
        description: Short description of the entity
    """
    try:
        data = await request("POST", "/graph/entity/create", json={
            "entity_name": entity_name,
            "entity_data": {"entity_type": entity_type, "description": description},
        }, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def edit_graph_entity(
    entity_name: str,
    updated_data: dict,
    allow_rename: bool = False,
    allow_merge: bool = False,
) -> str:
    """
    Edit an existing entity in the knowledge graph.

    Args:
        entity_name: Name of the entity to edit
        updated_data: Dict with fields to update, e.g. {"description": "...", "entity_type": "..."}
        allow_rename: Allow changing entity name (may affect relations)
        allow_merge: Allow merging with existing entity if rename conflicts
    """
    try:
        data = await request("POST", "/graph/entity/edit", json={
            "entity_name": entity_name,
            "updated_data": updated_data,
            "allow_rename": allow_rename,
            "allow_merge": allow_merge,
        }, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def merge_graph_entities(
    entities_to_change: list[str],
    entity_to_change_into: str,
) -> str:
    """
    Merge duplicate or misspelled entities into one canonical entity.
    All relationships from source entities are transferred to the target.

    Args:
        entities_to_change: List of entity names to merge FROM (will be deleted)
                            e.g. ["Sergei S.", "S. Stekh", "Сергей"]
        entity_to_change_into: Entity name to merge INTO (will be preserved)
                               e.g. "Sergei Stekh"
    """
    try:
        data = await request("POST", "/graph/entities/merge", json={
            "entities_to_change": entities_to_change,
            "entity_to_change_into": entity_to_change_into,
        }, timeout=60)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def create_graph_relation(
    source_entity: str,
    target_entity: str,
    description: str,
    keywords: str = "",
    weight: float = 1.0,
) -> str:
    """
    Manually create a relationship between two entities in the knowledge graph.

    Args:
        source_entity: Name of the source entity (must exist)
        target_entity: Name of the target entity (must exist)
        description: Description of the relationship
        keywords: Comma-separated keywords describing the relation
        weight: Relationship strength (default 1.0)
    """
    try:
        data = await request("POST", "/graph/relation/create", json={
            "source_entity": source_entity,
            "target_entity": target_entity,
            "relation_data": {"description": description, "keywords": keywords, "weight": weight},
        }, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def edit_graph_relation(
    source_id: str,
    target_id: str,
    updated_data: dict,
) -> str:
    """
    Edit an existing relationship between two entities.

    Args:
        source_id: Name/ID of the source entity
        target_id: Name/ID of the target entity
        updated_data: Dict with fields to update, e.g. {"description": "...", "weight": 0.8}
    """
    try:
        data = await request("POST", "/graph/relation/edit", json={
            "source_id": source_id,
            "target_id": target_id,
            "updated_data": updated_data,
        }, timeout=30)
        return json.dumps(data, ensure_ascii=False) if isinstance(data, dict) else str(data)
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def delete_graph_entity(entity_name: str) -> str:
    """
    Delete an entity and all its relationships from the knowledge graph.

    Args:
        entity_name: Name of the entity to delete
    """
    try:
        await request(
            "DELETE", "/documents/delete_entity",
            json={"entity_name": entity_name},
            timeout=30,
        )
        return f"✅ Entity '{entity_name}' deleted"
    except LightRAGError as e:
        return _err(e)


@mcp.tool()
async def delete_graph_relation(source_entity: str, target_entity: str) -> str:
    """
    Delete a specific relationship between two entities.

    Args:
        source_entity: Name of the source entity
        target_entity: Name of the target entity
    """
    try:
        await request(
            "DELETE", "/documents/delete_relation",
            json={"source_entity": source_entity, "target_entity": target_entity},
            timeout=30,
        )
        return f"✅ Relation deleted: {source_entity} → {target_entity}"
    except LightRAGError as e:
        return _err(e)


# ─── SYSTEM ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def check_memory_health() -> str:
    """
    Check if the LightRAG memory server is running and healthy.
    Returns server version, active models, and pipeline status.
    """
    try:
        data = await request("GET", "/health", timeout=10)
        if isinstance(data, dict):
            return json.dumps({
                "status": data.get("status"),
                "version": data.get("core_version"),
                "llm_model": data.get("configuration", {}).get("llm_model"),
                "embedding_model": data.get("configuration", {}).get("embedding_model"),
                "pipeline_busy": data.get("pipeline_busy"),
            }, ensure_ascii=False)
        return str(data)
    except LightRAGError as e:
        return _err(e)
