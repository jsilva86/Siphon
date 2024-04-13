const { expect } = require('chai');
const { ethers } = require("hardhat");

describe('MyContract', () => {
  let myContract;

  beforeEach(async () => {
    const MyContract = await ethers.getContractFactory('test_usage');
    myContract = await MyContract.deploy();
    await myContract.deployed();
  });

    // it('should estimate gas for original', async () => {
    //     await myContract.func5(1, 2, 2);
    // });

    // it('should estimate gas for optimized', async () => {
    //     await myContract.func5_optimized(1, 2, 2);
    // });

    it('should estimate gas for normal', async () => {
      await myContract.test();
    });

    it('should estimate gas for optimized', async () => {
      await myContract.test2();
    });


    // it('should estimate gas for optimized', async () => {
    //     await myContract.test1_old();
    // });

    // it('should estimate gas for optimized', async () => {
    //     await myContract.test1();
    // });

    // it('should estimate gas for optimized', async () => {
    //     await myContract.test1_optimized();
    // });

    // it('should estimate gas for optimized', async () => {
    //     await myContract.test2_old();
    // });

    // it('should estimate gas for optimized', async () => {
    //     await myContract.test2_optimized();
    // });
});