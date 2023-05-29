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
            for(int j = 0; j < 9; j++) {
                x = 9;
            }
        }
        x = 3;
    }      
}

contract Test2 {
    int b = 32;
    int c = 37;
    //myStruct s;

    struct myStruct2 {
        uint p1;
        uint p2;
    }

    enum myEnum { SMALL, MEDIUM, LARGE }

    function func1() public returns (uint256) {
        return 1;
    }

    function func2(uint256 x) public returns (uint256) {
        uint256 result = 5 + x + 12;
        result += 2;
        uint256 result2 = result;

        if ((x > 10 && x < 5) && !(result != 5)) {
            result =  x + 2;
            func1();
        } else {
            result = x * 3;
        }

        // This code block is unreachable
        if (result > 100) {
            result = 100;
        }

        return result;  
    }   
}