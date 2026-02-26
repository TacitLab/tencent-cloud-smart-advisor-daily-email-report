#!/bin/bash
#
# advisor-sync.sh - Sync emails from Tencent Smart Advisor and cache them
# Usage: ./advisor-sync.sh [OPTIONS]
#

set -e

CACHE_DIR="${HOME}/.advisor"
SINCE_HOURS=24
DRY_RUN=false
PRUNE_DAYS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --since-hours)
      SINCE_HOURS="$2"
      shift 2
      ;;
    --cache-dir)
      CACHE_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --prune-days)
      PRUNE_DAYS="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --since-hours N      Sync emails from last N hours (default: 24)"
      echo "  --cache-dir PATH     Cache directory (default: ~/.advisor)"
      echo "  --dry-run            Show what would be synced without downloading"
      echo "  --prune-days N       Remove cache entries older than N days"
      echo "  --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Ensure cache structure exists
mkdir -p "${CACHE_DIR}"/{raw,reports,compare}

# Initialize index if not exists
INDEX_FILE="${CACHE_DIR}/index.json"
if [[ ! -f "$INDEX_FILE" ]]; then
  echo '{"version":"1.0","lastSync":null,"emails":{}}' > "$INDEX_FILE"
fi

# Calculate since date
SINCE_DATE=$(date -u -d "${SINCE_HOURS} hours ago" +%Y-%m-%d 2>/dev/null || date -v-${SINCE_HOURS}H -u +%Y-%m-%d)

echo "🔍 Fetching emails since ${SINCE_DATE}..."

# Fetch emails from Tencent Smart Advisor
EMAILS_JSON=$(himalaya envelope list from:email@advisor.cloud.tencent.com --output json 2>/dev/null | jq -c '.')

if [[ -z "$EMAILS_JSON" || "$EMAILS_JSON" == "null" ]]; then
  echo "⚠️ No emails found"
  exit 0
fi

# Count emails
EMAIL_COUNT=$(echo "$EMAILS_JSON" | jq 'length')
echo "📧 Found ${EMAIL_COUNT} emails"

# Process each email
echo "$EMAILS_JSON" | jq -c '.[]' | while read -r email; do
  MSG_ID=$(echo "$email" | jq -r '.id')
  SUBJECT=$(echo "$email" | jq -r '.subject')
  DATE_STR=$(echo "$email" | jq -r '.date')
  HAS_ATTACH=$(echo "$email" | jq -r '.has_attachment')
  
  # Skip non-Advisor emails
  if [[ ! "$SUBJECT" =~ "腾讯云智能顾问" ]]; then
    continue
  fi
  
  # Parse subject to extract metadata
  # Subject format: 腾讯云智能顾问(TSA)-[报告类型]-[架构名]
  REPORT_TYPE=""
  ARCHITECTURE=""
  
  if [[ "$SUBJECT" =~ "架构风险治理报告" ]]; then
    REPORT_TYPE="risk"
  elif [[ "$SUBJECT" =~ "日常巡检报告" ]]; then
    REPORT_TYPE="inspection"
  elif [[ "$SUBJECT" =~ "架构负载报告" ]]; then
    REPORT_TYPE="capacity"
  elif [[ "$SUBJECT" =~ "告警" ]]; then
    REPORT_TYPE="alert"
  else
    REPORT_TYPE="other"
  fi
  
  # Extract architecture name from subject
  if [[ "$SUBJECT" =~ -([a-zA-Z0-9_-]+)$ ]]; then
    ARCHITECTURE="${BASH_REMATCH[1]}"
  else
    ARCHITECTURE="default"
  fi
  
  # Parse date
  EMAIL_DATE=$(echo "$DATE_STR" | cut -d' ' -f1)
  
  # Check if already cached (by message ID)
  ALREADY_CACHED=$(jq -r ".emails[\"${MSG_ID}\"] | if . == null then false else true end" "$INDEX_FILE")
  
  if [[ "$ALREADY_CACHED" == "true" && "$DRY_RUN" == false ]]; then
    echo "  ⏭️  Skipping ${MSG_ID} (already cached)"
    continue
  fi
  
  if [[ "$DRY_RUN" == true ]]; then
    echo "  [DRY-RUN] Would sync: ${SUBJECT}"
    continue
  fi
  
  echo "  📥 Processing: ${SUBJECT}"
  
  # Fetch full email content to extract APPID
  EMAIL_CONTENT=$(himalaya message read "$MSG_ID" 2>/dev/null || true)
  
  # Extract APPID from content
  APPID=$(echo "$EMAIL_CONTENT" | grep -oE 'APPID[^0-9]*[0-9]+' | grep -oE '[0-9]+' | head -1)
  if [[ -z "$APPID" ]]; then
    APPID=$(echo "$EMAIL_CONTENT" | grep -oE '1312346585' | head -1)
  fi
  if [[ -z "$APPID" ]]; then
    APPID="unknown"
  fi
  
  # Create cache directories
  CACHE_PATH="${CACHE_DIR}/raw/${APPID}/${EMAIL_DATE}/${ARCHITECTURE}"
  mkdir -p "$CACHE_PATH/attachments"
  
  # Save email metadata
  META_FILE="${CACHE_PATH}/${MSG_ID}-meta.json"
  echo "{\"messageId\":\"${MSG_ID}\",\"subject\":\"${SUBJECT}\",\"date\":\"${DATE_STR}\",\"appId\":\"${APPID}\",\"reportType\":\"${REPORT_TYPE}\",\"architecture\":\"${ARCHITECTURE}\",\"cachedAt\":\"$(date -Iseconds)\"}" > "$META_FILE"
  
  # Save email content
  echo "$EMAIL_CONTENT" > "${CACHE_PATH}/${MSG_ID}-content.txt"
  
  # Download attachments
  if [[ "$HAS_ATTACH" == "true" ]]; then
    echo "     └─ Downloading attachments..."
    cd "${CACHE_PATH}/attachments" && himalaya attachment download "$MSG_ID" 2>/dev/null || true
  fi
  
  # Update index
  TMP_INDEX=$(mktemp)
  jq ".emails[\"${MSG_ID}\"] = {\"subject\":\"${SUBJECT}\",\"appId\":\"${APPID}\",\"reportType\":\"${REPORT_TYPE}\",\"architecture\":\"${ARCHITECTURE}\",\"date\":\"${EMAIL_DATE}\",\"cachedAt\":\"$(date -Iseconds)\"}" "$INDEX_FILE" > "$TMP_INDEX"
  mv "$TMP_INDEX" "$INDEX_FILE"
done

# Update last sync timestamp
TMP_INDEX=$(mktemp)
jq ".lastSync = \"$(date -Iseconds)\"" "$INDEX_FILE" > "$TMP_INDEX"
mv "$TMP_INDEX" "$INDEX_FILE"

# Prune old cache if requested
if [[ $PRUNE_DAYS -gt 0 ]]; then
  echo "🧹 Pruning cache older than ${PRUNE_DAYS} days..."
  find "${CACHE_DIR}/raw" -type d -mtime +$PRUNE_DAYS -exec rm -rf {} + 2>/dev/null || true
fi

echo "✅ Sync complete"
