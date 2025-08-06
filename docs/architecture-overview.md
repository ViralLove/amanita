# Amanita Architecture Overview

## System Vision

Amanita is a decentralized ecosystem that bridges traditional e-commerce with blockchain technology, creating a network of seller nodes connected through shared smart contracts. Each seller maintains their own e-commerce solution while participating in a collective marketplace infrastructure.

## Core Architecture Principles

- **Decentralized Seller Nodes**: Each seller operates independently with their own e-commerce platform
- **Shared Blockchain Infrastructure**: Common smart contracts provide marketplace functionality
- **Bridge Architecture**: Amanita connects existing e-commerce systems to blockchain
- **Trust Through Technology**: Invite system and on-chain reputation ensure community quality
- **Cross-Seller Cooperation**: Product sharing and cross-selling with shared rewards

## High-Level System Components

### 🏗️ **Core Infrastructure Layer**

#### **Blockchain Network (Polygon)**
- **Smart Contracts**: InviteNFT, ProductRegistry, LoveDoPostNFT, LoveEmissionEngine, AmanitaToken and more
- **Purpose**: Trust, reputation, product registry, social mining, shared loyalty systems
- **Key Features**: Low-cost transactions, fast confirmation, Ethereum compatibility

#### **Decentralized Storage**
- **Primary**: ArWeave (permanent, decentralized storage)
- **Fallback**: Pinata (IPFS gateway for compatibility)
- **Purpose**: Product metadata, images, descriptions, user data

#### **Supabase Edge Functions**
- **Purpose**: Serverless infrastructure for ArWeave integration
- **Features**: WebAssembly modules for cryptographic operations
- **Integration**: Python backend ↔ Edge Functions ↔ ArWeave

### 🤖 **User Interface Layer**

#### **Telegram Bot**
- **Purpose**: Primary user interface for onboarding and interaction
- **Features**: 
  - Multi-language support (12+ languages)
  - FSM (Finite State Machine) for user flow management
  - Invite code validation and user onboarding
  - Product catalog browsing and ordering
- **Integration**: Connects to Python backend via API

#### **WebApp Wallet**
- **Purpose**: Non-custodial wallet interface
- **Features**:
  - Wallet creation and recovery
  - Transaction signing
  - Seed phrase management
  - Integration with Telegram WebApp API
- **Security**: Client-side key generation, no server-side storage

#### **WordPress Plugin**
- **Purpose**: Bridge between WooCommerce and Amanita ecosystem
- **Features**:
  - Product catalog synchronization
  - Order management integration
  - HMAC authentication with Python API
  - Automatic seller node setup

### 🔗 **Integration Layer**

#### **Python Backend/API**
- **Purpose**: Central orchestration and business logic
- **Architecture**: FastAPI with microservice pattern
- **Key Services**:
  - BlockchainService (singleton for all blockchain operations)
  - ProductRegistryService (product management)
  - AccountService (user and seller management)
  - StorageService (IPFS/ArWeave operations)
- **Security**: HMAC authentication, input validation, rate limiting

#### **Service Factory Pattern**
- **Purpose**: Centralized service management and dependency injection
- **Benefits**: Singleton management, clean dependency graph, testability
- **Services**: All business logic services created and managed centrally

### 📦 **Smart Contract Ecosystem**

#### **InviteNFT (ERC-721)**
- **Purpose**: Access control and trust system
- **Features**: Unique invite codes, one-time use, inviter tracking
- **Integration**: Telegram bot validation, user onboarding
- **Details**: See [Network Economy](Network-Economy.md) for invite system mechanics and social capital model

#### **ProductRegistry**
- **Purpose**: Decentralized product catalog
- **Features**: Product metadata storage, seller association, cross-selling
- **Integration**: Python API, WordPress plugin, catalog synchronization

#### **LoveEmissionEngine**
- **Purpose**: Social mining and token distribution
- **Features**: $LOVE token rewards, reputation building, community engagement
- **Integration**: Telegram bot, user activities, cross-seller cooperation
- **Details**: See [Network Economy](Network-Economy.md) for social mining mechanics and economic model

#### **AmanitaToken (ERC-20)**
- **Purpose**: Non-transferable loyalty token for sales stimulation
- **Features**: 
  - Mined through loyalty programs and burned on first payment
  - Payment only from users to sellers (inter-user transfers prohibited)
  - Stimulates sales and cross-selling within the ecosystem
  - Internal ecosystem currency for seller rewards
- **Integration**: LoveEmissionEngine, seller rewards, user benefits
- **Details**: See [Network Economy](Network-Economy.md) for comprehensive tokenomics

#### **LoveToken (ERC-20)**
- **Purpose**: Universal P2P token across all themed ecosystems
- **Features**:
  - Social emission based on LoveDoPostNFT activities
  - Issued but never burned (permanent supply)
  - Universal across all themed ecosystems (Amanita is first example - folk medicine)
  - P2P transfers between any roles allowed
  - Used alongside InviteNFT in all ecosystems
- **Integration**: Cross-ecosystem compatibility, universal reputation system

