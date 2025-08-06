# Amanita

## 🌱 Overview
Amanita is a decentralized ecosystem for p2p commerce, loyalty, and reputation, uniting Telegram bots, a WebApp wallet, a WordPress plugin, and smart contracts on Polygon. The project is built on principles of openness, autonomy, and social value.

## 🎯 Project Mission
To create an open, ethical, and scalable platform for fair trade and cooperation, where anyone can be a seller, buyer, or promoter, and trust and rewards are built on transparent smart contracts and social reputation.

## 🏗️ Amanita Architecture
- **Telegram Bot** — the main user interface for sellers and buyers
- **WebApp Wallet** — a non-custodial wallet for managing assets and invites
- **WordPress Plugin** — a bridge between WooCommerce and the Amanita ecosystem
- **Python Backend/API** — services for catalog, orders, users, and blockchain integration
- **Smart Contracts (Solidity, Polygon)** — InviteNFT, AmanitaToken, OrderNFT, ReviewNFT, AmanitaSale
- **Supabase Edge Functions** — ArWeave integration for data storage

## 🔑 Key Components
- **Invite NFT** — invitation and trust system (ERC-721)
- **AMANITA Coin** — non-transferable loyalty token (ERC-20)
- **Order NFT** — on-chain purchase receipts
- **Review NFT** — reviews and reputation
- **API** — secure HMAC REST API for integrations
- **WebApp** — wallet and user interface
- **WordPress Plugin** — catalog and order sync with WooCommerce

## ⚙️ How It Works between sellers' e-commerce bots and consumers

### For Sellers (Seller Nodes)
Each seller is a **seller node** with their own e-commerce solution deployed through a network of partner IT companies. We provide the **Amanita bridge** from WooCommerce (and other e-commerce platforms) to our Python3 web service, which communicates on behalf of the seller with shared smart contracts that solve tasks similar to centralized marketplaces like Amazon.

**What Amanita collects from sellers' e-commerce platforms:**
- **Product catalog** — for sharing between sellers, implementing cross-selling mechanisms with rewards in the shared $AMANITA ecosystem token
- **Sales history** — for credibility and transparency across the network
- **User base** — through SBT (Soulbound Token) = Invite NFT, activated by unique codes. Each new user receives 12 codes after activation, and sellers can distribute invites at their discretion (configurable integration with loyalty schemes)

### For Consumers
1. **User onboarding** starts with a warm welcome and a brief explanation of the closed, invite-only nature of Amanita.
2. **Language selection** — the user chooses their preferred language (10+ supported).
3. **Invite code entry**:
   - If the bot is launched via a link with an invite code, it is auto-filled.
   - Otherwise, the user is prompted to enter or paste an invite code manually.
   - The code is validated on-chain (InviteNFT smart contract).
4. **Wallet creation** — after successful invite validation, the user creates a non-custodial wallet via the integrated WebApp (Telegram WebApp API).
5. **Access to main menu** — the user can now browse the product catalog, manage their cart, view order history, invite friends, and contact support.
6. **Help is always available** — at every step, a "Help" button provides FAQ or direct support.

## 👥 Who Is It For
- **Small and medium sellers** — quick start without a website or complex integration
- **Buyers** — transparent conditions, reviews, participation bonuses
- **Developers** — open API, extensible architecture, WooCommerce integration
- **Web3 enthusiasts** — fair tokenomics, DAO, social mining

## 🚀 Getting Started
1. **Join Amanita via Telegram Bot**:
   - Launch the bot and select your language.
   - Enter your invite code (or use a link with a code from an existing member).
   - Follow the simple onboarding steps — no crypto experience required.
2. **Create your wallet** in the WebApp (guided, secure, non-custodial).
3. **Explore the ecosystem**:
   - Browse products, make your first purchase, invite friends, or connect your WooCommerce store.
4. **Need help?** Use the in-bot Help button or see the [documentation](docs/doc-master.md).

## 📚 Documentation
- [AI-Navigator.md](AI-Navigator.md) — working diary and decision history
- [Manifest & Mission](docs/manifest.md)
- [Architecture & Components](docs/architecture-overview.md)
- [Network Economy](docs/Network-Economy.md) — tokenomics and social mining mechanics
- [API & Integrations](docs/webapi-overview.md)
- [Smart Contracts](docs/contracts-overview.md)

## 💬 Contacts & Support
- Telegram: [@zeya888](https://t.me/zeya888)
- Email: zeya.metsapuu@gmail.com
- Issues: [GitHub Issues](https://github.com/ViralLove/amanita/issues)

---
Amanita — fair trade, trust, and cooperation in every Invite NFT.
