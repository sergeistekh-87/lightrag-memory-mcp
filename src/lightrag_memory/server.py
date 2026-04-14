"""LightRAG Memory MCP Server — complete tool set (verified against source code)."""

import json
from mcp.server.fastmcp import FastMCP
from .client import get_client

mcp = FastMCP("LightRAG Memory")


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

    async with get_client(timeout=90) as c:
        r = await c.post("/query", json=payload)
        if r.status_code == 401:
            return "Error 401: invalid API key (check LIGHTRAG_API_KEY)"
        try:
            data = r.json()
            return data.get("response", str(data))
        except Exception:
            return r.text


@mcp.tool()
async def query_memory_with_citations(query: str, mode: str = "hybrid") -> str:
    """
    Search the knowledge graph — answer WITH source references.

    Args:
        query: Your question or search query
        mode: naive | local | global | hybrid (default) | mix
    """
    async with get_client(timeout=90) as c:
        r = await c.post(
            "/query",
            json={"query": query, "mode": mode, "include_references": True},
        )
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def query_context_only(query: str, mode: str = "hybrid") -> str:
    """
    Get raw context chunks WITHOUT LLM answer generation.
    Useful to inspect what's actually stored on a topic.

    Args:
        query: Topic or question
        mode: naive | local | global | hybrid (default) | mix
    """
    async with get_client(timeout=60) as c:
        r = await c.post(
            "/query",
            json={"query": query, "mode": mode, "only_need_context": True},
        )
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=60) as c:
        r = await c.post(
            "/query/data",
            json={"query": query, "mode": mode, "top_k": top_k},
        )
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=90) as c:
        r = await c.post(
            "/query",
            json={"query": query, "mode": mode, "conversation_history": history},
        )
        if r.status_code == 401:
            return "Error 401: invalid API key"
        try:
            return r.json().get("response", r.text)
        except Exception:
            return r.text


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

    async with get_client(timeout=120) as c:
        r = await c.post("/documents/text", json=payload)
        if r.status_code == 200:
            label = f" as '{file_source}'" if file_source else ""
            return f"✅ Saved to memory{label}"
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return f"Error {r.status_code}: {r.text}"


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

    async with get_client(timeout=300) as c:
        r = await c.post("/documents/texts", json=payload)
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def upload_file_to_memory(file_path: str) -> str:
    """
    Upload a file (PDF, TXT, MD, DOCX, PPTX, XLSX) into the memory graph.

    Args:
        file_path: Absolute path to the file on the local machine
    """
    import os
    if not os.path.exists(file_path):
        return f"Error: file not found at {file_path}"

    async with get_client(timeout=300) as c:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            r = await c.post("/documents/upload", files=files)
        if r.status_code == 200:
            return f"✅ File uploaded: {os.path.basename(file_path)}"
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return f"Error {r.status_code}: {r.text}"


@mcp.tool()
async def scan_input_folder() -> str:
    """
    Trigger scanning of the /inputs folder on the LightRAG server.
    Use to index files manually placed in the server's input directory.
    """
    async with get_client(timeout=30) as c:
        r = await c.post("/documents/scan")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


# ─── DOCUMENTS: VIEW & DELETE ────────────────────────────────────────────────

@mcp.tool()
async def list_memory_documents(page: int = 1, page_size: int = 20) -> str:
    """
    List documents in memory with their processing status (paginated).

    Args:
        page: Page number (default: 1)
        page_size: Results per page, max 100 (default: 20)
    """
    async with get_client(timeout=30) as c:
        r = await c.post(
            "/documents/paginated",
            json={"page": page, "page_size": min(page_size, 100)},
        )
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def get_document_status_counts() -> str:
    """
    Get a quick summary: how many documents are completed / failed / pending / processing.
    """
    async with get_client(timeout=15) as c:
        r = await c.get("/documents/status_counts")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def delete_memory_document(document_id: str) -> str:
    """
    Delete a specific document from memory by its ID.
    Get document IDs from list_memory_documents().

    Args:
        document_id: Document ID (e.g. doc-abc123...)
    """
    async with get_client(timeout=30) as c:
        r = await c.request(
            "DELETE",
            "/documents/delete_document",
            json={"doc_ids": [document_id]},
        )
        if r.status_code in (200, 204):
            return f"✅ Document {document_id} deleted"
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return f"Error {r.status_code}: {r.text}"


# ─── PIPELINE CONTROL ────────────────────────────────────────────────────────

@mcp.tool()
async def get_pipeline_status() -> str:
    """
    Check the current document processing pipeline status.
    """
    async with get_client(timeout=15) as c:
        r = await c.get("/documents/pipeline_status")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def reprocess_failed_documents() -> str:
    """
    Retry all documents that previously failed processing (e.g. due to 503/429 errors).
    Use this after Gemini API temporary outages or rate limit issues.
    """
    async with get_client(timeout=30) as c:
        r = await c.post("/documents/reprocess_failed")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        if r.status_code == 200:
            return f"✅ Reprocessing started: {r.text}"
        return f"Status {r.status_code}: {r.text}"


