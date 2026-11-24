"""Run the offline demo, publish the fixture, or verify a testnet transaction."""
import argparse
import getpass
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import receipt

ROOT = Path(__file__).resolve().parent
EXPECTED = "0x8a2ab8e5e1ebb5effdc941ce01867dae932f76eaab1ea920bcb3e77ba96fb877"


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("demo", help="Check the sample locally, without network access")
    actions.add_parser("contract", help="Verify the sample against the deployed ReceiptRegistry")
    actions.add_parser("publish", help="Legacy pilot: submit a self-addressed testnet transaction")
    check = actions.add_parser("verify", help="Legacy pilot: verify a self-addressed testnet transaction")
    check.add_argument("transaction", help="Transaction hash from publish")
    check.add_argument("signer", help="Public address of the test wallet that published it")
    args = parser.parse_args()

    sample = json.loads((ROOT / "example-receipt.json").read_text(encoding="utf-8"))
    digest = receipt.commitment(sample)
    if digest != EXPECTED:
        raise ValueError("The example does not match the published fixture digest")
    if args.action == "demo":
        altered = dict(sample, amount=10000)
        if receipt.commitment(altered) == digest:
            raise ValueError("Altered example unexpectedly matched")
        print("Offline fixture check (no chain lookup)")
        print(f"1,000 KRW: MATCH {digest}")
        print(f"10,000 KRW: MISMATCH {receipt.commitment(altered)}")
        return

    if int(receipt.rpc("eth_chainId"), 16) != receipt.CHAIN:
        raise ValueError("Expected GIWA Sepolia")
    if args.action == "contract":
        import registry
        registry.check(sample)
        return
    if args.action == "verify":
        if not re.fullmatch(r"0x[0-9a-fA-F]{64}", args.transaction):
            raise ValueError("Expected a transaction hash")
        if not re.fullmatch(r"0x[0-9a-fA-F]{40}", args.signer):
            raise ValueError("Expected a public signer address")
        receipt.verify(args.transaction, SimpleNamespace(address=args.signer), sample)
        return

    from eth_account import Account
    from filelock import FileLock

    if not sys.stdin.isatty():
        raise ValueError("Use an interactive terminal and a disposable testnet wallet")
    account = Account.from_key(getpass.getpass("Disposable GIWA Sepolia wallet key (hidden): "))
    state = ROOT / ".review-state" / account.address / digest
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with FileLock(str(state / "publish.lock"), timeout=5):
        tx_hash = receipt.submit(account, digest, state)
    print(f"Transaction: {tx_hash}\nSigner: {account.address}", flush=True)
    receipt.verify(tx_hash, account, sample)


if __name__ == "__main__":
    run()
