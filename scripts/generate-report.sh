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
RED=''
GREEN=''
YELLOW=''
NC=''

log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1"
}

# Check dependencies
check_deps() {
    local missing=()
    
    if ! command -v himalaya &> /dev/null; then
        missing+=("himalaya")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi
    
    if [ ${#missing[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        echo "Please install the required tools:"
        for tool in "${missing[@]}"; do
            if [ "$tool" = "himalaya" ]; then
                echo "  - cargo install himalaya"
            elif [ "$tool" = "jq" ]; then
                echo "  - apt-get install jq  (or equivalent)"
            fi
        done
        exit 1
    fi
    
    # Warn if summarize is not available
    if ! command -v summarize &> /dev/null; then
        log_warn "summarize not found. Attachment content will be listed but not summarized."
        log_warn "To install: brew install steipete/tap/summarize"
    fi
}

# Fetch emails from Tencent Advisor
fetch_emails() {
    local since_date
    since_date=$(date -u -d "$HOURS hours ago" +%Y-%m-%d 2>/dev/null || date -v-${HOURS}H +%Y-%m-%d)
    
    log_info "Fetching emails from $SENDER since $since_date..." >&2
    
    # Filter by sender and date (date format in email: "2026-02-25 17:22+08:00")
    himalaya envelope list --output json 2>/dev/null | jq -c '.[] | select(.from.addr == "'"$SENDER"'" and (.date | split(" ")[0] >= "'"$since_date"'"))' || echo "[]"
}

# Extract key information from email body
extract_email_info() {
    local body_file="$1"
    local email_type="$2"
    
    if [ ! -f "$body_file" ]; then
        echo "{}"
        return
    fi
    
    local body_content
    body_content=$(cat "$body_file" 2>/dev/null | tr -d '\0' | head -c 10000)
    
    # Extract key information based on patterns
    local appid=""
    local account_name=""
    local architecture=""
    local resource_count=""
    local risk_level=""
    local dashboard_url=""
    
    # Extract APPID
    if [[ "$body_content" =~ APPID[^0-9]*([0-9]+) ]]; then
        appid="${BASH_REMATCH[1]}"
    fi
    
    # Extract architecture name
    if [[ "$body_content" =~ 架构名称[^：]*[:：][[:space:]]*([^[:space:]]+) ]]; then
        architecture="${BASH_REMATCH[1]}"
    fi
    
    # Extract resource count
    if [[ "$body_content" =~ 本次共扫描资源[^0-9]*([0-9]+) ]]; then
        resource_count="${BASH_REMATCH[1]}"
    fi
    
    # Extract account name
    if [[ "$body_content" =~ 账号名称[^：]*[：:][^a-zA-Z0-9]*([0-9]+) ]]; then
        account_name="${BASH_REMATCH[1]}"
    fi
    
    # Extract dashboard URL
    if [[ "$body_content" =~ (https://[a-zA-Z0-9._-]+missionses[a-zA-Z0-9._/?&=-]*) ]]; then
        dashboard_url="${BASH_REMATCH[1]}"
    fi
    
    # Determine risk level based on email type and content
    if [[ "$email_type" == "risk" ]]; then
        risk_level="high"
    elif [[ "$email_type" == "alert" ]]; then
        risk_level="critical"
    elif [[ "$email_type" == "capacity" ]]; then
        risk_level="medium"
    else
        risk_level="low"
    fi
    
    # Output as JSON
    jq -n \
        --arg appid "$appid" \
        --arg account_name "$account_name" \
        --arg architecture "$architecture" \
        --arg resource_count "$resource_count" \
        --arg risk_level "$risk_level" \
        --arg dashboard_url "$dashboard_url" \
        '{
            appid: $appid,
            account_name: $account_name,
            architecture: $architecture,
            resource_count: $resource_count,
            risk_level: $risk_level,
            dashboard_url: $dashboard_url
        }'
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
    
    log_info "Processing: $subject" >&2
    
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
    
    # Extract key information from email body
    local content_summary
    content_summary=$(extract_email_info "$email_dir/body.txt" "$email_type")
    
    # Summarize attachments if any
    local attachments_summary="[]"
    if [ -d "$email_dir/attachments" ] && [ -n "$(find "$email_dir/attachments" -maxdepth 1 -type f 2>/dev/null | head -1)" ]; then
        attachments_summary=$(summarize_attachments "$email_dir/attachments")
    fi
    
    # Output structured data
    jq -n \
        --arg id "$email_id" \
        --arg subject "$subject" \
        --arg date "$date" \
        --arg type "$email_type" \
        --arg body_file "$email_dir/body.txt" \
        --argjson content_summary "$content_summary" \
        --argjson attachments "$attachments_summary" \
        '{
            id: $id,
            subject: $subject,
            date: $date,
            type: $type,
            content_summary: $content_summary,
            body_file: $body_file,
            attachments: $attachments
        }'
}

# Summarize all attachments in a directory
summarize_attachments() {
    local dir="$1"
    local results=()
    
    # Check if summarize is available
    local has_summarize=false
    if command -v summarize &> /dev/null; then
        has_summarize=true
    fi
    
    # Find all supported attachment files
    while IFS= read -r -d '' file; do
        [ -f "$file" ] || continue
        
        local filename
        filename=$(basename "$file")
        local filesize
        filesize=$(stat -c%s "$file" 2>/dev/null || stat -f%z "$file" 2>/dev/null || echo "unknown")
        
        if [ "$has_summarize" = true ]; then
            log_info "  Summarizing: $filename" >&2
            
            # Use summarize skill with JSON output
            local summary
            if summary=$(summarize "$file" --json --model google/gemini-3-flash-preview 2>/dev/null); then
                results+=("$(jq -n --arg name "$filename" --arg content "$summary" '{name: $name, summary: $content}')")
            else
                results+=("$(jq -n --arg name "$filename" --arg size "$filesize" '{name: $name, size: $size, note: "summarize failed"}')")
            fi
        else
            # Just list the file info without summarizing
            results+=("$(jq -n --arg name "$filename" --arg size "$filesize" '{name: $name, size: $size, note: "summarize not available"}')")
        fi
    done < <(find "$dir" -maxdepth 1 -type f \( -name "*.xlsx" -o -name "*.pdf" -o -name "*.csv" -o -name "*.txt" \) -print0 2>/dev/null)
    
    # Output as JSON array
    if [ ${#results[@]} -eq 0 ]; then
        echo '[]'
    else
        printf '%s\n' "${results[@]}" | jq -s '.'
    fi
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
