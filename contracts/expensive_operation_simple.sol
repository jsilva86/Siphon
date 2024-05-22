contract SimpleWrite {
    address[] private _payees;

    constructor(address[] memory payees) {
        for (uint256 i = 0; i < payees.length; i++) {
            _payees.push(payees[i]);
        }
    }

    function write() public {
        uint sum = 0;
        for (uint i = 0; i < _payees.length; i++) {
            sum++;
        }
    }

    function write_optimized() public {
        uint256 SP__payees_length = _payees.length;
        uint sum = 0;
        for (uint i = 0; i < SP__payees_length; i++) {
            sum++;
        }
    }
}
