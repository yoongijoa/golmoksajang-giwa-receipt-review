"""Receipt commitment, GIWA Sepolia submission and verification from the pilot."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

CHAIN = 91342
RPC = "https://sepolia-rpc.giwa.io"


def commitment(receipt):
    data = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    return "0x" + hashlib.sha256(b"golmok:dev-payment-receipt:v1\0" + data).hexdigest()


def rpc(method, *params):
    payload = json.dumps(dict(jsonrpc="2.0", id=1, method=method, params=params)).encode()
    response = subprocess.run(
        ["curl", "--fail", "--silent", "--show-error", "--max-time", "20",
         "-H", "Content-Type: application/json", "--data-binary", "@-", RPC],
        input=payload, stdout=subprocess.PIPE, check=True,
    )
    result = json.loads(response.stdout)
    if "error" in result:
        raise RuntimeError(f"{method}: {result['error'].get('message', 'RPC error')}")
    return result["result"]


def save(name, data, state):
    path = state / name
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(temp, path)


def submit(account, digest, state):
    journal = state / "transaction.json"
    if not journal.exists():
        address = account.address
        gas = int(rpc("eth_estimateGas", {"from": address, "to": address, "data": digest}), 16)
        price = int(rpc("eth_gasPrice"), 16)
        nonce = int(rpc("eth_getTransactionCount", address, "pending"), 16)
        tx = dict(chainId=CHAIN, nonce=nonce, to=address, value=0, data=digest,
                  gas=gas * 12 // 10, gasPrice=price)
        signed = account.sign_transaction(tx)
        save("transaction.json", {"hash": "0x" + bytes(signed.hash).hex(),
                                  "raw": "0x" + bytes(signed.raw_transaction).hex()}, state)
    saved = json.loads(journal.read_text())
    if rpc("eth_getTransactionByHash", saved["hash"]) is None:
        try:
            observed = rpc("eth_sendRawTransaction", saved["raw"])
            if observed.lower() != saved["hash"].lower():
                raise RuntimeError("Unexpected transaction hash")
        except RuntimeError as exc:
            if "already known" not in str(exc).lower():
                raise
    return saved["hash"]


def verify(tx_hash, account, receipt, hash_receipt=commitment):
    for _ in range(40):
        result = rpc("eth_getTransactionReceipt", tx_hash)
        if result and int(rpc("eth_blockNumber"), 16) >= int(result["blockNumber"], 16) + 1:
            break
        time.sleep(3)
    else:
        raise RuntimeError(f"Awaiting confirmation: {tx_hash}")
    tx = rpc("eth_getTransactionByHash", tx_hash)
    block = rpc("eth_getBlockByNumber", result["blockNumber"], False)
    if not (result["status"] == "0x1" and result["blockHash"] == block["hash"] == tx["blockHash"]
            and tx["from"].lower() == tx["to"].lower() == account.address.lower()
            and int(tx["value"], 16) == 0 and tx["input"].lower() == hash_receipt(receipt)):
        raise RuntimeError("Receipt does not match the confirmed chain record")
    altered = copy.copy(receipt)
    altered["amount"] += 9000
    if tx["input"].lower() == hash_receipt(altered):
        raise RuntimeError("Altered receipt unexpectedly matched")
    print(json.dumps(dict(status="verified", transaction=tx_hash, block=int(result["blockNumber"], 16),
                          originalMatches=True, alteredMatches=False)))
