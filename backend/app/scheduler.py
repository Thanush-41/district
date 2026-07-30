from datetime import datetime, timezone

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:  # pragma: no cover - optional dependency fallback
    BackgroundScheduler = None

from app.config import settings

scheduler = None


def _run_daily_pipeline():
    """Runs once a day: refresh Google Places data, recompute lead scores,
    and report how many restaurants are due for a District/Meta/Swiggy check.

    District/Meta Ads/Swiggy verification itself stays manual (via
    /check-district, /sync-meta, /sync-swiggy) since it requires scraping
    live third-party sites that this project does not have verified
    selectors or credentials for.
    """
    from app.collectors.google_places import run_google_discovery
    from app.database.mongo import get_restaurants_db
    from app.scoring.lead_score import calculate_scores
    from app.services import district_due_for_check, meta_due_for_check, swiggy_due_for_check

    print(f"[scheduler] daily pipeline starting at {datetime.now(timezone.utc).isoformat()}Z")

    if settings.google_maps_api_key:
        try:
            result = run_google_discovery()
            print(f"[scheduler] google discovery result: {result}")
        except Exception as exc:  # keep the pipeline alive even if Google fails
            print(f"[scheduler] google discovery failed: {exc}")
    else:
        print("[scheduler] GOOGLE_MAPS_API_KEY not set, skipping Google discovery")

    calculate_scores()

    restaurants = list(get_restaurants_db().values())
    due_district = sum(1 for r in restaurants if district_due_for_check(r, settings.district_recheck_days))
    due_meta = sum(1 for r in restaurants if meta_due_for_check(r, settings.meta_recheck_days))
    due_swiggy = sum(1 for r in restaurants if swiggy_due_for_check(r, settings.swiggy_recheck_days))
    print(f"[scheduler] due for check -> district: {due_district}, meta: {due_meta}, swiggy: {due_swiggy}")


def start_scheduler(app):
    global scheduler
    if BackgroundScheduler is None:
        return
    if scheduler is not None:
        return
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _run_daily_pipeline,
        "cron",
        hour=settings.scheduler_hour_utc,
        minute=0,
        id="district-daily-pipeline",
    )
    scheduler.start()


def shutdown_scheduler():
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
