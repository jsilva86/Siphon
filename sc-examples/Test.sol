// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

/**
 * @title Storage
 * @dev Store & retrieve value in a variable
 * @custom:dev-run-script ./scripts/deploy_with_ethers.ts
 */
contract Test {
    int a = 69;
    function one() private {
        int x = 35;
        if (x < 10) {
            x = 4;
            if (x < 89) {
                x = 3;
            }
            for (int i = 0; i < 20; i++) {
                x = 6;
            }
        } else {
            a = 69;
            this.damasio();
        }
    }

    function damasio() public {

    }   
}

contract Test2 {
    int b = 69;
    function func1() public {
    }

    function func2() public {

    }   
}