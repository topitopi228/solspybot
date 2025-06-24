from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.db_helper import db_helper
from core.models.tracked_statistics import TrackedStatistics
from core.service.tracked_statistics_service import TrackedStatisticsService


class WorkerService:
    def __init__(self, scheduler: AsyncIOScheduler):
        self.scheduler = scheduler
        self.tracked_statistics = TrackedStatisticsService(db_helper.session_factory)

    def setup_jobs(self):
        self.scheduler.add_job(
            self.tracked_statistics.create_statistics_for_all_wallets,
            trigger=IntervalTrigger(hours=1, timezone="UTC"),
            id="check_expired_subscriptions_job",
            replace_existing=True
        )

    async def start(self):

        self.scheduler.start()

    async def shutdown(self):

        self.scheduler.shutdown()
