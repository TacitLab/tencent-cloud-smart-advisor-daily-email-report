#!/bin/bash
#
# generate-report.sh - Generate structured report from cached data
# Usage: ./generate-report.sh --appid ID --date YYYY-MM-DD --architecture NAME [OPTIONS]
#

set -e

# Defaults
CACHE_DIR="${HOME}/.advisor"
OUTPUT_FORMAT="markdown"
APPID=""
DATE=""
ARCHITECTURE="default"
ACCOUNT_NAME=""
COMPARE=false
OUTPUT_FILE=""

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --appid) APPID="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    --architecture) ARCHITECTURE="$2"; shift 2 ;;
    --account-name) ACCOUNT_NAME="$2"; shift 2 ;;
    --cache-dir) CACHE_DIR="$2"; shift 2 ;;
    --output-format) OUTPUT_FORMAT="$2"; shift 2 ;;
    --compare) COMPARE=true; shift ;;
    --output-file) OUTPUT_FILE="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --appid ID              Account APPID (required)"
      echo "  --date YYYY-MM-DD       Report date (required)"
      echo "  --architecture NAME     Architecture name (default: default)"
      echo "  --account-name NAME     Display name for account"
      echo "  --cache-dir PATH        Cache directory (default: ~/.advisor)"
      echo "  --output-format FORMAT  markdown|json|terminal (default: markdown)"
      echo "  --compare               Enable period comparison"
      echo "  --output-file PATH      Output file path"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$APPID" || -z "$DATE" ]]; then
  echo "Error: --appid and --date are required"
  exit 1
fi

echo -e "${BLUE}  📂 Loading data for ${APPID}/${DATE}/${ARCHITECTURE}${NC}"

# Build cache path
CACHE_PATH="${CACHE_DIR}/raw/${APPID}/${DATE}/${ARCHITECTURE}"
REPORT_DIR="${CACHE_DIR}/reports/${APPID}/${DATE}/${ARCHITECTURE}"
mkdir -p "$REPORT_DIR"

if [[ ! -d "$CACHE_PATH" ]]; then
  echo "  ⚠️ No cached data found at ${CACHE_PATH}"
  exit 0
fi

# Find meta files
META_FILES=($(find "$CACHE_PATH" -name "*-meta.json" 2>/dev/null))

if [[ ${#META_FILES[@]} -eq 0 ]]; then
  echo "  ⚠️ No metadata found"
  exit 0
fi

# Generate report content
OUTPUT=""

if [[ "$OUTPUT_FORMAT" == "markdown" ]]; then
  # Get account display name
  DISPLAY_NAME="${ACCOUNT_NAME:-$APPID}"
  if [[ -f "${CACHE_DIR}/accounts.json" ]]; then
    MAPPED_NAME=$(jq -r ".[\"${APPID}\"] // empty" "${CACHE_DIR}/accounts.json" 2>/dev/null)
    [[ -n "$MAPPED_NAME" ]] && DISPLAY_NAME="$MAPPED_NAME"
  fi
  
  OUTPUT="## 账号: ${DISPLAY_NAME} (${APPID})\n\n"
  
  if [[ "$ARCHITECTURE" != "default" ]]; then
    OUTPUT+="### 架构图: ${ARCHITECTURE}\n\n"
  fi
  
  # Process each report
  for META_FILE in "${META_FILES[@]}"; do
    REPORT_TYPE=$(jq -r '.reportType // "unknown"' "$META_FILE")
    EVAL_TIME=$(jq -r '.date + " " + (.timestamp // "")' "$META_FILE" 2>/dev/null | cut -d' ' -f1-2)
    
    # Map report type to display name
    case "$REPORT_TYPE" in
      risk) TYPE_NAME="🔴 架构风险治理报告" ;;
      inspection) TYPE_NAME="🔍 日常巡检报告" ;;
      capacity) TYPE_NAME="📈 架构负载报告" ;;
      alert) TYPE_NAME="⚠️ 告警" ;;
      *) TYPE_NAME="📄 $REPORT_TYPE" ;;
    esac
    
    OUTPUT+="**报告类型**: ${TYPE_NAME}\n\n"
    [[ -n "$EVAL_TIME" ]] && OUTPUT+="**评估时间**: ${EVAL_TIME}\n\n"
    
    # Look for attachments
    ATTACH_DIR="$(dirname "$META_FILE")/attachments"
    if [[ -d "$ATTACH_DIR" ]]; then
      # Process Excel files with summarize
      for XLSX in "$ATTACH_DIR"/*.xlsx; do
        [[ -f "$XLSX" ]] || continue
        echo -e "${BLUE}  📊 Parsing: $(basename "$XLSX")${NC}"
        
        OUTPUT+="### 📊 数据概览\n\n"
        OUTPUT+="\`\`\`json\n"
        
        # Use summarize to extract content (required dependency)
        SUMMARIZE_OUTPUT=$(summarize "$XLSX" --json 2>/dev/null | head -c 2000 || echo "{}")
        OUTPUT+="${SUMMARIZE_OUTPUT}"
        OUTPUT+="\n\`\`\`\n\n"
      done
      
      # List PDFs if any
      for PDF in "$ATTACH_DIR"/*.pdf; do
        [[ -f "$PDF" ]] || continue
        OUTPUT+="📎 附件: $(basename "$PDF")\n\n"
      done
    fi
  done
  
  # Period comparison
  if [[ "$COMPARE" == true ]]; then
    # Find previous date
    RAW_DIR="${CACHE_DIR}/raw/${APPID}"
    PREV_DATE=$(find "$RAW_DIR" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; 2>/dev/null | grep -v "$DATE" | sort -r | head -1)
    
    if [[ -n "$PREV_DATE" ]]; then
      echo -e "${BLUE}  📊 Comparing with ${PREV_DATE}${NC}"
      OUTPUT+="### 📈 趋势对比\n\n"
      OUTPUT+="> 对比上期: ${PREV_DATE}\n\n"
      OUTPUT+="- 上期数据已缓存，可供对比\n\n"
    else
      echo -e "${YELLOW}  ℹ️  No previous data for comparison${NC}"
    fi
  fi
  
elif [[ "$OUTPUT_FORMAT" == "json" ]]; then
  # Build JSON output
  JSON_OBJ="{"
  JSON_OBJ+="\"appid\":\"${APPID}\","
  JSON_OBJ+="\"date\":\"${DATE}\","
  JSON_OBJ+="\"architecture\":\"${ARCHITECTURE}\","
  JSON_OBJ+="\"reports\":["
  
  FIRST=true
  for META_FILE in "${META_FILES[@]}"; do
    [[ "$FIRST" == true ]] || JSON_OBJ+=","
    FIRST=false
    META_JSON=$(cat "$META_FILE" | tr '\n' ' ')
    JSON_OBJ+="${META_JSON}"
  done
  
  JSON_OBJ+="]}"
  OUTPUT="$JSON_OBJ"
  
else
  # Terminal format
  OUTPUT="账号: ${APPID} | 架构: ${ARCHITECTURE}"
fi

# Output
if [[ -n "$OUTPUT_FILE" ]]; then
  echo -e "$OUTPUT" > "$OUTPUT_FILE"
  echo -e "${GREEN}  ✅ Saved to ${OUTPUT_FILE}${NC}"
else
  echo -e "\n${OUTPUT}"
fi

# Also save to reports directory
REPORT_FILE="${REPORT_DIR}/report.${OUTPUT_FORMAT}"
echo -e "$OUTPUT" > "$REPORT_FILE"

echo -e "${GREEN}  ✅ Report saved to ${REPORT_FILE}${NC}"
exit 0
