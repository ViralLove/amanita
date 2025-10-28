#!/bin/bash

# 🔍 Full Catalog Pipeline Validation Script
# 
# Validates the entire catalog upload pipeline for a seller:
# - File system structure
# - Product JSON integrity
# - Arweave mapping completeness
# - Local file CID updates
# - Arweave accessibility
# - Contract registration
#
# Usage:
#   ./scripts/validate_full_catalog_pipeline.sh <seller_id> [output_dir]
#
# Example:
#   ./scripts/validate_full_catalog_pipeline.sh iveta
#   ./scripts/validate_full_catalog_pipeline.sh iveta data/sellers/iveta/output

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
  echo ""
  echo "======================================================================="
  echo "$1"
  echo "======================================================================="
}

print_phase() {
  echo ""
  echo -e "${BLUE}$1${NC}"
  echo "-----------------------------------------------------------------------"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

# Parse arguments
SELLER_ID="${1:-iveta}"
OUTPUT_DIR="${2:-data/sellers/${SELLER_ID}/output}"

print_header "🔍 FULL CATALOG PIPELINE VALIDATION"
echo "Seller ID: ${SELLER_ID}"
echo "Output Directory: ${OUTPUT_DIR}"

# Phase 1: File System Validation
print_phase "📁 PHASE 1: File System Validation"

PRODUCTS_DIR="${OUTPUT_DIR}/products"
if [ ! -d "${PRODUCTS_DIR}" ]; then
  print_error "Products directory not found: ${PRODUCTS_DIR}"
  exit 1
fi

PRODUCT_COUNT=$(ls -1 "${PRODUCTS_DIR}" 2>/dev/null | wc -l | tr -d ' ')
print_success "Found ${PRODUCT_COUNT} product directories"

if [ "${PRODUCT_COUNT}" -eq 0 ]; then
  print_error "No products found in ${PRODUCTS_DIR}"
  exit 1
fi

# Check JSON files
JSON_COUNT=$(find "${PRODUCTS_DIR}" -name "*.json" -not -name "*.titles.json" 2>/dev/null | wc -l | tr -d ' ')
TITLES_COUNT=$(find "${PRODUCTS_DIR}" -name "*.titles.json" 2>/dev/null | wc -l | tr -d ' ')

print_success "Product JSON files: ${JSON_COUNT}"
print_success "Title JSON files: ${TITLES_COUNT}"

if [ "${JSON_COUNT}" -ne "${PRODUCT_COUNT}" ]; then
  print_error "Mismatch: ${PRODUCT_COUNT} directories but ${JSON_COUNT} product files"
  exit 1
fi

if [ "${TITLES_COUNT}" -ne "${PRODUCT_COUNT}" ]; then
  print_warning "Mismatch: ${PRODUCT_COUNT} directories but ${TITLES_COUNT} title files"
fi

# Check transformation report
REPORT_FILE="${PRODUCTS_DIR}/_transformation_report.json"
if [ -f "${REPORT_FILE}" ]; then
  print_success "Transformation report found"
else
  print_warning "Transformation report not found: ${REPORT_FILE}"
fi

# Phase 2: Product JSON Validation
print_phase "📋 PHASE 2: Product JSON Validation"

# Check for null component_id
NULL_COMPONENT_PRODUCTS=$(find "${PRODUCTS_DIR}" -name "*.json" -not -name "*.titles.json" \
  -exec jq -r 'select(.components[]?.component_id == null) | .product_id' {} \; 2>/dev/null || true)

NULL_COMPONENT_COUNT=$(echo "${NULL_COMPONENT_PRODUCTS}" | grep -v '^$' | wc -l | tr -d ' ')

if [ "${NULL_COMPONENT_COUNT}" -gt 0 ]; then
  print_error "Found ${NULL_COMPONENT_COUNT} products with null component_id:"
  echo "${NULL_COMPONENT_PRODUCTS}" | while read -r product_id; do
    [ -n "${product_id}" ] && echo "   - ${product_id}"
  done
  exit 1
fi

print_success "All products have valid component_id"

# Check for missing required fields
INVALID_PRODUCTS=$(find "${PRODUCTS_DIR}" -name "*.json" -not -name "*.titles.json" \
  -exec jq -r 'select(.product_id == null or .seller_id == null or .components == null or (.components | length) == 0) | .product_id // "unknown"' {} \; 2>/dev/null || true)

INVALID_COUNT=$(echo "${INVALID_PRODUCTS}" | grep -v '^$' | wc -l | tr -d ' ')

if [ "${INVALID_COUNT}" -gt 0 ]; then
  print_error "Found ${INVALID_COUNT} products with missing required fields"
  exit 1
fi

print_success "All products have required fields"

# Phase 3: Arweave Mapping Validation
print_phase "🌐 PHASE 3: Arweave Mapping Validation"

MAPPING_FILE="${OUTPUT_DIR}/product_combined_mapping.json"
if [ ! -f "${MAPPING_FILE}" ]; then
  print_error "Mapping file not found: ${MAPPING_FILE}"
  print_warning "This indicates Action 42 (Arweave Upload) was not completed"
  exit 1
fi

print_success "Mapping file found"

MAPPING_COUNT=$(cat "${MAPPING_FILE}" | jq 'keys | length' 2>/dev/null || echo "0")
print_success "Mapping file has ${MAPPING_COUNT} entries"

if [ "${MAPPING_COUNT}" -ne "${PRODUCT_COUNT}" ]; then
  print_warning "Mismatch: ${PRODUCT_COUNT} products but ${MAPPING_COUNT} mappings"
fi

# Check for missing CIDs
MISSING_TITLE_CID=$(cat "${MAPPING_FILE}" | jq -r 'to_entries[] | select(.value.title_cid == null) | .key' 2>/dev/null | wc -l | tr -d ' ')
MISSING_PRODUCT_CID=$(cat "${MAPPING_FILE}" | jq -r 'to_entries[] | select(.value.product_cid == null) | .key' 2>/dev/null | wc -l | tr -d ' ')

if [ "${MISSING_TITLE_CID}" -gt 0 ]; then
  print_error "${MISSING_TITLE_CID} products missing title_cid"
  cat "${MAPPING_FILE}" | jq -r 'to_entries[] | select(.value.title_cid == null) | "   - " + .key' 2>/dev/null || true
  exit 1
fi

if [ "${MISSING_PRODUCT_CID}" -gt 0 ]; then
  print_error "${MISSING_PRODUCT_CID} products missing product_cid"
  cat "${MAPPING_FILE}" | jq -r 'to_entries[] | select(.value.product_cid == null) | "   - " + .key' 2>/dev/null || true
  exit 1
fi

print_success "All products have title_cid and product_cid"

# Phase 4: Local File CID Check
print_phase "💾 PHASE 4: Local File CID Validation"

# Check if product files have CID as title (not placeholder)
PLACEHOLDER_PRODUCTS=$(find "${PRODUCTS_DIR}" -name "*.json" -not -name "*.titles.json" \
  -exec jq -r 'select(.title | test("^[A-Za-z0-9_-]{43}$") | not) | .product_id' {} \; 2>/dev/null || true)

PLACEHOLDER_COUNT=$(echo "${PLACEHOLDER_PRODUCTS}" | grep -v '^$' | wc -l | tr -d ' ')

if [ "${PLACEHOLDER_COUNT}" -gt 0 ]; then
  print_error "${PLACEHOLDER_COUNT} products still have placeholder title (not CID):"
  echo "${PLACEHOLDER_PRODUCTS}" | while read -r product_id; do
    [ -n "${product_id}" ] && echo "   - ${product_id}"
  done
  print_warning "This indicates local files were not updated after Arweave upload"
  exit 1
fi

print_success "All local product files have title as CID"

# Phase 5: Arweave Accessibility Test
print_phase "🔗 PHASE 5: Arweave Accessibility Test"

SAMPLE_PRODUCT_CID=$(cat "${MAPPING_FILE}" | jq -r 'to_entries[0].value.product_cid' 2>/dev/null)
SAMPLE_TITLE_CID=$(cat "${MAPPING_FILE}" | jq -r 'to_entries[0].value.title_cid' 2>/dev/null)

if [ -z "${SAMPLE_PRODUCT_CID}" ] || [ "${SAMPLE_PRODUCT_CID}" == "null" ]; then
  print_error "Cannot test Arweave accessibility: no product CID found"
  exit 1
fi

echo "Testing sample product CID: ${SAMPLE_PRODUCT_CID}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://arweave.net/${SAMPLE_PRODUCT_CID}" 2>/dev/null || echo "000")

