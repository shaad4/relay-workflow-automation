"""Machine-readable authoring guidance generated from the live node validators."""

from copy import deepcopy

from app.contracts.ai_generate import AIGenerateOutput
from app.schemas.node_registry import NODE_VALIDATORS, TRIGGER_TYPES
from app.schemas.workflow_edge import WorkflowEdgeCreate

EXAMPLE_ID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
EXAMPLES = {
    "trigger.manual": {},
    "trigger.webhook": {},
    "trigger.schedule": {"schedule_type": "interval", "interval_minutes": 60, "timezone": "UTC"},
    "action.http_request": {
        "connection_id": EXAMPLE_ID,
        "url": "https://example.com/api/items",
        "method": "GET",
    },
    "action.email": {
        "connection_id": EXAMPLE_ID,
        "to": "{{trigger.data.email}}",
        "subject": "Your report",
        "body": "{{nodes.generate_1.content}}",
        "body_format": "plain",
    },
    "action.refund": {
        "connection_id": EXAMPLE_ID,
        "payment_id": "{{trigger.data.payment_id}}",
        "amount": "10.00",
    },
    "human.approval": {"approver_user_id": EXAMPLE_ID, "message": "Approve this request?"},
    "ai.rag_search": {
        "knowledge_base_id": EXAMPLE_ID,
        "query": "{{trigger.data.question}}",
        "top_k": 5,
    },
    "ai.decision": {
        "connection_id": EXAMPLE_ID,
        "model": "REPLACE_WITH_DISCOVERED_MODEL_ID",
        "instructions": "Classify the request.",
        "input_mappings": {"request": "{{trigger.data.request}}"},
        "allowed_decisions": ["APPROVE", "REJECT"],
    },
    "ai.generate": {
        "connection_id": EXAMPLE_ID,
        "model": "REPLACE_WITH_DISCOVERED_MODEL_ID",
        "prompt": "Write a report about {{trigger.data.research_topic}}.",
    },
    "logic.condition": {"value": "{{nodes.decision_1.decision}}"},
}


def object_schema(properties, **kwargs):
    return {"type": "object", "properties": properties, "additionalProperties": False, **kwargs}


# Only provider-independent output fields are closed. HTTP bodies and AI decision
# data intentionally remain open because their structure is supplied at runtime.
OUTPUT_SCHEMAS = {
    "ai.generate": AIGenerateOutput.model_json_schema(),
    "ai.decision": object_schema(
        {
            "decision": {"type": "string"},
            "reason": {"type": "string"},
            "data": {"type": "object", "additionalProperties": True},
            "model": {"type": "string"},
            "input_tokens": {"type": "integer"},
            "output_tokens": {"type": "integer"},
        }
    ),
    "ai.rag_search": object_schema(
        {
            "context": {"type": "string"},
            "chunks": {
                "type": "array",
                "items": object_schema(
                    {
                        "chunk_id": {"type": "string"},
                        "document_id": {"type": "string"},
                        "chunk_index": {"type": "integer"},
                        "content": {"type": "string"},
                        "score": {"type": "number"},
                    }
                ),
            },
        }
    ),
    "action.http_request": object_schema(
        {
            "status_code": {"type": "integer"},
            "body": {},
            "headers": {"type": "object", "additionalProperties": True},
            "success": {"type": "boolean"},
        },
        additionalProperties=True,  # Object body fields are also exposed as root aliases.
    ),
    "action.email": object_schema(
        {
            "message_id": {"type": "string"},
            "thread_id": {"type": "string"},
            "label_ids": {"type": "array", "items": {"type": "string"}},
            "success": {"type": "boolean"},
        }
    ),
    "action.refund": {"type": "object", "additionalProperties": True},
    "logic.condition": object_schema(
        {
            "value": {"type": "string"},
            "selected_branch": {"type": "string"},
            "next_node_id": {"type": "string"},
        }
    ),
    "human.approval": {"type": "null"},
    **{node_type: {"type": "null"} for node_type in TRIGGER_TYPES},
}

EXPRESSION_GUIDE = {
    "trigger_input": "{{trigger.data.research_topic}}",
    "node_output": "{{nodes.generate_1.content}}",
    "array_item": "{{nodes.http_1.body.items[0].name}}",
    "rules": [
        "Expressions are dot paths, not JavaScript or Python. No functions or operators.",
        "Trigger inputs always use trigger.data, regardless of the trigger node ID.",
        "Outputs are stored directly at nodes.<node_id>; there is no extra .output wrapper.",
        "Referenced nodes must execute before this node on every path reaching it.",
        "Whole-value expressions preserve types; embedded expressions become text.",
        "variables.<name> requires a value supplied in the execution context; no node currently sets variables.",
        "Trigger configuration is static; it is not resolved against its own future input.",
        "Use node IDs containing letters, digits, and underscores, starting with a letter or underscore, when referencing outputs.",
    ],
}


def get_node_catalog(node_type: str | None = None) -> dict:
    if node_type is not None and node_type not in NODE_VALIDATORS:
        raise ValueError("Unsupported node type")
    selected = [node_type] if node_type else list(NODE_VALIDATORS)
    nodes = []
    for name in selected:
        schema, _, label = NODE_VALIDATORS[name]
        nodes.append(
            {
                "node_type": name,
                "name": label,
                "configuration_schema": schema.model_json_schema(),
                "output_schema": OUTPUT_SCHEMAS[name],
                "example_configuration": EXAMPLES[name],
                "connection_kind": "ai"
                if name in {"ai.generate", "ai.decision"}
                else "app"
                if name.startswith("action.")
                else None,
                "notes": [
                    "Example IDs and model names are placeholders; replace them using discovery.",
                    "Runtime expressions may supply dynamic configuration values; validate the complete definition before creating or publishing it.",
                ]
                + (
                    [
                        "AI Generate has no provider, input_mappings, output_format, or output_schema configuration. Provider comes from the active AI connection."
                    ]
                    if name == "ai.generate"
                    else []
                ),
            }
        )
    return deepcopy(
        {
            "contract_version": 1,
            "nodes": nodes,
            "expressions": EXPRESSION_GUIDE,
            "edge_schema": WorkflowEdgeCreate.model_json_schema(),
            "branching": {
                "logic.condition": "Set edge.condition to the exact resolved value; it must have at least one branch.",
                "human.approval": "Use approved and/or rejected as edge.condition.",
                "other_nodes": "At most one outgoing edge; condition is not used for routing.",
            },
            "authoring_steps": [
                "Read the schema for each node type before constructing configurations.",
                "Discover app/AI connections; select by account/name and use an active AI connection.",
                "List models for the selected AI connection; choose a model supporting the requested generation task.",
                "Build one trigger and an acyclic connected graph using the documented expressions and outputs.",
                "Validate the definition, optionally with sample trigger input; correct all errors.",
                "Create a draft, validate the saved version, then publish only with user approval.",
            ],
        }
    )
