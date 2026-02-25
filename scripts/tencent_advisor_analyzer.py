#!/usr/bin/env python3
"""
Tencent Smart Advisor Email Analyzer
Enhanced version with attachment support, deep HTML parsing, and intelligent summarization.
"""

import imaplib
import email
import json
import os
import re
import base64
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Tuple
import argparse
import logging
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HTMLTextExtractor(HTMLParser):
    """Extract text from HTML"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.in_script = False
        self.in_style = False
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        if tag in ['script', 'style']:
            if tag == 'script':
                self.in_script = True
            else:
                self.in_style = True
        elif tag == 'a':
            attrs_dict = dict(attrs)
            if 'href' in attrs_dict:
                self.links.append(attrs_dict['href'])
                
    def handle_endtag(self, tag):
        if tag == 'script':
            self.in_script = False
        elif tag == 'style':
            self.in_style = False
        self.current_tag = None
        
    def handle_data(self, data):
        if not self.in_script and not self.in_style:
            text = data.strip()
            if text:
                self.text.append(text)
                
    def get_text(self):
        return ' '.join(self.text)
    
    def get_links(self):
        return self.links

class TencentAdvisorAnalyzer:
    """Enhanced email analyzer for Tencent Smart Advisor"""
    
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST', 'imap.exmail.qq.com')
        self.email_user = os.getenv('EMAIL_USER', '')
        self.email_pass = os.getenv('EMAIL_PASS', '')
        self.target_sender = os.getenv('EMAIL_SENDER', 'email@advisor.cloud.tencent.com')
        self.hours_back = int(os.getenv('EMAIL_HOURS', '24'))
        
        # Data storage
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, 'data')
        self.attachments_dir = os.path.join(self.data_dir, 'attachments')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.attachments_dir, exist_ok=True)
        
        self.history_file = os.path.join(self.data_dir, 'email_history.json')
        self.report_file = os.path.join(self.data_dir, 'latest_report.json')
        
        logger.info(f"Initializing Tencent Advisor Analyzer - Monitoring: {self.target_sender}")
    
    def connect_to_mailbox(self) -> imaplib.IMAP4_SSL:
        """Connect to mailbox"""
        try:
            mail = imaplib.IMAP4_SSL(self.email_host)
            mail.login(self.email_user, self.email_pass)
            mail.select('INBOX')
            logger.info("Successfully connected to mailbox")
            return mail
        except Exception as e:
            logger.error(f"Mailbox connection failed: {e}")
            raise
    
    def fetch_emails(self, hours: int = None) -> List[Dict]:
        """Fetch and parse emails from target sender"""
        if hours is None:
            hours = self.hours_back
            
        since_date = datetime.now() - timedelta(hours=hours)
        
        try:
            mail = self.connect_to_mailbox()
            since_str = since_date.strftime("%d-%b-%Y")
            search_criteria = f'(FROM "{self.target_sender}" SINCE "{since_str}")'
            
            logger.info(f"Searching emails: {search_criteria}")
            status, messages = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.warning("No emails found")
                mail.logout()
                return []
            
            email_ids = messages[0].split()
            logger.info(f"Found {len(email_ids)} emails")
            
            emails = []
            for email_id in email_ids:
                email_data = self.parse_email_full(mail, email_id)
                if email_data:
                    emails.append(email_data)
            
            mail.logout()
            logger.info(f"Successfully parsed {len(emails)} emails")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def parse_email_full(self, mail: imaplib.IMAP4_SSL, email_id: bytes) -> Optional[Dict]:
        """Parse email with full content extraction including attachments"""
        try:
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                return None
            
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Basic info
            subject = self.decode_mime_words(email_message.get('Subject', ''))
            from_addr = email_message.get('From', '')
            date_str = email_message.get('Date', '')
            
            try:
                email_date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except:
                email_date = datetime.now()
            
            # Extract all content parts
            content = self.extract_all_content(email_message, email_id.decode())
            
            # Analyze email type and importance
            email_type = self.classify_email_type(subject, content['text'])
            importance = self.assess_importance_advanced(subject, content)
            
            # Extract key information
            key_info = self.extract_key_information(subject, content, email_type)
            
            return {
                'id': email_id.decode(),
                'subject': subject,
                'from': from_addr,
                'date': email_date.isoformat(),
                'type': email_type,
                'importance': importance,
                'content': content,
                'key_info': key_info,
                'size': len(raw_email)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse email {email_id}: {e}")
            return None
    
    def extract_all_content(self, email_message, email_id: str) -> Dict:
        """Extract all content including HTML, text, and attachments"""
        content = {
            'text': '',
            'html': '',
            'links': [],
            'attachments': [],
            'structured_data': {}
        }
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Handle attachments
                if "attachment" in content_disposition:
                    attachment_info = self.save_attachment(part, email_id)
                    if attachment_info:
                        content['attachments'].append(attachment_info)
                
                # Handle body content
                elif content_type == "text/plain":
                    try:
                        text = part.get_payload(decode=True)
                        if text:
                            content['text'] = text.decode('utf-8', errors='ignore')
                    except Exception as e:
                        logger.warning(f"Failed to decode plain text: {e}")
                
                elif content_type == "text/html":
                    try:
                        html = part.get_payload(decode=True)
                        if html:
                            content['html'] = html.decode('utf-8', errors='ignore')
                            # Extract text and links from HTML
                            extractor = HTMLTextExtractor()
                            extractor.feed(content['html'])
                            content['html_text'] = extractor.get_text()
                            content['links'] = extractor.get_links()
                            
                            # Parse structured data from HTML
                            content['structured_data'] = self.parse_html_data(content['html'])
                    except Exception as e:
                        logger.warning(f"Failed to decode HTML: {e}")
        else:
            # Single part email
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    content_type = email_message.get_content_type()
                    decoded = payload.decode('utf-8', errors='ignore')
                    if content_type == "text/html":
                        content['html'] = decoded
                        extractor = HTMLTextExtractor()
                        extractor.feed(decoded)
                        content['html_text'] = extractor.get_text()
                        content['links'] = extractor.get_links()
                        content['structured_data'] = self.parse_html_data(decoded)
                    else:
                        content['text'] = decoded
            except Exception as e:
                logger.warning(f"Failed to decode single part: {e}")
        
        # Combine text sources
        if not content['text'] and content.get('html_text'):
            content['text'] = content['html_text']
        
        return content
    
    def save_attachment(self, part, email_id: str) -> Optional[Dict]:
        """Save attachment and return info"""
        try:
            filename = part.get_filename()
            if not filename:
                return None
            
            # Clean filename
            filename = self.decode_mime_words(filename)
            safe_filename = re.sub(r'[^\w\-\.]', '_', filename)
            
            # Create unique filename with email_id prefix
            unique_name = f"{email_id}_{safe_filename}"
            filepath = os.path.join(self.attachments_dir, unique_name)
            
            # Save attachment
            payload = part.get_payload(decode=True)
            if payload:
                with open(filepath, 'wb') as f:
                    f.write(payload)
                
                file_size = os.path.getsize(filepath)
                file_type = part.get_content_type()
                
                logger.info(f"Saved attachment: {unique_name} ({file_size} bytes)")
                
                return {
                    'original_name': filename,
                    'saved_name': unique_name,
                    'filepath': filepath,
                    'size': file_size,
                    'type': file_type,
                    'is_csv': filename.lower().endswith('.csv'),
                    'is_excel': filename.lower().endswith(('.xls', '.xlsx')),
                    'is_pdf': filename.lower().endswith('.pdf'),
                    'is_image': file_type.startswith('image/')
                }
        except Exception as e:
            logger.error(f"Failed to save attachment: {e}")
        
        return None
    
    def parse_html_data(self, html: str) -> Dict:
        """Extract structured data from HTML content"""
        data = {
            'app_id': None,
            'architecture_id': None,
            'metrics': [],
            'alerts': [],
            'recommendations': [],
            'report_links': []
        }
        
        try:
            # Extract APP ID
            app_match = re.search(r'APPID\s*:?\s*(\d+)', html, re.IGNORECASE)
            if app_match:
                data['app_id'] = app_match.group(1)
            
            # Extract Architecture ID
            arch_match = re.search(r'arch-[a-z0-9]+', html, re.IGNORECASE)
            if arch_match:
                data['architecture_id'] = arch_match.group(0)
            
            # Extract metrics (CPU, Memory, Disk usage patterns)
            metric_patterns = [
                r'(CPU|内存|磁盘|存储|带宽)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(%|GB|MB|Mbps)',
                r'使用率|利用率)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%',
            ]
            for pattern in metric_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    data['metrics'].append(''.join(match))
            
            # Extract alerts and warnings
            alert_keywords = ['风险', '告警', '警告', '异常', 'critical', 'warning', 'alert']
            for keyword in alert_keywords:
                if keyword in html.lower():
                    # Find context around alert
                    idx = html.lower().find(keyword)
                    start = max(0, idx - 100)
                    end = min(len(html), idx + 200)
                    context = re.sub(r'<[^>]+>', '', html[start:end]).strip()
                    if context and len(context) > 10:
                        data['alerts'].append(context)
            
            # Extract recommendations
            rec_patterns = [
                r'建议[^<>]{10,200}',
                r'recommend[^<>]{10,200}',
                r'优化[^<>]{10,200}',
            ]
            for pattern in rec_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches[:3]:  # Limit to 3
                    clean = re.sub(r'<[^>]+>', '', match).strip()
                    if clean and len(clean) > 10:
                        data['recommendations'].append(clean)
            
            # Extract report/dashboard links
            links = re.findall(r'href=["\'](https?://[^"\']+)["\']', html)
            data['report_links'] = list(set(links))[:5]  # Unique links, limit to 5
            
        except Exception as e:
            logger.warning(f"HTML parsing error: {e}")
        
        return data
    
    def classify_email_type(self, subject: str, body: str) -> str:
        """Classify email by type"""
        subject_lower = subject.lower()
        body_lower = body.lower()
        
        if any(kw in subject_lower for kw in ['容量', '负载', 'capacity', 'load', 'arch']):
            return 'capacity_report'
        elif any(kw in subject_lower for kw in ['巡检', '巡检', 'inspection', 'check']):
            return 'inspection_report'
        elif any(kw in subject_lower for kw in ['告警', 'alert', '警告', 'warning']):
            return 'alert'
        elif any(kw in subject_lower for kw in ['成本', 'cost', 'billing', '费用']):
            return 'cost_report'
        elif any(kw in subject_lower for kw in ['安全', 'security', 'risk']):
            return 'security_report'
        else:
            return 'general'
    
    def assess_importance_advanced(self, subject: str, content: Dict) -> str:
        """Advanced importance assessment"""
        text = (subject + ' ' + content.get('text', '')).lower()
        
        # Critical indicators
        critical = ['critical', 'urgent', 'emergency', '严重', '紧急', 'p0', '故障', '宕机']
        high = ['high', 'important', '告警', '警告', '风险', '异常', 'important']
        
        for kw in critical:
            if kw in text:
                return 'critical'
        
        for kw in high:
            if kw in text:
                return 'high'
        
        # Check for metrics indicating high usage
        if content.get('structured_data', {}).get('alerts'):
            return 'high'
        
        return 'normal'
    
    def extract_key_information(self, subject: str, content: Dict, email_type: str) -> Dict:
        """Extract key information from email"""
        info = {
            'summary': '',
            'highlights': [],
            'action_items': [],
            'dashboard_links': []
        }
        
        structured = content.get('structured_data', {})
        text = content.get('text', '')
        
        # Generate summary based on email type
        if email_type == 'capacity_report':
            arch_id = structured.get('architecture_id', 'unknown')
            app_id = structured.get('app_id', 'unknown')
            info['summary'] = f"容量监测报告 - 架构ID: {arch_id}, APPID: {app_id}"
            
            if structured.get('metrics'):
                info['highlights'].append(f"监测指标: {', '.join(structured['metrics'][:3])}")
            
        elif email_type == 'inspection_report':
            info['summary'] = "智能巡检报告 - 基于DeepSeek/混元T1大模型分析"
            
            if structured.get('recommendations'):
                info['highlights'].extend(structured['recommendations'][:2])
        
        elif email_type == 'alert':
            alerts = structured.get('alerts', [])
            if alerts:
                info['summary'] = f"告警通知 - {len(alerts)}项需要注意"
                info['highlights'] = alerts[:3]
        
        else:
            # General summary from text
            sentences = re.split(r'[。！？.!?]', text)
            if sentences:
                info['summary'] = sentences[0][:100] + '...' if len(sentences[0]) > 100 else sentences[0]
        
        # Extract action items
        action_patterns = [
            r'请[^<>]{10,100}(?:查看|处理|注意|关注)',
            r'建议[^<>]{10,100}',
            r'需要[^<>]{10,100}(?:处理|优化|调整)',
        ]
        for pattern in action_patterns:
            matches = re.findall(pattern, text)
            for match in matches[:2]:
                clean = re.sub(r'\s+', ' ', match).strip()
                if clean and len(clean) > 5:
                    info['action_items'].append(clean)
        
        # Dashboard links
        if structured.get('report_links'):
            info['dashboard_links'] = structured['report_links'][:3]
        
        return info
    
    def generate_intelligent_report(self, emails: List[Dict]) -> Dict:
        """Generate intelligent summary report"""
        if not emails:
            return {
                'status': 'no_emails',
                'summary': '今日未收到腾讯智能顾问邮件',
                'details': []
            }
        
        report = {
            'status': 'success',
            'generated_at': datetime.now().isoformat(),
            'period_hours': self.hours_back,
            'total_emails': len(emails),
            'summary': '',
            'by_type': {},
            'highlights': [],
            'attention_required': [],
            'action_items': [],
            'details': []
        }
        
        # Group by type and importance
        for email in emails:
            email_type = email.get('type', 'general')
            importance = email.get('importance', 'normal')
            
            if email_type not in report['by_type']:
                report['by_type'][email_type] = []
            report['by_type'][email_type].append(email)
            
            if importance in ['critical', 'high']:
                report['attention_required'].append({
                    'subject': email['subject'],
                    'type': email_type,
                    'importance': importance,
                    'reason': email.get('key_info', {}).get('summary', '')
                })
        
        # Generate overall summary
        type_names = {
            'capacity_report': '容量报告',
            'inspection_report': '巡检报告',
            'alert': '告警',
            'cost_report': '成本报告',
            'security_report': '安全报告',
            'general': '一般通知'
        }
        
        type_summary = []
        for email_type, type_emails in report['by_type'].items():
            name = type_names.get(email_type, email_type)
            type_summary.append(f"{name}: {len(type_emails)}封")
        
        report['summary'] = f"过去{self.hours_back}小时收到{len(emails)}封邮件，包括{', '.join(type_summary)}"
        
        # Collect highlights and actions
        for email in emails:
            key_info = email.get('key_info', {})
            
            if key_info.get('highlights'):
                report['highlights'].extend(key_info['highlights'])
            
            if key_info.get('action_items'):
                report['action_items'].extend(key_info['action_items'])
            
            # Add detailed info
            detail = {
                'subject': email['subject'],
                'type': email.get('type', 'general'),
                'importance': email.get('importance', 'normal'),
                'summary': key_info.get('summary', ''),
                'time': email.get('date', ''),
                'attachments': [a['original_name'] for a in email.get('content', {}).get('attachments', [])],
                'links': key_info.get('dashboard_links', [])
            }
            report['details'].append(detail)
        
        # Save report
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report
    
    def format_report_markdown(self, report: Dict) -> str:
        """Format report as markdown"""
        if report['status'] == 'no_emails':
            return f"""# 腾讯智能顾问日报 - {datetime.now().strftime('%Y-%m-%d')}

