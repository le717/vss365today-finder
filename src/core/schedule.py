from typing import List

from apscheduler.schedulers.blocking import BlockingScheduler

from src.core import archive, fetch
from src.helpers import api


__all__ = ["main"]


def main():
    scheduler = BlockingScheduler()

    # Get the scheduled times
    schedule_times: List[str] = api.get(
        "settings", "timings", headers=api.create_auth_token()
    )
    for time in schedule_times:
        minute, hour = time.split()

        # Create a job for each time
        scheduler.add_job(
            fetch.main,
            args=[],
            trigger="cron",
            hour=hour,
            minute=minute,
            day_of_week="*",
        )

    # Schedule the word archive generation to
    # run time to be 5 minutes after the last scheduled one
    minute, hour = schedule_times[-1].split()
    minute = str(int(minute) + 5)
    scheduler.add_job(
        archive.main,
        args=[],
        trigger="cron",
        hour=hour,
        minute=minute,
        day_of_week="*",
    )

    # Start the scheduler
    scheduler.start()
