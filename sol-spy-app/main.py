import logging

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from api.helius_api import HeliusApi
from api.jupiter_api import JupiterAPI
from api.routers import bot_wallet_route
from api.routers import tracked_wallet_route
from api.routers import copy_traiding_route
from api.routers import tracked_statistics_route
from api.routers import user_route
from core.config import settings
from core.db_helper import db_helper
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as api_router
from core.service.tracked_statistics_service import TrackedStatisticsService
from core.service.worker_service import WorkerService
from api.api_init_helper import api_helper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
worker_service = WorkerService(scheduler)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application started")
    worker_service.setup_jobs()
    await worker_service.start()
    input_mint="So11111111111111111111111111111111111111112"
    output_mint="Exms4qnKb7GtnPXom1Z4fWn1MnyX46jkcmAy3RWxpump"
    hh= await api_helper.jupiter_api.get_swap_quote_for_buy(input_mint,output_mint,5)
    input_mint1 = "Exms4qnKb7GtnPXom1Z4fWn1MnyX46jkcmAy3RWxpump"
    output_mint1 = "So11111111111111111111111111111111111111112"
    hh = await api_helper.jupiter_api.get_swap_quote_for_sell(input_mint, output_mint, 552352531)

    print(hh)


    yield
    # shutdown
    print("dispose engine")
    await db_helper.dispose()


main_app = FastAPI(
    lifespan=lifespan,
)
origins = [

    "http://localhost:3000",
    "https://localhost:3000",
]

# Добавляем CORS middleware
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

main_app.include_router(api_router, prefix=settings.api.prefix)
main_app.include_router(tracked_wallet_route.router, prefix=settings.api.prefix)

main_app.include_router(copy_traiding_route.router, prefix=settings.api.prefix)

main_app.include_router(user_route.router, prefix=settings.api.prefix)
main_app.include_router(bot_wallet_route.router, prefix=settings.api.prefix)

main_app.include_router(tracked_statistics_route.router, prefix=settings.api.prefix)

if __name__ == '__main__':
    uvicorn.run('main:main_app',
                host=settings.run.host,
                port=settings.run.port,
                reload=True,
                )
