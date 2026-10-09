"""Native Word, Excel, and PowerPoint workflows through Windows COM."""

from contextlib import contextmanager
from pathlib import Path
import re

from Features.file_agent import resolve_allowed_path


_MAX_ROWS = 10000
_MAX_COLUMNS = 100
_MAX_CELL_CHARS = 10000
_SHEET_NAME_BAD = re.compile(r"[\\/*?:\[\]]")


@contextmanager
def _com_apartment():
    try:
        import pythoncom
    except ImportError as exc:
        raise RuntimeError("Office automation requires pywin32 from requirements.txt.") from exc
    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _dispatch(program_id):
    try:
        from win32com.client import DispatchEx
    except ImportError as exc:
        raise RuntimeError("Office automation requires pywin32 from requirements.txt.") from exc
    return DispatchEx(program_id)


def _target_path(path, suffix, confirm_overwrite=False):
    target = resolve_allowed_path(path)
    if target.suffix.casefold() != suffix:
        raise ValueError(f"Choose a {suffix} file path.")
    if target.exists() and not confirm_overwrite:
        raise PermissionError(f"Replacing a file requires confirmation: {target}")
    if target.exists() and not target.is_file():
        raise ValueError("The target exists and is not a regular file.")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _verify_saved(target):
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(f"Office did not create a verifiable file at {target}.")
    return {"path": str(target), "verified": True, "size_bytes": target.stat().st_size}


def _safe_cell(value):
    if value is None or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    if len(text) > _MAX_CELL_CHARS:
        raise ValueError(f"A spreadsheet cell exceeds {_MAX_CELL_CHARS} characters.")
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _validated_rows(rows):
    if not isinstance(rows, (list, tuple)) or not rows:
        raise ValueError("Provide a non-empty list of spreadsheet rows.")
    if len(rows) > _MAX_ROWS:
        raise ValueError(f"A workbook is limited to {_MAX_ROWS} rows per create action.")
    normalized = []
    width = None
    for row in rows:
        if not isinstance(row, (list, tuple)) or not row:
            raise ValueError("Each spreadsheet row must be a non-empty list.")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise ValueError("Spreadsheet rows must have the same number of columns.")
        if width > _MAX_COLUMNS:
            raise ValueError(f"A workbook is limited to {_MAX_COLUMNS} columns per create action.")
        normalized.append(tuple(_safe_cell(value) for value in row))
    return tuple(normalized), len(normalized), width


def _safe_sheet_name(name):
    value = str(name or "Sheet1").strip() or "Sheet1"
    if len(value) > 31 or _SHEET_NAME_BAD.search(value):
        raise ValueError("Excel sheet names must be at most 31 characters and cannot contain \\ / * ? : [ ].")
    return value


def create_word_document(path, title, content="", confirm_overwrite=False):
    target = _target_path(path, ".docx", confirm_overwrite)
    title = str(title or "").strip()
    body = str(content or "")
    if len(title) > _MAX_CELL_CHARS or len(body) > 100000:
        raise ValueError("Word title/content exceeds ASTRA's document creation limit.")
    with _com_apartment():
        app = _dispatch("Word.Application")
        document = None
        saved = False
        try:
            app.Visible = True
            app.DisplayAlerts = 0
            document = app.Documents.Add()
            selection = app.Selection
            if title:
                selection.Style = "Title"
                selection.TypeText(title)
                selection.TypeParagraph()
                selection.TypeParagraph()
            selection.Style = "Normal"
            for paragraph in body.splitlines() or ([""] if not title else []):
                selection.TypeText(paragraph)
                selection.TypeParagraph()
            document.SaveAs2(str(target), FileFormat=16)
            saved = True
            result = _verify_saved(target)
            return {**result, "application": "Microsoft Word", "window_open": True}
        finally:
            if not saved:
                try:
                    if document is not None:
                        document.Close(SaveChanges=0)
                except Exception:
                    pass
                try:
                    app.Quit()
                except Exception:
                    pass


def append_word_text(path, content, confirmed=False):
    target = resolve_allowed_path(path, must_exist=True)
    if target.suffix.casefold() != ".docx" or not target.is_file():
        raise ValueError("Choose an existing DOCX file inside ASTRA's allowed roots.")
    if not confirmed:
        raise PermissionError(f"Editing a document requires confirmation: {target}")
    text = str(content)
    if not text or len(text) > 100000:
        raise ValueError("Provide non-empty text under 100,000 characters.")
    with _com_apartment():
        app = _dispatch("Word.Application")
        document = None
        try:
            app.Visible = True
            app.DisplayAlerts = 0
            document = app.Documents.Open(str(target), ReadOnly=False, AddToRecentFiles=False)
            selection = app.Selection
            selection.EndKey(Unit=6)
            selection.TypeParagraph()
            for paragraph in text.splitlines():
                selection.TypeText(paragraph)
                selection.TypeParagraph()
            document.Save()
            result = _verify_saved(target)
            return {**result, "application": "Microsoft Word", "window_open": True}
        finally:
            # Leave the document open for the user to inspect and continue editing.
            document = None


