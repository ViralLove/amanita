#!/usr/bin/env node
/**
 * Query MagicRegistry: list all contract names and addresses from the registry.
 * By default uses mainnet profile (constants below). Override via .env if needed.
 * Run from project root: node scripts/utility/query_magic_registry.js
 */

const path = require('path');
const { ethers } = require('ethers');

// --- Mainnet profile (константы для проверки конкретной сети) ---
const MAINNET_PROFILE = {
  name: 'mainnet',
  rpcUrl: 'https://polygon-rpc.com',
  magicRegistryAddress: '0x6a3d3e2328e9D613a6F9cf42FF1fBa655fc71576'
};

const projectRoot = path.resolve(__dirname, '../..');
require('dotenv').config({ path: path.join(projectRoot, '.env') });

const useMainnetProfile = process.argv.includes('--mainnet');

// Use mainnet constants when --mainnet, else .env, else mainnet as fallback
const registryAddress = useMainnetProfile ? MAINNET_PROFILE.magicRegistryAddress : (process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS || MAINNET_PROFILE.magicRegistryAddress);
const rpcUrl = useMainnetProfile ? MAINNET_PROFILE.rpcUrl : (process.env.RPC_URL || process.env.WEB3_PROVIDER_URI || process.env.POLYGON_MAINNET_RPC || MAINNET_PROFILE.rpcUrl);
const profileUsed = useMainnetProfile ? MAINNET_PROFILE.name : ((registryAddress === MAINNET_PROFILE.magicRegistryAddress && rpcUrl === MAINNET_PROFILE.rpcUrl) ? MAINNET_PROFILE.name : 'env');

if (!registryAddress || registryAddress === 'undefined' || registryAddress === '') {
  console.error('MAGIC_REGISTRY_CONTRACT_ADDRESS is not set (and mainnet constant not used)');
  process.exit(1);
}
if (!rpcUrl || rpcUrl === '') {
  console.error('RPC URL is not set');
  process.exit(1);
}

const abiPath = path.join(projectRoot, 'bot', 'artifacts', 'contracts', 'MagicRegistry.sol', 'MagicRegistry.json');

async function main() {
  const artifact = require(abiPath);
  const provider = new ethers.JsonRpcProvider(rpcUrl);
  const registry = new ethers.Contract(registryAddress, artifact.abi, provider);

  console.log('Profile:', profileUsed);
  console.log('MagicRegistry:', registryAddress);
  console.log('RPC:', rpcUrl.replace(/[?].*/, '').slice(0, 55) + (rpcUrl.length > 55 ? '...' : ''));
  console.log('');

  const names = await registry.getNames();
  if (!names || names.length === 0) {
    console.log('(no entries in registry)');
    return;
  }

  console.log('Key                          | Address');
  console.log('-----------------------------|------------------------------------------');
  const zero = ethers.ZeroAddress;
  for (let i = 0; i < names.length; i++) {
    const key = names[i];
    let display;
    try {
      const addr = await registry.get(key);
      display = addr === zero ? '(zero)' : addr;
    } catch (err) {
      display = `(error: ${err.info?.error?.message || err.shortMessage || 'call failed'})`;
    }
    console.log(`${key.padEnd(28)} | ${display}`);
    // Small delay to avoid RPC rate limit on public endpoints
    if (i < names.length - 1) await new Promise((r) => setTimeout(r, 150));
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
