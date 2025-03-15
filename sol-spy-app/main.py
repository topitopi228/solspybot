import uvicorn
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from sys import prefix

from sqlalchemy.ext.asyncio import create_async_engine

from api.bitquery_api import BitqueryAPI
from api.routers.tracked_wallet_route import tracked_wallet_router
from api.helius_api import HeliusApi
from core.config import settings
from core.db_helper import db_helper
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.dao import db_queries
from core.service.tracked_wallet_service import WalletService

from api import router as api_router
from api.solana_api import SolanaAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application started")
    # engine = create_async_engine("postgresql+asyncpg://postgres:1111@localhost:2701/solbot", echo=True)
    #await db_queries.create_tables()
    #bitquery = BitqueryAPI()
    #wtoken= await bitquery.fetch_token_data("GHPCChGqtKf4sFaN1wPPCapcweKXBBngB3hF7D6nT29e","G36dYPnfDaYTNsEX7XJnUa6i15Nyn9apMzj2skkppump")
    #wtoken= await bitquery.update_tokens_data("GHPCChGqtKf4sFaN1wPPCapcweKXBBngB3hF7D6nT29e")
    solscan=HeliusApi()
    tokens= await  solscan.get_token_balance("HFqx9e6QmY6EewAEawCdbkuPFHXUNus9B2KBd8MPb2Jx","GSHhPz2AVL5efwV9PVxR1SxDdLU5So2PT641W7QRpump")
    print(tokens)
    #print(wtoken)
    #solana = SolanaAPI()
    #info_tran= await solana.get_transaction_details("LZHKNam1oaFYHQanYRcCUfusPSdrj4Sa2K9PR7eTWoAMyxziKkb9ctdUGT1rJekUnY8BwQ8XbUQk9ubyrGtxuiC")
    #info_tran= await solana.get_wallet_transactions("GHPCChGqtKf4sFaN1wPPCapcweKXBBngB3hF7D6nT29e")
    #print(info_tran)
    #service=WalletService()
    #trans=service.update_wallet_data("GHPCChGqtKf4sFaN1wPPCapcweKXBBngB3hF7D6nT29e")
    #type =await bitquery.get_transaction_info(
    #    "4va8WUXwGBUvzHoUXCaDVVzdS9HV7xHvjP9oiVnRMNc4myvetC9StAYLcu7puV7XQB64EvKwDyfxzmaM63Vrwb6Y")
    #price=await  bitquery.get_token_price_in_sol("G5HjbQ7WCfvNKMv1LAz8puDifHTYaQefUHRvMZYfJgay")
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
