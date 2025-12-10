# 🌐 Social Connectivity Architecture в AMANITA Ecosystem

**Version:** 1.0  
**Date:** 2025-12-03  
**Author:** Zeya888  
**Status:** Conceptual Framework

---

## 📊 Executive Summary

AMANITA ecosystem использует **двухслойную модель социальных связей**:

1. **Organic Trust Communities (Implicit Layer)** — автоматически формируются через активации
2. **Explicit Circles (Explicit Layer)** — создаются пользователями как сообщества по интересам

Эти два слоя **дополняют друг друга** и решают разные задачи.

---

## 🔍 Layer 1: Organic Trust Communities (Существует)

### 1.1 Определение

**Organic Trust Community (Органическое Сообщество Доверия):**
- Формируется **автоматически** через механизм активаций в SpiralEngine
- Основано на **инвайт-графе** (кто кого пригласил)
- **Implicit** — пользователь не создает явно, но является частью
- **Неизменяемое** — нельзя покинуть или изменить (on-chain history)

**Простыми словами:**
> "Твое Organic Community = те, кого ты активировал + тот, кто активировал тебя"

---

### 1.2 Техническая Реализация

**Contract:** `contracts/SpiralEngine.sol`

**Storage:**
```solidity
// Line 67: Все активированные пользователи
address[] public activatedUsers;

// Line 75: Кто активировал пользователя (parent в графе)
mapping(address => address) public userActivator;

// Line 81: Кого активировал пользователь (дети в графе)
mapping(address => address[]) public activatedBy;
```

**View Functions:**
```solidity
// Line 298: Размер органического сообщества
function getCircleSize(address activator) public view returns (uint256) {
    return activatedBy[activator].length;
}

// Line 307: Члены органического сообщества
function getCircleMembers(address activator) public view returns (address[] memory) {
    return activatedBy[activator];
}
```

**Graph Structure:**
```
User A (Activator)
  ├─ activatedBy[A] = [B, C, D, ..., M]  (max 12)
  │
  └─ Organic Community "A" = {A, B, C, D, ..., M}

User B (Member of A's community)
  ├─ userActivator[B] = A  (parent)
  ├─ activatedBy[B] = [N, O, P, ...]  (B's own community)
  │
  └─ Organic Community "B" = {B, N, O, P, ...}
```

---

### 1.3 Свойства Organic Communities

**Properties:**

| Property | Value | Rationale |
|----------|-------|-----------|
| **Size** | Fixed (1-13) | Leader + max 12 members |
| **Formation** | Automatic | Через activateUser() |
| **Membership** | Immutable | Записано в blockchain |
| **Hierarchy** | Tree | Parent-child relationships |
| **Trust Basis** | Activation | "I vouched for you" |
| **Purpose** | Trust network | Reputation, matchmaking, dating |

**Constraints:**
```solidity
// Line 371: Circle limit (12 members max)
if (activatedBy[msg.sender].length >= 12) revert CircleLimitReached();

// Line 450: Invite ownership (trust chain)
if (inviteMinter[tokenId] != activator) revert InviteNotFromActivator();
```

---

### 1.4 Use Cases (Existing & Planned)

**✅ Already Implemented:**

**1. Trust Verification (LoveDoPostNFT)**
```solidity
// contracts/docs/LoveDoPostNFT.md:186
// Проверка социальных связей для суперлайков
address inviterOfAuthor = inviteGraph.invitedBy(loveDos[tokenId].author);
address inviterOfLiker = inviteGraph.invitedBy(msg.sender);
require(inviterOfLiker == inviterOfAuthor, "LoveDo: liker not in same circle");
```

**Rationale:**
- Суперлайки только от людей из одного organic community
- Предотвращает sybil attacks
- Trust = "мы из одного круга активаций"

---

**2. Reputation Propagation (SpiralEngine)**
```solidity
// contracts/SpiralEngineLogic.sol:268-270
// Каскадные санкции
if (userActivator[user] != address(0)) {
    activationViolations[userActivator[user]]++;
}
```

