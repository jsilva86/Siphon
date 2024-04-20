// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.0;

contract Evaluation {
    uint256 minThreshold = 5;
    uint256 maxThreshold = 10;
    uint256 scalingFactor = 2;
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