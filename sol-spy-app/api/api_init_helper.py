from decouple import config
from solana.rpc.api import Client

from api.helius_api import HeliusApi
from api.jupiter_api import JupiterAPI
from api.raydium_api import RaydiumAPI
from api.solana_api import SolanaAPI


class ApiHelper:
    def __init__(self):
        quicknode_endpoint = config("QUICKNODE_ENDPOINT")
        self.solana_client = Client(quicknode_endpoint)
        self.solana_api = SolanaAPI()
        self.raydium_api = RaydiumAPI(rpc_endpoint=quicknode_endpoint)
        self.helius_api=HeliusApi()
        self.jupiter_api=JupiterAPI(quicknode_endpoint)




api_helper = ApiHelper()