**Rationale:**
- Activator несет ответственность за своих активированных
- Нарушения cascading вверх по графу
- Trust = "ты отвечаешь за тех, кого привел"

---

**📋 Planned Use Cases:**

**3. Matchmaking & Dating**

**Concept:**
- Люди из одного organic community имеют **общего активатора**
- Это создает implicit trust ("друзья друзей")
- Можно использовать для matching

**Algorithm:**
```python
def find_potential_matches(user, preferences):
    """
    Находит potential matches в organic trust network.
    Priority: same community > 1 hop away > 2 hops away
    """
    # Get user's organic community
    activator = contract.functions.userActivator(user).call()
    community_members = contract.functions.getCircleMembers(activator).call()
    
    # Priority 1: Same community (siblings)
    same_community = [m for m in community_members if m != user and matches_preferences(m, preferences)]
    
    # Priority 2: 1 hop (activator's other circles, or members' circles)
    one_hop = []
    for sibling in community_members:
        sibling_circle = contract.functions.getCircleMembers(sibling).call()
        one_hop.extend(sibling_circle)
    
    # Priority 3: 2 hops (extended network)
    # ...
    
    return {
        'high_trust': same_community,
        'medium_trust': one_hop,
        'low_trust': two_hop
    }
```

**Benefits:**
- ✅ Trust-based (через activation graph)
- ✅ Privacy-preserving (on-chain только addresses)
- ✅ Sybil-resistant (нельзя fake activations)

---

**4. Interest Graph (Implicit)**

**Concept:**
- Activator выбирает кого активировать (likely схожие интересы)
- Organic communities естественно группируются по интересам
- Можно анализировать для recommendations

**Analysis:**
```python
def analyze_community_interests(community_leader):
    """
    Анализирует интересы organic community через on-chain behavior.
    """
    members = contract.functions.getCircleMembers(community_leader).call()
    
    # Analyze product purchases
    interests = {}
    for member in members:
        products = get_user_purchases(member)
        for product in products:
            category = product.category
            interests[category] = interests.get(category, 0) + 1
    
    # Dominant interests
    dominant = sorted(interests.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return {
        'community': community_leader,
        'size': len(members),
        'top_interests': dominant,
        'diversity': calculate_diversity(interests)
    }
```

**Use Cases:**
- Recommend products based on community interests
- Match communities с similar interests
- Suggest sellers to community

---

**5. Reputation Inheritance**

**Concept:**
- Активатор передает часть репутации активируемому
- Создает incentive активировать качественных пользователей

**Algorithm:**
```python
def calculate_inherited_reputation(user):
    """
    Часть репутации наследуется от activator'а.
    """
    activator = contract.functions.userActivator(user).call()
    
    if activator == '0x0000000000000000000000000000000000000000':
        return 0  # Root (no parent)
    
    activator_reputation = get_reputation(activator)
    inheritance_rate = 0.3  # 30% от activator's reputation
    
    inherited = activator_reputation * inheritance_rate
    
    return inherited
```

---

## 🔍 Layer 2: Explicit Circles (Planned Feature)

### 2.1 Определение

**Explicit Circle (Явный Круг):**
- Создается **пользователем намеренно** (user action)
- Основано на **общих интересах или целях**
- **Explicit** — пользователь явно создает и присоединяется
- **Изменяемое** — можно покинуть, пригласить, исключить

**Простыми словами:**
> "Explicit Circle = Telegram группа on-chain"

**Examples:**
- "Mushroom Foragers Club" (по интересу к грибам)
- "Moscow Amanita Sellers" (по географии)
- "Organic Beauty Products DAO" (по категории товаров)

---

### 2.2 Планируемая Реализация

**Contract:** `contracts/Circles.sol` (future)

**Storage (Planned):**
```solidity
struct Circle {
    uint256 id;
    string name;
    string description;
    address creator;
    address[] members;
    bool isPublic;  // Open vs Closed
    bool daoEnabled;
    mapping(address => bool) isMember;
    mapping(address => CircleRole) memberRoles;
}

mapping(uint256 => Circle) public circles;
mapping(address => uint256[]) public userCircles;  // Circles user is member of
```

