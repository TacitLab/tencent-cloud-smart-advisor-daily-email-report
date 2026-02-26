#!/bin/bash
#
# advisor-report.sh - Main report generator for Tencent Smart Advisor
# Usage: ./advisor-report.sh [OPTIONS]
#

set -e

# Default values
CACHE_DIR="${HOME}/.advisor"
OUTPUT_FORMAT="markdown"
DATE=""
APPID=""
ARCHITECTURE=""
COMPARE=false
FORCE=false
TODAY=false

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --today)
      TODAY=true
      DATE=$(date +%Y-%m-%d)
      shift
      ;;
    --date)
      DATE="$2"
      shift 2
      ;;
    --appid)
      APPID="$2"
      shift 2
      ;;
    --architecture)
      ARCHITECTURE="$2"
      shift 2
      ;;
    --compare)
      COMPARE=true
      shift
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --output)
      OUTPUT_FORMAT="$2"
      shift 2
      ;;
    --cache-dir)
      CACHE_DIR="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --today              Generate report for today"
      echo "  --date YYYY-MM-DD    Generate report for specific date"
      echo "  --appid ID           Filter by specific APPID"
      echo "  --architecture NAME  Filter by architecture diagram name"
      echo "  --compare            Enable period-over-period comparison"
      echo "  --force              Ignore cache, re-fetch all emails"
      echo "  --output FORMAT      Output format: markdown|json|terminal"
      echo "  --cache-dir PATH     Cache directory (default: ~/.advisor)"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate
if [[ -z "$DATE" && "$TODAY" == false ]]; then
  echo "Error: Please specify --today or --date YYYY-MM-DD"
  exit 1
fi

# Check dependencies
check_deps() {
  local missing=()
  
  if ! command -v himalaya &> /dev/null; then
    missing+=("himalaya")
  fi
  
  if ! command -v summarize &> /dev/null; then
    missing+=("summarize")
  fi
  
  if ! command -v jq &> /dev/null; then
    missing+=("jq")
  fi
  
  if [[ ${#missing[@]} -ne 0 ]]; then
    echo -e "${RED}Error: Missing required tools: ${missing[*]}${NC}"
    echo "Please install the required skills:"
    echo "  openclaw skills install himalaya"
    echo "  openclaw skills install summarize"
    exit 1
  fi
}

check_deps

if [[ -z "$DATE" ]]; then
  DATE=$(date +%Y-%m-%d)
fi

# Ensure cache directory exists
mkdir -p "${CACHE_DIR}"/{raw,reports,compare,scripts}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 1: Sync emails (unless force is used with existing cache)
if [[ "$FORCE" == true ]]; then
  echo -e "${BLUE}🔄 Force mode: Clearing cache for ${DATE}...${NC}"
  # Only clear raw data for the date, keep reports
fi

echo -e "${BLUE}🔄 Syncing emails...${NC}"
"${SCRIPT_DIR}/advisor-sync.sh" --cache-dir "${CACHE_DIR}" --since-hours 48

# Step 2: Parse and generate reports
echo -e "${BLUE}📊 Generating reports...${NC}"

# Get list of accounts to process
if [[ -n "$APPID" ]]; then
  ACCOUNTS="$APPID"
else
  # Find all accounts with data for the date
  ACCOUNTS=$(find "${CACHE_DIR}/raw" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; 2>/dev/null | sort -u)
fi

if [[ -z "$ACCOUNTS" ]]; then
  echo -e "${YELLOW}⚠️ No cached data found${NC}"
  exit 0
fi

# Generate report for each account
for AID in $ACCOUNTS; do
  echo -e "${GREEN}📋 Processing account: ${AID}${NC}"
  
  # Get account name from mapping
  ACCOUNT_NAME=""
  if [[ -f "${CACHE_DIR}/accounts.json" ]]; then
    ACCOUNT_NAME=$(jq -r ".[\"${AID}\"] // empty" "${CACHE_DIR}/accounts.json" 2>/dev/null)
  fi
  
  # Find architectures for this account
  if [[ -n "$ARCHITECTURE" ]]; then
    ARCHES="$ARCHITECTURE"
  else
    # Find all architectures with data
    ARCH_DIR="${CACHE_DIR}/raw/${AID}/${DATE}"
    if [[ -d "$ARCH_DIR" ]]; then
      ARCHES=$(find "$ARCH_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; 2>/dev/null | sort -u)
    else
      ARCHES="default"
    fi
  fi
  
  for ARCH in $ARCHES; do
    echo -e "${BLUE}  └─ Architecture: ${ARCH}${NC}"
    
    # Generate report using shell script
    "${SCRIPT_DIR}/generate-report.sh" \
      --appid "$AID" \
      --account-name "$ACCOUNT_NAME" \
      --date "$DATE" \
      --architecture "$ARCH" \
      --cache-dir "$CACHE_DIR" \
      --output-format "$OUTPUT_FORMAT" \
      $(if [[ "$COMPARE" == true ]]; then echo "--compare"; fi)
  done
done

echo -e "${GREEN}✅ Report generation complete${NC}"

# Step 3: Generate daily summary
echo -e "${BLUE}📋 Generating daily summary...${NC}"
"${SCRIPT_DIR}/daily-summary.sh" --date "$DATE" --cache-dir "$CACHE_DIR"

echo -e "${BLUE}📁 Reports saved to: ${CACHE_DIR}/reports/${NC}"
