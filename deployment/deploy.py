#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple deployment script for Automa smart contracts."""

import json
import os
from web3 import Web3
from solcx import compile_files, install_solc, get_installed_solc_versions

CONTRACTS = [
    "contracts/EntropyNFT.sol",
    "contracts/ElasticUSD.sol",
    "contracts/LLMDemocracyOracle.sol",
]


def deploy_contract(w3: Web3, interface: dict, *args) -> str:
    contract = w3.eth.contract(abi=interface["abi"], bytecode=interface["bin"])
    try:
        tx = contract.constructor(*args).transact()
    except Exception as exc:
        raise SystemExit(f"Deployment failed: {exc}")
    receipt = w3.eth.wait_for_transaction_receipt(tx)
    return receipt.contractAddress


def main() -> None:
    rpc = os.environ.get("RPC_URL")
    if not rpc:
        raise SystemExit("RPC_URL environment variable is not set")

    if "0.8.25" not in get_installed_solc_versions():
        install_solc("0.8.25")

    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise SystemExit("Web3 provider is not connected")
    w3.eth.default_account = w3.eth.accounts[0]

    try:
        compiled = compile_files(CONTRACTS, output_values=["abi", "bin"])
    except Exception as exc:
        raise SystemExit(f"Compilation failed: {exc}")

    entropy_iface = compiled["contracts/EntropyNFT.sol:EntropyNFT"]
    entropy_addr = deploy_contract(w3, entropy_iface)

    oracle_iface = compiled["contracts/LLMDemocracyOracle.sol:LLMDemocracyOracle"]
    oracle_addr = deploy_contract(w3, oracle_iface)

    eusd_iface = compiled["contracts/ElasticUSD.sol:ElasticUSD"]
    eusd_addr = deploy_contract(w3, eusd_iface, oracle_addr)

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
