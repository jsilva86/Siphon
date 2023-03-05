// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 * @custom:dev-run-script ./scripts/deploy_with_ethers.ts
 */
contract Test2 {
    int damas = 69;
    function two() public {
        int x = 35;
        if (x < 10) {
            for (int i = 0; i < 20; i++) {
                x = 6;
            }
        } else {
            damas = 69;
            this.damasio();
        }
    }

    function damasio() public {

    }   
}