#### **LoveGovToken (ERC-20)**
- **Purpose**: Governance token for collective action and OpenGov
- **Features**:
  - Triggered by $LOVE mining activities
  - Enables coalition formation for large-scale projects
  - Supports collective property acquisition, facility rentals, and other capital-intensive tasks
  - Part of OpenGov system for decentralized decision-making
- **Integration**: Coalition governance, collective resource management

### 🌐 **Themed Ecosystem Architecture**

#### **Ecosystem Organization**
- **Thematic Focus**: Each ecosystem specializes in specific industries or themes
- **Amanita Example**: First ecosystem focused on natural remmidies (biohacking)
- **Cross-Ecosystem**: $LOVE and InviteNFT work across all themed ecosystems
- **Shared Infrastructure**: Common blockchain and storage infrastructure

#### **Ecosystem Benefits**
- **Specialized Knowledge**: Deep expertise in specific domains
- **Targeted Communities**: Focused user bases with shared interests
- **Cross-Selling**: Products and services shared across related ecosystems
- **Collective Growth**: Shared resources and knowledge across themes

### 🌐 **External Integrations**

#### **E-commerce Platforms**
- **WooCommerce**: Primary integration via WordPress plugin
- **Other Platforms**: Extensible architecture for additional e-commerce systems
- **Purpose**: Product catalog and order management

#### **Telegram Platform**
- **Bot API**: User interaction and onboarding
- **WebApp API**: Wallet interface integration
- **Purpose**: User experience and wallet management

#### **Blockchain Infrastructure**
- **Polygon RPC**: Transaction processing and contract interaction
- **Web3 Providers**: Infura, Alchemy, or custom nodes
- **Purpose**: Blockchain connectivity and transaction management

## Data Flow Architecture

### **User Onboarding Flow**
1. User receives invite code (link or manual entry)
2. Telegram bot validates code through InviteNFT contract
3. User creates wallet via WebApp
4. User gains access to ecosystem features

*For detailed economic flows and token distribution, see [Network Economy](Network-Economy.md)*

### **Product Management Flow**
1. Seller uploads catalog via WordPress plugin or API
2. Products stored in ArWeave with metadata
3. ProductRegistry contract updated with new entries
4. Products available for cross-selling across network

### **Transaction Flow**
1. User selects products from any seller
2. Order processed through seller's e-commerce system
3. Transaction recorded on blockchain
4. Rewards distributed via LoveEmissionEngine

*For comprehensive tokenomics and social mining details, see [Network Economy](Network%20Economy.md)*

## Security Architecture

### **Authentication & Authorization**
- **HMAC Authentication**: API security with shared secrets
- **Invite System**: Access control through unique codes
- **Wallet Security**: Non-custodial, client-side key management

### **Data Protection**
- **Decentralized Storage**: No single point of failure
- **Encryption**: Sensitive data encrypted at rest and in transit
- **Privacy**: User data remains under user control

### **Smart Contract Security**
- **Audited Contracts**: Professional security audits
- **Access Control**: Role-based permissions and multisig capabilities
- **Upgradeability**: Controlled upgrade mechanisms for critical contracts

## Scalability Considerations

### **Horizontal Scaling**
- **Microservice Architecture**: Independent scaling of components
- **Edge Functions**: Serverless scaling for storage operations
- **Database Sharding**: User data distributed across nodes

### **Performance Optimization**
- **Caching**: Multi-layer caching for frequently accessed data
- **CDN**: Content delivery for product images and metadata
- **Async Processing**: Non-blocking operations for better responsiveness

### **Network Growth**
- **Seller Node Expansion**: New sellers can join without infrastructure changes
- **Cross-Seller Discovery**: Products automatically available across network
- **Token Economics**: Incentivized growth through $AMANITA rewards

*For detailed economic model and growth mechanics, see [Network Economy](Network-Economy.md)*

## Deployment Architecture

### **Infrastructure Components**
- **Python Backend**: Containerized deployment with load balancing
- **Telegram Bot**: Stateless service with horizontal scaling
- **WebApp**: Static hosting with CDN
- **WordPress Plugin**: Distributed across seller websites
- **Smart Contracts**: Deployed on Polygon mainnet

### **Monitoring & Observability**
- **Logging**: Structured logging across all components
- **Metrics**: Performance and business metrics collection
- **Health Checks**: Automated monitoring of all services
- **Alerting**: Proactive notification of issues

## Future Architecture Evolution

### **DAO Governance**
- **Multisig Contracts**: Community-controlled upgrades
- **Voting Mechanisms**: Token-based governance
- **Proposal System**: Community-driven development

### **Advanced Features**
- **AI Integration**: Product recommendations and fraud detection
- **Mobile Apps**: Native mobile applications
- **Advanced Analytics**: Cross-seller insights and optimization

### **Interoperability**
- **Cross-Chain**: Integration with other blockchain networks
- **Standards**: Adoption of emerging Web3 standards
- **APIs**: Open APIs for third-party integrations

---

*This architecture overview provides a high-level understanding of the Amanita ecosystem components and their interactions. For detailed implementation specifics, refer to the individual component documentation.*

## 📊 **Related Documentation**

For comprehensive understanding of the economic model and tokenomics:
- **[Network Economy](Network-Economy.md)** — Detailed tokenomics, social mining mechanics, and economic sustainability model