**Functions (Planned):**
```solidity
// Create circle
function createCircle(string name, string description, bool isPublic) external returns (uint256);

// Join/Leave
function joinCircle(uint256 circleId) external;  // If public
function leaveCircle(uint256 circleId) external;

// Invite/Remove (for creator/admins)
function inviteToCircle(uint256 circleId, address user) external;
function removeFromCircle(uint256 circleId, address user) external;

// DAO functions
function enableDAO(uint256 circleId) external;  // Make circle into DAO
function createProposal(uint256 circleId, string description) external;
function vote(uint256 circleId, uint256 proposalId, bool support) external;
```

---

### 2.3 Свойства Explicit Circles

**Properties:**

| Property | Value | Rationale |
|----------|-------|-----------|
| **Size** | Variable (5-500+) | No fixed limit |
| **Formation** | Explicit | User clicks "Create Circle" |
| **Membership** | Mutable | Can join/leave |
| **Hierarchy** | Flat | Creator + members (optional roles) |
| **Trust Basis** | Interest | "We share a goal/interest" |
| **Purpose** | Collaboration | DAOs, interest groups, communities |

**Constraints (Planned):**
```solidity
// Minimum viable circle
require(members.length >= 5, "Circle needs at least 5 members");

// Maximum для gas optimization
require(members.length <= 500, "Circle too large for on-chain governance");

// DAO requirements
require(daoEnabled ? members.length >= 10 : true, "DAO needs at least 10 members");
```

---

### 2.4 Use Cases (Future)

**1. Interest-Based Communities**

**Example:**
```
Circle "Amanita Muscaria Enthusiasts":
  Creator: @mycologist_anna
  Members: 47 users
  Type: Public
  Description: "Fans of fly agaric mushrooms"
  
  Features:
  - Shared knowledge base (IPFS content)
  - Group discussions (posts)
  - Collective purchases (group discounts)
```

---

**2. Geographic Communities**

**Example:**
```
Circle "Moscow Sellers Union":
  Creator: @moscow_seller_1
  Members: 23 sellers
  Type: Closed (invite-only)
  Description: "Moscow-based Amanita sellers"
  
  Features:
  - Local logistics coordination
  - Price agreements (no competition)
  - Joint marketing campaigns
```

---

**3. DAO Communities**

**Example:**
```
Circle "Organic Certification DAO":
  Creator: @quality_inspector
  Members: 156 users
  Type: Public
  DAO: Enabled
  Description: "Community governance for organic standards"
  
  Features:
  - Proposal creation (new standards)
  - Voting (weighted by reputation)
  - Treasury management (shared funds)
  - Multi-sig decisions
```

---

**4. Collaboration Circles**

**Example:**
```
Circle "Product Innovation Lab":
  Creator: @researcher_zeya
  Members: 12 experts
  Type: Closed
  Description: "R&D collaboration for new products"
  
  Features:
  - Shared component library
  - Co-creation workflows
  - Intellectual property agreements
  - Revenue sharing
```

---

## 🔄 Comparison: Organic vs Explicit

### 3.1 Side-by-Side Comparison

| Aspect | Organic Trust Communities | Explicit Circles |
|--------|--------------------------|------------------|
| **Formation** | Automatic (через activateUser) | Manual (user creates) |
| **Basis** | Activation / Trust | Interest / Goal |
| **Size** | Fixed (max 13) | Variable (5-500) |
| **Membership** | Immutable | Mutable |
| **Structure** | Tree (parent-child) | Graph (peer-to-peer) |
| **Discovery** | Via activation graph | Via search/browse |
| **Purpose** | Trust network | Collaboration |
| **Contract** | SpiralEngine (exists) | Circles.sol (planned) |
| **Data Source** | `activatedBy[]` mapping | `circles[]` mapping |

---

### 3.2 Relationship Between Layers

**Organic → Explicit Bridge:**

