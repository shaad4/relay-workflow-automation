def evaluate_condition(
    configuration: dict,
) -> str:
    """
    Return the resolved value used to select
    a matching outgoing workflow edge.
    """

    if not isinstance(configuration, dict):
        raise ValueError("Invalid Condition node configuration")

    value = configuration.get("value")

    if value is None:
        raise ValueError("Condition value is missing")

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (str, int, float)):
        result = str(value).strip()

        if not result:
            raise ValueError("Condition value cannot be empty")

        if "{{" in result or "}}" in result:
            raise ValueError("Condition contains unresolved expression")

        return result

    raise ValueError("Condition value must be a string, number, or boolean")
