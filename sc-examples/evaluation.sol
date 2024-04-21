// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.0;

contract EvaluationPattern1 {
    uint256 minThreshold = 5;
    uint256 maxThreshold = 10;
    uint256 scalingFactor = maxThreshold / minThreshold;
    uint256 offset = 2;
    bool public Error;

    function pattern1(uint256 x) public {
        uint256 y;
        uint256 z;
        if (minThreshold < x && x < maxThreshold) {
            y = x * scalingFactor;

            if (y < maxThreshold) {
                Error = true;
            }
        } else {
            y  = 2 * maxThreshold;
        } 

        z = y - offset;

        if (z < maxThreshold) {
            Error = true;
        } else {
            Error = false;
        }
    }
}

contract EvaluationPattern2 {
    uint256 amount = 15;
    uint256 interest = 2;
    uint256 balance;
    bool public Error;

    function pattern2() public {
        uint256 tentativeBalance = balance;
        if (tentativeBalance > amount * interest) {
            tentativeBalance -= amount * interest;

            if (tentativeBalance > 0) {
                Error = false;
            } else {
                Error = true;
            }

            balance = tentativeBalance;
        }
    }
}

contract EvaluationPattern4 {
    uint256 numberOfTransactions;
    address[] userList;
    mapping(address => uint256) usersBalance;
    address smallestBalanceIndex;

    function pattern4(uint256 transactionAmount) public {
       for(uint256 i = 0; i < userList.length; i++) {
            numberOfTransactions++;

            address userAddress = userList[i];

            usersBalance[userAddress] += transactionAmount;

            if (usersBalance[userAddress] < usersBalance[smallestBalanceIndex]) {
                smallestBalanceIndex = userAddress;
            }
       }

       for(uint256 i = 0; i < userList.length; i++) { 
            usersBalance[smallestBalanceIndex] += transactionAmount * 2;
       }
    }
}

contract EvaluationPattern5 {
    address[] userList;
    mapping(address => uint256) usersBalance;

    function validAddress(address userAddress) public pure returns (bool) {
        return true;
    }

    function interest(uint256 amount) public pure returns (uint256) {
        return amount * 2;
    }

    function pattern5(uint256 amount) public {
       for(uint256 i = 0; i < userList.length; i++) {
            address userAddress = userList[i];
            if (validAddress(userAddress)) {
                usersBalance[userAddress] += interest(amount);
            }
       }    
    }
}

contract EvaluationPattern6 {
    address[] userList;
    mapping(address => uint256) usersBalance;

    function adjustedMinThreshold(uint256 amount) public pure returns (uint256) {
        return (amount) / (amount + 100);
    }

    function pattern6(uint256 amount) public {
       for(uint256 i = 0; i < userList.length; i++) {
            address userAddress = userList[i];
            uint256 value;
            if (amount < adjustedMinThreshold(amount)) {
                value = amount;
            } else {
                value = 100;
            }

            usersBalance[userAddress] += value;
       }    
    }
}