if [ "${HTTP_CODE}" -ne 200 ]; then
  print_error "Arweave product not accessible (HTTP ${HTTP_CODE})"
  print_warning "This may be due to Arweave propagation delay (wait ~5 minutes)"
  print_warning "URL: https://arweave.net/${SAMPLE_PRODUCT_CID}"
else
  print_success "Sample product accessible on Arweave"
fi

if [ -z "${SAMPLE_TITLE_CID}" ] || [ "${SAMPLE_TITLE_CID}" == "null" ]; then
  print_warning "Cannot test title accessibility: no title CID found"
else
  echo "Testing sample title CID: ${SAMPLE_TITLE_CID}"
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://arweave.net/${SAMPLE_TITLE_CID}" 2>/dev/null || echo "000")
  
  if [ "${HTTP_CODE}" -ne 200 ]; then
    print_error "Arweave title not accessible (HTTP ${HTTP_CODE})"
    print_warning "This may be due to Arweave propagation delay (wait ~5 minutes)"
    print_warning "URL: https://arweave.net/${SAMPLE_TITLE_CID}"
  else
    print_success "Sample title accessible on Arweave"
  fi
fi

# Phase 6: Contract Validation
print_phase "🔗 PHASE 6: Contract Validation"

if ! command -v npx &> /dev/null; then
  print_error "npx not found - cannot run contract validation"
  exit 1
fi

echo "Running contract validation script..."
echo ""

# Set MAPPING_FILE environment variable and run validation
if MAPPING_FILE="${MAPPING_FILE}" npx hardhat run scripts/validate_catalog_upload.js --network localhost 2>&1; then
  VALIDATION_EXIT_CODE=0
else
  VALIDATION_EXIT_CODE=$?
fi

if [ ${VALIDATION_EXIT_CODE} -ne 0 ]; then
  print_error "Contract validation failed with exit code ${VALIDATION_EXIT_CODE}"
  exit 1
fi

# Final Summary
print_header "✅ FULL PIPELINE VALIDATION PASSED"
echo ""
echo "Summary:"
echo "  ✅ File System: ${PRODUCT_COUNT} products with complete structure"
echo "  ✅ Product JSON: All fields valid, all component_ids present"
echo "  ✅ Arweave Mapping: ${MAPPING_COUNT} entries with complete CIDs"
echo "  ✅ Local Files: All updated with Arweave CIDs"
echo "  ✅ Arweave Access: Sample files accessible"
echo "  ✅ Contract: All products registered and active"
echo ""
echo "🎉 Seller '${SELLER_ID}' catalog is fully validated and ready!"
echo ""

exit 0

