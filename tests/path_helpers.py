def join_tag_path(base_path: str, *parts: str) -> str:
    """Join Ignition tag paths without inserting a slash after provider roots."""
    base_path = base_path.rstrip("/")
    suffix = "/".join(part.strip("/") for part in parts if part)
    if not suffix:
        return base_path
    separator = "" if base_path.endswith("]") else "/"
    return base_path + separator + suffix
