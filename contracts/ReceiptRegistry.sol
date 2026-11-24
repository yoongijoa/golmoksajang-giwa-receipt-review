// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.28;

/// Records only salted receipt commitments on GIWA Sepolia.
contract ReceiptRegistry {
    address public recorder;
    mapping(bytes32 => bool) public recorded;

    event ReceiptRecorded(bytes32 indexed commitment);
    error Unauthorized();
    error EmptyCommitment();
    error AlreadyRecorded();

    constructor() {
        recorder = msg.sender;
    }

    function record(bytes32 commitment) external {
        if (msg.sender != recorder) revert Unauthorized();
        if (commitment == bytes32(0)) revert EmptyCommitment();
        if (recorded[commitment]) revert AlreadyRecorded();
        recorded[commitment] = true;
        emit ReceiptRecorded(commitment);
    }
}
