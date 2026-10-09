"""Path-scoped file operations for ASTRA's local tool layer."""

import os
import base64
from pathlib import Path
import shutil
import zipfile
import csv
import io
import textwrap


PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}
_TEXT_SUFFIXES = {
    ".txt", ".md", ".py", ".java", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".csv", ".log", ".xml", ".html", ".css", ".js", ".ts", ".sql",
}


def allowed_roots():
    configured = os.environ.get("ASTRA_FILE_ROOTS", "").strip()
    paths = [Path(item.strip()).expanduser() for item in configured.split(";") if item.strip()]
    if not paths:
        paths = [PROJECT_ROOT]
    roots = []
    for path in paths:
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            continue
        if resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def resolve_allowed_path(path, *, must_exist=False):
    """Resolve a user-supplied path safely inside configured ASTRA roots.

    Rejects absolute paths outside roots, symlinks pointing outside roots,
    and any path that resolves outside the configured boundaries.
    """
    candidate = Path(path).expanduser()

    # REJECT absolute paths outside roots immediately
    if candidate.is_absolute():
        roots = allowed_roots()
        if not roots:
            raise PermissionError("No valid ASTRA_FILE_ROOTS are configured.")
        for root in roots:
            try:
                candidate.relative_to(root)
                break
            except ValueError:
                continue
        else:
            raise PermissionError(f"Absolute path outside allowed roots: {candidate}")

    # For relative paths, join with first root then verify
    roots = allowed_roots()
    if not roots:
        raise PermissionError("No valid ASTRA_FILE_ROOTS are configured.")

    candidate = (roots[0] / candidate)

    # Resolve the path, but check for symlink attacks
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError:
        if must_exist:
            raise
        resolved = candidate.resolve(strict=False)

    # Verify resolved path is within allowed roots
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    raise PermissionError(f"Path is outside ASTRA's allowed file roots: {resolved}")


def search_files(query, max_results=30):
    query = str(query).casefold().strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    limit = max(1, min(int(max_results), 100))
    results = []
    for root in allowed_roots():
        for current, dirs, filenames in os.walk(root):
            dirs[:] = [name for name in dirs if name.casefold() not in _SKIP_DIRS and not name.startswith(".")]
            for filename in filenames:
                if query in filename.casefold():
                    results.append(str(Path(current) / filename))
                    if len(results) >= limit:
                        return results
    return results


def read_file(path, max_bytes=1_000_000):
    target = resolve_allowed_path(path, must_exist=True)
    if not target.is_file():
        raise ValueError("The selected path is not a file.")
    size = target.stat().st_size
    if size > int(max_bytes):
        raise ValueError(f"File is {size} bytes; the read limit is {int(max_bytes)} bytes.")
    suffix = target.suffix.casefold()
    if suffix in _TEXT_SUFFIXES:
        return target.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF reading requires the optional pypdf package.") from exc
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(target)).pages)
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX reading requires the optional python-docx package.") from exc
        return "\n".join(paragraph.text for paragraph in Document(str(target)).paragraphs)
    if suffix == ".xlsx":
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("XLSX reading requires the optional openpyxl package.") from exc
        workbook = load_workbook(target, read_only=True, data_only=True)
        return "\n".join(
            f"[{sheet.title}]\n" + "\n".join(", ".join("" if value is None else str(value) for value in row)
                                           for row in sheet.iter_rows(values_only=True))
            for sheet in workbook.worksheets
        )
    if suffix == ".pptx":
        try:
            from pptx import Presentation
        except ImportError as exc:
            raise RuntimeError("PPTX reading requires the optional python-pptx package.") from exc
        presentation = Presentation(str(target))
        return "\n".join(
            shape.text for slide in presentation.slides for shape in slide.shapes if shape.has_text_frame
        )
    raise ValueError(f"Reading {suffix or 'this file type'} is not supported.")


def analyze_image(path, prompt="Describe the image and read visible text."):
    target = resolve_allowed_path(path, must_exist=True)
    if not target.is_file() or target.suffix.casefold() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise ValueError("Choose a supported image file inside ASTRA's configured roots.")
    if target.stat().st_size > 20_000_000:
        raise ValueError("Image is larger than ASTRA's 20 MB limit.")
    from Vision.Vbrain import vision_brain

    encoded = base64.b64encode(target.read_bytes()).decode("ascii")
    return vision_brain(encoded, prompt=prompt)