```
Organic Trust Community (User A)
  Members: [B, C, D, ..., M] (12 people A activated)
  
  ↓ (User A создает Explicit Circle)
  
Explicit Circle "A's Mushroom Club"
  Creator: A
  Initial Members: [B, C, D] (subset из organic community)
  + External: [X, Y, Z] (joined via interest, not activated by A)
  
  Total: 6 members (3 from organic + 3 external)
```

**Key Insight:**
- ✅ Organic дает **base trust** (vouching через activation)
- ✅ Explicit дает **purpose** (collaboration на интересах)
- ✅ Combined: Trusted collaboration ✅

---

### 3.3 Data Flow

```
SpiralEngine (Organic Layer)
  ↓
  activatedBy[user] → Organic Community
  ↓
User explores organic community
  ↓
Finds people with shared interests
  ↓
Creates Explicit Circle
  ↓
Invites members (from organic + external)
  ↓
Circle grows & collaborates
  ↓
Forms DAO (if needed)
  ↓
Circles.sol (Explicit Layer)
```

---

## 🎯 4. Use Case Matrix

### 4.1 Matchmaking & Dating

**Scenario:** User ищет romantic partner

**Organic Layer (Trust):**
```python
# Step 1: Find people in organic network (trusted)
same_community = get_community_members(user)  # Siblings (12 max)
one_hop = get_extended_network(user, depth=1)  # Friends of friends (~144)
```

**Explicit Layer (Interest):**
```python
# Step 2: Filter by interests (via Explicit Circles)
user_circles = get_user_circles(user)
# ['Hiking Club', 'Mushroom Foragers', 'Yoga Practitioners']

potential_matches = []
for person in one_hop:
    person_circles = get_user_circles(person)
    common_circles = set(user_circles) & set(person_circles)
    
    if len(common_circles) >= 2:  # Shared interests
        potential_matches.append({
            'user': person,
            'trust_level': calculate_trust(user, person, organic_graph),
            'interest_match': len(common_circles),
            'common_circles': common_circles
        })
```

**Combined Result:**
```python
{
    'user': '0xABC...',
    'trust_level': 0.8,  # From organic (1 hop = medium trust)
    'interest_match': 3,  # 3 common explicit circles
    'common_circles': ['Hiking Club', 'Mushroom Foragers', 'Meditation']
}
```

**Algorithm:**
```
Match Score = (Trust × 0.4) + (Interest × 0.6)
            = (0.8 × 0.4) + (3/5 × 0.6)
            = 0.32 + 0.36
            = 0.68 (Good match!)
```

---

### 4.2 Community Formation → DAO

**Scenario:** Group хочет создать DAO для governance

**Step 1: Organic Foundation (Trust)**
```python
# User A has organic community из 12 человек
organic_members = contract.functions.getCircleMembers(user_a).call()
# [B, C, D, ..., M]

# These are trusted (A vouched for them via activation)
trust_level = "high"
```

**Step 2: Explicit Circle Creation (Purpose)**
```python
# User A creates Explicit Circle
circle_id = circles_contract.functions.createCircle(
    name="Organic Beauty Products DAO",
    description="Governance for organic beauty standards",
    isPublic=True
).call()

# Invite organic community members
for member in organic_members:
    circles_contract.functions.inviteToCircle(circle_id, member).call()
```

**Step 3: Growth Beyond Organic**
```python
# Circle grows via public join (interest-based)
# External user X finds circle via search
circles_contract.functions.joinCircle(circle_id, from=user_x)

# Now circle has:
# - 12 from organic (high trust)
# - 15 external (high interest)
# Total: 27 members
```

**Step 4: DAO Activation**
```python
# Enable DAO when достаточно членов
circles_contract.functions.enableDAO(circle_id).call()

# Now can create proposals
proposal_id = circles_contract.functions.createProposal(
    circleId=circle_id,
    description="Should we certify Product X as organic?"
).call()

# Vote (weighted by reputation from SpiralEngine!)
for member in circle_members:
    weight = get_governance_weight(member, organic_graph)
    circles_contract.functions.vote(proposal_id, support=True, weight=weight).call()
```

