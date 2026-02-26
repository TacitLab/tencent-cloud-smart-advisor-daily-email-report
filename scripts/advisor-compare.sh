#!/bin/bash
#
# advisor-compare.sh - Compare current and previous period reports
# Usage: ./advisor-compare.sh --appid ID [--architecture NAME] [--current DATE] [--previous DATE]
#

set -e

CACHE_DIR="${HOME}/.advisor"
APPID=""
ARCHITECTURE="default"
CURRENT_DATE=""
PREVIOUS_DATE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --appid)
      APPID="$2"
      shift 2
      ;;
    --architecture)
      ARCHITECTURE="$2"
      shift 2
      ;;
    --current)
      CURRENT_DATE="$2"
      shift 2
      ;;
    --previous)
      PREVIOUS_DATE="$2"
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
      echo "  --appid ID           Account to compare (required)"
      echo "  --architecture NAME  Architecture to compare (default: default)"
      echo "  --current DATE       Current period date (default: today)"
      echo "  --previous DATE      Previous period date (auto-detected if not specified)"
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

if [[ -z "$APPID" ]]; then
  echo "Error: --appid is required"
  exit 1
fi

if [[ -z "$CURRENT_DATE" ]]; then
  CURRENT_DATE=$(date +%Y-%m-%d)
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Auto-detect previous date if not specified
if [[ -z "$PREVIOUS_DATE" ]]; then
  RAW_PATH="${CACHE_DIR}/raw/${APPID}"
  if [[ -d "$RAW_PATH" ]]; then
    PREVIOUS_DATE=$(find "$RAW_PATH" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | grep -v "$CURRENT_DATE" | sort -r | head -1)
  fi
fi

if [[ -z "$PREVIOUS_DATE" ]]; then
  echo "⚠️ No previous date found for comparison"
  exit 1
fi

echo "📊 Comparing ${CURRENT_DATE} vs ${PREVIOUS_DATE}"
echo "   Account: ${APPID}"
echo "   Architecture: ${ARCHITECTURE}"
echo ""

# Generate reports for comparison
CURRENT_REPORT=$(mktemp)
PREVIOUS_REPORT=$(mktemp)

python3 "${SCRIPT_DIR}/generate-report.py" \
  --appid "$APPID" \
  --date "$CURRENT_DATE" \
  --architecture "$ARCHITECTURE" \
  --cache-dir "$CACHE_DIR" \
  --output-format json \
  --output-file "$CURRENT_REPORT"

python3 "${SCRIPT_DIR}/generate-report.py" \
  --appid "$APPID" \
  --date "$PREVIOUS_DATE" \
  --architecture "$ARCHITECTURE" \
  --cache-dir "$CACHE_DIR" \
  --output-format json \
  --output-file "$PREVIOUS_REPORT"

# Display comparison
echo "📈 Comparison Results:"
echo ""

# Use Python to do the comparison logic
python3 << EOF
import json
import sys

with open("$CURRENT_REPORT", 'r') as f:
    current = json.load(f)

with open("$PREVIOUS_REPORT", 'r') as f:
    previous = json.load(f)

def get_summary(data):
    reports = data.get("reports", [])
    if reports:
        return reports[0].get("xlsx_data", {}).get("summary", {})
    return {}

curr_sum = get_summary(current)
prev_sum = get_summary(previous)

print(f"{'指标':<15} {'上期':>8} {'本期':>8} {'变化':>8}")
print("-" * 42)

metrics = [
    ("高风险", "high_risk", "🔴"),
    ("中风险", "medium_risk", "🟡"),
    ("低风险", "low_risk", "🟢"),
    ("健康", "healthy", "✅"),
]

for label, key, emoji in metrics:
    c = curr_sum.get(key, 0)
    p = prev_sum.get(key, 0)
    diff = c - p
    trend = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
    print(f"{emoji} {label:<12} {p:>8} {c:>8} {trend}{abs(diff):>6}")

EOF

# Cleanup
rm -f "$CURRENT_REPORT" "$PREVIOUS_REPORT"

echo ""
echo "✅ Comparison complete"
