#!/bin/bash
#
# Tencent Smart Advisor Daily Report Generator
# Orchestrates himalaya + summarize + jq to generate reports
#

set -euo pipefail

# Configuration
SENDER="email@advisor.cloud.tencent.com"
HOURS=${1:-24}
TEMP_DIR=$(mktemp -d)
OUTPUT_DIR="${OUTPUT_DIR:-/tmp/advisor-reports}"

# Cleanup on exit
trap 'rm -rf "$TEMP_DIR"' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

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
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        echo "Please install the required skills:"
        for tool in "${missing[@]}"; do
            echo "  - openclaw skills install $tool"
        done
        exit 1
    fi
}

# Fetch emails from Tencent Advisor
fetch_emails() {
    local since_date
    since_date=$(date -u -d "$HOURS hours ago" +%Y-%m-%d 2>/dev/null || date -v-${HOURS}H +%Y-%m-%d)
    
    log_info "Fetching emails from $SENDER since $since_date..."
    
    himalaya envelope list from:"$SENDER" since:"$since_date" --output json 2>/dev/null | jq -c '.[]' || echo "[]"
}

# Process a single email
process_email() {
    local email_json="$1"
    local email_id
    local subject
    local date
    
    email_id=$(echo "$email_json" | jq -r '.id')
    subject=$(echo "$email_json" | jq -r '.subject // "(no subject)"')
    date=$(echo "$email_json" | jq -r '.date // "unknown"')
    
    log_info "Processing: $subject"
    
    # Create directory for this email
    local email_dir="$TEMP_DIR/$email_id"
    mkdir -p "$email_dir"
    
    # Read email body
    himalaya message read "$email_id" > "$email_dir/body.txt" 2>/dev/null || true
    
    # Download attachments
    himalaya attachment download "$email_id" --dir "$email_dir/attachments" 2>/dev/null || true
    
    # Classify email type based on subject
    local email_type="unknown"
    if [[ "$subject" == *"负载报告"* ]]; then
        email_type="capacity"
    elif [[ "$subject" == *"巡检报告"* ]]; then
        email_type="inspection"
    elif [[ "$subject" == *"风险"* ]]; then
        email_type="risk"
    elif [[ "$subject" == *"告警"* ]]; then
        email_type="alert"
    fi
    
    # Summarize attachments if any
    local attachments_summary="[]"
    if [ -d "$email_dir/attachments" ] && [ "$(ls -A "$email_dir/attachments" 2>/dev/null)" ]; then
        attachments_summary=$(summarize_attachments "$email_dir/attachments")
    fi
    
    # Output structured data
    jq -n \
        --arg id "$email_id" \
        --arg subject "$subject" \
        --arg date "$date" \
        --arg type "$email_type" \
        --arg body_file "$email_dir/body.txt" \
        --argjson attachments "$attachments_summary" \
        '{
            id: $id,
            subject: $subject,
            date: $date,
            type: $type,
            body_file: $body_file,
            attachments: $attachments
        }'
}

# Summarize all attachments in a directory
summarize_attachments() {
    local dir="$1"
    local results=()
    
    for file in "$dir"/*.{xlsx,pdf,csv,txt} 2>/dev/null; do
        [ -f "$file" ] || continue
        
        log_info "  Summarizing: $(basename "$file")"
        
        # Use summarize skill with JSON output
        local summary
        if summary=$(summarize "$file" --json --model google/gemini-3-flash-preview 2>/dev/null); then
            results+=("$(jq -n --arg name "$(basename "$file")" --arg content "$summary" '{name: $name, summary: $content}')")
        else
            results+=("$(jq -n --arg name "$(basename "$file")" --arg error "Failed to summarize" '{name: $name, error: $error}')")
        fi
    done
    
    # Output as JSON array
    printf '%s\n' "${results[@]}" | jq -s '.'
}

# Generate final report
generate_report() {
    local data="$1"
    local report_time
    report_time=$(date -u +"%Y-%m-%d %H:%M UTC")
    
    # Count by type
    local capacity_count
    local inspection_count
    local risk_count
    local alert_count
    
    capacity_count=$(echo "$data" | jq '[.[] | select(.type == "capacity")] | length')
    inspection_count=$(echo "$data" | jq '[.[] | select(.type == "inspection")] | length')
    risk_count=$(echo "$data" | jq '[.[] | select(.type == "risk")] | length')
    alert_count=$(echo "$data" | jq '[.[] | select(.type == "alert")] | length')
    
    local total
    total=$(echo "$data" | jq 'length')
    
    # Output report as JSON
    jq -n \
        --arg report_time "$report_time" \
        --arg hours "$HOURS" \
        --argjson total "$total" \
        --argjson capacity "$capacity_count" \
        --argjson inspection "$inspection_count" \
        --argjson risk "$risk_count" \
        --argjson alert "$alert_count" \
        --argjson emails "$data" \
        '{
            metadata: {
                generated_at: $report_time,
                period_hours: ($hours | tonumber),
                sender: "email@advisor.cloud.tencent.com"
            },
            summary: {
                total_emails: $total,
                by_type: {
                    capacity: $capacity,
                    inspection: $inspection,
                    risk: $risk,
                    alert: $alert
                }
            },
            emails: $emails
        }'
}

# Main execution
main() {
    log_info "Tencent Smart Advisor Daily Report Generator"
    log_info "Time range: last $HOURS hours"
    
    # Check dependencies
    check_deps
    
    # Fetch emails
    local emails_json
    emails_json=$(fetch_emails)
    
    if [ -z "$emails_json" ] || [ "$emails_json" == "[]" ]; then
        log_warn "No emails found from $SENDER in the last $HOURS hours"
        echo '{"emails": [], "summary": {"total_emails": 0}}'
        exit 0
    fi
    
    log_info "Found emails, processing..."
    
    # Process each email
    local processed=()
    while IFS= read -r email; do
        [ -n "$email" ] || continue
        processed+=("$(process_email "$email")")
    done <<< "$emails_json"
    
    # Combine results
    local all_data
    all_data=$(printf '%s\n' "${processed[@]}" | jq -s '.')
    
    # Generate final report
    local report
    report=$(generate_report "$all_data")
    
    # Output
    echo "$report" | jq '.'
    
    # Also save to file
    mkdir -p "$OUTPUT_DIR"
    local report_file="$OUTPUT_DIR/report-$(date -u +%Y%m%d-%H%M%S).json"
    echo "$report" > "$report_file"
    log_info "Report saved to: $report_file"
}

main "$@"