---

### 4.3 Product Recommendations

**Scenario:** Recommend products based на social connectivity

**Organic Layer (Social Proof):**
```python
def get_community_popular_products(user):
    """Products popular в organic community"""
    community = get_organic_community(user)
    
    product_votes = {}
    for member in community:
        purchases = get_user_purchases(member)
        for product in purchases:
            product_votes[product.id] = product_votes.get(product.id, 0) + 1
    
    # Most popular в community
    return sorted(product_votes.items(), key=lambda x: x[1], reverse=True)
```

**Explicit Layer (Interest Alignment):**
```python
def get_circle_recommended_products(user):
    """Products recommended в user's explicit circles"""
    user_circles = get_user_circles(user)
    
    recommendations = {}
    for circle in user_circles:
        # Circle может иметь curated product list
        circle_products = get_circle_product_list(circle.id)
        recommendations.update(circle_products)
    
    return recommendations
```

**Combined:**
```python
def hybrid_recommendations(user):
    organic_popular = get_community_popular_products(user)
    circle_recommended = get_circle_recommended_products(user)
    
    # Combine с весами
    hybrid = []
    for product in all_products:
        organic_score = get_score(product, organic_popular)
        circle_score = get_score(product, circle_recommended)
        
        total_score = (organic_score × 0.3) + (circle_score × 0.7)
        hybrid.append((product, total_score))
    
    return sorted(hybrid, key=lambda x: x[1], reverse=True)
```

---

## 🔍 5. Graph Theory Perspective

### 5.1 Organic Communities = Tree Structure

**Properties:**
```
Type: Directed Tree (rooted at deployer)
Nodes: Users
Edges: Activation relationships (activator → activated)
Direction: Parent → Child
Max Degree (out): 12 (circle limit)
Max Degree (in): 1 (один activator)
Cycles: None (tree structure)
```

**Graph Metrics:**
```python
organic_graph = {
    'nodes': len(activatedUsers),
    'edges': sum(len(activatedBy[u]) for u in users),
    'diameter': max_depth,
    'clustering': 0.0,  # Tree has no clustering
    'components': 1  # Connected tree
}
```

---

### 5.2 Explicit Circles = General Graph

**Properties:**
```
Type: Undirected Graph (or multi-graph)
Nodes: Users
Edges: Membership relationships (user ↔ circle)
Direction: Bidirectional
Max Degree: Unlimited (user can join many circles)
Cycles: Yes (complex interconnections)
```

**Graph Metrics:**
```python
explicit_graph = {
    'nodes': len(users) + len(circles),  # Bipartite
    'edges': sum(len(circle.members) for circle in circles),
    'diameter': variable,
    'clustering': high,  # Users in same circles cluster
    'components': multiple  # Many disconnected circles possible
}
```

---

### 5.3 Overlay Graph (Combined)

**When Combined:**
```
User A:
  - Organic: Activated by Deployer (parent)
  - Organic: Activated [B, C] (children)
  - Explicit: Member of ['Hiking Club', 'DAO 1', 'Moscow Sellers']

User B:
  - Organic: Activated by A (parent)
  - Organic: No activations yet (no children)
  - Explicit: Member of ['Hiking Club', 'Newbies Circle']

Connections:
  A ← Deployer (organic, implicit, immutable)
  A → B (organic, implicit, immutable)
  A ↔ 'Hiking Club' (explicit, mutable)
  B ↔ 'Hiking Club' (explicit, mutable)
  
  A and B share:
  - Organic: Parent-child relationship (trust)
  - Explicit: 'Hiking Club' membership (interest)
  
  Combined strength: HIGH (trust + shared interest)
```

---

## 📊 6. Terminology Clarification

### 6.1 Используемые Термины

**В Коде:**

| Term | Meaning | Source | Layer |
|------|---------|--------|-------|
| **Circle** | Activator's activated users | `activatedBy[]` | Organic |
| **Community** | Same as Circle (graph theory) | Calculated | Organic |
| **Member** | User in someone's circle | Array element | Organic |
| **Leader** | Circle creator (activator) | Activator | Organic |

