"""Recognize deterministic, read-scoped file intents before model inference."""

import re
import time
import json
from Automation.open_App import APP_ALLOWLIST


_SEARCH = re.compile(
    r"^(?:find|search for|search|locate|tìm kiếm|tìm)\s+(?:my\s+)?"
    r"(?:files?|documents?|tệp|tập tin)\s*(.+)$",
    re.I,
)
_READ = re.compile(r"^(?:read|đọc)\s+(?:the\s+)?(?:file|document|tệp|tập tin)\s+(.+)$", re.I)
_CREATE = re.compile(
    r"^(?:create|make|tạo)\s+(?:a\s+|new\s+)?"
    r"(?:(text|python|java|html|css|javascript|json|xml|csv|markdown|yaml|pdf|word|excel|powerpoint|zip)\s+)?"
    r"(?:file|tệp|tập tin)\s+(?:(?:named|called|tên là)\s*)?(.+)$",
    re.I,
)
_FILE_SUFFIXES = {
    "text": ".txt", "python": ".py", "java": ".java", "html": ".html",
    "css": ".css", "javascript": ".js", "json": ".json", "xml": ".xml",
    "csv": ".csv", "markdown": ".md", "yaml": ".yaml", "pdf": ".pdf",
    "word": ".docx", "excel": ".xlsx", "powerpoint": ".pptx", "zip": ".zip",
}
_DELETE = re.compile(r"^(?:delete|remove|xóa)\s+(?:the\s+)?(?:file|tệp)\s+(.+)$", re.I)
_MOVE = re.compile(
    r"^(?:move|rename|di chuyển|đổi tên)\s+(?:the\s+)?(?:file|tệp)\s+(.+?)\s+(?:to|thành|sang)\s+(.+)$",
    re.I,
)
_COPY = re.compile(r"^(?:copy|sao chép)\s+(?:the\s+)?(?:file|tệp)\s+(.+?)\s+(?:to|thành|sang)\s+(.+)$", re.I)
_OPEN = re.compile(r"^(?:open|launch|start|mở|chạy)\s+(?:the\s+)?(?:application\s+|app\s+)?(.+)$", re.I)
_IMAGE = re.compile(r"^(?:analyze|describe|what is in|phân tích|mô tả)\s+(?:the\s+)?(?:image|picture|ảnh|hình ảnh)\s+(.+)$", re.I)
_WINDOWS_LIST = re.compile(r"^(?:list|show) (?:open )?windows$|^liệt kê cửa sổ$", re.I)
_WINDOW_INSPECT = re.compile(r"^(?:inspect window|xem cửa sổ)\s+(.+)$", re.I)
_WINDOW_FOCUS = re.compile(r"^(?:focus window|tập trung cửa sổ)\s+(.+)$", re.I)
_CONTROL_CLICK = re.compile(
    r"^(?:click control|bấm điều khiển)\s+(.+?)\s+(?:in|trong) (?:the )?(?:window|cửa sổ)\s+(.+)$",
    re.I,
)
_CONTROL_TEXT = re.compile(
    r"^(?:set text in control|nhập văn bản vào điều khiển)\s+(.+?)\s+"
    r"(?:in|trong) (?:the )?(?:window|cửa sổ)\s+(.+?)\s+(?:to|thành)\s+(.+)$",
    re.I,
)
_WORD_CREATE = re.compile(
    r'^(?:create word document|tạo tài liệu word) "([^"]+)" (?:with title|với tiêu đề) "([^"]+)" '
    r'(?:and content|và nội dung) "([\s\S]*)"$', re.I,
)
_WORD_APPEND = re.compile(
    r'^(?:append to word document|thêm vào tài liệu word) "([^"]+)" '
    r'(?:text|nội dung) "([\s\S]*)"$', re.I,
)
# "open word and type hello world" → office_word_create
_OPEN_WORD_TYPE = re.compile(
    r'^(?:open|launch|mở)\s+(?:word|winword)\s+(?:and|và|với)\s*(?:type|nhập|write|viết)\s+(.+)$',
    re.I,
)
_EXCEL_CREATE = re.compile(r'^create excel workbook "([^"]+)" data ([\s\S]+)$', re.I)
_EXCEL_CHART = re.compile(r'^(?:add chart to excel workbook|thêm biểu đồ vào workbook excel) "([^"]+)"$', re.I)
_PPT_CREATE = re.compile(
    r'^(?:create powerpoint presentation|tạo bản trình chiếu powerpoint) "([^"]+)" '
    r'(?:with title|với tiêu đề) "([^"]+)" (?:and content|và nội dung) "([\s\S]*)"$', re.I,
)
# Web search patterns - match "search google for X" or "search X"
_WEB_SEARCH = re.compile(
    r"^(?:search|tìm kiếm|search for|search about)\s+(?:the\s+)?(?:web|google|internet|online)?\s*(.+)$",
    re.I,
)
# "open google" / "open youtube" → web_search (not open_url)
_OPEN_GOOGLE = re.compile(
    r"^(?:open|launch|mở)\s+(?:google|youtube|bing|duckduckgo|web|internet|browser)\s*(.*)$",
    re.I,
)
# Only match actual URLs with scheme or www prefix
_OPEN_URL = re.compile(
    r"^(?:open|navigate to|mở)\s+(?:url|website|web)?\s*(https?://\S+|www\.\S+)$",
    re.I,
)


