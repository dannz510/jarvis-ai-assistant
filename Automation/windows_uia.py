"""Windows UI Automation helpers grounded on accessible control properties."""


def _desktop():
    try:
        from pywinauto import Desktop
    except ImportError as exc:
        raise RuntimeError(
            "Windows UI Automation is unavailable. Install dependencies from requirements.txt."
        ) from exc
    return Desktop(backend="uia")


def _window_title(window):
    try:
        return str(window.window_text() or "").strip()
    except Exception:
        return ""


def _find_window(title, desktop=None):
    requested = str(title or "").strip()
    if not requested:
        raise ValueError("A window title is required.")
    matches = [
        window for window in (desktop or _desktop()).windows()
        if _window_title(window).casefold() == requested.casefold()
    ]
    if not matches:
        raise LookupError(f"No open window has the exact title '{requested}'.")
    if len(matches) > 1:
        raise LookupError(f"More than one open window has the title '{requested}'.")
    return matches[0]


def list_windows(max_results=50):
    limit = max(1, min(100, int(max_results)))
    items = []
    for window in _desktop().windows():
        title = _window_title(window)
        if not title:
            continue
        try:
            process_id = int(window.element_info.process_id)
        except (AttributeError, TypeError, ValueError):
            process_id = None
        items.append({"title": title[:300], "process_id": process_id})
        if len(items) >= limit:
            break
    return items


def inspect_window(window_title, max_controls=80):
    limit = max(1, min(200, int(max_controls)))
    window = _find_window(window_title)
    controls = []
    for control in window.descendants():
        info = control.element_info
        name = str(getattr(info, "name", "") or "").strip()
        control_type = str(getattr(info, "control_type", "") or "").strip()
        if not name and not control_type:
            continue
        controls.append({
            "name": name[:300],
            "control_type": control_type[:80],
            "automation_id": str(getattr(info, "automation_id", "") or "")[:120],
            "enabled": bool(control.is_enabled()),
            "visible": bool(control.is_visible()),
        })
        if len(controls) >= limit:
            break
    return {"window": _window_title(window), "controls": controls}


def focus_window(window_title):
    window = _find_window(window_title)
    window.set_focus()
    return {"window": _window_title(window), "focused": True}


def _find_control(window, control_name, control_type=None):
    requested = str(control_name or "").strip()
    if not requested:
        raise ValueError("A control name is required.")
    expected_type = str(control_type or "").strip().casefold()
    matches = []
    for control in window.descendants():
        info = control.element_info
        if str(getattr(info, "name", "") or "").strip().casefold() != requested.casefold():
            continue
        actual_type = str(getattr(info, "control_type", "") or "").strip().casefold()
        if expected_type and actual_type != expected_type:
            continue
        matches.append(control)
    if not matches:
        raise LookupError(f"No accessible control named '{requested}' was found in that window.")
    if len(matches) > 1:
        raise LookupError(f"Multiple controls are named '{requested}'. Specify a control type or use a unique name.")
    return matches[0]


def click_control(window_title, control_name, control_type=""):
    window = _find_window(window_title)
    control = _find_control(window, control_name, control_type)
    if not control.is_visible() or not control.is_enabled():
        raise RuntimeError("The selected control is hidden or disabled.")
    window.set_focus()
    control.click_input()
    return {"window": _window_title(window), "control": control_name, "clicked": True}


def set_control_text(window_title, control_name, text):
    value = str(text)
    if len(value) > 20000:
        raise ValueError("Text input is limited to 20,000 characters per action.")
    window = _find_window(window_title)
    control = _find_control(window, control_name, "Edit")
    if not control.is_visible() or not control.is_enabled():
        raise RuntimeError("The selected edit control is hidden or disabled.")
    window.set_focus()
    control.set_edit_text(value)
    actual = str(control.window_text() or "")
    if actual != value:
        raise RuntimeError("The edit control did not retain the requested text.")
    return {"window": _window_title(window), "control": control_name, "characters_written": len(value)}

