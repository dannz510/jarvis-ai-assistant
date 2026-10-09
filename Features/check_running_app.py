"""Check running applications on Windows."""

import psutil


def check_running_app() -> str:
    """Return a summary of top CPU/memory processes."""
    try:
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                if info['cpu_percent'] and info['cpu_percent'] > 0.5:
                    procs.append(f"{info['name']} (PID {info['pid']}) CPU {info['cpu_percent']:.1f}% MEM {info['memory_percent']:.1f}%")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        procs.sort(key=lambda x: float(x.split('CPU ')[1].split('%')[0]) if 'CPU ' in x else 0, reverse=True)
        if procs:
            return "Top processes:\n" + "\n".join(procs[:15])
        return "No significant CPU processes."
    except Exception as e:
        return f"Process check failed: {e}"