"""User settings persisted as JSON in the user data folder. Never holds the password."""
import json
import logging
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from src.paths import default_output_dir, settings_file

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    output_dir: str = field(default_factory=lambda: str(default_output_dir()))
    show_browser: bool = False
    download_timeout: int = 60
    username: str = ''
    # Last course list shown in the UI: [{"id": 17, "template": "final", "attendance": "zoom"}]
    courses: list = field(default_factory=list)
    # Cache of course id -> course name, so the UI can show names without logging in
    course_names: dict = field(default_factory=dict)
    # Course id -> {template column header: platform quiz name}
    grade_mappings: dict = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> 'Settings':
        path = path or settings_file()
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            logger.exception('Settings file %s is unreadable; using defaults', path)
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        path = path or settings_file()
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, path)

    def remember_course_name(self, course_id: int, name: str) -> None:
        self.course_names[str(course_id)] = name

    def course_name(self, course_id: int) -> str | None:
        return self.course_names.get(str(course_id))

    def grade_mapping(self, course_id: int) -> dict:
        return self.grade_mappings.get(str(course_id), {})

    def remember_grade_mapping(self, course_id: int, mapping: dict) -> None:
        self.grade_mappings[str(course_id)] = dict(mapping)