@mcp.tool()
async def cancel_pipeline() -> str:
    """
    Cancel the currently running document processing pipeline.
    Use this if processing is stuck or you need to stop a long-running batch.
    """
    async with get_client(timeout=15) as c:
        r = await c.post("/documents/cancel_pipeline")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        if r.status_code == 200:
            return "✅ Pipeline cancelled"
        return f"Status {r.status_code}: {r.text}"


@mcp.tool()
async def track_operation_status(track_id: str) -> str:
    """
    Track the status of a specific async operation by its track ID.

    Args:
        track_id: Operation tracking ID returned by insert/upload operations
    """
    async with get_client(timeout=15) as c:
        r = await c.get(f"/documents/track_status/{track_id}")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def clear_memory_cache() -> str:
    """
    Clear the LightRAG LLM response cache.
    Use this if you notice stale or outdated query responses.
    """
    async with get_client(timeout=15) as c:
        r = await c.post("/documents/clear_cache")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        if r.status_code in (200, 204):
            return "✅ Cache cleared"
        return f"Status {r.status_code}: {r.text}"


# ─── KNOWLEDGE GRAPH: VIEW ────────────────────────────────────────────────────

@mcp.tool()
async def get_graph_labels(limit: int = 50) -> str:
    """
    Get the most common entity types and relationship types in the graph.

    Args:
        limit: Max number of labels to return (default: 50)
    """
    async with get_client(timeout=30) as c:
        r = await c.get(f"/graph/label/popular?limit={limit}")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def search_graph_labels(query: str) -> str:
    """
    Search for entity types or relation types by name pattern.

    Args:
        query: Search term to match against label names
    """
    async with get_client(timeout=30) as c:
        r = await c.get(f"/graph/label/search?query={query}")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def get_graph_stats() -> str:
    """
    Get knowledge graph statistics: total node count and edge count.
    """
    async with get_client(timeout=30) as c:
        r = await c.get("/graphs?label=*&max_depth=1&max_nodes=5")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        try:
            data = r.json()
            nodes = len(data.get("nodes", []))
            edges = len(data.get("edges", []))
            return json.dumps({"node_count": nodes, "edge_count": edges}, ensure_ascii=False)
        except Exception:
            return r.text


@mcp.tool()
async def check_entity_exists(entity_name: str) -> str:
    """
    Check if a specific entity exists in the knowledge graph.

    Args:
        entity_name: The entity name to look up
    """
    async with get_client(timeout=15) as c:
        r = await c.get(f"/graph/entity/exists?entity_name={entity_name}")
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=30) as c:
        r = await c.post("/graph/entity/create", json={
            "entity_name": entity_name,
            "entity_data": {
                "entity_type": entity_type,
                "description": description,
            },
        })
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=30) as c:
        r = await c.post("/graph/entity/edit", json={
            "entity_name": entity_name,
            "updated_data": updated_data,
            "allow_rename": allow_rename,
            "allow_merge": allow_merge,
        })
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=60) as c:
        r = await c.post("/graph/entities/merge", json={
            "entities_to_change": entities_to_change,
            "entity_to_change_into": entity_to_change_into,
        })
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


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
    async with get_client(timeout=30) as c:
        r = await c.post("/graph/relation/create", json={
            "source_entity": source_entity,
            "target_entity": target_entity,
            "relation_data": {
                "description": description,
                "keywords": keywords,
                "weight": weight,
            },
        })
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return r.text


@mcp.tool()
async def delete_graph_entity(entity_name: str) -> str:
    """
    Delete an entity and all its relationships from the knowledge graph.

    Args:
        entity_name: Name of the entity to delete
    """
    async with get_client(timeout=30) as c:
        r = await c.request(
            "DELETE",
            "/documents/delete_entity",
            json={"entity_name": entity_name},
        )
        if r.status_code in (200, 204):
            return f"✅ Entity '{entity_name}' deleted"
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return f"Error {r.status_code}: {r.text}"


@mcp.tool()
async def delete_graph_relation(source_entity: str, target_entity: str) -> str:
    """
    Delete a specific relationship between two entities.

    Args:
        source_entity: Name of the source entity
        target_entity: Name of the target entity
    """
    async with get_client(timeout=30) as c:
        r = await c.request(
            "DELETE",
            "/documents/delete_relation",
            json={"source_entity": source_entity, "target_entity": target_entity},
        )
        if r.status_code in (200, 204):
            return f"✅ Relation deleted: {source_entity} → {target_entity}"
        if r.status_code == 401:
            return "Error 401: invalid API key"
        return f"Error {r.status_code}: {r.text}"


# ─── SYSTEM ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def check_memory_health() -> str:
    """
    Check if the LightRAG memory server is running and healthy.
    Returns server version, active models, and pipeline status.
    """
    async with get_client(timeout=10) as c:
        r = await c.get("/health")
        try:
            data = r.json()
            return json.dumps({
                "status": data.get("status"),
                "version": data.get("core_version"),
                "llm_model": data.get("configuration", {}).get("llm_model"),
                "embedding_model": data.get("configuration", {}).get("embedding_model"),
                "pipeline_busy": data.get("pipeline_busy"),
            }, ensure_ascii=False)
        except Exception:
            return r.text
