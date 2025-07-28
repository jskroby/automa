#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple deployment script for Automa smart contracts."""

import json
import os
from web3 import Web3
from solcx import compile_files, install_solc

CONTRACTS = [
    "contracts/EntropyNFT.sol",
    "contracts/ElasticUSD.sol",
    "contracts/LLMDemocracyOracle.sol",
]


def main() -> None:
    rpc = os.environ.get("RPC_URL")
    if not rpc:
        raise SystemExit("RPC_URL environment variable is not set")
    install_solc("0.8.25")
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise SystemExit("Web3 provider is not connected")
    w3.eth.default_account = w3.eth.accounts[0]

    compiled = compile_files(CONTRACTS, output_values=["abi", "bin"])

    entropy_iface = compiled['contracts/EntropyNFT.sol:EntropyNFT']
    EntropyNFT = w3.eth.contract(abi=entropy_iface['abi'], bytecode=entropy_iface['bin'])
    receipt = w3.eth.wait_for_transaction_receipt(EntropyNFT.constructor().transact())
    entropy_addr = receipt.contractAddress

    oracle_iface = compiled['contracts/LLMDemocracyOracle.sol:LLMDemocracyOracle']
    Oracle = w3.eth.contract(abi=oracle_iface['abi'], bytecode=oracle_iface['bin'])
    receipt = w3.eth.wait_for_transaction_receipt(Oracle.constructor().transact())
    oracle_addr = receipt.contractAddress

    eusd_iface = compiled['contracts/ElasticUSD.sol:ElasticUSD']
    ElasticUSD = w3.eth.contract(abi=eusd_iface['abi'], bytecode=eusd_iface['bin'])
    receipt = w3.eth.wait_for_transaction_receipt(ElasticUSD.constructor(oracle_addr).transact())
    eusd_addr = receipt.contractAddress

    oracle = w3.eth.contract(address=oracle_addr, abi=oracle_iface['abi'])
    oracle.functions.registerLLMNode(w3.eth.default_account, True).transact()
    oracle.functions.submitVote(1000000, 123456).transact()

    os.makedirs("deploy_output", exist_ok=True)
    with open("deploy_output/addresses.json", "w") as f:
        json.dump({"EntropyNFT": entropy_addr, "ElasticUSD": eusd_addr, "LLMOracle": oracle_addr}, f)
    with open("deploy_output/EntropyNFT.abi", "w") as f:
        json.dump(entropy_iface['abi'], f)
    with open("deploy_output/ElasticUSD.abi", "w") as f:
        json.dump(eusd_iface['abi'], f)
    with open("deploy_output/LLMDemocracyOracle.abi", "w") as f:
        json.dump(oracle_iface['abi'], f)

    print("Contracts deployed:\n", entropy_addr, eusd_addr, oracle_addr)


if __name__ == "__main__":
    main()
