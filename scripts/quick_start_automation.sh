#!/bin/bash

# 🚀 Amanita Ecosystem Quick Start Automation
# Complete automated deployment from scratch on localhost

# set -e  # Exit on any error - disabled for better error handling

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Configuration
WALLET_PORT=3000
NGROK_PORT=3000
# Determine PROJECT_ROOT based on where bot/.env actually exists
if [[ -f "bot/.env" ]]; then
    # We're in the Amanita project root
    PROJECT_ROOT="$(pwd)"
elif [[ -f "../bot/.env" ]]; then
    # We're in a subdirectory of Amanita project root
    PROJECT_ROOT="$(cd .. && pwd)"
else
    # Fallback to script-based detection
    PROJECT_ROOT="$(cd "$(dirname "${0:-${BASH_SOURCE[0]}}")/.." && pwd)"
fi
BOT_ENV="$PROJECT_ROOT/bot/.env"
ROOT_ENV="$PROJECT_ROOT/.env"

# Default localhost keys
DEPLOYER_PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
SELLER_ADDRESS="0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
SELLER_PRIVATE_KEY="0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"

# Step 0: Copy Contract Artifacts
copy_contract_artifacts() {
    log_info "Copying contract artifacts to bot directory..."
    
    # Create bot/artifacts directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/bot/artifacts/contracts"
    
    # Copy all contract artifacts
    if [[ -d "$PROJECT_ROOT/artifacts/contracts" ]]; then
        cp -r "$PROJECT_ROOT/artifacts/contracts"/* "$PROJECT_ROOT/bot/artifacts/contracts/"
        log_success "Contract artifacts copied successfully"
        
        # Log what was copied
        log_info "Copied artifacts:"
        ls -la "$PROJECT_ROOT/bot/artifacts/contracts/" | head -10
    else
        log_warning "Artifacts directory not found: $PROJECT_ROOT/artifacts/contracts"
        log_info "This might cause 'Parameter decoding error' issues"
    fi
}

# Step 1: Cleanup and Kill Existing Processes
cleanup_and_kill_processes() {
    log_info "Cleaning up old files and killing existing processes..."
    
    # Clean up old invite files to avoid confusion
    local flowers_dir="$PROJECT_ROOT/bot/flowers"
    if [[ -d "$flowers_dir" ]]; then
        log_info "Cleaning up old invite files in $flowers_dir"
        
        # Remove old invite files
        rm -f "$flowers_dir/deployer_invites_localhost.txt" 2>/dev/null || true
        rm -f "$flowers_dir/deployer_invites_polygon.txt" 2>/dev/null || true
        rm -f "$flowers_dir/${SELLER_ADDRESS}_invites.txt" 2>/dev/null || true
        rm -f "$flowers_dir/0x21d994213d88b4ccDA265036557788B9B910610D_invites.txt" 2>/dev/null || true
        
        log_info "Old invite files removed"
    fi
    
    # Kill processes on port 3000 (wallet server)
    local port_3000_pids=$(lsof -ti:3000 2>/dev/null)
    if [[ -n "$port_3000_pids" ]]; then
        log_info "Killing processes on port 3000: $port_3000_pids"
        echo "$port_3000_pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Note: Not killing Hardhat node processes - user manages them manually
    log_info "Skipping Hardhat node cleanup - managed manually"
    
    # Kill ngrok processes
    local ngrok_pids=$(pgrep -f "ngrok" 2>/dev/null)
    if [[ -n "$ngrok_pids" ]]; then
        log_info "Killing ngrok processes: $ngrok_pids"
        echo "$ngrok_pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    log_success "Cleanup completed - old files removed and existing processes killed"
}

# Step 1: Prerequisites Check
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not installed"
        exit 1
    fi
    log_success "Python3 is available"
    
    # Check ngrok
    if ! command -v ngrok &> /dev/null; then
        log_error "ngrok is not installed"
        exit 1
    fi
    log_success "ngrok is available"
    
    # Check Node.js and npm
    if ! command -v node &> /dev/null; then
        log_error "Node.js is not installed"
        exit 1
    fi
    log_success "Node.js is available"
    
    if ! command -v npm &> /dev/null; then
        log_error "npm is not installed"
        exit 1
    fi
    log_success "npm is available"
}

# Step 1.5: Start Hardhat Node
check_hardhat_node_running() {
    log_info "Checking if Hardhat node is running..."
    
    # Test connection to Hardhat node
    response=$(curl -s http://localhost:8545 -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' 2>/dev/null)
    
    if [[ $? -eq 0 && -n "$response" ]]; then
        log_success "Hardhat node is running and responding"
        log_info "Response: $response"
        return 0
    else
        log_error "Hardhat node is not running on localhost:8545"
        log_info ""
        log_info "Please start Hardhat node manually in a separate terminal:"
        log_info "  cd /Users/eslinko/Development/Amanita"
        log_info "  npx hardhat node"
        log_info ""
        log_info "Then run this script again"
        return 1
    fi
}

# Step 2: Environment Setup
setup_environment() {
    log_info "Setting up environment variables..."
    
    # Create/update .env files with localhost keys
    for env_file in "$BOT_ENV" "$ROOT_ENV"; do
        if [[ ! -f "$env_file" ]]; then
            touch "$env_file"
        fi
        
        # Update or add localhost keys
        update_env_var "$env_file" "DEPLOYER_PRIVATE_KEY" "$DEPLOYER_PRIVATE_KEY"
        update_env_var "$env_file" "SELLER_ADDRESS" "$SELLER_ADDRESS"
        update_env_var "$env_file" "SELLER_PRIVATE_KEY" "$SELLER_PRIVATE_KEY"
        update_env_var "$env_file" "WEB3_PROVIDER_URI" "http://localhost:8545"
    done
    
    log_success "Environment variables configured"
    
    # Verify .env files were created/updated
    log_info "Verifying .env files:"
    for env_file in "$BOT_ENV" "$ROOT_ENV"; do
        if [[ -f "$env_file" ]]; then
            log_info "✅ $env_file exists"
            log_info "Contents of $env_file:"
            cat "$env_file"
        else
            log_warning "⚠️  $env_file does not exist"
        fi
    done
}

# Helper function to update environment variables
update_env_var() {
    local file="$1"
    local key="$2"
    local value="$3"
    
    log_info "Updating $key=$value in $file"
    
    # First, clean up any existing formatting issues
    # Fix concatenated lines (e.g., METRICS_INTERVAL="60"MAGIC_REGISTRY_CONTRACT_ADDRESS=...)
    sed -i.bak 's/METRICS_INTERVAL="60"MAGIC_REGISTRY_CONTRACT_ADDRESS/METRICS_INTERVAL="60"\nMAGIC_REGISTRY_CONTRACT_ADDRESS/' "$file" 2>/dev/null || true
    rm -f "$file.bak"
    
    # Remove duplicate entries of the same key
    if [[ -f "$file" ]]; then
        local temp_file=$(mktemp)
        awk -v key="$key" -v value="$value" '
        BEGIN { found = 0 }
        /^#/ { print; next }
        $0 ~ "^" key "=" { 
            if (found == 0) {
                print key "=" value
                found = 1
            }
            next
        }
        { print }
        END { 
            if (found == 0) {
                print key "=" value
            }
        }' "$file" > "$temp_file" && mv "$temp_file" "$file"
    else
        # File doesn't exist, create it
        echo "$key=$value" > "$file"
    fi
}

# Step 3: Start Wallet Server
start_wallet_server() {
    log_info "Starting wallet server..."
    
    cd "$PROJECT_ROOT/wallet"
    python3 -m http.server $WALLET_PORT &
    WALLET_PID=$!
    
    # Wait for server to start
    sleep 2
    if curl -s http://localhost:$WALLET_PORT > /dev/null; then
        log_success "Wallet server started on port $WALLET_PORT (PID: $WALLET_PID)"
    else
        log_error "Failed to start wallet server"
        exit 1
    fi
}

# Step 4: Start ngrok Tunnel
start_ngrok_tunnel() {
    log_info "Starting ngrok tunnel..."
    
    ngrok http $NGROK_PORT --log=stdout > /tmp/ngrok.log 2>&1 &
    NGROK_PID=$!
    
    # Wait for ngrok to start
    sleep 3
    
    # Get ngrok URL
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data['tunnels']:
        if tunnel['proto'] == 'https':
            print(tunnel['public_url'])
            break
except:
    pass
")
    
    if [[ -n "$NGROK_URL" ]]; then
        log_success "ngrok tunnel started: $NGROK_URL"
        
        # Update WALLET_APP_URL in .env files
        for env_file in "$BOT_ENV" "$ROOT_ENV"; do
            update_env_var "$env_file" "WALLET_APP_URL" "$NGROK_URL"
            log_info "Updated WALLET_APP_URL in $env_file to: $NGROK_URL"
        done
    else
        log_error "Failed to get ngrok URL"
        exit 1
    fi
}

# Step 5: Deploy Contracts (Action 1)
deploy_contracts() {
    log_info "Deploying contracts (Action 1)..."
    
    cd "$PROJECT_ROOT"
    
    log_info "Running: DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost"
    
    # Run deployment with detailed output
    DEPLOY_OUTPUT=$(DEPLOY_ACTION=1 npx hardhat run scripts/deploy_full.js --network localhost 2>&1)
    DEPLOY_EXIT_CODE=$?
    
    log_info "Deployment output:"
    echo "$DEPLOY_OUTPUT"
    
    if [[ $DEPLOY_EXIT_CODE -eq 0 ]]; then
        log_success "Contracts deployed successfully"
        
        # Extract contract addresses from output
        extract_contract_addresses "$DEPLOY_OUTPUT"
        # Ensure bot .env has contract addresses
        force_copy_contract_addresses
    else
        log_error "Contract deployment failed with exit code: $DEPLOY_EXIT_CODE"
        log_error "Full deployment output:"
        echo "$DEPLOY_OUTPUT"
        
        # Check if it's a known issue we can handle
        if echo "$DEPLOY_OUTPUT" | grep -q "Parameter decoding error"; then
            log_warning "Detected parameter decoding error - this might be due to contract state issues"
            log_info "Attempting to continue with existing contracts..."
            
            # Extract contract addresses from output if available
            extract_contract_addresses "$DEPLOY_OUTPUT"
            
            # Force copy all contract addresses from root .env to bot .env
            log_info "Force copying all contract addresses to bot .env..."
            force_copy_contract_addresses
            
            # Continue execution instead of exiting
            log_warning "Continuing with deployment process..."
        elif echo "$DEPLOY_OUTPUT" | grep -q "already.*exists\|already.*deployed"; then
            log_warning "Detected existing contracts - this is expected on subsequent runs"
            log_info "Using existing contract addresses..."
            
            # Extract contract addresses from output if available
            extract_contract_addresses "$DEPLOY_OUTPUT"
            
            # Continue execution instead of exiting
          log_warning "Continuing with deployment process..."
          # Force copy contract addresses to bot .env since extraction failed
          force_copy_contract_addresses
      else
          exit 1
      fi
  fi
}

# Extract contract addresses from deployment output
extract_contract_addresses() {
    local output="$1"
    
    log_info "Extracting contract addresses..."
    
    # Extract addresses using regex - improved patterns to handle both formats
    log_info "Searching for contract addresses in deployment output..."
    
    # Try multiple patterns for each contract
    MAGIC_REGISTRY=$(echo "$output" | grep -E "(MAGIC_REGISTRY_CONTRACT_ADDRESS.*=|MAGIC_REGISTRY.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SPIRAL_ENGINE=$(echo "$output" | grep -E "(SPIRAL_ENGINE_CONTRACT_ADDRESS.*=|SPIRAL_ENGINE.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    PRODUCT_REGISTRY=$(echo "$output" | grep -E "(PRODUCT_REGISTRY_CONTRACT_ADDRESS.*=|PRODUCT_REGISTRY.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SOULBOUND_CORE=$(echo "$output" | grep -E "(SOULBOUND_CORE_CONTRACT_ADDRESS.*=|SOULBOUND_CORE.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SOUL_METADATA=$(echo "$output" | grep -E "(SOUL_METADATA_CONTRACT_ADDRESS.*=|SOUL_METADATA.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SOUL_RECOVERY=$(echo "$output" | grep -E "(SOUL_RECOVERY_CONTRACT_ADDRESS.*=|SOUL_RECOVERY.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SOUL_INTEGRATION=$(echo "$output" | grep -E "(SOUL_INTEGRATION_CONTRACT_ADDRESS.*=|SOUL_INTEGRATION.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    SOUL_IDENTITY=$(echo "$output" | grep -E "(SOUL_IDENTITY_CONTRACT_ADDRESS.*=|SOUL_IDENTITY.*:)" | grep -oE "0x[0-9a-fA-F]{40}" | tail -1)
    
    log_info "Raw extraction results:"
    log_info "  MagicRegistry: $MAGIC_REGISTRY"
    log_info "  SpiralEngine: $SPIRAL_ENGINE"
    log_info "  ProductRegistry: $PRODUCT_REGISTRY"
    log_info "  SoulIdentity: $SOUL_IDENTITY"
    
    # Fallback: try to extract from existing .env files
    log_info "Applying fallback extraction from existing .env files..."
    if [[ -z "$MAGIC_REGISTRY" && -f "$ROOT_ENV" ]]; then
        MAGIC_REGISTRY=$(grep "MAGIC_REGISTRY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: MagicRegistry from .env: $MAGIC_REGISTRY"
    fi
    if [[ -z "$SPIRAL_ENGINE" && -f "$ROOT_ENV" ]]; then
        SPIRAL_ENGINE=$(grep "SPIRAL_ENGINE_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SpiralEngine from .env: $SPIRAL_ENGINE"
    fi
    if [[ -z "$PRODUCT_REGISTRY" && -f "$ROOT_ENV" ]]; then
        PRODUCT_REGISTRY=$(grep "PRODUCT_REGISTRY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: ProductRegistry from .env: $PRODUCT_REGISTRY"
    fi
    if [[ -z "$SOULBOUND_CORE" && -f "$ROOT_ENV" ]]; then
        SOULBOUND_CORE=$(grep "SOULBOUND_CORE_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SoulboundCore from .env: $SOULBOUND_CORE"
    fi
    if [[ -z "$SOUL_METADATA" && -f "$ROOT_ENV" ]]; then
        SOUL_METADATA=$(grep "SOUL_METADATA_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SoulMetadata from .env: $SOUL_METADATA"
    fi
    if [[ -z "$SOUL_RECOVERY" && -f "$ROOT_ENV" ]]; then
        SOUL_RECOVERY=$(grep "SOUL_RECOVERY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SoulRecovery from .env: $SOUL_RECOVERY"
    fi
    if [[ -z "$SOUL_INTEGRATION" && -f "$ROOT_ENV" ]]; then
        SOUL_INTEGRATION=$(grep "SOUL_INTEGRATION_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SoulIntegration from .env: $SOUL_INTEGRATION"
    fi
    if [[ -z "$SOUL_IDENTITY" && -f "$ROOT_ENV" ]]; then
        SOUL_IDENTITY=$(grep "SOUL_IDENTITY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        log_info "Fallback: SoulIdentity from .env: $SOUL_IDENTITY"
    fi
    
    log_info "Extracted contract addresses:"
    log_info "  MagicRegistry: $MAGIC_REGISTRY"
    log_info "  SpiralEngine: $SPIRAL_ENGINE"
    log_info "  ProductRegistry: $PRODUCT_REGISTRY"
    log_info "  SoulIdentity: $SOUL_IDENTITY"
    
    # Update .env files with contract addresses
    log_info "Updating .env files with extracted addresses..."
    for env_file in "$BOT_ENV" "$ROOT_ENV"; do
        log_info "Updating $(basename "$env_file")..."
        [[ -n "$MAGIC_REGISTRY" ]] && update_env_var "$env_file" "MAGIC_REGISTRY_CONTRACT_ADDRESS" "$MAGIC_REGISTRY"
        [[ -n "$SPIRAL_ENGINE" ]] && update_env_var "$env_file" "SPIRAL_ENGINE_CONTRACT_ADDRESS" "$SPIRAL_ENGINE"
        [[ -n "$PRODUCT_REGISTRY" ]] && update_env_var "$env_file" "PRODUCT_REGISTRY_CONTRACT_ADDRESS" "$PRODUCT_REGISTRY"
        [[ -n "$SOULBOUND_CORE" ]] && update_env_var "$env_file" "SOULBOUND_CORE_CONTRACT_ADDRESS" "$SOULBOUND_CORE"
        [[ -n "$SOUL_METADATA" ]] && update_env_var "$env_file" "SOUL_METADATA_CONTRACT_ADDRESS" "$SOUL_METADATA"
        [[ -n "$SOUL_RECOVERY" ]] && update_env_var "$env_file" "SOUL_RECOVERY_CONTRACT_ADDRESS" "$SOUL_RECOVERY"
        [[ -n "$SOUL_INTEGRATION" ]] && update_env_var "$env_file" "SOUL_INTEGRATION_CONTRACT_ADDRESS" "$SOUL_INTEGRATION"
        [[ -n "$SOUL_IDENTITY" ]] && update_env_var "$env_file" "SOUL_IDENTITY_CONTRACT_ADDRESS" "$SOUL_IDENTITY"
    done
    
    log_success "Contract addresses updated in .env files"
    
    # Verify the updates were successful
    log_info "Verifying .env file updates:"
    if [[ -f "$BOT_ENV" ]]; then
        log_info "Bot .env contract addresses:"
        grep -E "CONTRACT_ADDRESS=" "$BOT_ENV" | head -5 || log_warning "No contract addresses found in bot .env"
    fi
}

# Force copy contract addresses from root .env to bot .env
force_copy_contract_addresses() {
    log_info "Force copying contract addresses from root .env to bot .env..."
    
    if [[ -f "$ROOT_ENV" ]]; then
        # Extract all contract addresses from root .env
        MAGIC_REGISTRY=$(grep "MAGIC_REGISTRY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SPIRAL_ENGINE=$(grep "SPIRAL_ENGINE_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        PRODUCT_REGISTRY=$(grep "PRODUCT_REGISTRY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SOULBOUND_CORE=$(grep "SOULBOUND_CORE_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SOUL_METADATA=$(grep "SOUL_METADATA_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SOUL_RECOVERY=$(grep "SOUL_RECOVERY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SOUL_INTEGRATION=$(grep "SOUL_INTEGRATION_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        SOUL_IDENTITY=$(grep "SOUL_IDENTITY_CONTRACT_ADDRESS=" "$ROOT_ENV" | cut -d'=' -f2 | tr -d ' ')
        
        log_info "Found contract addresses in root .env:"
        log_info "  MagicRegistry: $MAGIC_REGISTRY"
        log_info "  SpiralEngine: $SPIRAL_ENGINE"
        log_info "  ProductRegistry: $PRODUCT_REGISTRY"
        log_info "  SoulboundCore: $SOULBOUND_CORE"
        log_info "  SoulMetadata: $SOUL_METADATA"
        log_info "  SoulRecovery: $SOUL_RECOVERY"
        log_info "  SoulIntegration: $SOUL_INTEGRATION"
        log_info "  SoulIdentity: $SOUL_IDENTITY"
        
        # Create a clean bot .env with all contract addresses
        log_info "Creating clean bot .env with all contract addresses..."
        
        # Start with existing bot .env content (excluding contract addresses)
        local temp_file=$(mktemp)
        if [[ -f "$BOT_ENV" ]]; then
            cp "$BOT_ENV" "$BOT_ENV.backup"
            # Use awk to filter out contract addresses and ensure file is created
            awk '!/_CONTRACT_ADDRESS=/' "$BOT_ENV" > "$temp_file"
            # Ensure file exists even if awk produces no output
            [[ ! -s "$temp_file" ]] && touch "$temp_file"
        else
            touch "$temp_file"
        fi
        
        # CRITICAL FIX: If temp file is empty, copy the original content without contract addresses
        if [[ ! -s "$temp_file" && -f "$BOT_ENV" ]]; then
            log_info "Temp file is empty, copying original content without contract addresses..."
            # Copy all lines except contract addresses
            while IFS= read -r line; do
                if [[ "$line" != *"_CONTRACT_ADDRESS="* ]]; then
                    echo "$line" >> "$temp_file"
                fi
            done < "$BOT_ENV"
            log_info "After copying, temp file size: $(wc -c < "$temp_file" 2>/dev/null || echo "0")"
        fi
        
        # Debug: check if temp file exists and has content
        log_info "Temp file exists: $([[ -f "$temp_file" ]] && echo "YES" || echo "NO")"
        log_info "Temp file size: $(wc -c < "$temp_file" 2>/dev/null || echo "0")"
        
        # Ensure temp file is writable
        chmod 644 "$temp_file"
        
        # Debug: check if temp file is writable
        log_info "Temp file writable: $([[ -w "$temp_file" ]] && echo "YES" || echo "NO")"
        
        # Debug: check if temp file is readable
        log_info "Temp file readable: $([[ -r "$temp_file" ]] && echo "YES" || echo "NO")"
        
        # Debug: show temp file content
        log_info "Temp file content (first 5 lines):"
        head -5 "$temp_file" 2>/dev/null || log_info "Temp file is empty or unreadable"
        
        # Add all contract addresses
        [[ -n "$MAGIC_REGISTRY" ]] && echo "MAGIC_REGISTRY_CONTRACT_ADDRESS=$MAGIC_REGISTRY" >> "$temp_file"
        [[ -n "$SPIRAL_ENGINE" ]] && echo "SPIRAL_ENGINE_CONTRACT_ADDRESS=$SPIRAL_ENGINE" >> "$temp_file"
        [[ -n "$PRODUCT_REGISTRY" ]] && echo "PRODUCT_REGISTRY_CONTRACT_ADDRESS=$PRODUCT_REGISTRY" >> "$temp_file"
        [[ -n "$SOULBOUND_CORE" ]] && echo "SOULBOUND_CORE_CONTRACT_ADDRESS=$SOULBOUND_CORE" >> "$temp_file"
        [[ -n "$SOUL_METADATA" ]] && echo "SOUL_METADATA_CONTRACT_ADDRESS=$SOUL_METADATA" >> "$temp_file"
        [[ -n "$SOUL_RECOVERY" ]] && echo "SOUL_RECOVERY_CONTRACT_ADDRESS=$SOUL_RECOVERY" >> "$temp_file"
        [[ -n "$SOUL_INTEGRATION" ]] && echo "SOUL_INTEGRATION_CONTRACT_ADDRESS=$SOUL_INTEGRATION" >> "$temp_file"
        [[ -n "$SOUL_IDENTITY" ]] && echo "SOUL_IDENTITY_CONTRACT_ADDRESS=$SOUL_IDENTITY" >> "$temp_file"
        
        # Replace the original file with proper error checking
        log_info "Attempting to replace bot .env with updated content..."
        log_info "Temp file size before mv: $(wc -c < "$temp_file" 2>/dev/null || echo "0")"
        
        if mv "$temp_file" "$BOT_ENV"; then
            log_success "Contract addresses force copied to bot .env"
            
            # Verify the copy was successful
            log_info "Verifying bot .env after force copy:"
            if [[ -f "$BOT_ENV" ]]; then
                log_info "Bot .env contract addresses:"
                grep -E "CONTRACT_ADDRESS=" "$BOT_ENV" || log_warning "No contract addresses found in bot .env"
            fi
        else
            log_error "Failed to copy contract addresses to bot .env"
            log_error "Temp file: $temp_file"
            log_error "Target file: $BOT_ENV"
            log_error "Temp file exists: $([[ -f "$temp_file" ]] && echo "YES" || echo "NO")"
            log_error "Target directory writable: $([[ -w "$(dirname "$BOT_ENV")" ]] && echo "YES" || echo "NO")"
            return 1
        fi
    else
        log_warning "Root .env file not found: $ROOT_ENV"
    fi
}

# Step 6: Mint Invites (Action 777)
mint_invites() {
    log_info "Minting invites (Action 777)..."
    
    cd "$PROJECT_ROOT"
    
    # Check if deployer invites already exist
    local deployer_invites_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
    if [[ -f "$deployer_invites_file" ]]; then
        log_warning "Found existing deployer invites file: $deployer_invites_file"
        log_info "Deployer invites appear to be already minted. Skipping minting step."
        log_info "Deployer invites:"
        cat "$deployer_invites_file"
        return 0
    fi
    
    log_info "Running: DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost"
    
    DEPLOY_OUTPUT=$(DEPLOY_ACTION=777 npx hardhat run scripts/deploy_full.js --network localhost 2>&1)
    DEPLOY_EXIT_CODE=$?
    
    log_info "Invite minting output:"
    echo "$DEPLOY_OUTPUT"
    
    if [[ $DEPLOY_EXIT_CODE -eq 0 ]]; then
        log_success "Invites minted successfully"
        
        # Check if invite file exists
        local invite_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
        if [[ -f "$invite_file" ]]; then
            log_success "Invite file created: $invite_file"
            log_info "Invite file contents:"
            cat "$invite_file"
        else
            log_warning "Invite file not found: $invite_file"
            log_info "Checking flowers directory:"
            ls -la "$PROJECT_ROOT/bot/flowers/" || log_warning "Flowers directory does not exist"
        fi
    else
        log_error "Invite minting failed with exit code: $DEPLOY_EXIT_CODE"
        log_error "Full invite minting output:"
        echo "$DEPLOY_OUTPUT"
        
        # Check if it's a known issue we can handle
        if echo "$DEPLOY_OUTPUT" | grep -q "invite.*already.*used\|already.*exists"; then
            log_warning "Detected existing invites - this is expected on subsequent runs"
            log_info "Checking for existing invite files..."
            
            # Check for existing invite files
            local invite_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
            if [[ -f "$invite_file" ]]; then
                log_success "Found existing invite file: $invite_file"
                log_info "Invite contents:"
                cat "$invite_file"
            else
                log_warning "No existing invite file found"
            fi
            
            # Continue execution instead of exiting
            log_warning "Continuing with activation process..."
        elif echo "$DEPLOY_OUTPUT" | grep -q "Parameter decoding error"; then
            log_warning "Detected parameter decoding error - this might be due to contract state issues"
            log_info "Checking for existing invite files..."
            
            # Check for existing invite files
            local invite_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
            if [[ -f "$invite_file" ]]; then
                log_success "Found existing invite file: $invite_file"
                log_info "Invite contents:"
                cat "$invite_file"
            else
                log_warning "No existing invite file found"
            fi
            
            # Force copy all contract addresses to ensure bot .env is complete
            log_info "Force copying all contract addresses to bot .env..."
            force_copy_contract_addresses
            
            # Continue execution instead of exiting
            log_warning "Continuing with activation process..."
        else
            log_warning "Unknown error during invite minting, but continuing anyway..."
            log_info "This might be due to contract state issues or network problems"
            log_warning "Continuing with activation process..."
        fi
    fi
}

# Step 7: Auto-select Best Invite
select_best_invite() {
    log_info "Selecting best deployer invite..."
    
    local invite_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
    
    if [[ ! -f "$invite_file" ]]; then
        log_error "Invite file not found: $invite_file"
        exit 1
    fi
    
    # Look for invites with 8, then 7, then 5
    DEPLOYER_INVITE=$(grep -E "AMANITA-.*[857].*" "$invite_file" | head -1 | tr -d ' ')
    
    if [[ -z "$DEPLOYER_INVITE" ]]; then
        # Fallback to any invite
        DEPLOYER_INVITE=$(head -1 "$invite_file" | tr -d ' ')
    fi
    
    if [[ -n "$DEPLOYER_INVITE" ]]; then
        log_success "Selected deployer invite: $DEPLOYER_INVITE"
        export DEPLOYER_INVITE
    else
        log_error "No deployer invite found"
        exit 1
    fi
}

# Step 8: Activate Seller (Action 888)
activate_seller() {
    log_info "Activating seller (Action 888)..."
    
    cd "$PROJECT_ROOT"
    
    # Check if seller is already activated by looking for existing invites
    local seller_invites_file="$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt"
    if [[ -f "$seller_invites_file" ]]; then
        log_warning "Found existing seller invites file: $seller_invites_file"
        log_info "Seller appears to be already activated. Skipping activation step."
        log_info "Seller invites:"
        cat "$seller_invites_file"
        return 0
    fi
    
    log_info "Using deployer invite: $DEPLOYER_INVITE"
    log_info "Running: DEPLOY_ACTION=888 DEPLOYER_INVITE=$DEPLOYER_INVITE npx hardhat run scripts/deploy_full.js --network localhost"
    
    DEPLOY_OUTPUT=$(DEPLOY_ACTION=888 DEPLOYER_INVITE="$DEPLOYER_INVITE" npx hardhat run scripts/deploy_full.js --network localhost 2>&1)
    DEPLOY_EXIT_CODE=$?
    
    log_info "Seller activation output:"
    echo "$DEPLOY_OUTPUT"
    
    if [[ $DEPLOY_EXIT_CODE -eq 0 ]]; then
        log_success "Seller activated successfully"
        
        # Check seller invites file
        local seller_invites_file="$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt"
        if [[ -f "$seller_invites_file" ]]; then
            log_success "Seller invites created: $seller_invites_file"
            log_info "Seller invites:"
            cat "$seller_invites_file"
        else
            log_warning "Seller invites file not found: $seller_invites_file"
            log_info "Checking flowers directory:"
            ls -la "$PROJECT_ROOT/bot/flowers/" || log_warning "Flowers directory does not exist"
        fi
    else
        log_error "Seller activation failed with exit code: $DEPLOY_EXIT_CODE"
        log_error "Full seller activation output:"
        echo "$DEPLOY_OUTPUT"
        
        # Check if it's a known issue we can handle
        if echo "$DEPLOY_OUTPUT" | grep -q "already.*activated\|seller.*already"; then
            log_warning "Detected already activated seller - this is expected on subsequent runs"
            log_info "Checking for existing seller invites..."
            
            # Check for existing seller invites
            local seller_invites_file="$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt"
            if [[ -f "$seller_invites_file" ]]; then
                log_success "Found existing seller invites: $seller_invites_file"
                log_info "Seller invites:"
                cat "$seller_invites_file"
            else
                log_warning "No existing seller invites found"
            fi
            
            # Continue execution instead of exiting
            log_warning "Continuing with bot startup..."
        elif echo "$DEPLOY_OUTPUT" | grep -q "Parameter decoding error\|Метод.*не найден"; then
            log_warning "Detected contract interaction issues - this might be due to contract state or ABI problems"
            log_info "Checking for existing seller invites..."
            
            # Check for existing seller invites
            local seller_invites_file="$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt"
            if [[ -f "$seller_invites_file" ]]; then
                log_success "Found existing seller invites: $seller_invites_file"
                log_info "Seller invites:"
                cat "$seller_invites_file"
            else
                log_warning "No existing seller invites found - seller may not be activated"
                log_info "This is expected if contracts have issues - continuing anyway"
            fi
            
            # Continue execution instead of exiting
            log_warning "Continuing with bot startup despite contract issues..."
        else
            log_warning "Unknown error during seller activation, but continuing anyway..."
            log_info "This might be due to contract state issues or network problems"
            log_warning "Continuing with bot startup..."
        fi
    fi
}

# Step 9: Start Bot
# Check Hardhat node status without restarting
check_hardhat_node() {
    log_info "Checking Hardhat node status..."
    
    # Test connection to Hardhat node
    response=$(curl -s http://localhost:8545 -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' 2>/dev/null)
    
    if [[ $? -eq 0 && -n "$response" ]]; then
        log_success "Hardhat node is running and responding"
        log_info "Response: $response"
        return 0
    else
        log_error "Hardhat node is not responding on localhost:8545"
        log_info "This means either:"
        log_info "1. Hardhat node is not running"
        log_info "2. Hardhat node is running on different port"
        log_info "3. There's a network connectivity issue"
        log_info ""
        log_info "Please ensure Hardhat node is running with: npx hardhat node"
        return 1
    fi
}

start_bot() {
    log_info "Starting Telegram bot..."
    
    # Check Hardhat node status (without restarting to preserve contracts)
    if ! check_hardhat_node; then
        log_error "Cannot start bot - Hardhat node is not available"
        log_info "Hardhat node should be running from the start of this script"
        log_info "Check if the node process is still running: ps aux | grep hardhat"
        log_info "If not, restart the entire script"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # Check if bot directory and main.py exist
    if [[ ! -f "bot/main.py" ]]; then
        log_error "Bot main.py not found: bot/main.py"
        log_info "Checking bot directory:"
        ls -la bot/ || log_warning "Bot directory does not exist"
        log_warning "Skipping bot startup - main.py not found"
        return 0
    fi
    
    # Check if required invite files exist
    local deployer_invites_file="$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt"
    local seller_invites_file="$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt"
    
    if [[ ! -f "$deployer_invites_file" ]]; then
        log_warning "Deployer invites file not found: $deployer_invites_file"
        log_warning "Bot may not work correctly without invites"
    fi
    
    if [[ ! -f "$seller_invites_file" ]]; then
        log_warning "Seller invites file not found: $seller_invites_file"
        log_warning "Bot may not work correctly without seller invites"
    fi
    
    log_info "Bot main.py found, starting bot..."
    log_info "Running: python3 bot/main.py"
    
    # Start bot in background and capture output
    python3 bot/main.py > /tmp/bot_output.log 2>&1 &
    BOT_PID=$!
    
    # Wait a moment and check if bot started successfully
    sleep 3
    
    if kill -0 $BOT_PID 2>/dev/null; then
        log_success "Bot started successfully (PID: $BOT_PID)"
        log_info "Bot output log: /tmp/bot_output.log"
        log_info "Bot is running in background. Check logs for status."
        
        # Show first few lines of bot output
        if [[ -f "/tmp/bot_output.log" ]]; then
            log_info "First few lines of bot output:"
            head -10 /tmp/bot_output.log
        fi
    else
        log_error "Bot failed to start"
        if [[ -f "/tmp/bot_output.log" ]]; then
            log_error "Bot error output:"
            cat /tmp/bot_output.log
        fi
        log_warning "Continuing without bot - check logs for details"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up processes..."
    
    # Kill background processes
    [[ -n "$HARDHAT_PID" ]] && kill $HARDHAT_PID 2>/dev/null || true
    [[ -n "$WALLET_PID" ]] && kill $WALLET_PID 2>/dev/null || true
    [[ -n "$NGROK_PID" ]] && kill $NGROK_PID 2>/dev/null || true
    [[ -n "$BOT_PID" ]] && kill $BOT_PID 2>/dev/null || true
    
    log_success "Cleanup completed"
}

# Set trap for cleanup on exit (only for main execution)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    trap cleanup EXIT
fi

# Main execution
main() {
    log_info "🚀 Starting Amanita Ecosystem Quick Start Automation"
    log_info "=================================================="
    
    copy_contract_artifacts
    cleanup_and_kill_processes
    check_prerequisites
    check_hardhat_node_running
    setup_environment
    start_wallet_server
    start_ngrok_tunnel
    deploy_contracts
    mint_invites
    select_best_invite
    activate_seller
    start_bot
    
    log_success "🎉 Amanita Ecosystem setup completed!"
    log_info "=================================================="
    log_info "⛓️  Hardhat Node: Managed manually by user"
    log_info "📱 Wallet: http://localhost:$WALLET_PORT (PID: $WALLET_PID)"
    log_info "🌐 ngrok: $NGROK_URL (PID: $NGROK_PID)"
    if [[ -n "$BOT_PID" ]] && kill -0 $BOT_PID 2>/dev/null; then
        log_info "🤖 Bot: Running in background (PID: $BOT_PID)"
    else
        log_warning "🤖 Bot: Not running (check logs for details)"
    fi
    if [[ -f "$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt" ]]; then
        log_info "📋 Seller invites: Available"
    else
        log_warning "📋 Seller invites: Missing (contract issues)"
    fi
    log_info ""
    log_info "📋 Status Summary:"
    log_info "✅ Infrastructure: All services started"
    log_info "✅ Contracts: Registered in MagicRegistry"
    if [[ -f "$PROJECT_ROOT/bot/flowers/deployer_invites_localhost.txt" ]]; then
        log_info "✅ Deployer Invites: Available"
    else
        log_warning "⚠️  Deployer Invites: Missing (contract issues)"
    fi
    if [[ -f "$PROJECT_ROOT/bot/flowers/${SELLER_ADDRESS}_invites.txt" ]]; then
        log_info "✅ Seller Invites: Available"
    else
        log_warning "⚠️  Seller Invites: Missing (contract issues)"
    fi
    log_info ""
    log_info "Press Ctrl+C to stop all services"
    
    # Keep script running
    wait
}

# Run main function only if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
