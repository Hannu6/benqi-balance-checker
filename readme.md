# BENQI Wallet Balance Checker

This tool checks specific wallet balances from BENQI core markets using Web3.py.

## Overview

This script connects to the Avalanche C-Chain and queries BENQI smart contracts to retrieve wallet balances for specified addresses.

## Prerequisites

- Python 3.8+
- Web3.py library
- An Avalanche C-Chain RPC endpoint

## Installation

1. Clone this repository
2. (Optional) Create and activate a virtual environment:
   ```
   python -m venv env
   source env/bin/activate  # On Windows, use: env\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Edit the `main.py` file to add your Avalanche RPC endpoint and the wallet addresses you want to check.
2. Run the script:
   ```
   python main.py
   ```

## How it works

When run, the script performs the following steps:

1. Connects to the Avalanche C-Chain using the provided RPC endpoint.
2. Loads the ABI (Application Binary Interface) for BENQI core market contracts.
3. For the wallet address specified in the configuration:
   a. Queries each BENQI core market contract for the wallet's balance.
   b. Retrieves the current exchange rate for the asset.
   c. Calculates the balance in the underlying asset and its USD value.
4. Displays the results, showing wallet balances across different BENQI markets.

## Configuration
Edit `main.py` to customize:

- `RPC_URL`: Your Avalanche C-Chain RPC endpoint
- `WALLET_ADDRESS`: Wallet address to check

## Disclaimer

This tool is for informational purposes only. Always verify important financial information through official channels.

## License

[MIT License](LICENSE)