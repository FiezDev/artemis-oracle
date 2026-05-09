"""Project configuration for ISO document generation."""

from datetime import datetime
import json
import os


class ProjectConfig:
    """Holds all project-specific configuration. Load from JSON or kwargs."""

    AUTHOR = "Ittipol Vongapai"
    ORGANIZATION = "go-thailand"
    STATUS = "Approved"
    CLASSIFICATION = "Internal"
    VERSION = "1.0"
    DOC_DATE = datetime.now().strftime("%Y-%m-%d")

    def __init__(self, project_name, project_code, description="",
                 github_url="", local_repo="", system_url="",
                 output_dir="", assets_dir="", languages=None,
                 docs=None, routes=None, auth=None, modules_overrides=None,
                 frontends=None, backend=None, architecture=None,
                 diagrams_source="", revision_entries=None):
        self.PROJECT_NAME = project_name
        self.PROJECT_CODE = project_code.upper()
        if isinstance(description, dict):
            self._description_map = description
            self.PROJECT_DESCRIPTION = description.get("en", "")
        else:
            self._description_map = {"en": description}
            self.PROJECT_DESCRIPTION = description
        self.GITHUB_URL = github_url
        self.LOCAL_REPO = local_repo
        self.SYSTEM_URL = system_url
        self.OUTPUT_DIR = output_dir or "/mnt/c/Users/bjgdr/OneDrive/Documents/ISODOC/newfinaldoc"
        self.ASSETS_DIR = assets_dir or os.path.join(self.OUTPUT_DIR, "assets")
        self.LANGUAGES = languages or ["en"]
        self.DOCS = docs or ["13", "15", "19"]
        self.ROUTES = routes or {}
        self.AUTH = auth or {}
        self.MODULES_OVERRIDES = modules_overrides or []
        self.FRONTENDS = frontends or []
        self.BACKEND = backend or {}
        self.ARCHITECTURE = architecture or {}
        self.DIAGRAMS_SOURCE = diagrams_source or ""
        self.REVISION_ENTRIES = revision_entries or []

        self.DIAGRAMS_DIR = os.path.join(self.ASSETS_DIR, "diagrams")
        self.SCREENSHOTS_DIR = os.path.join(self.ASSETS_DIR, "screenshots")

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        os.makedirs(self.DIAGRAMS_DIR, exist_ok=True)
        os.makedirs(self.SCREENSHOTS_DIR, exist_ok=True)

    @classmethod
    def from_json(cls, path, **overrides):
        """Load from iso-doc.json. CLI overrides win over JSON values."""
        with open(path) as f:
            data = json.load(f)

        project = data.get("project", {})
        urls = data.get("urls", {})

        kwargs = {
            "project_name": project.get("name", ""),
            "project_code": project.get("code", ""),
            "description": project.get("description", ""),
            "github_url": urls.get("github", ""),
            "local_repo": urls.get("local_repo", ""),
            "system_url": urls.get("live", ""),
            "output_dir": data.get("output_dir", os.path.dirname(os.path.abspath(path))),
            "languages": data.get("languages", ["en"]),
            "docs": data.get("docs", ["13", "15", "19"]),
            "routes": data.get("routes", {}),
            "auth": data.get("auth", {}),
            "modules_overrides": data.get("modules_overrides", []),
            "frontends": data.get("frontends", []),
            "backend": data.get("backend", {}),
            "architecture": data.get("architecture", {}),
            "diagrams_source": data.get("diagrams_source", ""),
            "revision_entries": data.get("revision_entries", []),
        }
        kwargs.update({k: v for k, v in overrides.items() if v})
        return cls(**kwargs)

    def description_for(self, lang):
        """Return project description in requested language (fallback: en)."""
        return (self._description_map.get(lang)
                or self._description_map.get("en")
                or self.PROJECT_DESCRIPTION)

    def doc_number(self, category):
        return f"DOC-{self.PROJECT_CODE}-{category}"

    def output_path(self, doc_type, lang="en"):
        names = {"13": "Software Components", "15": "Software Design web", "19": "Test Report"}
        base = names.get(doc_type, f"Document {doc_type}")
        suffix = f"_{lang.upper()}" if lang != "en" else ""
        filename = f"{doc_type}_{base} - {self.PROJECT_CODE}{suffix}.docx"
        return os.path.join(self.OUTPUT_DIR, filename)

    def lang_screenshots_dir(self, lang):
        """Per-language screenshot dir: assets/screenshots/{lang}/"""
        return os.path.join(self.SCREENSHOTS_DIR, lang)

    def common_screenshot_ids(self):
        """Return set of screenshot IDs (filename without .png) that exist in
        EVERY configured language's dir. A page only belongs in the ISO docs
        if it captured cleanly in ALL languages — per user rule: the page
        must work in both EN and TH to be present."""
        if not self.LANGUAGES:
            return set()
        sets = []
        for lang in self.LANGUAGES:
            d = self.lang_screenshots_dir(lang)
            if not os.path.isdir(d):
                return set()
            sets.append({f[:-4] for f in os.listdir(d) if f.endswith(".png")})
        return set.intersection(*sets) if sets else set()
