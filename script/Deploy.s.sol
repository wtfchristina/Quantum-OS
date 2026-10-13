// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script} from "forge-std/Script.sol";
import {QuantumVault} from "../src/QuantumVault.sol";
import {ERC20} from "lib/openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";

contract TestUSD is ERC20 {
    constructor() ERC20("Quantum USD", "qUSD") {
        _mint(msg.sender, 100000 * 10**6);
    }
}

contract DeploySystem is Script {
    function run() external {
        address agent = 0x70997970C51812dc3A010C7d01b50e0d17dc79C8;

        // Uses the private key supplied to forge via the CLI
        vm.startBroadcast();

        TestUSD token = new TestUSD();
        QuantumVault vault = new QuantumVault(address(token), agent, 5 * 10**6, 20 * 10**6);

        // Fund the vault with $1,000 qUSD
        token.transfer(address(vault), 1000 * 10**6);

        vm.stopBroadcast();
    }
}
