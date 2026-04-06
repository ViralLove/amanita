require("@nomicfoundation/hardhat-toolbox");
require("@openzeppelin/hardhat-upgrades");
const { SCRIPTS_DOTENV_PATH } = require("./scripts/lib/env-path");
// Секреты деплоя: scripts/.env (единый SSOT с deploy_full.js), не корень репо
require("dotenv").config({ path: SCRIPTS_DOTENV_PATH });

// Используем те же имена переменных, что и в deploy.js для единообразия
const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY;
// ⚠️ БЕЗОПАСНОСТЬ: НИКОГДА не логируем приватные ключи!
// console.log("[hardhat.config.js] DEPLOYER_PRIVATE_KEY:", DEPLOYER_PRIVATE_KEY); // ❌ КРИТИЧЕСКАЯ УЯЗВИМОСТЬ - УДАЛЕНО
if (!DEPLOYER_PRIVATE_KEY) {
  console.warn("[hardhat.config.js] ⚠️ DEPLOYER_PRIVATE_KEY не установлен");
} else {
  console.log("[hardhat.config.js] ✅ DEPLOYER_PRIVATE_KEY установлен");
}

const MAGIC_REGISTRY_CONTRACT_ADDRESS = process.env.MAGIC_REGISTRY_CONTRACT_ADDRESS;
console.log("[hardhat.config.js] MAGIC_REGISTRY_CONTRACT_ADDRESS:", MAGIC_REGISTRY_CONTRACT_ADDRESS);

const POLYGON_MAINNET_RPC = process.env.POLYGON_MAINNET_RPC;
const POLYGON_MUMBAI_RPC = process.env.POLYGON_MUMBAI_RPC;
const DOGEOS_TESTNET_RPC = process.env.DOGEOS_TESTNET_RPC;

const POLYGON_RPC_URL = POLYGON_MAINNET_RPC || "https://polygon-rpc.com";
try {
  const u = new URL(POLYGON_RPC_URL);
  const host = u.hostname;
  console.log(
    "[hardhat.config.js] polygon RPC:",
    host,
    POLYGON_MAINNET_RPC ? "(POLYGON_MAINNET_RPC from .env)" : "(default, no POLYGON_MAINNET_RPC)"
  );
  // Alchemy без ключа в пути отвечает «Must be authenticated!» — подсказка без утечки секрета
  if (host.includes("alchemy.com")) {
    const parts = u.pathname.split("/").filter(Boolean);
    const v2i = parts.indexOf("v2");
    const afterV2 = v2i >= 0 ? parts[v2i + 1] : "";
    if (!afterV2 || afterV2.length < 16) {
      console.warn(
        "[hardhat.config.js] ⚠️ Похоже, в URL Alchemy нет API key после /v2/ (или он обрезан). " +
          "В scripts/.env одна строка без пробелов вокруг = и без кавычек, без переноса строки посередине URL."
      );
    }
  }
} catch {
  console.warn("[hardhat.config.js] polygon RPC URL is not a valid URL; check POLYGON_MAINNET_RPC");
}

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  defaultNetwork: 'hardhat', // Используем встроенную сеть Hardhat
  solidity: {
    compilers: [
      {
        version: "0.8.20",
        settings: {
          optimizer: {
            enabled: true,
            runs: 1
          }
        }
      },
      {
        version: "0.8.22",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200
          },
          viaIR: true // Включаем IR-based code generator для решения "Stack too deep"
        }
      }
    ]
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
    // Ganache локальная сеть (Amanita application)
    ganache: {
      url: "http://127.0.0.1:7545",
      chainId: 5777, // Chain ID из Ganache (eth_chainId возвращает 0x539 = 1337)
      gasPrice: "auto",
      // Используем ключи из .env (DEPLOYER_PRIVATE_KEY и SELLER_PRIVATE_KEY)
      accounts: DEPLOYER_PRIVATE_KEY ? [`0x${DEPLOYER_PRIVATE_KEY.replace(/^0x/, '')}`] : undefined,
      timeout: 60000
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
      url: POLYGON_RPC_URL,
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
    },
    dogetestnet: {
      url: DOGEOS_TESTNET_RPC || "https://rpc.testnet.dogeos.com/",
      accounts: DEPLOYER_PRIVATE_KEY ? [DEPLOYER_PRIVATE_KEY.startsWith('0x') ? DEPLOYER_PRIVATE_KEY : `0x${DEPLOYER_PRIVATE_KEY}`] : [],
      chainId: 6281971,
      gasPrice: "auto",
      timeout: 60000
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
    tests: "./contracts/tests",
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