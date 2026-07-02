"""
角色加载器：从 YAML 加载 11 个角色，转换为运行时数据结构。"""
import yaml
from pathlib import Path


class PersonaLoader:
    def __init__(self, persona_dir: Path):
        self.persona_dir = persona_dir
        self.personas = {}
        self.load_all()

    def load_all(self):
        for yaml_file in self.persona_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self.personas[data["id"]] = data

    def get(self, persona_id: str) -> dict:
        return self.personas.get(persona_id, {})

    def get_display_name(self, persona_id: str) -> str:
        p = self.get(persona_id)
        return p.get("name", persona_id)

    def list_all(self) -> list:
        return [
            {"id": pid, "name": p.get("name", pid), "type": p.get("type", "")}
            for pid, p in self.personas.items()
        ]

    def get_chat_style(self, persona_id: str) -> dict:
        p = self.get(persona_id)
        speech = p.get("speech_style", {})
        personality = p.get("personality", {})
        return {
            "default_tone": speech.get("default", ""),
            "private_tone": speech.get("private", ""),
            "habits": speech.get("habits", []),
            "is_female": p.get("base_info", {}).get("gender") != "male",
        }
