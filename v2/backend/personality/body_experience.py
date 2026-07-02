"""Build body-part experience summaries from persona YAML."""

BODY_PART_CN: dict[str, str] = {
    "neck": "颈部",
    "ears": "耳朵",
    "chest": "胸部",
    "breast": "胸部",
    "waist": "腰肢",
    "thighs": "大腿",
    "inner_thigh": "大腿内侧",
    "lips": "嘴唇",
    "spine": "后背",
    "hands": "双手",
    "hips": "臀部",
    "belly": "小腹",
    "shoulders": "肩膀",
}


def build_body_experiences(persona: dict, rel_summary: dict | None = None) -> list[dict]:
    """Return list of {part, sensitivity, experience} for UI display."""
    rel = rel_summary or {}
    love = float(rel.get("love", 0))
    intimate = persona.get("intimate_state", {})
    custom = intimate.get("body_experiences") or {}
    sensitivity = intimate.get("sensitivity") or {}

    if persona.get("relationship_type") == "brotherhood" or persona.get("gender") == "male":
        return []

    results: list[dict] = []
    seen: set[str] = set()

    for key, text in custom.items():
        part_cn = BODY_PART_CN.get(key, key)
        seen.add(key)
        results.append({
            "part": part_cn,
            "key": key,
            "sensitivity": sensitivity.get(key),
            "experience": str(text),
        })

    for key, sens in sorted(sensitivity.items(), key=lambda x: x[1], reverse=True):
        if key in seen:
            continue
        part_cn = BODY_PART_CN.get(key, key)
        sens_val = float(sens)
        if love >= 85:
            exp = f"敏感度 {sens_val:.0f}/10，与你已有深度亲密经历，会在触碰时不自觉软下来。"
        elif love >= 60:
            exp = f"敏感度 {sens_val:.0f}/10，曾在你怀里被温柔对待，对这里有记忆。"
        elif love >= 30:
            exp = f"敏感度 {sens_val:.0f}/10，有过暧昧接触，仍会因你的靠近而心跳加快。"
        else:
            exp = f"敏感度 {sens_val:.0f}/10，尚未完全交付，但对你并不排斥。"
        results.append({
            "part": part_cn,
            "key": key,
            "sensitivity": sens_val,
            "experience": exp,
        })

    return results
