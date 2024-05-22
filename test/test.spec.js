const { ethers } = require("hardhat");

describe('Loop Invariant operation', () => {
  let myContract;

  beforeEach(async () => {
    const MyContract = await ethers.getContractFactory('MoonStaking');
    myContract = await MyContract.deploy("0x1234567890123456789012345678901234567890");
    await myContract.deployed();
  });

  for (let i = 100; i <= 1000; i += 100) {
    it(`should estimate gas for normal with ${i} elements`, async () => {
      const array = new Array(i).fill(0);

      const gasEstimateNormal = await myContract.estimateGas.stake721(
        "0x1234567890123456789012345678901234567891",
        array
      );
      const txNormal = await myContract.stake721(
        "0x1234567890123456789012345678901234567891",
        array,
        { gasLimit: gasEstimateNormal.add(ethers.BigNumber.from("100000")) }
      );
      const receiptNormal = await txNormal.wait();
      console.log(`Gas used for normal with ${i} elements:`, receiptNormal.gasUsed.toString());
    });

    it(`should estimate gas for optimized with ${i} elements`, async () => {
      const array = new Array(i).fill(0);

      const gasEstimateOptimized = await myContract.estimateGas.stake721_optimized(
        "0x1234567890123456789012345678901234567891",
        array
      );
      const txOptimized = await myContract.stake721_optimized(
        "0x1234567890123456789012345678901234567891",
        array,
        { gasLimit: gasEstimateOptimized.add(ethers.BigNumber.from("100000")) }
      );
      const receiptOptimized = await txOptimized.wait();
      console.log(`Gas used for optimized with ${i} elements:`, receiptOptimized.gasUsed.toString());
    });
  }
});

describe("Expensive operation inside loop - length of array", function () {
  let PaymentSplitter, paymentSplitter;
  let MockERC20, token;
  let shares;

  for (let i = 100; i <= 500; i += 100) {
    it(`should estimate gas for tokenRescue with ${i} payees`, async function () {
      const addresses = new Array(i).fill(0).map((_, idx) => 
        ethers.Wallet.createRandom().address
      );

      PaymentSplitter = await ethers.getContractFactory("PaymentSplitter");
      MockERC20 = await ethers.getContractFactory("MockERC20");

      shares = addresses.map(() => 1);

      paymentSplitter = await PaymentSplitter.deploy(addresses, shares);
      await paymentSplitter.deployed();

      token = await MockERC20.deploy(ethers.utils.parseEther("1000"));
      await token.deployed();

      const gasEstimateNormal = await paymentSplitter.estimateGas.tokenRescue(token.address);
      const txNormal = await paymentSplitter.tokenRescue(token.address, {
        gasLimit: gasEstimateNormal.add(ethers.BigNumber.from("1000000")),
      });
      const receiptNormal = await txNormal.wait();
      console.log(`Gas used for tokenRescue with ${i} payees:`, receiptNormal.gasUsed.toString());
    });

    it(`should estimate gas for tokenRescue_optimized with ${i} payees`, async function () {
      const addresses = new Array(i).fill(0).map((_, idx) => 
        ethers.Wallet.createRandom().address
      );

      PaymentSplitter = await ethers.getContractFactory("PaymentSplitter");
      MockERC20 = await ethers.getContractFactory("MockERC20");

      shares = addresses.map(() => 1);

      paymentSplitter = await PaymentSplitter.deploy(addresses, shares);
      await paymentSplitter.deployed();

      token = await MockERC20.deploy(ethers.utils.parseEther("1000"));
      await token.deployed();

      const gasEstimateOptimized = await paymentSplitter.estimateGas.tokenRescue_optimized(token.address);
      const txOptimized = await paymentSplitter.tokenRescue_optimized(token.address, {
        gasLimit: gasEstimateOptimized.add(ethers.BigNumber.from("1000000")),
      });
      const receiptOptimized = await txOptimized.wait();
      console.log(`Gas used for tokenRescue_optimized with ${i} payees:`, receiptOptimized.gasUsed.toString());
    });
  }
});

describe.only("Expensive operation inside loop - length of array - simple write", function () {
  let Contract;
  let contract;

  for (let i = 100; i <= 500; i += 100) {
    it(`should estimate gas for write with ${i} payees`, async function () {
      const addresses = new Array(i).fill(0).map((_, idx) => 
        ethers.Wallet.createRandom().address
      );

      Contract = await ethers.getContractFactory("SimpleWrite");

      contract = await Contract.deploy(addresses);
      await contract.deployed();

      const gasEstimateNormal = await contract.estimateGas.write();
      const txNormal = await contract.write({
        gasLimit: gasEstimateNormal.add(ethers.BigNumber.from("1000000")),
      });
      const receiptNormal = await txNormal.wait();
      console.log(`Gas used for write with ${i} payees:`, receiptNormal.gasUsed.toString());
    });

    it(`should estimate gas for write_optimized with ${i} payees`, async function () {
      const addresses = new Array(i).fill(0).map((_, idx) => 
        ethers.Wallet.createRandom().address
      );

      Contract = await ethers.getContractFactory("SimpleWrite");

      contract = await Contract.deploy(addresses);
      await contract.deployed();

      const gasEstimateOptimized = await contract.estimateGas.write_optimized();
      const txOptimized = await contract.write_optimized({
        gasLimit: gasEstimateOptimized.add(ethers.BigNumber.from("1000000")),
      });
      const receiptOptimized = await txOptimized.wait();
      console.log(`Gas used for write_optimized with ${i} payees:`, receiptOptimized.gasUsed.toString());
    });
  }
});