**В Feature (Future):**

| Term | Meaning | Source | Layer |
|------|---------|--------|-------|
| **Explicit Circle** | User-created group | `circles[]` | Explicit |
| **Community** | Large explicit circle (50+ members) | Size threshold | Explicit |
| **Member** | User who joined circle | `circle.members[]` | Explicit |
| **Creator** | Circle founder | `circle.creator` | Explicit |
| **Admin** | Circle manager (delegated role) | `circle.admins[]` | Explicit |

---

### 6.2 Recommended Naming Convention

**To Avoid Confusion:**

**Organic Layer:**
- Use: **"Activation Circle"** or **"Trust Circle"**
- Example: "User A's activation circle"
- Code: `activatedBy[userA]`

**Explicit Layer:**
- Use: **"Interest Circle"** or just **"Circle"**
- Example: "Hiking Club circle"
- Code: `circles[circleId]`

**Combined:**
- Use: **"Community"** for large groups (50+ members)
- Can be organic (if activator activated 50+) OR explicit (if circle has 50+ members)

---

## 🎯 7. Integration Points

### 7.1 Organic → Explicit Flow

**User Journey:**

```
1. User gets activated (joins organic network)
   ↓
2. Explores their activation circle (organic)
   ↓
3. Finds people with shared interests
   ↓
4. Creates Explicit Circle (or joins existing)
   ↓
5. Invites trusted members from organic circle
   ↓
6. Circle grows via public join (interest-based)
   ↓
7. Circle forms DAO (if size > threshold)
```

**Code Integration:**
```solidity
// In Circles.sol (future)
function createCircleFromActivationCircle(string name) external {
    // Pre-populate с organic community
    address[] memory organicMembers = spiralEngine.getCircleMembers(msg.sender);
    
    uint256 circleId = _createCircle(name, msg.sender);
    
    // Auto-invite organic community
    for (uint i = 0; i < organicMembers.length; i++) {
        _inviteToCircle(circleId, organicMembers[i]);
    }
    
    return circleId;
}
```

---

### 7.2 Trust Verification для Explicit Circles

**Use Organic для Trust в Explicit:**

```solidity
// In Circles.sol
function verifyMemberTrust(uint256 circleId, address newMember) public view returns (uint8) {
    Circle storage circle = circles[circleId];
    
    // Check organic connections to existing members
    uint8 trustScore = 0;
    
    for (uint i = 0; i < circle.members.length; i++) {
        address existingMember = circle.members[i];
        
        // Same organic community (siblings)?
        address newMemberActivator = spiralEngine.userActivator(newMember);
        address existingMemberActivator = spiralEngine.userActivator(existingMember);
        
        if (newMemberActivator == existingMemberActivator) {
            trustScore += 10;  // High trust (same activator)
        }
        
        // Direct activation relationship?
        if (spiralEngine.userActivator(newMember) == existingMember) {
            trustScore += 20;  // Very high (parent-child)
        }
        
        // 1 hop away?
        // ... (check circles)
    }
    
    return trustScore;
}
```

**Use Cases:**
- Auto-approve members с high organic trust
- Flag suspicious members (no organic connections)
- Prioritize invites to organic-connected users

---

## 📊 8. Data Structure Summary

### 8.1 On-Chain State (Organic)

**Location:** SpiralEngine contract

```javascript
// Query organic network
const organicNetwork = {
    totalUsers: await spiralEngine.activatedUsers.length,
    
    // For each user
    users: await Promise.all(allUsers.map(async (user) => ({
        address: user,
        activator: await spiralEngine.userActivator(user),
        circle: await spiralEngine.getCircleMembers(user),
        circleSize: await spiralEngine.getCircleSize(user),
        generation: calculateGeneration(user)
    })))
};
```

**Storage Cost:** FREE (already in contract) ✅

---

### 8.2 On-Chain State (Explicit) — Future

**Location:** Circles contract (planned)

