from app.models import WorkflowEdge, WorkflowNode
from app.schemas.node_registry import NODE_VALIDATORS as NODE_VALIDATORS
from app.schemas.node_registry import TRIGGER_TYPES
from app.services.expression_validation import validate_expression_references
from pydantic import ValidationError


def validate_node_configurations(nodes: list[WorkflowNode]) -> list[dict]:
    errors = []
    for node in nodes:
        validator = NODE_VALIDATORS.get(node.node_type)
        if validator is None:
            errors.append(
                {
                    "code": "UNSUPPORTED_NODE_TYPE",
                    "node_id": node.node_id,
                    "message": (f"Node '{node.node_id}' uses unsupported type '{node.node_type}'."),
                }
            )
            continue

        schema, code, label = validator
        try:
            # None is a legacy empty configuration; other non-objects are invalid.
            configuration = {} if node.configuration is None else node.configuration
            schema.model_validate(configuration)
        except ValidationError as exc:
            for error in exc.errors():
                field = ".".join(str(part) for part in error["loc"]) or "configuration"
                errors.append(
                    {
                        "code": code,
                        "node_id": node.node_id,
                        "field": field,
                        "message": f"{label} node '{node.node_id}': {field} - {error['msg']}",
                        "suggestion": "Read the node's configuration_schema and correct this field.",
                    }
                )
    return errors


def validate_node_ids(nodes: list[WorkflowNode], errors: list[dict]) -> set[str]:
    node_ids = {node.node_id for node in nodes}

    if not nodes:
        errors.append(
            {
                "code": "NO_NODES",
                "message": "Workflow must contain at least one node.",
            }
        )

    if len(node_ids) != len(nodes):
        errors.append(
            {
                "code": "DUPLICATE_NODE_ID",
                "message": "Workflow contains duplicate node IDs.",
            }
        )
    return node_ids


def validate_triggers(nodes: list[WorkflowNode], errors: list[dict]) -> list[WorkflowNode]:
    triggers = [node for node in nodes if node.node_type in TRIGGER_TYPES]

    if len(triggers) != 1:
        errors.append(
            {
                "code": "INVALID_TRIGGER",
                "message": ("Workflow must have exactly one supported trigger."),
            }
        )
    return triggers


def validate_edges(
    edges: list[WorkflowEdge],
    node_ids: set[str],
    errors: list[dict],
) -> tuple[dict[str, list[WorkflowEdge]], dict[str, int]]:
    for edge in edges:
        if edge.source_node_id not in node_ids:
            errors.append(
                {
                    "code": "INVALID_EDGE_SOURCE",
                    "message": (f"Edge references missing source node '{edge.source_node_id}'."),
                }
            )

        if edge.target_node_id not in node_ids:
            errors.append(
                {
                    "code": "INVALID_EDGE_TARGET",
                    "message": (f"Edge references missing target node '{edge.target_node_id}'."),
                }
            )

    outgoing = {node_id: [] for node_id in node_ids}

    indegree = {node_id: 0 for node_id in node_ids}

    for edge in edges:
        if edge.source_node_id in node_ids and edge.target_node_id in node_ids:
            outgoing[edge.source_node_id].append(edge)
            indegree[edge.target_node_id] += 1
    return outgoing, indegree


def validate_branching(
    nodes: list[WorkflowNode],
    outgoing: dict[str, list[WorkflowEdge]],
    errors: list[dict],
) -> None:
    for node in nodes:
        branches = outgoing[node.node_id]

        if node.node_type == "human.approval":
            conditions = [edge.condition for edge in branches]

            invalid = any(value not in {"approved", "rejected"} for value in conditions) or len(
                set(conditions)
            ) != len(conditions)

        elif node.node_type == "logic.condition":
            conditions = [edge.condition for edge in branches]

            invalid = (
                len(branches) == 0
                or any(
                    not isinstance(value, str) or not value.strip() or value != value.strip()
                    for value in conditions
                )
                or len(set(conditions)) != len(conditions)
            )

        else:
            invalid = len(branches) > 1

        if invalid:
            errors.append(
                {
                    "code": "INVALID_BRANCHING",
                    "node_id": node.node_id,
                    "message": (
                        f"Node '{node.node_id}' has invalid or ambiguous outgoing branches."
                    ),
                }
            )


def validate_cycles(
    outgoing: dict[str, list[WorkflowEdge]],
    indegree: dict[str, int],
    errors: list[dict],
) -> None:
    """Detect cycles using Kahn's algorithm without mutating the caller's graph."""
    indegree = indegree.copy()
    pending = [node_id for node_id, count in indegree.items() if count == 0]

    visited = set()

    while pending:
        node_id = pending.pop()

        visited.add(node_id)

        for edge in outgoing[node_id]:
            indegree[edge.target_node_id] -= 1

            if indegree[edge.target_node_id] == 0:
                pending.append(edge.target_node_id)

    if len(visited) != len(outgoing):
        errors.append(
            {
                "code": "WORKFLOW_CYCLE",
                "message": "Workflow must not contain cycles.",
            }
        )


def validate_reachability(
    triggers: list[WorkflowNode],
    outgoing: dict[str, list[WorkflowEdge]],
    node_ids: set[str],
    errors: list[dict],
) -> None:
    if len(triggers) == 1:
        reachable = set()
        pending = [triggers[0].node_id]

        while pending:
            node_id = pending.pop()

            if node_id in reachable:
                continue

            reachable.add(node_id)

            pending.extend(edge.target_node_id for edge in outgoing[node_id])

        if reachable != node_ids:
            errors.append(
                {
                    "code": "DISCONNECTED_NODES",
                    "message": ("Every node must be reachable from the trigger."),
                }
            )


def validate_definition(nodes, edges, sample_input=None):
    """Shared by draft preflight, saved-version validation, and publication."""
    errors = []
    node_ids = validate_node_ids(nodes, errors)
    errors.extend(validate_node_configurations(nodes))
    triggers = validate_triggers(nodes, errors)
    outgoing, indegree = validate_edges(edges, node_ids, errors)
    validate_branching(nodes, outgoing, errors)
    validate_cycles(outgoing, indegree, errors)
    validate_reachability(triggers, outgoing, node_ids, errors)
    if not any(error["code"] in {"WORKFLOW_CYCLE", "DUPLICATE_NODE_ID"} for error in errors):
        errors.extend(validate_expression_references(nodes, edges, sample_input))
    return {"valid": not errors, "errors": errors, "warnings": []}