def create_file(path, content="", confirm_overwrite=False):
    target = resolve_allowed_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not confirm_overwrite:
        raise PermissionError(f"Overwriting requires confirmation: {target}")
    if target.exists() and not target.is_file():
        raise ValueError("The target exists and is not a regular file.")
    suffix = target.suffix.casefold()
    text = str(content)
    if suffix in _TEXT_SUFFIXES:
        target.write_text(text, encoding="utf-8")
    elif suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("DOCX creation requires the optional python-docx package.") from exc
        document = Document()
        for line in text.splitlines() or [""]:
            document.add_paragraph(line)
        document.save(str(target))
    elif suffix == ".xlsx":
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise RuntimeError("XLSX creation requires the optional openpyxl package.") from exc
        workbook = Workbook()
        sheet = workbook.active
        for row_index, row in enumerate(csv.reader(io.StringIO(text)), start=1):
            for column_index, value in enumerate(row, start=1):
                sheet.cell(row=row_index, column=column_index, value=value)
        workbook.save(target)
    elif suffix == ".pptx":
        try:
            from pptx import Presentation
        except ImportError as exc:
            raise RuntimeError("PPTX creation requires the optional python-pptx package.") from exc
        presentation = Presentation()
        slide = presentation.slides.add_slide(presentation.slide_layouts[6])
        box = slide.shapes.add_textbox(0, 0, presentation.slide_width, presentation.slide_height)
        box.text_frame.text = text
        presentation.save(str(target))
    elif suffix == ".pdf":
        try:
            from reportlab.pdfgen import canvas
        except ImportError as exc:
            raise RuntimeError("PDF creation requires the optional reportlab package.") from exc
        buffer = io.BytesIO()
        document = canvas.Canvas(buffer)
        y = 780
        for paragraph in text.splitlines() or [""]:
            for line in textwrap.wrap(paragraph, width=95) or [""]:
                if y < 48:
                    document.showPage()
                    y = 780
                document.drawString(48, y, line)
                y -= 16
        document.save()
        target.write_bytes(buffer.getvalue())
    elif suffix == ".zip":
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if text:
                archive.writestr("README.txt", text)
    else:
        raise ValueError(f"Creating {suffix or 'this file type'} is not supported.")
    return str(target)


def copy_file(source, destination, confirmed=False):
    source_path = resolve_allowed_path(source, must_exist=True)
    target = resolve_allowed_path(destination)
    if target.exists() and not confirmed:
        raise PermissionError(f"Replacing a file requires confirmation: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    return str(target)


def move_file(source, destination, confirmed=False):
    source_path = resolve_allowed_path(source, must_exist=True)
    target = resolve_allowed_path(destination)
    if target.exists() and not confirmed:
        raise PermissionError(f"Replacing a file requires confirmation: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    return str(shutil.move(str(source_path), str(target)))


def rename_file(source, destination, confirmed=False):
    return move_file(source, destination, confirmed=confirmed)


def delete_file(path, confirmed=False):
    target = resolve_allowed_path(path, must_exist=True)
    if not confirmed:
        raise PermissionError(f"Deleting requires confirmation: {target}")
    if target.is_dir():
        raise ValueError("Directory deletion is not supported by this tool.")
    target.unlink()
    return str(target)


def inspect_file(path):
    target = resolve_allowed_path(path, must_exist=True)
    stat = target.stat()
    return {
        "path": str(target),
        "name": target.name,
        "suffix": target.suffix.casefold(),
        "size_bytes": stat.st_size,
        "modified_at": stat.st_mtime,
        "is_file": target.is_file(),
        "is_directory": target.is_dir(),
    }


def extract_zip(path, destination, confirmed=False):
    """Safely extract a ZIP archive, validating each member path individually."""
    archive = resolve_allowed_path(path, must_exist=True)
    target_root = resolve_allowed_path(destination)
    if target_root.exists() and any(target_root.iterdir()) and not confirmed:
        raise PermissionError(f"Extracting into a non-empty directory requires confirmation: {target_root}")
    target_root.mkdir(parents=True, exist_ok=True)

    extracted = []
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        for member in members:
            # Resolve member path and verify it stays within target_root
            member_target = (target_root / member.filename).resolve()
            try:
                member_target.relative_to(target_root.resolve())
            except ValueError as exc:
                raise PermissionError(f"Unsafe archive member path: {member.filename}") from exc

            # Extract each member individually after validation (prevents TOCTOU)
            if member.is_dir():
                member_target.mkdir(parents=True, exist_ok=True)
            else:
                member_target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(member) as source, open(member_target, "wb") as dest:
                    shutil.copyfileobj(source, dest)
            extracted.append(str(member_target))

    return extracted
