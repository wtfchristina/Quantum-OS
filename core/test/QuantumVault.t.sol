// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {QuantumVault} from "../src/QuantumVault.sol";
import {ERC20} from "lib/openzeppelin-contracts/contracts/token/ERC20/ERC20.sol";

contract MockUSDC is ERC20 {
    constructor() ERC20("Mock USD", "mUSD") {
        _mint(msg.sender, 10000 * 10**6);
    }
}

contract QuantumVaultTest is Test {
    QuantumVault vault;
    MockUSDC usdc;
    address agent = address(0xAA);
    address merchant = address(0xBB);

    function setUp() public {
        usdc = new MockUSDC();
        vault = new QuantumVault(address(usdc), agent, 5 * 10**6, 20 * 10**6);
        usdc.transfer(address(vault), 100 * 10**6);
    }

    function testAgentCanPayWithinLimits() public {
        vm.prank(agent);
        vault.pay(merchant, 3 * 10**6);
        assertEq(usdc.balanceOf(merchant), 3 * 10**6);
    }

    function testAgentBlockedWhenExceedingPerTxCap() public {
        vm.prank(agent);
        vm.expectRevert("Error: Exceeds single payment limit");
        vault.pay(merchant, 6 * 10**6);
    }
}
