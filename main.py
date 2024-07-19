from web3 import Web3
import json
import re

# Avalanche RPC node
RPC_URL = "https://api.avax.network/ext/bc/C/rpc"

# Wallet address to check
WALLET_ADDRESS = "0x123123123"

# Unitroller address
UNITROLLER_ADDRESS = "0x486Af39519B4Dc9a7fCcd318217352830E8AD9b4"

# Add Oracle address
ORACLE_ADDRESS = "0x316aE55EC59e0bEb2121C0e41d4BDef8bF66b32B"

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABIs
with open('Unitroller.abi.json') as f:
    unitroller_abi = json.load(f)

with open('qiTokenABI.json') as f:
    qi_token_abi = json.load(f)

erc20_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [
            {
                "name": "",
                "type": "uint8"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

# Oracle ABI (only the necessary part)
oracle_abi = [
    {
        "constant": True,
        "inputs": [
            {
                "internalType": "contract QiToken",
                "name": "qiToken",
                "type": "address"
            }
        ],
        "name": "getUnderlyingPrice",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

# Initialize Unitroller contract
unitroller_contract = w3.eth.contract(address=UNITROLLER_ADDRESS, abi=unitroller_abi)

# Initialize Oracle contract
oracle_contract = w3.eth.contract(address=ORACLE_ADDRESS, abi=oracle_abi)

def is_valid_ethereum_address(address):
    # Check if the address is a valid Ethereum address
    # It should be 42 characters long, start with '0x', and contain only hexadecimal characters
    pattern = re.compile(r'^0x[a-fA-F0-9]{40}$')
    return bool(pattern.match(address))

def get_assets_in(address):
    try:
        assets = unitroller_contract.functions.getAssetsIn(address).call()
        print(f"Assets for {address}:")
        for asset in assets:
            print(f"- {asset}")
        return assets
    except Exception as e:
        return []

def get_account_snapshot(address, qi_token_address):
    try:
        qi_token_contract = w3.eth.contract(address=qi_token_address, abi=qi_token_abi)
        error_code, token_balance, borrow_balance, exchange_rate = qi_token_contract.functions.getAccountSnapshot(address).call()
        exchange_rate_stored = qi_token_contract.functions.exchangeRateStored().call()
        return error_code, token_balance, borrow_balance, exchange_rate, exchange_rate_stored
    except Exception as e:
        print(f"Error getting account snapshot for {qi_token_address}: {e}")
        return None, 0, 0, 0, 0

def calculate_token_balance(qi_token_balance, exchange_rate_stored, qi_token_decimals, underlying_decimals):
    token_balance = (qi_token_balance * exchange_rate_stored) / (10 ** (qi_token_decimals + 28))
    return token_balance

def get_collateral_factor(qi_token_address):
    try:
        market_data = unitroller_contract.functions.markets(qi_token_address).call()
        return market_data[1]  # collateral factor is the second item in the tuple
    except Exception as e:
        print(f"Error getting collateral factor for {qi_token_address}: {e}")
        return 0

def get_token_info(token_address):
    try:
        token_contract = w3.eth.contract(address=token_address, abi=qi_token_abi)
        decimals = token_contract.functions.decimals().call()
        name = token_contract.functions.name().call()
        symbol = token_contract.functions.symbol().call()
        
        try:
            underlying = token_contract.functions.underlying().call()
            underlying_contract = w3.eth.contract(address=underlying, abi=erc20_abi)
            underlying_decimals = underlying_contract.functions.decimals().call()
        except Exception as e:
            #print(f"No underlying token for {token_address}, assuming it's the native token")
            underlying = token_address
            underlying_decimals = decimals
        
        return {
            "qiToken": token_address,
            "decimals": decimals,
            "name": name,
            "symbol": symbol,
            "underlying": underlying,
            "underlying_decimals": underlying_decimals
        }
    except Exception as e:
        return None

def generate_assets_dict(address):
    assets = get_assets_in(address)
    assets_dict = {}
    
    for asset in assets:
        token_info = get_token_info(asset)
        if token_info:
            assets_dict[token_info['symbol']] = token_info
    
    return assets_dict

def get_token_price(qi_token_address):
    try:
        price = oracle_contract.functions.getUnderlyingPrice(qi_token_address).call()
        
        # Adjust the price based on whether the token is a stablecoin, can't remember how this was supposed to be deducted dynamically so this is quick stab to make it work
        if qi_token_address in ["0xB715808a78F6041E46d61Cb123C9B4A27056AE9C", "0xd8fcDa6ec4Bdc547C0827B8804e89aCd817d56EF"]:
            # Stablecoin with 30 decimals
            adjusted_price = price / 1e30
        else:
            # Token with 18 decimals
            adjusted_price = price / 1e18
        
        return adjusted_price
    except Exception as e:
        print(f"Error getting token price for {qi_token_address}: {e}")
        return 0

def calculate_health_factor(address):
    ASSETS = generate_assets_dict(address)
    
    total_collateral_value = 0
    total_borrowed_value = 0
    
    for symbol, asset_data in ASSETS.items():
        error_code, qi_token_balance, borrow_balance, exchange_rate, exchange_rate_stored = get_account_snapshot(address, asset_data['qiToken'])
        if error_code is None:
            continue
        
        collateral_factor = get_collateral_factor(asset_data['qiToken'])
        underlying_decimals = asset_data['underlying_decimals']
        qi_token_decimals = asset_data['decimals']

        token_balance = calculate_token_balance(qi_token_balance, exchange_rate_stored, qi_token_decimals, underlying_decimals)
        
        token_price = get_token_price(asset_data['qiToken'])
        
        collateral_value = token_balance * token_price
        borrow_balance = borrow_balance / (10 ** underlying_decimals)
        borrow_value = borrow_balance * token_price
        
        total_collateral_value += collateral_value * (collateral_factor / 1e18)
        total_borrowed_value += borrow_value
        
        print(f"\nAsset: {asset_data['qiToken']} ({symbol})")
        print(f"qiToken Balance: {qi_token_balance / (10 ** qi_token_decimals):.8f}")
        print(f"Token Balance: {token_balance:.8f}")
        print(f"Token Price: ${token_price:.6f}")
        print(f"Collateral Value: ${collateral_value:.4f}")
        print(f"Borrow Balance: {borrow_balance:.8f}")
        print(f"Borrow Value: ${borrow_value:.4f}")
        print(f"Collateral Factor: {collateral_factor / 1e18:.2f}")
    
    if total_borrowed_value == 0:
        health_factor = float('inf')
    else:
        health_factor = total_collateral_value / total_borrowed_value
    
    return health_factor, total_collateral_value, total_borrowed_value

def main():
    print(f"Checking wallet health for: {WALLET_ADDRESS}")
    print(f"Is connected to Avalanche: {w3.is_connected()}")
    print(f"Wallet balance: {w3.eth.get_balance(WALLET_ADDRESS) / 1e18:.4f} AVAX")

    health_factor, total_collateral_value, total_borrowed_value = calculate_health_factor(WALLET_ADDRESS)
    print(f"\nHealth Factor: {health_factor:.2f}")
    print(f"Total Collateral Value: ${total_collateral_value:.4f}")
    print(f"Total Borrowed Value: ${total_borrowed_value:.4f}")
    print(f"Liquidation Threshold: {(1 / health_factor * 100):.2f}%")

if __name__ == "__main__":
    if not WALLET_ADDRESS or not is_valid_ethereum_address(WALLET_ADDRESS):
        print("Error: Wallet address is missing or invalid. Please fill in a valid address for the WALLET_ADDRESS variable in main.py.")
    else:
        main()