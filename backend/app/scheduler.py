from datetime import datetime

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - optional dependency fallback
    BackgroundScheduler = None

scheduler = None


def _tick():
    print(f"[scheduler] verification queue refreshed at {datetime.utcnow().isoformat()}Z")


def start_scheduler(app):
    global scheduler
    if BackgroundScheduler is None:
        return
    if scheduler is not None:
        return
    scheduler = BackgroundScheduler()
    scheduler.add_job(_tick, "interval", minutes=5, id="district-refresh")
    scheduler.start()


def shutdown_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
