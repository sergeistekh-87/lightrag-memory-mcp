# lightrag-memory-mcp

MCP server for [LightRAG](https://github.com/HKUDS/LightRAG) — connects AI agents (Claude, Cursor, Windsurf, n8n) to a shared long-term memory graph.

Built from a complete analysis of the LightRAG REST API (`/openapi.json`) and verified against the source code.

## Tools (27)

### Query (5)

### Query (5)
| Tool | Description |
|------|-------------|
| `query_memory(query, mode, top_k, response_type)` | Search + generate answer |
| `query_memory_with_citations(query, mode)` | Answer + source references |
| `query_context_only(query, mode)` | Raw context chunks, no LLM generation |
| `query_raw_data(query, mode, top_k)` | Structured JSON data — entities, relations, chunks (no LLM) |
| `query_with_conversation(query, history, mode)` | Multi-turn dialogue with conversation history |

### Documents — Insert (4)
| Tool | Description |
|------|-------------|
| `save_to_memory(text, description)` | Save text with optional label |
| `save_multiple_to_memory(texts)` | Batch insert list of texts |
| `upload_file_to_memory(file_path)` | Upload PDF/TXT/MD/DOCX |
| `scan_input_folder()` | Index files from server /inputs dir |

### Documents — View & Delete (3)
| Tool | Description |
|------|-------------|
| `list_memory_documents(page, page_size)` | Paginated document list |
| `get_document_status_counts()` | Quick summary: completed/failed/pending |
| `delete_memory_document(document_id)` | Delete by ID |

### Pipeline Control (5)
| Tool | Description |
|------|-------------|
| `get_pipeline_status()` | Current processing queue status |
| `reprocess_failed_documents()` | 🔥 Retry all failed documents (use after 503 errors) |
| `cancel_pipeline()` | Stop current processing |
| `track_operation_status(track_id)` | Track specific async operation |
| `clear_memory_cache()` | Clear LLM response cache |

### Knowledge Graph — View (4)
| Tool | Description |
|------|-------------|
| `get_graph_labels(limit)` | Most common entity/relation types |
| `search_graph_labels(query)` | Search labels by pattern |
| `get_graph_stats()` | Node and edge counts |
| `check_entity_exists(entity_name)` | Check if entity is in graph |

### Knowledge Graph — Edit (5)
| Tool | Description |
|------|-------------|
| `create_graph_entity(entity_name, entity_type, description)` | Manually add entity |
| `edit_graph_entity(entity_name, updated_data, allow_rename, allow_merge)` | Modify existing entity |
| `merge_graph_entities(entities_to_change, entity_to_change_into)` | Merge duplicate entities |
| `create_graph_relation(source, target, description, keywords, weight)` | Add relation between entities |
| `delete_graph_entity(entity_name)` | Remove entity + all its relations |
| `delete_graph_relation(source_entity, target_entity)` | Remove specific relation |

### System (1)
| Tool | Description |
|------|-------------|
| `check_memory_health()` | Server status + model info |

## Query Modes

| Mode | Best for |
|------|---------|
| `hybrid` | Most queries — default |
| `local` | Specific facts about entities |
| `global` | High-level summaries |
| `naive` | Simple keyword search |
| `mix` | LightRAG chooses automatically |

## Setup

### 1. Prerequisites
- LightRAG server running (see `../install.md`)
- `uv` installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 2. Configure

```bash
git clone https://github.com/YOUR_USERNAME/lightrag-memory-mcp.git
cd lightrag-memory-mcp
cp .env.example .env
# Edit .env: set LIGHTRAG_BASE_URL and LIGHTRAG_API_KEY
```

### 3. Run

```bash
uv run -m lightrag_memory
```

### 4. MCP config (Claude Desktop / Cursor / Windsurf)

```json
{
  "mcpServers": {
    "lightrag": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/lightrag-memory-mcp", "-m", "lightrag_memory"],
      "env": {
        "LIGHTRAG_BASE_URL": "http://localhost:9621",
        "LIGHTRAG_API_KEY": "your-key-here"
      }
    }
  }
}
```

## System Prompt for Agents

See `../agent.md` for the ready-to-use system prompt block.

## License

MIT
