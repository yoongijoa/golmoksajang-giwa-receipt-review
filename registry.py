"""Read-only replay of the public GIWA Sepolia fictional receipt example."""
from receipt import commitment, rpc

ADDRESS = "0xda0b98c4b8BEbbAD5af3b9CdE32A71f01767797B"
TRANSACTION = "0x4536a056b8e05e2ecda6ca546081e366e680920d86a5fec6fdb4ae60edc1cdb2"
EVENT = "0x4f5d8199357096b753b61c42277bf0b5c2d4cd53eabab82c0f169c0285118f31"


def check(sample):
    digest = commitment(sample)
    result = rpc("eth_getTransactionReceipt", TRANSACTION)
    if not result or result["status"] != "0x1" or result["to"].lower() != ADDRESS.lower():
        raise ValueError("Missing successful registry transaction")
    block = result["blockNumber"]
    if rpc("eth_getBlockByNumber", block, False)["hash"] != result["blockHash"]:
        raise ValueError("Receipt block is not canonical")
    if not any(log["address"].lower() == ADDRESS.lower() and log["topics"] == [EVENT, digest]
               for log in result["logs"]):
        raise ValueError("Expected ReceiptRecorded event missing")

    def recorded(value):
        # recorded(bytes32); the append-only registry can be read without an archive node.
        return int(rpc("eth_call", {"to": ADDRESS, "data": "0xd6399790" + value[2:]}, "latest"), 16)

    if recorded(digest) != 1 or recorded(commitment(dict(sample, amount=10000))) != 0:
        raise ValueError("Unexpected registry state")
    print(f"GIWA Sepolia | ReceiptRegistry {ADDRESS} | block {int(block, 16)}")
    print(f"ReceiptRecorded event confirmed: {TRANSACTION}")
    print("1,000 KRW: recorded\n10,000 KRW: not recorded")
