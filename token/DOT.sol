// SPDX-License-Identifier: MIT
pragma solidity ^0.8.26;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title DOT — the Talvio Generate token (BNB Chain)
/// @notice Plain fixed-supply ERC-20. The full supply of 1,000,000,000 DOT is
///         minted once, in the constructor, and never again:
///           - 60% (600,000,000 DOT) to the claim pool address given at deploy
///             (the future Talvio discharge/claim contract or pool wallet);
///           - 40% (400,000,000 DOT) to the deployer.
///         No mint after deploy, no pause, no transfer fees, no blacklist.
contract DOT is ERC20 {
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10 ** 18;

    constructor(address claimPool) ERC20("DOT", "DOT") {
        require(claimPool != address(0), "DOT: zero pool address");
        uint256 poolAmount = (TOTAL_SUPPLY * 60) / 100; // 600,000,000 DOT
        _mint(claimPool, poolAmount);
        _mint(msg.sender, TOTAL_SUPPLY - poolAmount); // 400,000,000 DOT
    }
}
