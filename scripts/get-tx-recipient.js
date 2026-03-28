/**
 * Quick script to get transaction recipient and balance
 * Usage: npx hardhat run scripts/get-tx-recipient.js --network polygon
 */

require('dotenv').config();
const { ethers } = require('hardhat');

const TOKEN_ADDRESS = '0xFF5053F2bE129c7A1BbcA839a93ebB027e80eF5a';
const TX_HASH = '0x8ceb7bb507545eb267b919dd3484e88f9c02b2fd4471eb18cef662254172e842';

async function main() {
  console.log('🔍 Getting transaction details...');
  console.log(`   TX Hash: ${TX_HASH}`);
  console.log(`   Token: ${TOKEN_ADDRESS}\n`);
  
  const provider = hre.ethers.provider;
  
  // Get transaction and receipt
  const tx = await provider.getTransaction(TX_HASH);
  const receipt = await provider.getTransactionReceipt(TX_HASH);
  
  if (!tx || !receipt) {
    console.error('❌ Transaction not found');
    return;
  }
  
  console.log('✅ Transaction found:');
  console.log(`   Block: ${receipt.blockNumber}`);
  console.log(`   Status: ${receipt.status === 1 ? 'Success' : 'Failed'}\n`);
  
  // Load IERC20Metadata ABI
  const IERC20_ABI = require('../bot/artifacts/@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol/IERC20Metadata.json').abi;
  const tokenContract = new ethers.Contract(TOKEN_ADDRESS, IERC20_ABI, provider);
  const iface = tokenContract.interface;
  
  // Get token decimals
  let decimals = 8;
  try {
    decimals = await tokenContract.decimals();
    console.log(`📊 Token decimals: ${decimals}\n`);
  } catch (e) {
    console.log(`📊 Using default decimals: ${decimals}\n`);
  }
  
  // Parse Transfer events from logs
  console.log('🔍 Parsing Transfer events...\n');
  let recipientFound = false;
  
  for (const log of receipt.logs) {
    if (log.address.toLowerCase() === TOKEN_ADDRESS.toLowerCase()) {
      try {
        const parsed = iface.parseLog(log);
        if (parsed && parsed.name === 'Transfer') {
          const from = parsed.args.from;
          const to = parsed.args.to;
          const value = parsed.args.value;
          const amount = ethers.formatUnits(value, decimals);
          
          console.log('✅ Transfer event found:');
          console.log(`   From: ${from}`);
          console.log(`   To: ${to}`);
          console.log(`   Amount: ${amount} CAPY\n`);
          
          // Get recipient balance
          console.log('💰 Getting recipient balance...');
          const balance = await tokenContract.balanceOf(to);
          const balanceFormatted = ethers.formatUnits(balance, decimals);
          
          console.log('\n' + '='.repeat(70));
          console.log('📋 RESULTS');
          console.log('='.repeat(70));
          console.log(`Recipient Address: ${to}`);
          console.log(`Current Balance: ${balanceFormatted} CAPY`);
          console.log(`Transaction Amount: ${amount} CAPY`);
          console.log(`View on PolygonScan: https://polygonscan.com/address/${to}`);
          console.log('='.repeat(70));
          
          recipientFound = true;
        }
      } catch (e) {
        // Not a Transfer event, skip
      }
    }
  }
  
  if (!recipientFound) {
    console.log('❌ No Transfer events found in this transaction');
  }
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });

