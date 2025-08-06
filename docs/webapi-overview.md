# Web API Overview - AMANITA Ecosystem

## Overview
This document provides a comprehensive overview of the AMANITA Web API, its architecture, services, and implementation details. The API serves as the backend for the decentralized social commerce platform, providing REST endpoints for product management, authentication, and blockchain integration.

**Related Documentation:**
- **[README.md](../README.md)** — Project overview and getting started
- **[Architecture Overview](architecture-overview.md)** — System architecture and components
- **[Network Economy](Network-Economy.md)** — Economic model and tokenomics
- **[Smart Contracts](contracts-overview.md)** — Blockchain contract documentation

## API Architecture

### Technology Stack
- **Framework:** FastAPI (Python 3.8+)
- **Authentication:** HMAC-SHA256 with timestamp validation
- **Database:** Supabase (PostgreSQL)
- **Blockchain:** Web3.py with Polygon integration
- **Storage:** IPFS/ArWeave for metadata
- **Documentation:** OpenAPI/Swagger

### Core Components

#### **FastAPI Application**
**Entry Point:** `bot/api/main.py`

**Key Features:**
- CORS middleware for web client support
- Trusted Host middleware for security
- HMAC authentication middleware
- Global error handlers
- Health check endpoints
- Service Factory integration

**Configuration:**
```python
# Environment-based configuration
API_TITLE = "AMANITA API"
API_VERSION = "1.0.0"
HOST = "0.0.0.0"
PORT = 8000
```

#### **Service Factory Pattern**
**File:** `bot/services/service_factory.py`

**Purpose:** Centralized service management and dependency injection

**Services:**
- BlockchainService (singleton)
- AccountService
- ApiKeyService
- ProductRegistryService
- ProductStorageService
- ProductValidationService

**Benefits:**
- Singleton management for expensive resources
- Clean dependency graph
- Easy testing and mocking
- Centralized service lifecycle

## API Endpoints

### Public Endpoints

#### **Health Check**
```http
GET /health
GET /health/detailed
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1640995200,
  "uptime": "2h 30m 15s",
  "version": "1.0.0"
}
```

#### **Documentation**
```http
GET /docs          # Swagger UI
GET /redoc         # ReDoc
GET /openapi.json  # OpenAPI schema
```

### Authenticated Endpoints

#### **API Key Management**
```http
POST   /api-keys/                    # Create API key
GET    /api-keys/{client_address}    # Get client keys
DELETE /api-keys/{api_key}           # Revoke key
GET    /api-keys/validate/{api_key}  # Validate key
```

**Create API Key Request:**
```json
{
  "client_address": "0x1234...",
  "description": "WooCommerce integration"
}
```

**Response:**
```json
{
  "success": true,
  "api_key": "ak_22bc74537e53698e",
  "secret_key": "sk_9160864a1ba617780cce32258248c21d085d8ddb18d3250ff4532925102d1b68",
  "request_id": "req_1234567890",
  "timestamp": 1640995200
}
```

#### **Product Management**
```http
POST   /products/upload              # Upload products
PUT    /products/{product_id}        # Update product
POST   /products/{product_id}/status # Update status
```

**Product Upload Request:**
```json
{
  "products": [
    {
      "id": "prod_123",
      "title": "Organic Herbs",
      "description": {"en": "Premium organic herbs"},
      "description_cid": "QmHash...",
      "cover_image": "QmImageHash...",
      "gallery": ["QmHash1...", "QmHash2..."],
      "categories": ["herbs", "organic"],
      "form": "powder",
      "species": "chamomile",
      "prices": [{"currency": "USD", "amount": 29.99}],
      "attributes": {"sku": "HERB001", "stock": 100}
    }
  ]
}
```

#### **Media Management**
```http
POST /media/upload     # Upload media files
GET  /media/{file_id}  # Get media info
```

#### **Description Management**
```http
POST /description/upload  # Upload product descriptions
GET  /description/{id}    # Get description
```

## Authentication System

### HMAC Authentication
**Middleware:** `bot/api/middleware/auth.py`

**Security Features:**
- HMAC-SHA256 signature validation
- Timestamp-based replay attack protection
- Nonce-based duplicate request prevention
- API key validation
- Configurable time windows

**Required Headers:**
```http
X-API-Key: ak_22bc74537e53698e
X-Timestamp: 1640995200
X-Nonce: unique_nonce_string
X-Signature: hmac_sha256_signature
```

**Signature Generation:**
```python
message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
signature = hmac.new(secret_key, message.encode(), hashlib.sha256).hexdigest()
```

**Configuration:**
```python
HMAC_TIMESTAMP_WINDOW = 300  # 5 minutes
HMAC_NONCE_CACHE_TTL = 600   # 10 minutes
```

### API Key Formats
- **Amanita Format:** `ak_` + 16 characters
- **Secret Key:** `sk_` + 64 hex characters
- **Traditional:** 64 hex characters

## Core Services

### BlockchainService
**File:** `bot/services/core/blockchain.py`

**Purpose:** Universal blockchain interaction layer

**Key Features:**
- Singleton pattern for resource efficiency
- Contract registry integration
- Multi-profile support (localhost, mainnet, amoy)
- Gas estimation and transaction management
- Error handling and retry logic

**Supported Operations:**
- Contract function calls (read/write)
- Transaction monitoring
- Gas estimation
- Event listening
- Address validation

**Configuration:**
```python
PROFILES = {
    "localhost": {"RPC": "http://127.0.0.1:8545"},
    "mainnet": {"RPC": "https://polygon-mainnet.infura.io/v3/KEY"},
    "amoy": {"RPC": "https://rpc-amoy.polygon.technology"}
}
```

### ApiKeyService
**File:** `bot/services/core/api_key.py`

**Purpose:** API key management and validation

**Features:**
- Key generation and validation
- Client address association
- Revocation support
- Usage tracking
- Security validation

**Key Functions:**
- `create_api_key()` - Generate new API key
- `validate_api_key()` - Validate existing key
- `revoke_api_key()` - Revoke key access
- `get_seller_api_keys()` - List client keys

### AccountService
**File:** `bot/services/core/account.py`

**Purpose:** User account and wallet management

**Features:**
- Wallet creation and validation
- Balance checking
- Transaction history
- Address validation
- Account recovery

### ProductRegistryService
**File:** `bot/services/product/registry.py`

**Purpose:** Product catalog management

**Features:**
- Product creation and updates
- IPFS metadata storage
- Blockchain integration
- Validation and sanitization
- Cross-selling support

**Integration:**
- ProductStorageService for IPFS operations
- ProductValidationService for data validation
- BlockchainService for on-chain operations

## Data Models

### Request Models
```python
# API Key Management
class ApiKeyCreateRequest(BaseModel):
    client_address: str
    description: Optional[str] = None

# Product Management
class ProductUploadIn(BaseModel):
    id: str | int
    title: str
    description: Dict[str, Any]
    description_cid: str
    cover_image: str
    gallery: List[str] = []
    categories: List[str] = []
    form: str
    species: str
    prices: List[Dict[str, Any]]
    attributes: Dict[str, Any] = {}
```

### Response Models
```python
# Health Check
class HealthCheckResponse(BaseModel):
    status: HealthStatus
    timestamp: Timestamp
    uptime: str
    version: str

# API Key Response
class ApiKeyCreateResponse(BaseModel):
    success: bool
    api_key: ApiKey
    secret_key: str
    request_id: RequestId
    timestamp: Timestamp
```

## Error Handling

### Global Error Handlers
**File:** `bot/api/error_handlers.py`

**Handled Exceptions:**
- RequestValidationError (400)
- ValidationError (422)
- HTTPException (custom status)
- StarletteHTTPException (404)
- Unhandled exceptions (500)

**Error Response Format:**
```json
{
  "success": false,
  "error": "validation_error",
  "message": "Validation failed",
  "details": [
    {
      "field": "title",
      "message": "Field required"
    }
  ],
  "timestamp": 1640995200,
  "request_id": "req_1234567890"
}
```

### Custom Exceptions
**File:** `bot/api/exceptions/`

**Authentication Exceptions:**
- AuthenticationError
- InvalidSignatureError
- ExpiredTimestampError
- InvalidTimestampError
- DuplicateNonceError
- MissingHeaderError
- InvalidAPIKeyError

## Configuration

### Environment Variables
```bash
# API Configuration
AMANITA_API_ENVIRONMENT=development
AMANITA_API_HOST=0.0.0.0
AMANITA_API_PORT=8000
AMANITA_API_LOG_LEVEL=INFO

# Security
AMANITA_API_HMAC_SECRET_KEY=your-secret-key
AMANITA_API_HMAC_TIMESTAMP_WINDOW=300
AMANITA_API_HMAC_NONCE_CACHE_TTL=600

# CORS
AMANITA_API_CORS_ORIGINS=*
AMANITA_API_CORS_ALLOW_CREDENTIALS=true

# Trusted Hosts
AMANITA_API_TRUSTED_HOSTS=*
```

### Configuration Classes
**File:** `bot/api/config.py`

**APIConfig Class:**
- Centralized configuration management
- Environment-based settings
- Validation and defaults
- Method-based config retrieval

## Logging and Monitoring

### Logging Configuration
**File:** `bot/utils/logging_setup.py`

**Features:**
- Rotating file handlers
- Structured logging
- Multiple log levels
- Performance tracking
- Error correlation

**Log Format:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "amanita_api",
  "message": "API request processed",
  "request_id": "req_1234567890",
  "user_id": "0x1234...",
  "duration_ms": 150
}
```

### Health Monitoring
**Endpoints:**
- `/health` - Basic health check
- `/health/detailed` - Component-level diagnostics

**Monitored Components:**
- API server status
- Service Factory availability
- Blockchain connectivity
- Database connectivity
- External API status

## Testing

### Test Structure
**Directory:** `bot/tests/api/`

**Test Files:**
- `test_api_auth.py` - Authentication tests
- `test_models.py` - Data model tests
- `test_error_handlers.py` - Error handling tests
- `test_data.py` - Test data fixtures

### Test Coverage
- ✅ HMAC authentication (100%)
- ✅ Data validation (100%)
- ✅ Error handling (100%)
- ✅ Health endpoints (100%)
- ✅ API key management (100%)

### Running Tests
```bash
# All API tests
python3 -m pytest tests/api/ -v

# Specific test file
python3 -m pytest tests/api/test_api_auth.py -v

# With coverage
python3 -m pytest tests/api/ --cov=bot.api --cov-report=html
```

## Performance and Scalability

### Optimization Strategies
- **Singleton Services:** BlockchainService for resource efficiency
- **Async Operations:** Non-blocking I/O for better performance
- **Caching:** Nonce cache for authentication
- **Connection Pooling:** Database and blockchain connections
- **Batch Operations:** Multiple products in single request

### Monitoring Metrics
- Request latency
- Error rates
- Throughput
- Resource usage
- Blockchain transaction success rates

## Security Considerations

### Authentication Security
- HMAC-SHA256 for request signing
- Timestamp validation (5-minute window)
- Nonce-based replay protection
- API key validation and revocation
- Rate limiting (configurable)

### Data Security
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CORS configuration
- Trusted host validation

### Infrastructure Security
- Environment-based configuration
- Secret management
- HTTPS enforcement (production)
- Regular security updates
- Audit logging

## Integration Examples

### WooCommerce Integration
```python
import requests
import hmac
import hashlib
import time

def create_amanita_request(method, path, data, api_key, secret_key):
    timestamp = str(int(time.time()))
    nonce = f"nonce_{int(time.time() * 1000)}"
    
    body = json.dumps(data) if data else ""
    message = f"{method}\n{path}\n{body}\n{timestamp}\n{nonce}"
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
        "X-Signature": signature
    }
    
    return headers

# Example: Upload products
products_data = {
    "products": [
        {
            "id": "wc_product_123",
            "title": "Organic Herbs",
            "description": {"en": "Premium organic herbs"},
            "description_cid": "QmHash...",
            "cover_image": "QmImageHash...",
            "form": "powder",
            "species": "chamomile",
            "prices": [{"currency": "USD", "amount": 29.99}]
        }
    ]
}

headers = create_amanita_request("POST", "/products/upload", products_data, api_key, secret_key)
response = requests.post("http://localhost:8000/products/upload", json=products_data, headers=headers)
```

### WordPress Plugin Integration
```php
// WordPress plugin example
function amanita_upload_product($product_data) {
    $api_key = get_option('amanita_api_key');
    $secret_key = get_option('amanita_secret_key');
    
    $timestamp = time();
    $nonce = 'nonce_' . (time() * 1000);
    
    $body = json_encode($product_data);
    $message = "POST\n/products/upload\n{$body}\n{$timestamp}\n{$nonce}";
    $signature = hash_hmac('sha256', $message, $secret_key);
    
    $headers = [
        'Content-Type: application/json',
        'X-API-Key: ' . $api_key,
        'X-Timestamp: ' . $timestamp,
        'X-Nonce: ' . $nonce,
        'X-Signature: ' . $signature
    ];
    
    $response = wp_remote_post('http://localhost:8000/products/upload', [
        'headers' => $headers,
        'body' => $body
    ]);
    
    return json_decode(wp_remote_retrieve_body($response), true);
}
```

## Deployment

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd amanita

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run API server
cd bot
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Deployment
```bash
# Using Docker
docker build -t amanita-api .
docker run -p 8000:8000 amanita-api

# Using systemd service
sudo systemctl enable amanita-api
sudo systemctl start amanita-api
```

### Environment Configuration
```bash
# Production environment variables
AMANITA_API_ENVIRONMENT=production
AMANITA_API_HOST=0.0.0.0
AMANITA_API_PORT=8000
AMANITA_API_LOG_LEVEL=WARNING
AMANITA_API_HMAC_SECRET_KEY=<production-secret>
AMANITA_API_CORS_ORIGINS=https://yourdomain.com
AMANITA_API_TRUSTED_HOSTS=yourdomain.com
```

---

## 📚 **Documentation Navigation**

**For comprehensive understanding of the Amanita ecosystem:**

- **[README.md](../README.md)** — Project overview, mission, and getting started
- **[Architecture Overview](architecture-overview.md)** — Technical architecture and system components
- **[Network Economy](Network-Economy.md)** — Economic model and tokenomics
- **[Smart Contracts](contracts-overview.md)** — Blockchain contract documentation
- **[AI-Navigator.md](../AI-Navigator.md)** — Development diary and decision history

**This document focuses on:**
- Web API architecture and implementation
- Authentication and security mechanisms
- Service layer design and patterns
- Integration examples and deployment
- Performance optimization and monitoring 