{report['summary']}

---
*报告生成时间: {datetime.now().strftime('%H:%M')}*"""
        
        md = f"""# 腾讯智能顾问日报 - {datetime.now().strftime('%Y-%m-%d')}

## 📊 概览
{report['summary']}

## 📈 邮件分类统计
"""
        
        type_names = {
            'capacity_report': '📊 容量报告',
            'inspection_report': '🔍 巡检报告',
            'alert': '🚨 告警',
            'cost_report': '💰 成本报告',
            'security_report': '🔒 安全报告',
            'general': '📧 一般通知'
        }
        
        for email_type, type_emails in report.get('by_type', {}).items():
            name = type_names.get(email_type, email_type)
            md += f"- {name}: {len(type_emails)} 封\n"
        
        # Attention required section
        if report.get('attention_required'):
            md += "\n## ⚠️ 需要关注\n"
            for item in report['attention_required']:
                md += f"- **{item['subject']}** - {item['reason']}\n"
        
        # Highlights
        if report.get('highlights'):
            md += "\n## 💡 重点信息\n"
            for highlight in report['highlights'][:5]:
                md += f"- {highlight}\n"
        
        # Action items
        if report.get('action_items'):
            md += "\n## 🎯 建议操作\n"
            for action in report['action_items'][:3]:
                md += f"- {action}\n"
        
        # Detailed reports
        md += "\n## 📋 详细报告\n"
        for detail in report.get('details', []):
            md += f"\n### {detail['subject']}\n"
            md += f"- **类型**: {type_names.get(detail['type'], detail['type'])}\n"
            md += f"- **重要性**: {detail['importance']}\n"
            md += f"- **摘要**: {detail['summary']}\n"
            
            if detail.get('attachments'):
                md += f"- **附件**: {', '.join(detail['attachments'])}\n"
            
            if detail.get('links'):
                md += f"- **查看详情**: [点击访问]({detail['links'][0]})\n"
        
        md += f"\n---\n*报告生成时间: {datetime.now().strftime('%H:%M')} | 统计周期: 过去{report['period_hours']}小时*"
        
        return md
    
    def run(self, output_format: str = 'markdown', output_file: str = None) -> str:
        """Run complete analysis"""
        try:
            logger.info("Starting Tencent Advisor email analysis...")
            
            # Fetch emails
            emails = self.fetch_emails()
            
            # Generate report
            report = self.generate_intelligent_report(emails)
            
            # Format output
            if output_format == 'json':
                output = json.dumps(report, ensure_ascii=False, indent=2)
            else:
                output = self.format_report_markdown(report)
            
            # Save to file if specified
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output)
                logger.info(f"Report saved to: {output_file}")
            
            return output
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return f"# 报告生成失败\n\n错误: {str(e)}"
    
    def decode_mime_words(self, text: str) -> str:
        """Decode MIME encoded text"""
        if not text:
            return ""
        decoded_parts = []
        for part, encoding in decode_header(text):
            if isinstance(part, bytes):
                if encoding:
                    decoded_parts.append(part.decode(encoding))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='ignore'))
            else:
                decoded_parts.append(part)
        return ''.join(decoded_parts)

def main():
    parser = argparse.ArgumentParser(description='Tencent Smart Advisor Email Analyzer')
    parser.add_argument('--hours', type=int, default=24, help='Time range in hours')
    parser.add_argument('--format', choices=['markdown', 'json'], default='markdown', help='Output format')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--hook', action='store_true', help='Run as heartbeat hook')
    
    args = parser.parse_args()
    
    analyzer = TencentAdvisorAnalyzer()
    
    if args.hours:
        analyzer.hours_back = args.hours
    
    result = analyzer.run(output_format=args.format, output_file=args.output)
    print(result)

if __name__ == '__main__':
    main()
