import requests
import json

#rpc = 'https://evmos-testnet.gateway.pokt.network/v1/lb/61ac07b995d548003aedf5ee'
rpc = 'https://ethereum.rpc.evmos.dev/'
#rpc = 'https://evmos-evm-rpc.tk/'
#rpc = 'https://evmos-rpc.mercury-nodes.net/'

#TODO How to handle if RPC is not anawering

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



