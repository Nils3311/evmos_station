import json

import requests
from web3 import Web3

# TODO checken ob das auch benötigt wird??


# rpc = 'https://evmos-testnet.gateway.pokt.network/v1/lb/61ac07b995d548003aedf5ee'
# rpc = 'https://ethereum.rpc.evmos.dev/'
# rpc = 'https://evmos-rpc.mercury-nodes.net:443/'
# rpc = 'https://evmos-evm-rpc.tk:443/'
# rpc = 'https://evmos-rpc.mercury-nodes.net/'
# rpc = 'https://evmos-eth.mercury-nodes.net/'

evmos1 = 'https://grpc.bd.evmos.org:9090'
evmos2 = 'https://rest.bd.evmos.org:1317'
evmos3 = 'https://tendermint.bd.evmos.org:26657'
evmos4 = 'https://eth.bd.evmos.org:8545'

rpc = evmos4


# WEB3_ENDPOINT="https://evmos-testnet.gateway.pokt.network/v1/lb/61afa495a6f4fb0039968571"
# WEB3_ENDPOINT = 'https://evmos-evm-rpc.tk/'
WEB3_ENDPOINT = evmos1
w3 = Web3(Web3.HTTPProvider(WEB3_ENDPOINT))

# TODO How to handle if RPC is not answering
def hex_to_int(BIGINT):
    return int(BIGINT, 16)


def int_to_hex(hex_string):
    return hex(hex_string)


def eth_currentblock_number():
    payload = {
        "method": "eth_blockNumber",
        "params": [],
        "jsonrpc": "2.0",
        "id": 1,
    }
    response = requests.post(rpc, json=payload).json()['result']
    return int(response, 16)


def eth_getblock_data(blockheight='latest'):
    if blockheight != "latest":
        blockheight = int_to_hex(blockheight)
    payload = {
        "method": "eth_getBlockByNumber",
        "params": [blockheight, True],
        "jsonrpc": "2.0",
        "id": 1,
    }
    return requests.post(rpc, json=payload).json()['result']


def cosm_gettransaction_count():
    data = requests.get(evmos2 + '/cosmos/base/tendermint/v1beta1/blocks/latest').json()
    return len(data['block']['data']['txs'])


# Schnittstelle zum Vertrag
def create_abi(contract_address: str, contract='/erc20.json'):
    w3 = Web3(Web3.HTTPProvider(WEB3_ENDPOINT))
    with open("erc20/erc20.json") as f:
        abi = json.load(f)
    contract = w3.eth.contract(
        address=Web3.toChecksumAddress(contract_address), abi=abi)
    return contract


def transfer_ERC20(
        contract_address: str,
        private_key: str,
        dest: str,
        amount: int,
        owner: str,
        nonce: int,
        gas: int = 2100000000000,
        gasPrice: int = 27,
) -> str:
    if nonce is None: w3.eth.get_transaction_count(owner)
    contract = create_abi(contract_address)
    contract_tx = contract.functions.transfer(
        Web3.toChecksumAddress(dest), amount).buildTransaction({
        'from': Web3.toChecksumAddress(owner),
        'gas': gas,
        'gasPrice': gasPrice,
        'nonce': nonce
    })
    signed_tx = w3.eth.account.sign_transaction(contract_tx, private_key)
    txn_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    return w3.toHex(txn_hash)
