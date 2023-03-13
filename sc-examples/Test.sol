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
            else {
                x = 9;
            }
            // for (int i = 0; i < 20; i++) {
            //     x = 6;
            // }
            x = 66;
        } else {
            a = 69;
            this.two();
        }
        x = 123;
    }

    function two() public {
        int x = 35;
        if(x < 10) {
            x = 3;
            if(x < 9) {
                x = 12;
            }
            //x = 6;
        }
        else {
            x = 9;

            if(x < 67) {
                x = 8;
            }
        }

        x = 123;
    }

    function three() public {
        int x = 35;
        if(x < 20) {
            if(x < 10) {
                x = 3;
            }
        }
        x = 9;
    }

    function four(int x) public {
        for (int i = 0; i < 10; i++) {
            // loop body
            x += 2;
        }
        x = 3;
    }      
}

contract Test2 {
    int b = 69;
    function func1() public {
        b = 2;
    }

    function func2() public {
        b = 3;
    }   
}