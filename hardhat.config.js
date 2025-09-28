require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
require("dotenv").config();

// Используем те же имена переменных, что и в deploy.js для единообразия
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY;
console.log("[hardhat.config.js] DEPLOYER_PRIVATE_KEY:", DEPLOYER_PRIVATE_KEY);

const AMANITA_REGISTRY_CONTRACT_ADDRESS = process.env.AMANITA_REGISTRY_CONTRACT_ADDRESS;
console.log("[hardhat.config.js] AMANITA_REGISTRY_CONTRACT_ADDRESS:", AMANITA_REGISTRY_CONTRACT_ADDRESS);

const POLYGON_MAINNET_RPC = process.env.POLYGON_MAINNET_RPC;
const POLYGON_MUMBAI_RPC = process.env.POLYGON_MUMBAI_RPC;

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  defaultNetwork: 'hardhat', // Используем встроенную сеть Hardhat
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 1
      }
    }
  },
  networks: {
    localhost: {
      url: "http://localhost:8545",
      chainId: 31337, // Стандартный chainId для локальной сети Hardhat
      gasPrice: "auto",
      // Для тестов используем стандартные Hardhat аккаунты
      // Для деплоя используем аккаунт из .env
      accounts: DEPLOYER_PRIVATE_KEY ? [`0x${DEPLOYER_PRIVATE_KEY.replace(/^0x/, '')}`] : undefined,
      // Добавляем настройки верификации для локальной сети
      verify: {
        etherscan: {
          apiUrl: "https://api.polygonscan.com"
        }
      }
    },
    // Тестовая сеть для upgrade scenarios
    upgradeTest: {
      url: "http://localhost:8546",
      chainId: 31338,
      gasPrice: "auto",
      accounts: DEPLOYER_PRIVATE_KEY ? [`0x${DEPLOYER_PRIVATE_KEY.replace(/^0x/, '')}`] : undefined,
      // Настройки для тестирования upgrades
      timeout: 60000,
      gas: 10000000
    },
    polygon: {
      url: POLYGON_MAINNET_RPC || "https://polygon-rpc.com",
      accounts: DEPLOYER_PRIVATE_KEY ? [`0x${DEPLOYER_PRIVATE_KEY.replace(/^0x/, '')}`] : [],
      chainId: 137,
      gasPrice: "auto",
      timeout: 60000,
      verify: {
        etherscan: {
          apiUrl: "https://api.polygonscan.com"
        }
      }
    },
    mumbai: {
      url: POLYGON_MUMBAI_RPC || "https://rpc-mumbai.maticvigil.com",
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY.startsWith('0x') ? DEPLOYER_PRIVATE_KEY : `0x${DEPLOYER_PRIVATE_KEY}`] : [],
      chainId: 80001,
      gasPrice: "auto",
      verify: {
        etherscan: {
          apiUrl: "https://api-testnet.polygonscan.com"
        }
      }
    }
  },
  // Добавляем настройки для верификации контрактов
  etherscan: {
    apiKey: {
      polygon: process.env.POLYGONSCAN_API_KEY,
      polygonMumbai: process.env.POLYGONSCAN_API_KEY
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
    root: ".",
    nodeModules: "./node_modules"
  },
  mocha: {
    timeout: 60000 // Увеличиваем timeout для upgrade тестов
  },
  // Настройки для OpenZeppelin upgrades
  upgradeable: {
    // Настройки для proxy контрактов
    proxy: {
      // Используем Transparent proxy по умолчанию
      type: "transparent"
    },
    // Настройки для верификации upgrades
    verify: {
      // Автоматическая верификация после upgrade
      auto: true
    }
  }
};