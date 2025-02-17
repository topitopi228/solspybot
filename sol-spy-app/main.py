import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sys import prefix

from sqlalchemy.ext.asyncio import create_async_engine

from api.routers.tracked_wallet_route import tracked_wallet_router
from core.config import settings
from core.db_helper import db_helper
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.dao import db_queries

from api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application started")

    #engine = create_async_engine("postgresql+asyncpg://postgres:1111@localhost:2701/solbot", echo=True)

    #await db_queries.create_tables()
    yield
    # shutdown
    print("dispose engine")
    await db_helper.dispose()


main_app = FastAPI(
    lifespan=lifespan,
)
origins = [

    "http://localhost:3000",  # Локальный фронтенд
    "https://localhost:3000",
]

# Добавляем CORS middleware
main_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Список доменов, которым разрешено отправлять запросы
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP методы (GET, POST и т.д.)
    allow_headers=["*"],  # Разрешаем все заголовки
)

main_app.include_router(api_router, prefix=settings.api.prefix)
main_app.include_router(tracked_wallet_router, prefix=settings.api.prefix)

if __name__ == '__main__':
    uvicorn.run('main:main_app',
                host=settings.run.host,
                port=settings.run.port,
                reload=True,
                )

# asyncio.run(query_methods.create_tables())
