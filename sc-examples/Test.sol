// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.7.0 <0.9.0;

import "./Test2.sol";

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
    uint256 s_result;
    uint256 s_variable;
    uint256 s_condition;
    uint256 public constant MAX_ITER = 100;
    mapping(address => uint) public s_mapping;
    mapping(uint256 => uint) public s_mapping_bad;
    uint256[] s_list;

    function func1(uint256 x) public returns (uint256) {
        uint256 result;

        if (x > 50) {
            result = x * 2;

            if(x < 25) {
                result = 3;
            }
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

        if (result + x > 100) {
            result = 100;
        }

        return result;  
    }

    function func3(uint256 x) public returns (uint256) {
        uint256 result;
        if (s_result < 100) {
           result = 3;
        }

        return result;
    }   

    function func4(uint256 x) public returns (uint256) {
        for(uint256 i = 0; i < 100; i++) {
            for(uint256 j = 0; j < 100; j++) {
                if (s_result + 1  + j < s_condition) {
                    x += s_variable * i;
                    s_variable *= i * j;
                }

                x = 9999;
            }
        }
    
        return s_result;
    }  

    function func5(address key, uint x) public returns (uint256) {
        uint256 sum;
        uint256 sum_bad;
        uint256 outside_bad;
        for(uint256 i = 0; i < s_list.length; i++) {
            s_mapping[key] += i;
            sum += s_mapping[key];

            // false positives
            uint256 loop_key = i;
            s_mapping_bad[i] += i;
            s_mapping_bad[loop_key] += i;
            sum_bad += s_mapping_bad[loop_key];

            // false positives
            outside_bad = i + x;
            s_mapping_bad[outside_bad] += i;
            sum_bad += s_mapping_bad[outside_bad];
        }

        return s_result;
    } 

    function func6(uint256[] memory list, address key) public returns (uint256) {
        uint256 min_length = 10;
        uint256 sum = 0;
        uint256 i;
        for(i = 0; i < s_list.length; i++) {
            if (list.length > min_length) {
                sum += i;
            }
            if (s_list.length > min_length + i) {
                sum -= i;
            }
        }

        return s_result;
    } 

    function pure_func() pure public returns (uint256) {
        return 12;
    }

    function func_arg(uint256 i) pure public returns (uint256) {
        return 10 * i;
    }

    function func_with_lib_call() public returns (uint256) {
        return LibExample.pow(1, 2);
    }

    function func7(uint256 j) public returns (uint256) {
        uint256 sum = 0;
        uint256 loop_key = 0;
        for(uint256 i = 0; i < 100; i++) {
            // sum -= pure_func() + i;
            // sum *= func_arg(i);
            // sum += func_with_lib_call();

            // false positive
            loop_key = i + j;
            sum *= func_arg(loop_key);

            // false positive
            uint256 key_in_loop = i * j;
            sum *= func_arg(key_in_loop);
        }

        return sum;
    }
    
}