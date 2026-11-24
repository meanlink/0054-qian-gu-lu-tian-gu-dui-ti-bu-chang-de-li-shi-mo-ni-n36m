from pathlib import Path

from fastapi import APIRouter
from venues_api import router as venues
from weather_api import router as weather
from scenarios_api import router as scenarios
from settlement_api import router as settlement, ticket_router as tickets
from corrections_api import router as corrections
from replay_job import run_job

router = APIRouter(prefix="/api")
router.include_router(venues)
router.include_router(weather)
router.include_router(scenarios)
router.include_router(settlement)
router.include_router(tickets)
router.include_router(corrections)


def seed(connection):
    connection.execute(Path(__file__).with_name("demo.sql").read_text())
