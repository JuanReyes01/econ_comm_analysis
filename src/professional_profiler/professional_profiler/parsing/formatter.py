def degrees_to_markdown(degrees_map: dict) -> str:
    lines = []
    for section, sents in degrees_map.items():
        header = "# Lead" if section == "_lead_" else f"## {section}"
        lines.append(header)
        lines += [f"- {s}" for s in sents]
        lines.append("")  # blank line
    return "\n".join(lines)