class LocalToolRouter:
    """Route only unambiguous non-destructive file requests to scoped tools."""

    def __init__(self, registry):
        self.registry = registry
        self.pending_confirmation = None

    @staticmethod
    def _clean(value):
        return str(value).strip().strip("\"'")

    def route(self, prompt):
        text = str(prompt or "").strip()
        if self.pending_confirmation:
            if time.monotonic() - self.pending_confirmation["created_at"] > 60:
                self.pending_confirmation = None
        if self.pending_confirmation:
            expected = self.pending_confirmation["confirmation_phrase"].casefold()
            if text.casefold() == expected or text.casefold() in {"cancel file action", "hủy thao tác file"}:
                return "__confirmation__", {}
        match = _OPEN_WORD_TYPE.match(text)
        if match:
            content = self._clean(match.group(1))
            return "office_word_create", {
                "path": "ASTRA_Document.docx",
                "title": "ASTRA Document",
                "content": content,
            }
        match = _WORD_CREATE.match(text)
        if match:
            return "office_word_create", {
                "path": self._clean(match.group(1)),
                "title": self._clean(match.group(2)),
                "content": self._clean(match.group(3)),
            }
        match = _WORD_APPEND.match(text)
        if match:
            return "office_word_append", {
                "path": self._clean(match.group(1)),
                "content": self._clean(match.group(2)),
            }
        match = _EXCEL_CREATE.match(text)
        if match:
            try:
                rows = json.loads(match.group(2))
            except json.JSONDecodeError:
                rows = None
            return "office_excel_create", {"path": self._clean(match.group(1)), "rows": rows}
        match = _EXCEL_CHART.match(text)
        if match:
            return "office_excel_chart", {"path": self._clean(match.group(1))}
        match = _PPT_CREATE.match(text)
        if match:
            return "office_ppt_create", {
                "path": self._clean(match.group(1)),
                "title": self._clean(match.group(2)),
                "content": self._clean(match.group(3)),
            }
        if _WINDOWS_LIST.match(text):
            return "windows_list", {}
        match = _WINDOW_INSPECT.match(text)
        if match:
            return "window_inspect", {"window_title": self._clean(match.group(1))}
        match = _WINDOW_FOCUS.match(text)
        if match:
            return "window_focus", {"window_title": self._clean(match.group(1))}
        match = _CONTROL_CLICK.match(text)
        if match:
            return "ui_control_click", {
                "control_name": self._clean(match.group(1)),
                "window_title": self._clean(match.group(2)),
            }
        match = _CONTROL_TEXT.match(text)
        if match:
            return "ui_control_set_text", {
                "control_name": self._clean(match.group(1)),
                "window_title": self._clean(match.group(2)),
                "text": self._clean(match.group(3)),
            }
        for pattern, tool_name, argument_name in (
            (_SEARCH, "file_search", "query"),
            (_READ, "file_read", "path"),
            (_DELETE, "file_delete", "path"),
        ):
            match = pattern.match(text)
            if match:
                return tool_name, {argument_name: self._clean(match.group(1))}
        match = _CREATE.match(text)
        if match:
            file_type = (match.group(1) or "").casefold()
            filename = self._clean(match.group(2))
            suffix = _FILE_SUFFIXES.get(file_type, "")
            if suffix and not filename.casefold().endswith(suffix):
                filename += suffix
            return "file_create", {"path": filename}
        match = _IMAGE.match(text)
        if match:
            return "vision_analyze", {"path": self._clean(match.group(1)), "prompt": text}
        match = _MOVE.match(text)
        if match:
            return "file_move", {"source": self._clean(match.group(1)), "destination": self._clean(match.group(2))}
        match = _COPY.match(text)
        if match:
            return "file_copy", {"source": self._clean(match.group(1)), "destination": self._clean(match.group(2))}
        match = _OPEN.match(text)
        if match:
            app = self._clean(match.group(1)).casefold()
            if app in APP_ALLOWLIST:
                return "open_application", {"app": app}
        # "open google" / "open youtube" → web_search
        match = _OPEN_GOOGLE.match(text)
        if match:
            query = self._clean(match.group(1)) or "google"
            return "web_search", {"query": query}
        # Web search patterns
        match = _WEB_SEARCH.match(text)
        if match:
            return "web_search", {"query": self._clean(match.group(1))}
        match = _OPEN_URL.match(text)
        if match:
            return "open_url", {"url": self._clean(match.group(1))}
        return None

    def execute(self, prompt):
        route = self.route(prompt)
        if route is None:
            return None
        name, arguments = route
        if name == "__confirmation__":
            if str(prompt).strip().casefold() in {"cancel file action", "hủy thao tác file"}:
                self.pending_confirmation = None
                return {
                    "content": "The pending file action was cancelled.",
                    "engine": "astra_local_tools",
                    "model": "local",
                    "tool_results": [{"tool_name": "confirmation", "success": True, "result": "cancelled"}],
                }
            pending = self.pending_confirmation
            self.pending_confirmation = None
            result = self.registry.execute(
                pending["name"], pending["arguments"], confirmation_granted=True
            )
            name = pending["name"]
        else:
            result = self.registry.execute(name, arguments)
            if result.get("confirmation_required"):
                target = str(result.get("target") or "the selected target")
                if name in {"ui_control_click", "ui_control_set_text"}:
                    confirmation_phrase = f"confirm desktop action {name} {target}"
                elif name.startswith("office_"):
                    confirmation_phrase = f"confirm office action {name} {target}"
                else:
                    confirmation_phrase = f"confirm file action {target}"
                self.pending_confirmation = {
                    "name": name,
                    "arguments": arguments,
                    "confirmation_phrase": confirmation_phrase,
                    "created_at": time.monotonic(),
                }
        if not result.get("success"):
            if result.get("confirmation_required"):
                phrase = self.pending_confirmation["confirmation_phrase"]
                content = f"ASTRA needs confirmation before acting on {result.get('target')}. To proceed, type exactly: {phrase}"
            else:
                content = f"ASTRA could not run {name}: {result.get('error', 'Unknown error')}"
        else:
            value = result.get("result")
            if name == "file_search":
                content = "\n".join(value) if value else "No matching files were found in ASTRA's configured roots."
            elif name == "file_read":
                content = f"File contents:\n{value}"
            elif name == "vision_analyze":
                content = str(value)
            elif name == "file_delete":
                content = f"Deleted file: {value}"
            elif name == "file_move":
                content = f"Moved file to: {value}"
            elif name == "file_copy":
                content = f"Copied file to: {value}"
            elif name == "open_application":
                content = f"Opened {value['application']}"
            elif name == "windows_list":
                content = "\n".join(item["title"] for item in value) if value else "No titled windows are open."
            elif name == "window_inspect":
                content = f"Accessible controls in {value['window']}:\n" + "\n".join(
                    f"- {control['control_type']}: {control['name']} (id: {control['automation_id']})"
                    for control in value["controls"]
                )
            elif name == "window_focus":
                content = f"Focused window: {value['window']}"
            elif name == "ui_control_click":
                content = f"Clicked {value['control']} in {value['window']}"
            elif name == "ui_control_set_text":
                content = f"Entered {value['characters_written']} characters in {value['control']} in {value['window']}"
            elif name == "office_word_create":
                content = f"Created and saved Word document: {value['path']} (verified; document left open)."
            elif name == "office_word_append":
                content = f"Updated and verified Word document: {value['path']} (document left open)."
            elif name == "office_excel_create":
                content = f"Created and saved Excel workbook: {value['path']} (verified; workbook left open)."
                if value.get("chart_created"):
                    content += " Added a chart sheet."
            elif name == "office_excel_chart":
                content = f"Added and verified a chart in Excel workbook: {value['path']} (workbook left open)."
            elif name == "office_ppt_create":
                content = f"Created and saved PowerPoint presentation: {value['path']} (verified; presentation left open)."
            elif name == "web_search":
                content = f"Opened Google search for: {value['query']}"
            elif name == "open_url":
                content = f"Opened URL: {value['url']}"
            elif name == "browser_search":
                content = f"Opened Google search for: {value['query']}"
            else:
                content = f"Created file: {value}"
        return {
            "content": content,
            "engine": "astra_local_tools",
            "model": "local",
            "tool_results": [{"tool_name": name, "success": result.get("success"), "result": result}],
        }