def create_excel_workbook(path, rows, sheet_name="Data", chart_title="", confirm_overwrite=False):
    target = _target_path(path, ".xlsx", confirm_overwrite)
    values, row_count, column_count = _validated_rows(rows)
    sheet_name = _safe_sheet_name(sheet_name)
    with _com_apartment():
        app = _dispatch("Excel.Application")
        workbook = None
        saved = False
        try:
            app.Visible = True
            app.DisplayAlerts = False
            workbook = app.Workbooks.Add()
            sheet = workbook.Worksheets(1)
            sheet.Name = sheet_name
            target_range = sheet.Range(sheet.Cells(1, 1), sheet.Cells(row_count, column_count))
            target_range.Value = values
            sheet.Rows(1).Font.Bold = True
            sheet.Columns.AutoFit()
            if chart_title:
                _add_chart_sheet(workbook, sheet, row_count, column_count, chart_title)
            workbook.SaveAs(str(target), FileFormat=51)
            saved = True
            result = _verify_saved(target)
            return {**result, "application": "Microsoft Excel", "window_open": True,
                    "rows": row_count, "columns": column_count,
                    "chart_created": bool(chart_title)}
        finally:
            if not saved:
                try:
                    if workbook is not None:
                        workbook.Close(SaveChanges=False)
                except Exception:
                    pass
                try:
                    app.Quit()
                except Exception:
                    pass


def _add_chart_sheet(workbook, source_sheet, row_count, column_count, title):
    chart_sheet = workbook.Worksheets.Add(After=workbook.Worksheets(workbook.Worksheets.Count))
    base = "ASTRA Chart"
    candidate = base
    suffix = 2
    existing = {str(workbook.Worksheets(index).Name).casefold()
                for index in range(1, workbook.Worksheets.Count + 1)}
    while candidate.casefold() in existing:
        candidate = f"{base} {suffix}"
        suffix += 1
    chart_sheet.Name = candidate
    chart_object = chart_sheet.ChartObjects().Add(Left=20, Top=20, Width=640, Height=360)
    chart = chart_object.Chart
    chart.SetSourceData(source_sheet.Range(
        source_sheet.Cells(1, 1), source_sheet.Cells(row_count, column_count)
    ))
    chart.ChartType = 51  # xlColumnClustered
    chart.HasTitle = True
    chart.ChartTitle.Text = str(title)[:200]


def add_excel_chart(path, sheet_name="", chart_title="ASTRA Chart", confirmed=False):
    target = resolve_allowed_path(path, must_exist=True)
    if target.suffix.casefold() != ".xlsx" or not target.is_file():
        raise ValueError("Choose an existing XLSX file inside ASTRA's allowed roots.")
    if not confirmed:
        raise PermissionError(f"Adding a chart modifies the workbook and requires confirmation: {target}")
    title = str(chart_title or "ASTRA Chart")
    with _com_apartment():
        app = _dispatch("Excel.Application")
        workbook = None
        try:
            app.Visible = True
            app.DisplayAlerts = False
            workbook = app.Workbooks.Open(str(target), ReadOnly=False, UpdateLinks=0, AddToMru=False)
            source = workbook.Worksheets(_safe_sheet_name(sheet_name)) if sheet_name else workbook.Worksheets(1)
            used = source.UsedRange
            rows = int(used.Rows.Count)
            columns = int(used.Columns.Count)
            if rows < 2 or columns < 1:
                raise ValueError("The selected worksheet needs a header row and at least one data row.")
            _add_chart_sheet(workbook, source, rows, columns, title)
            workbook.Save()
            result = _verify_saved(target)
            return {**result, "application": "Microsoft Excel", "window_open": True,
                    "chart_created": True, "source_sheet": source.Name}
        finally:
            # Leave the workbook open for the user to inspect the new chart sheet.
            workbook = None


def create_powerpoint_presentation(path, title, content="", confirm_overwrite=False):
    target = _target_path(path, ".pptx", confirm_overwrite)
    title = str(title or "").strip()
    body = str(content or "")
    if not title or len(title) > 500 or len(body) > 100000:
        raise ValueError("Provide a title and content under ASTRA's presentation limits.")
    with _com_apartment():
        app = _dispatch("PowerPoint.Application")
        presentation = None
        saved = False
        try:
            app.Visible = True
            presentation = app.Presentations.Add()
            slide = presentation.Slides.Add(1, 2)  # ppLayoutText
            slide.Shapes.Placeholders(1).TextFrame.TextRange.Text = title
            slide.Shapes.Placeholders(2).TextFrame.TextRange.Text = body
            presentation.SaveAs(str(target), 24)  # ppSaveAsOpenXMLPresentation
            saved = True
            result = _verify_saved(target)
            return {**result, "application": "Microsoft PowerPoint", "window_open": True}
        finally:
            if not saved:
                try:
                    if presentation is not None:
                        presentation.Close()
                except Exception:
                    pass
                try:
                    app.Quit()
                except Exception:
                    pass

