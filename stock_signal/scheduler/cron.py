import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from data.poller import run_poller
from ml.train import train_all

logger = logging.getLogger(__name__)


def nightly_training():
    logger.info("Starting nightly model training")
    train_all()
    logger.info("Nightly training complete")


def start_scheduler():
    scheduler = BlockingScheduler(timezone="America/New_York")

    scheduler.add_job(
        nightly_training,
        CronTrigger(hour=23, minute=0, day_of_week="mon-fri"),
        id="nightly_trainer",
        name="Nightly XGBoost Training",
        misfire_grace_time=3600,
    )

    logger.info("Scheduler started — nightly training at 23:00 ET Mon-Fri")
    scheduler.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_scheduler()
