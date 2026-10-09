import schedule
import time
import threading
from pathlib import Path
from Brain.logger import logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def check_schedule():
    """Check schedule.txt for due tasks."""
    schedule_file = PROJECT_ROOT / "schedule.txt"
    if not schedule_file.exists():
        return
    
    current_time = time.strftime("%H:%M%p").upper()
    try:
        with open(schedule_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if line.startswith(current_time):
                task = line.split("=", 1)[1].strip() if "=" in line else line
                logger.info(f"Schedule due: {task}")
                # Could trigger notification here
    except Exception as e:
        logger.error(f"Error checking schedule: {e}")

def check_Alam():
    """Check Alam_data.txt for due alarms."""
    alam_file = PROJECT_ROOT / "Alam_data.txt"
    if not alam_file.exists():
        return
    
    current_time = time.strftime("%H:%M%p").upper()
    try:
        with open(alam_file, 'r') as f:
            alarm_time = f.read().strip().upper()
        
        if alarm_time == current_time:
            logger.info("Alarm triggered!")
            # Could trigger alarm sound here
            return True
    except Exception as e:
        logger.error(f"Error checking alarm: {e}")
    
    return False

def start_schedule_checker(interval_seconds=30):
    """Start background thread to check schedule and alarms."""
    def run_checker():
        while True:
            check_schedule()
            check_Alam()
            time.sleep(interval_seconds)
    
    thread = threading.Thread(target=run_checker, daemon=True)
    thread.start()
    return thread