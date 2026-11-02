"""Validate references without executing actions or requiring future trigger data."""

from app.contracts.expressions import expression_matches, path_parts
from app.schemas.node_registry import TRIGGER_TYPES
from app.services.node_catalog import OUTPUT_SCHEMAS


def configuration_strings(value, field=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from configuration_strings(item, f"{field}.{key}" if field else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from configuration_strings(item, f"{field}[{index}]")
    elif isinstance(value, str):
        yield field, value


def guaranteed_predecessors(nodes, edges):
    """Dominators exclude references that only exist on one side of a branch."""
    by_id = {node.node_id: node for node in nodes}
    triggers = [node.node_id for node in nodes if node.node_type in TRIGGER_TYPES]
    if len(triggers) != 1:
        return {}
    root = triggers[0]
    parents = {key: set() for key in by_id}
    children = {key: set() for key in by_id}
    for edge in edges:
        if edge.source_node_id in by_id and edge.target_node_id in by_id:
            parents[edge.target_node_id].add(edge.source_node_id)
            children[edge.source_node_id].add(edge.target_node_id)
    reachable, pending = set(), [root]
    while pending:
        key = pending.pop()
        if key not in reachable:
            reachable.add(key)
            pending.extend(children[key])
    dominators = {key: {root} if key == root else set(reachable) for key in reachable}
    changed = True
    while changed:
        changed = False
        for key in reachable - {root}:
            incoming = parents[key] & reachable
            common = set.intersection(*(dominators[parent] for parent in incoming))
            value = {key} | common
            if dominators[key] != value:
                dominators[key] = value
                changed = True
    return {key: value - {key} for key, value in dominators.items()}


def supports_output_path(schema, parts):
    for part in parts:
        kind = schema.get("type")
        if kind == "object":
            properties = schema.get("properties", {})
            if part in properties:
                schema = properties[part]
            elif schema.get("additionalProperties", True) is not False:
                return True  # Runtime-defined dictionary, e.g. an HTTP body.
            else:
                return False
        elif kind == "array":
            if not part.isascii() or not part.isdigit():
                return False
            schema = schema.get("items", {})
        elif kind is None:
            return True  # Arbitrary provider data; no static shape is promised.
        else:
            return False
    return True


def sample_has_path(sample, parts):
    current = {"trigger": {"data": sample}}
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif (
            isinstance(current, list)
            and part.isascii()
            and part.isdigit()
            and int(part) < len(current)
        ):
            current = current[int(part)]
        else:
            return False
    return current is not None


def validate_expression_references(nodes, edges, sample_input=None):
    by_id = {node.node_id: node for node in nodes}
    predecessors = guaranteed_predecessors(nodes, edges)
    errors = []
    for node in nodes:
        if node.node_type in TRIGGER_TYPES:
            continue  # Trigger configuration is static, not passed through the resolver.
        for field, value in configuration_strings(node.configuration):
            try:
                matches = expression_matches(value)
            except ValueError:
                errors.append(
                    {
                        "code": "INVALID_EXPRESSION_SYNTAX",
                        "node_id": node.node_id,
                        "field": field,
                        "message": f"Field '{field}' contains a malformed expression.",
                        "suggestion": "Use a dot path such as {{trigger.data.research_topic}}; expressions do not support operators or function calls.",
                    }
                )
                continue
            for match in matches:
                parts = path_parts(match.group(1))
                root = parts[0]
                message = suggestion = None
                code = "INVALID_EXPRESSION_REFERENCE"
                if root not in {"trigger", "nodes", "variables"}:
                    message = f"Unknown expression root '{root}'."
                    suggestion = "Trigger inputs use {{trigger.data.<field>}}; node outputs use {{nodes.<node_id>.<field>}}."
                    if root in by_id and by_id[root].node_type in TRIGGER_TYPES:
                        suffix = parts[1:]
                        if suffix and suffix[0] == "data":
                            suffix = suffix[1:]
                        corrected = ".".join(["trigger", "data", *suffix])
                        suggestion = (
                            "Use {{"
                            + corrected
                            + "}}; trigger inputs are stored under trigger.data."
                        )
                elif root == "trigger":
                    if len(parts) > 1 and parts[1] != "data":
                        message = "Trigger input fields must be read under trigger.data."
                        suggestion = (
                            "Use {{trigger.data.<field>}}, regardless of the trigger node ID."
                        )
                    elif sample_input is not None and not sample_has_path(sample_input, parts):
                        code = "MISSING_SAMPLE_INPUT"
                        message = "The referenced trigger field is absent or null in the supplied sample input."
                        suggestion = "Correct the expression or include this field in sample_input and the actual trigger payload."
                elif root == "nodes":
                    source = by_id.get(parts[1]) if len(parts) > 1 else None
                    if source is None:
                        message = "The expression must reference an existing node ID."
                        suggestion = "Use {{nodes.<existing_node_id>.<output_field>}}."
                    elif source.node_type in TRIGGER_TYPES:
                        message = "Trigger nodes do not store outputs under nodes."
                        suggestion = "Use {{trigger.data.<field>}}."
                    elif source.node_type == "human.approval":
                        message = "Human approval does not expose node output data."
                        suggestion = "Use approved/rejected edge conditions to route the workflow."
                    elif source.node_id not in predecessors.get(node.node_id, set()):
                        message = (
                            "The referenced node is not guaranteed to execute before this node."
                        )
                        suggestion = "Reference a node that precedes this node on every incoming path; do not reference later nodes or another branch."
                    elif not supports_output_path(
                        OUTPUT_SCHEMAS.get(source.node_type, {}), parts[2:]
                    ):
                        message = "The referenced output field does not exist in this node's output schema."
                        suggestion = "Read the source node's output_schema. Outputs use nodes.<node_id>.<field> with no .output wrapper."
                if message:
                    errors.append(
                        {
                            "code": code,
                            "node_id": node.node_id,
                            "field": field,
                            "expression": match.group(0),
                            "message": message,
                            "suggestion": suggestion,
                        }
                    )
    return errors
