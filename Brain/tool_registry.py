"""Typed local tool registry with explicit permission gates."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable
import webbrowser
import urllib.parse

from Features import file_agent
from Automation.open_App import open_App
from Automation import windows_uia
from Automation import office_automation


class PermissionLevel(IntEnum):
    READ_ONLY = 0
    SAFE_ACTION = 1
    CONFIRM_REQUIRED = 2
    FULL_CONTROL = 3


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    schema: dict
    permission: PermissionLevel
    execute: Callable
    validate: Callable[[dict], None]
    confirmation_argument: str | None = None


def _validate_required(required):
    def validate(arguments):
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ValueError("Missing required argument(s): " + ", ".join(missing))
    return validate


def _launch_application(app):
    process = open_App(app)
    return {"application": app, "pid": getattr(process, "pid", None)}


def _google_search(query):
    """Open Google search in default browser with validated query."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return {"query": query, "url": url}


def _open_url(url):
    """Open a URL in the default browser with validation."""
    parsed = urllib.parse.urlparse(url)
    # Validate scheme and hostname
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme or 'none'}")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL: missing hostname")
    # Block credential-bearing URLs (user@host)
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    webbrowser.open(url)
    return {"url": url}


def _search_and_open(query):
    """Search Google and open the search results page."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return {"query": query, "opened": url}


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, spec):
        if spec.name in self._tools:
            raise ValueError(f"Tool is already registered: {spec.name}")
        self._tools[spec.name] = spec

    def list_tools(self):
        return [
            {
                "name": item.name,
                "description": item.description,
                "schema": item.schema,
                "permission": item.permission.name,
            }
            for item in sorted(self._tools.values(), key=lambda entry: entry.name)
        ]

    def execute(self, name, arguments, confirmation_granted=False):
        spec = self._tools.get(name)
        if spec is None:
            return {"success": False, "error": f"Unknown tool: {name}"}
        arguments = dict(arguments or {})
        try:
            spec.validate(arguments)
            properties = spec.schema.get("properties", {})
            unknown = set(arguments) - set(properties)
            if unknown:
                raise ValueError("Unexpected argument(s): " + ", ".join(sorted(unknown)))
            type_checks = {
                "string": lambda value: isinstance(value, str),
                "integer": lambda value: isinstance(value, int) and not isinstance(value, bool),
                "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
                "boolean": lambda value: isinstance(value, bool),
                "array": lambda value: isinstance(value, list),
                "object": lambda value: isinstance(value, dict),
            }
            for key, value in arguments.items():
                expected_type = properties.get(key, {}).get("type")
                checker = type_checks.get(expected_type)
                if checker and not checker(value):
                    raise ValueError(f"Argument '{key}' must be {expected_type}.")
            target = (
                arguments.get("path") or arguments.get("destination") or arguments.get("source")
                or " / ".join(value for value in (
                    arguments.get("control_name"), arguments.get("window_title")
                ) if value)
            )
            overwrite_needs_confirmation = False
            if name in {"file_create", "office_word_create", "office_excel_create", "office_ppt_create"} and target:
                try:
                    overwrite_needs_confirmation = file_agent.resolve_allowed_path(target).exists()
                except (OSError, PermissionError):
                    pass
            needs_confirmation = (
                spec.permission >= PermissionLevel.CONFIRM_REQUIRED or overwrite_needs_confirmation
            )
            if needs_confirmation and not confirmation_granted:
                return {
                    "success": False,
                    "confirmation_required": True,
                    "tool": name,
                    "target": target,
                }
            if spec.confirmation_argument and confirmation_granted:
                arguments[spec.confirmation_argument] = True
            if name in {"file_create", "office_word_create", "office_excel_create", "office_ppt_create"} and overwrite_needs_confirmation and confirmation_granted:
                arguments["confirm_overwrite"] = True
            result = spec.execute(**arguments)
            return {"success": True, "tool": name, "result": result}
        except Exception as exc:
            return {"success": False, "tool": name, "error": str(exc)}


def create_default_registry():
    registry = ToolRegistry()
    definitions = (
        ToolSpec("open_application", "Launch an allowlisted desktop application.",
                 {"type": "object", "properties": {"app": {"type": "string"}}, "required": ["app"]}, PermissionLevel.SAFE_ACTION,
                 _launch_application, _validate_required(("app",))),
        ToolSpec("file_search", "Find filenames inside configured ASTRA roots.",
                 {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}, PermissionLevel.READ_ONLY,
                 file_agent.search_files, _validate_required(("query",))),
        ToolSpec("file_read", "Read supported text, PDF, DOCX, or XLSX files within configured roots.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, "required": ["path"]}, PermissionLevel.READ_ONLY,
                 file_agent.read_file, _validate_required(("path",))),
        ToolSpec("file_create", "Create a UTF-8 text file within configured roots.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path"]}, PermissionLevel.SAFE_ACTION,
                 file_agent.create_file, _validate_required(("path",))),
        ToolSpec("file_inspect", "Read file or directory metadata within configured roots.",
                 {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, PermissionLevel.READ_ONLY,
                 file_agent.inspect_file, _validate_required(("path",))),
        ToolSpec("vision_analyze", "Analyze an image file locally with the configured Ollama vision model.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["path"]}, PermissionLevel.READ_ONLY,
                 file_agent.analyze_image, _validate_required(("path",))),
        ToolSpec("file_copy", "Copy a file within configured roots.",
                 {"type": "object", "properties": {"source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["source", "destination"]}, PermissionLevel.CONFIRM_REQUIRED,
                 file_agent.copy_file, _validate_required(("source", "destination")), "confirmed"),
        ToolSpec("file_move", "Move or rename a file within configured roots.",
                 {"type": "object", "properties": {"source": {"type": "string"}, "destination": {"type": "string"}}, "required": ["source", "destination"]}, PermissionLevel.CONFIRM_REQUIRED,
                 file_agent.move_file, _validate_required(("source", "destination")), "confirmed"),
        ToolSpec("file_delete", "Delete one file within configured roots.",
                 {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}, PermissionLevel.CONFIRM_REQUIRED,
                 file_agent.delete_file, _validate_required(("path",)), "confirmed"),
        ToolSpec("windows_list", "List visible desktop windows and process IDs.",
                 {"type": "object", "properties": {"max_results": {"type": "integer"}}}, PermissionLevel.READ_ONLY,
                 windows_uia.list_windows, _validate_required(())),
        ToolSpec("window_inspect", "Read accessible control names and types from one exact window title.",
                 {"type": "object", "properties": {"window_title": {"type": "string"}, "max_controls": {"type": "integer"}}, "required": ["window_title"]}, PermissionLevel.READ_ONLY,
                 windows_uia.inspect_window, _validate_required(("window_title",))),
        ToolSpec("window_focus", "Focus one open window by its exact title.",
                 {"type": "object", "properties": {"window_title": {"type": "string"}}, "required": ["window_title"]}, PermissionLevel.SAFE_ACTION,
                 windows_uia.focus_window, _validate_required(("window_title",))),
        ToolSpec("ui_control_click", "Click one uniquely named accessible control after explicit confirmation.",
                 {"type": "object", "properties": {"window_title": {"type": "string"}, "control_name": {"type": "string"}, "control_type": {"type": "string"}}, "required": ["window_title", "control_name"]}, PermissionLevel.CONFIRM_REQUIRED,
                 windows_uia.click_control, _validate_required(("window_title", "control_name"))),
        ToolSpec("ui_control_set_text", "Set text in one uniquely named edit control after explicit confirmation.",
                 {"type": "object", "properties": {"window_title": {"type": "string"}, "control_name": {"type": "string"}, "text": {"type": "string"}}, "required": ["window_title", "control_name", "text"]}, PermissionLevel.CONFIRM_REQUIRED,
                 windows_uia.set_control_text, _validate_required(("window_title", "control_name", "text"))),
        ToolSpec("office_word_create", "Create a formatted DOCX through Microsoft Word and leave it open for review.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "title"]}, PermissionLevel.SAFE_ACTION,
                 office_automation.create_word_document, _validate_required(("path", "title"))),
        ToolSpec("office_word_append", "Append text to an existing DOCX in Microsoft Word after confirmation.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}, PermissionLevel.CONFIRM_REQUIRED,
                 office_automation.append_word_text, _validate_required(("path", "content")), "confirmed"),
        ToolSpec("office_excel_create", "Create a formatted XLSX workbook through Microsoft Excel, with an optional chart sheet.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "rows": {"type": "array"}, "sheet_name": {"type": "string"}, "chart_title": {"type": "string"}}, "required": ["path", "rows"]}, PermissionLevel.SAFE_ACTION,
                 office_automation.create_excel_workbook, _validate_required(("path", "rows"))),
        ToolSpec("office_excel_chart", "Add a chart sheet to an existing XLSX workbook after confirmation.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "sheet_name": {"type": "string"}, "chart_title": {"type": "string"}}, "required": ["path"]}, PermissionLevel.CONFIRM_REQUIRED,
                 office_automation.add_excel_chart, _validate_required(("path",)), "confirmed"),
ToolSpec("office_ppt_create", "Create a titled PowerPoint presentation with a content slide and leave it open for review.",
                  {"type": "object", "properties": {"path": {"type": "string"}, "title": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "title"]}, PermissionLevel.SAFE_ACTION,
                  office_automation.create_powerpoint_presentation, _validate_required(("path", "title"))),
        ToolSpec("web_search", "Search Google in the default browser.",
                 {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, PermissionLevel.SAFE_ACTION,
                 _google_search, _validate_required(("query",))),
        ToolSpec("open_url", "Open a URL in the default browser.",
                 {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}, PermissionLevel.SAFE_ACTION,
                 _open_url, _validate_required(("url",))),
        ToolSpec("browser_search", "Search Google and open the search results page.",
                 {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}, PermissionLevel.SAFE_ACTION,
                 _search_and_open, _validate_required(("query",))),
        ToolSpec("notepad_create", "Create a text file with Notepad.",
                 {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path"]}, PermissionLevel.SAFE_ACTION,
                 file_agent.create_file, _validate_required(("path",))),
    )
    for spec in definitions:
        registry.register(spec)
    return registry
