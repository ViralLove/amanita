# Amanita Ecosystem - Abstraction Layers

**Date:** 2025-10-28  
**Analysis Method:** @analysis.mdc (Zeya888 Vibe-Coding Methodology)

---

## 🏗️ 5-LAYER ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: DEPLOYMENT & MANAGEMENT                               │
│  ├─ deploy_full.js (19 actions)                                 │
│  ├─ Configuration (.env, networks)                              │
│  ├─ Testing & Validation (37/37 tests)                          │
│  └─ Documentation & Logging                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓ deploys & configures
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: APPLICATION                                           │
│  ├─ Telegram Bot (aiogram, 50+ handlers)                        │
│  ├─ WebApp Wallet (Vue.js, non-custodial)                       │
│  ├─ WordPress Plugin (WooCommerce bridge)                       │
│  └─ Seller App (планируется)                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓ uses APIs from
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: INTEGRATION                                           │
│  ├─ Python Backend (FastAPI + aiogram)                          │
│  │  ├─ BlockchainService                                        │
│  │  ├─ ProductRegistryService                                   │
│  │  ├─ StorageService (ArWeave/IPFS)                            │
│  │  └─ PaymentService                                           │
│  ├─ Service Factory Pattern                                     │
│  ├─ WordPress API Bridge                                        │
│  └─ Web3.py / ethers.js                                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓ interacts with
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: SMART CONTRACTS (25+ contracts)                       │
│  ├─ Economic Contracts                                          │
│  │  ├─ LoveEmissionEngine (token mining)                        │
│  │  ├─ AmanitaToken (ERC-20, 888M supply)                       │
│  │  ├─ AmanitaGovToken (ERC-20Votes)                            │
│  │  └─ LoveDoPostNFT (ERC-721, social proof)                    │
│  ├─ Access Control & Social Capital                             │
│  │  ├─ SpiralEngine (UUPS, ERC721, IERC5192)                    │
│  │  │   └─ 12-invite system (Soulbound NFTs)                    │
│  │  └─ Soul* Contracts (SBT ecosystem, EIP-5192)                │
│  │     └─ SoulIdentity integration (delegation)                 │
│  ├─ Product & Component Registry                                │
│  │  ├─ ProductRegistry (UUPS)                                   │
│  │  └─ OrganicComponentRegistry (UUPS)                          │
│  └─ Infrastructure                                              │
│     ├─ AmanitaRegistry (central registry)                       │
│     ├─ Orders (OTP validation)                                  │
│     ├─ AmanitaPaymentRouter (stablecoin payments)               │
│     └─ AmanitaInternational (localization, 3-contract)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ runs on
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: INFRASTRUCTURE                                        │
│  ├─ Blockchain: Polygon PoS (+ Mumbai testnet)                  │
│  ├─ Storage: ArWeave (permanent) + IPFS/Pinata (gateway)        │
│  ├─ Serverless: Supabase Edge Functions (Deno + WASM)           │
│  └─ RPC: Alchemy/Infura endpoints                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 LAYER RESPONSIBILITIES

### Layer 1: Infrastructure
**Формирует:** Polygon blockchain, ArWeave/IPFS storage, Supabase Edge Functions  
**Производит:** Block confirmations, storage links (CIDs), event logs, RPC responses

### Layer 2: Smart Contracts
**Формирует:** 25+ Solidity contracts (UUPS upgradeable), token systems, access control  
**Производит:** Token emissions, invite NFTs (ERC721), product/component IDs, events, on-chain state  
**⚠️ NOTE:** InviteNFT.sol НЕ СУЩЕСТВУЕТ - вся функциональность инвайтов в SpiralEngine.sol

### Layer 3: Integration
**Формирует:** Python Backend (FastAPI), Service Factory, Web3.py/ethers.js, WordPress API  
**Производит:** REST APIs, blockchain transaction orchestration, data transformations

### Layer 4: Application
**Формирует:** Telegram Bot, WebApp Wallet, WordPress Plugin  
**Производит:** User interfaces, forms, commands, notifications, transaction approvals

### Layer 5: Deployment & Management
**Формирует:** deploy_full.js (19 actions), testing suite, configuration  
**Производит:** Deployed contracts, verified code, logs, state snapshots, documentation

---

## 🔄 KEY DATA FLOWS

### Flow 1: User Activation (Invite System)
```
Bot → Backend → SpiralEngine.activateUser() → Mints 12 InviteNFTs → Events → Bot notification
```

### Flow 2: Product Creation
```
App → StorageService (ArWeave upload) → ProductRegistry.createProduct(CID) → Event → Cache update
```

### Flow 3: Social Mining (LoveDo → Tokens)
```
Bot → LoveDoPostNFT.mint() → Seller superlikes → LoveEmissionEngine → 1 AMANITA + 1 AGOV
```

### Flow 4: Contract Upgrade (UUPS)
```
deploy_full.js → Deploy new Logic → Proxy.upgradeToAndCall() → State preserved → Services restart
```

---

## 🎯 ARCHITECTURAL PRINCIPLES

