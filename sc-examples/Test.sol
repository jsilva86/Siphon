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
            else {
                x = 1234;
            }
            x = 6;
            x = 5566;
        }
        else {
            x = 9;

            if(x < 67) {
                x = 8;
            }
            x = 2;
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
    struct myStruct2 {
        uint256 p1;
        uint256 p2;
    }

    int b = 32;
    int c = 37;
    //myStruct s;
    uint256 s_result;
    uint256 s_variable;
    uint256 public constant MAX_ITER = 100;
    myStruct2 s_struct;
    uint256[] s_list;

    enum myEnum { SMALL, MEDIUM, LARGE }

    function func1(uint256 x) public returns (uint256) {
        uint256 result;

        if (x > 50 && x < 100) {
            result =  x * 2;
        } else {
            result = 200;
        }

        // This code block is unreachable
        if (result < 100) {
            result = 100;
        }
    }

    function func2(uint256 x) public returns (uint256) {
        uint256 result = 5 + x + 12;
        result += 2;

        if ((x > 10 && x < 5) || !(result != 5)) {
            result =  x + 2;
        } else {
            result = x * 3;
        }

        // This code block is unreachable
        if (result + x > 100) {
            result = 100;
        }

        return result;  
    }

    function func3(uint256 x) public pure returns (uint256) {
        if (x < 100) {
            if(x < 200) {
                uint256 result = 312;
            }
        }

        uint256 result = 123;

        return result;
    }   

     function func4(uint256 x) public returns (uint256) {
        for(uint256 i = 0; i < MAX_ITER; i++) {
            for(uint256 j = 0; j < MAX_ITER; j++) {
                if (j < i) {
                    x += s_result * i;
                    s_variable -= i * j;
                    // s_struct.p1 = i + x;
                    // s_list = [123];
                    // s_list[j] = 123;
                }
            }
        }
          
  
        return s_result;


    }  
}