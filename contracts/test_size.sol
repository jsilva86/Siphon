contract test_size_optimized {
    uint256 s_result;

    function func1(uint256 x) public returns (uint256) {
        uint256 result;
        if (x > 50) {
            result = x * 2;
            if (x < 60) {
                result = 5;
            } else {
                result = 900;
                result = 9;
            }
        } else {
            result = 50;
            if (s_result < 60) {
                s_result = 3;
            } else {
                s_result = 6;
            }
        }

        result = 100;
        return result;
        }
}

contract test_size {
    uint256 s_result;
     function func1(uint256 x) public returns (uint256) {
        uint256 result;
        if (x > 50) {
            result = x * 2;
            if (x < 25) {
                result = 3;
            } 
            else if (x < 60) {
                result = 5;
            } 
            else {
                result = 900;
                result = 9;
            }
        } 
        else {
            result = 50;
            if (s_result < 60){
                s_result = 3;
            }
            else {
                s_result = 6;
            }
        }

        if (result < 100) {
            result = 100;
        }

        return result;
    }
}