1. **Separation of Concerns** - каждый слой имеет четкую ответственность
2. **UUPS Upgradeability** - 3 core contracts upgradeable без потери данных
3. **Decentralization** - non-custodial wallets, IPFS/ArWeave storage, governance
4. **Modularity** - Service Factory, numbered actions, shareable components
5. **Security** - AccessControl, ReentrancyGuard, Pausable, input validation

---

## 💡 KEY INNOVATIONS

### Triple Token System
- **$AMANITA** (utility) - seller rewards, 888M supply
- **$AGOV** (governance) - ERC20Votes, 8 LoveDo threshold
- **Invite NFTs** (social capital) - ERC721 в SpiralEngine, 12 per user, Soulbound (IERC5192)

### Social Mining Mechanism
- **LoveDo Posts** → **Superlikes** → **Token Emission** (1 AMANITA + 1 AGOV per superlike)
- **Monthly Limits:** 8 posts/user, 8 superlikes/seller
- **Reputation Threshold:** 8 LoveDo posts required for AGOV activation

### UUPS Proxy Pattern
- **Contracts:** SpiralEngine, ProductRegistry, OrganicComponentRegistry
- **Upgradeable Logic** without data loss
- **UPGRADER_ROLE** protected

### Component-Based Products
- **Shareable Library:** OrganicComponentRegistry (community-driven)
- **Features & Forms:** Centralized dictionaries (features.json, component_forms.json)
- **Version Tracking:** Incremental catalogVersion for sync

---

## 📈 TECHNICAL METRICS

| Metric | Value |
|--------|-------|
| **Smart Contracts** | 25+ deployed |
| **UUPS Upgradeable** | 3 core contracts |
| **Test Coverage** | 37/37 (100% for OrganicComponentRegistry) |
| **API Endpoints** | 50+ (FastAPI) |
| **Bot Handlers** | 50 handlers (aiogram) |
| **Deployment Actions** | 19 numbered actions |
| **Supported Networks** | 3 (Hardhat, Polygon, Mumbai) |
| **Token Supply** | 888,888,888 AMANITA |
| **Invite Limit** | 12 per activated user |
| **Social Mining Rate** | 1 token/superlike |

---

## 🔗 INTEGRATION MATRIX

| Component | Integrates With | Integration Type |
|-----------|-----------------|------------------|
| **SpiralEngine** | ProductRegistry, OrganicComponentRegistry | Role validation (SELLER_ROLE) |
| **SpiralEngine** | SoulIdentity | SBT delegation (EIP-5192) |
| **LoveEmissionEngine** | LoveDoPostNFT | Token emission on superlike |
| **ProductRegistry** | OrganicComponentRegistry | Component validation |
| **OrganicComponentRegistry** | AmanitaInternational | Localization (planned) |
| **Python Backend** | All Smart Contracts | Web3.py/ethers.js calls |
| **Telegram Bot** | Python Backend | aiogram → FastAPI |
| **WordPress Plugin** | Python Backend | REST API bridge |
| **WebApp Wallet** | Python Backend | Vue.js → FastAPI |
| **deploy_full.js** | All Contracts | Deployment & upgrades |

---

## 🚀 DEPLOYMENT ACTIONS (19 Actions)

| Action | Description | Scope |
|--------|-------------|-------|
| **0** | Registry Only | AmanitaRegistry deployment |
| **1** | Full Ecosystem | All contracts + integrations |
| **2** | OrganicComponentRegistry | UUPS proxy + logic |
| **3** | ProductRegistry | UUPS proxy + logic |
| **4** | SpiralEngine | UUPS proxy + logic |
| **5** | Single Contract | Deploy any single contract |
| **6** | Upgrade ProductRegistry | UUPS upgrade |
| **7** | Upgrade SpiralEngine | UUPS upgrade |
| **8** | Upgrade OrganicComponentRegistry | UUPS upgrade |
| **555** | Seller + Components | Activation + component upload |
| **777** | Test Connection | Validation & connection test |
| **888** | Full Seller Init | Complete seller onboarding |

---

## 📚 RELATED DOCUMENTATION

**Architecture:**
- [architecture-overview.md](./architecture-overview.md) - Detailed system architecture
- [AIJournal.md](../AIJournal.md) - Comprehensive layer analysis (@analysis.mdc)

**Smart Contracts:**
- [contracts/docs/SpiralEngine.md](../../contracts/docs/SpiralEngine.md) - Core access control
- [contracts/docs/UUPS-Strategy-Analysis.md](../../contracts/docs/UUPS-Strategy-Analysis.md) - Upgrade pattern
- [contracts/docs/OrganicComponentRegistry.md](../../contracts/docs/OrganicComponentRegistry.md) - Component library
- [contracts/docs/ProductRegistry.md](../../contracts/docs/ProductRegistry.md) - Product catalog

**Deployment:**
- [scripts/docs/Deploy_Full.md](../../scripts/docs/Deploy_Full.md) - Deployment guide
- [scripts/docs/Deploy_Architecture.md](../../scripts/docs/Deploy_Architecture.md) - Deployment architecture

**Economy:**
- [concept/Network-Economy.md](../concept/Network-Economy.md) - Economic model & tokenomics

**Methodology:**
- [Zeya888.md](../Zeya888.md) - Vibe-Coding Methodology

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-28  
**Analysis Method:** @analysis.mdc (Zeya888)  
**Status:** ✅ COMPLETE

