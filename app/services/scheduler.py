import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    定时任务调度服务 (Singleton)
    """
    _instance = None
    _scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SchedulerService, cls).__new__(cls)
            cls._scheduler = AsyncIOScheduler()
        return cls._instance

    def start(self):
        """启动调度器并添加任务"""
        if not self._scheduler.running:
            self._setup_jobs()
            self._scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        """停止调度器"""
        if self._scheduler.running:
            self._scheduler.shutdown()
            logger.info("Scheduler stopped")

    def _setup_jobs(self):
        """配置定时任务"""
        # 任务 1: 每晚 03:00 全量同步 (UTC 时间，对应北京时间 11:00，或者调整为北京时间 03:00)
        # 为避免服务器时区依赖，我们这里显式指定 UTC，或者依赖 tzlocal 但确保容器有时区
        # 稳健做法：指定 timezone，例如 'Asia/Shanghai'
        # 需要确保 apscheduler 能识别字符串时区，这通常需要 pytz 或 zoneinfo
        # Python 3.9+ 自带 zoneinfo
        from apscheduler.triggers.cron import CronTrigger
        
        # 尝试使用 Asia/Shanghai，如果环境缺失可能会报错，稳妥起见我们先用 UTC
        # 北京时间 03:00 = UTC 19:00 (前一天)
        # 既然用户想要每晚 3 点，我们假设是 Beijing Time
        
        try:
             import pytz
             tz = pytz.timezone('Asia/Shanghai')
        except ImportError:
             # Fallback to UTC if pytz missing (though we should have it via dependencies)
             from datetime import timezone, timedelta
             tz = timezone(timedelta(hours=8))

        self._scheduler.add_job(
            self._run_nightly_sync,
            trigger=CronTrigger(hour=3, minute=0, timezone=tz),
            id="nightly_sync",
            replace_existing=True
        )
        logger.info("Job 'nightly_sync' scheduled for 03:00 AM daily")

    async def _run_nightly_sync(self):
        """执行全量同步任务"""
        logger.info(">>> Starting Nightly Auto-Sync Task <<<")
        service = SyncService()
        try:
            await service.sync_all()
        except Exception as e:
            logger.error(f"Nightly sync failed: {e}", exc_info=True)
        finally:
            await service.client.close()