```javascript
// Query explicit circles
const explicitCircles = {
    totalCircles: await circles.totalCircles(),
    
    // For each circle
    circles: await Promise.all(allCircles.map(async (id) => ({
        id: id,
        name: await circles.circleName(id),
        creator: await circles.circleCreator(id),
        members: await circles.getCircleMembers(id),
        isPublic: await circles.isPublic(id),
        daoEnabled: await circles.daoEnabled(id)
    })))
};
```

**Storage Cost:** ~200k gas per circle creation

---

### 8.3 Off-Chain Analytics Storage

**Location:** Database or JSON exports

**Organic Network Export:**
```json
{
  "metadata": {
    "exported_at": "2025-12-03T10:00:00Z",
    "total_nodes": 157,
    "total_communities": 13,
    "max_generation": 2
  },
  "nodes": [
    {
      "address": "0x8F62...",
      "generation": 0,
      "circleSize": 12,
      "role": "deployer"
    },
    ...
  ],
  "edges": [
    {"from": "0x8F62...", "to": "0xABC...", "type": "activation"},
    ...
  ],
  "communities": [
    {
      "id": "root",
      "leader": "0x8F62...",
      "members": ["0xABC...", "0xDEF...", ...],
      "size": 13,
      "type": "organic"
    },
    ...
  ]
}
```

**Explicit Circles Export (Future):**
```json
{
  "circles": [
    {
      "id": 1,
      "name": "Mushroom Foragers Club",
      "creator": "0xABC...",
      "members": ["0xABC...", "0xDEF...", ...],
      "size": 47,
      "isPublic": true,
      "daoEnabled": false,
      "type": "explicit"
    },
    ...
  ]
}
```

---

## 🎯 9. Implementation Priorities

### 9.1 Current Sprint (Now)

**Focus:** Organic Trust Communities

**Tasks:**
1. ✅ Build exponential network через tests
2. ✅ Export organic graph to JSON
3. ✅ Visualize activation communities
4. ✅ Test trust-based features (matchmaking algorithms)

**Deliverable:** Realistic organic network для testing

---

### 9.2 Future Sprint (After Circles Feature)

**Focus:** Explicit Circles Integration

**Tasks:**
1. Implement `Circles.sol` contract
2. Build UI для circle creation/management
3. Integrate organic trust scoring
4. Enable DAO formation from circles
5. Test hybrid (organic + explicit) algorithms

**Deliverable:** Full dual-layer social connectivity

---

## 📌 10. Key Takeaways

### Organic Trust Communities (Implicit, Exists)
- ✅ **Source:** SpiralEngine `activatedBy[]`
- ✅ **Basis:** Activation / Vouching
- ✅ **Purpose:** Trust network, reputation, matchmaking
- ✅ **Size:** Fixed (1-13)
- ✅ **Formation:** Automatic
- ✅ **Example:** "Deployer's activation circle" = 12 people deployer activated

### Explicit Circles (Explicit, Planned)
- 📋 **Source:** Circles.sol (future)
- 📋 **Basis:** Shared interest / goal
- 📋 **Purpose:** Collaboration, DAO, communities
- 📋 **Size:** Variable (5-500)
- 📋 **Formation:** Manual (user creates)
- 📋 **Example:** "Mushroom Foragers Club" = 47 members joined voluntarily

### Why Both?
```
Organic = WHO you trust (activation graph)
Explicit = WHAT you're interested in (interest graph)
Combined = Trusted collaboration ✅
```

---

## 🚀 Next Steps

**For Testing Infrastructure:**
1. Build organic network через exponential test growth
2. Export graph with "communities" labeled
3. Use для testing trust algorithms

**For Product:**
1. Document distinction clearly (this doc!)
2. Plan Circles.sol contract architecture
3. Design UI для both layers

**Terminology:**
- Tests: Use "organic community" or "activation circle"
- Product: Use "Circle" для explicit feature
- Combined: Use "trust network" + "interest network"

---

**Файл создан:** `docs/concept/connectivity.md` ✅

Теперь понятно различие? 🎯


