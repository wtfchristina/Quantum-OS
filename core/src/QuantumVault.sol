// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {IERC20} from "lib/openzeppelin-contracts/contracts/token/ERC20/IERC20.sol";

contract QuantumVault {
    address public owner;
    address public authorizedAgent;
    IERC20 public token;

    uint256 public maxPerTx;
    uint256 public hourlyCap;
    uint256 public spentThisHour;
    uint256 public lastResetTime;

    event PaymentExecuted(address indexed recipient, uint256 amount);

    constructor(address _token, address _agent, uint256 _maxPerTx, uint256 _hourlyCap) {
        owner = msg.sender;
        token = IERC20(_token);
        authorizedAgent = _agent;
        maxPerTx = _maxPerTx;
        hourlyCap = _hourlyCap;
        lastResetTime = block.timestamp;
    }

    function pay(address recipient, uint256 amount) external {
        require(msg.sender == authorizedAgent, "Error: Only the AI agent can call this");
        require(amount <= maxPerTx, "Error: Exceeds single payment limit");

        if (block.timestamp >= lastResetTime + 1 hours) {
            spentThisHour = 0;
            lastResetTime = block.timestamp;
        }

        require(spentThisHour + amount <= hourlyCap, "Error: Hourly spend limit reached");

        spentThisHour += amount;
        require(token.transfer(recipient, amount), "Error: Transfer failed");

        emit PaymentExecuted(recipient, amount);
    }
}
