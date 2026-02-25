#!/usr/bin/env python3
"""
Attachment Content Parser
Extract data from Excel and PDF attachments
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class AttachmentParser:
    """Parse content from various attachment types"""
    
    def __init__(self):
        self.parsers = {
            '.xlsx': self.parse_excel,
            '.xls': self.parse_excel,
            '.csv': self.parse_csv,
            '.pdf': self.parse_pdf,
        }
    
    def parse_attachment(self, filepath: str) -> Dict[str, Any]:
        """Parse attachment based on file extension"""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext not in self.parsers:
            return {
                'type': 'unknown',
                'filename': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'content': None,
                'error': f'Unsupported file type: {ext}'
            }
        
        try:
            return self.parsers[ext](filepath)
        except Exception as e:
            logger.error(f"Failed to parse {filepath}: {e}")
            return {
                'type': ext[1:],
                'filename': os.path.basename(filepath),
                'size': os.path.getsize(filepath),
                'content': None,
                'error': str(e)
            }
    
    def parse_excel(self, filepath: str) -> Dict[str, Any]:
        """Parse Excel file using pandas/openpyxl"""
        result = {
            'type': 'excel',
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath),
            'sheets': [],
            'summary': {},
            'metrics': [],
            'alerts': [],
            'recommendations': []
        }
        
        try:
            import pandas as pd
            
            # Read all sheets
            excel_file = pd.ExcelFile(filepath)
            
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(filepath, sheet_name=sheet_name)
                    
                    sheet_info = {
                        'name': sheet_name,
                        'rows': len(df),
                        'columns': len(df.columns),
                        'column_names': df.columns.tolist()[:10],  # First 10 columns
                        'preview': []
                    }
                    
                    # Get preview data (first 5 rows)
                    if not df.empty:
                        preview_df = df.head(5)
                        sheet_info['preview'] = preview_df.to_dict('records')
                        
                        # Try to extract metrics from numeric columns
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                            stats = df[col].describe()
                            result['metrics'].append({
                                'sheet': sheet_name,
                                'column': col,
                                'mean': round(stats.get('mean', 0), 2) if not pd.isna(stats.get('mean')) else 0,
                                'max': round(stats.get('max', 0), 2) if not pd.isna(stats.get('max')) else 0,
                                'min': round(stats.get('min', 0), 2) if not pd.isna(stats.get('min')) else 0
                            })
                    
                    result['sheets'].append(sheet_info)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse sheet {sheet_name}: {e}")
            
            # Generate summary
            total_rows = sum(s['rows'] for s in result['sheets'])
            result['summary'] = {
                'total_sheets': len(result['sheets']),
                'total_rows': total_rows,
                'sheet_names': [s['name'] for s in result['sheets']]
            }
            
            # Try to find alerts and recommendations in text columns
            result['alerts'] = self._extract_alerts_from_excel(result['sheets'])
            result['recommendations'] = self._extract_recommendations_from_excel(result['sheets'])
            
        except ImportError:
            result['error'] = 'pandas/openpyxl not installed. Run: pip install pandas openpyxl'
            result['content'] = self._basic_file_info(filepath)
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def parse_csv(self, filepath: str) -> Dict[str, Any]:
        """Parse CSV file"""
        result = {
            'type': 'csv',
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath),
            'rows': 0,
            'columns': [],
            'preview': [],
            'metrics': []
        }
        
        try:
            import pandas as pd
            
            df = pd.read_csv(filepath)
            result['rows'] = len(df)
            result['columns'] = df.columns.tolist()
            
            if not df.empty:
                result['preview'] = df.head(5).to_dict('records')
                
                # Extract metrics from numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                for col in numeric_cols[:3]:
                    stats = df[col].describe()
                    result['metrics'].append({
                        'column': col,
                        'mean': round(stats.get('mean', 0), 2),
                        'max': round(stats.get('max', 0), 2),
                        'min': round(stats.get('min', 0), 2)
                    })
                    
        except ImportError:
            result['error'] = 'pandas not installed. Run: pip install pandas'
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def parse_pdf(self, filepath: str) -> Dict[str, Any]:
        """Parse PDF file using pdfplumber"""
        result = {
            'type': 'pdf',
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath),
            'pages': 0,
            'text_preview': '',
            'tables': [],
            'metrics': [],
            'alerts': [],
            'recommendations': []
        }
        
        try:
            import pdfplumber
            
            with pdfplumber.open(filepath) as pdf:
                result['pages'] = len(pdf.pages)
                
                full_text = []
                
                # Extract text from first few pages
                for i, page in enumerate(pdf.pages[:5]):  # Limit to first 5 pages
                    try:
                        text = page.extract_text()
                        if text:
                            full_text.append(f"=== Page {i+1} ===\n{text}")
                        
                        # Extract tables
                        tables = page.extract_tables()
                        for table in tables[:2]:  # Limit tables per page
                            if table and len(table) > 1:
                                result['tables'].append({
                                    'page': i + 1,
                                    'rows': len(table),
                                    'headers': table[0] if table else [],
                                    'preview': table[:5]  # First 5 rows
                                })
                    except Exception as e:
                        logger.warning(f"Failed to extract page {i+1}: {e}")
                
                # Store text preview
                combined_text = '\n\n'.join(full_text)
                result['text_preview'] = combined_text[:3000]  # First 3000 chars
                
                # Extract metrics from text
                result['metrics'] = self._extract_metrics_from_text(combined_text)
                
                # Extract alerts and recommendations
                result['alerts'] = self._extract_alerts_from_text(combined_text)
                result['recommendations'] = self._extract_recommendations_from_text(combined_text)
                
        except ImportError:
            result['error'] = 'pdfplumber not installed. Run: pip install pdfplumber'
            result['content'] = self._basic_file_info(filepath)
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def _extract_alerts_from_excel(self, sheets: List[Dict]) -> List[str]:
        """Extract alert information from Excel data"""
        alerts = []
        alert_keywords = ['告警', '警告', '风险', '异常', 'critical', 'warning', 'alert', 'high', 'error']
        
        for sheet in sheets:
            for row in sheet.get('preview', []):
                row_text = ' '.join(str(v) for v in row.values())
                if any(kw in row_text.lower() for kw in alert_keywords):
                    alerts.append({
                        'sheet': sheet['name'],
                        'content': row_text[:200]
                    })
        
        return alerts[:5]  # Limit to 5 alerts
    
    def _extract_recommendations_from_excel(self, sheets: List[Dict]) -> List[str]:
        """Extract recommendations from Excel data"""
        recommendations = []
        rec_keywords = ['建议', '推荐', '优化', '改进', 'recommend', 'suggest', 'optimize', 'improve']
        
        for sheet in sheets:
            for row in sheet.get('preview', []):
                row_text = ' '.join(str(v) for v in row.values())
                if any(kw in row_text.lower() for kw in rec_keywords):
                    recommendations.append({
                        'sheet': sheet['name'],
                        'content': row_text[:200]
                    })
        
        return recommendations[:5]
    
    def _extract_metrics_from_text(self, text: str) -> List[Dict]:
        """Extract metrics from text content"""
        metrics = []
        
        # Pattern for CPU, Memory, Disk usage
        patterns = [
            (r'(CPU|处理器)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%', 'CPU'),
            (r'(内存|Memory)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%', 'Memory'),
            (r'(磁盘|存储|Disk)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%', 'Disk'),
            (r'(带宽|网络|Bandwidth)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(Mbps|Gbps)', 'Bandwidth'),
        ]
        
        for pattern, metric_type in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                metrics.append({
                    'type': metric_type,
                    'value': match[1] if isinstance(match, tuple) else match,
                    'unit': '%' if metric_type != 'Bandwidth' else (match[2] if isinstance(match, tuple) else 'Mbps')
                })
        
        return metrics
    
    def _extract_alerts_from_text(self, text: str) -> List[str]:
        """Extract alerts from text"""
        alerts = []
        alert_keywords = ['告警', '警告', '风险', '异常', 'critical', 'warning', 'alert']
        
        sentences = re.split(r'[。！？\n]', text)
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in alert_keywords):
                clean = sentence.strip()
                if len(clean) > 10 and clean not in alerts:
                    alerts.append(clean[:200])
        
        return alerts[:5]
    
    def _extract_recommendations_from_text(self, text: str) -> List[str]:
        """Extract recommendations from text"""
        recommendations = []
        rec_keywords = ['建议', '推荐', '优化', '改进', 'recommend', 'suggest', 'optimize']
        
        sentences = re.split(r'[。！？\n]', text)
        for sentence in sentences:
            if any(kw in sentence.lower() for kw in rec_keywords):
                clean = sentence.strip()
                if len(clean) > 10 and clean not in recommendations:
                    recommendations.append(clean[:200])
        
        return recommendations[:5]
    
    def _basic_file_info(self, filepath: str) -> Dict:
        """Return basic file info when parsing fails"""
        return {
            'filename': os.path.basename(filepath),
            'size': os.path.getsize(filepath),
            'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat()
        }
    
    def generate_attachment_summary(self, parsed_attachments: List[Dict]) -> str:
        """Generate markdown summary of parsed attachments"""
        if not parsed_attachments:
            return ""
        
        md = "### 📎 附件内容分析\n\n"
        
        for att in parsed_attachments:
            filename = att.get('filename', 'Unknown')
            file_type = att.get('type', 'unknown')
            
            md += f"#### {filename}\n"
            md += f"- **类型**: {file_type.upper()}\n"
            
            if 'error' in att:
                md += f"- **状态**: ⚠️ 解析失败 - {att['error']}\n"
                continue
            
            # Excel specific
            if file_type == 'excel':
                summary = att.get('summary', {})
                md += f"- **工作表**: {summary.get('total_sheets', 0)} 个\n"
                md += f"- **总行数**: {summary.get('total_rows', 0)} 行\n"
                md += f"- **表名**: {', '.join(summary.get('sheet_names', []))}\n"
                
                if att.get('metrics'):
                    md += "- **关键指标**:\n"
                    for metric in att['metrics'][:3]:
                        md += f"  - {metric.get('column', 'Unknown')}: 平均 {metric.get('mean', 0)}, 最大 {metric.get('max', 0)}\n"
                
                if att.get('alerts'):
                    md += "- **⚠️ 告警**:\n"
                    for alert in att['alerts'][:2]:
                        md += f"  - {alert.get('content', '')[:80]}...\n"
            
            # PDF specific
            elif file_type == 'pdf':
                md += f"- **页数**: {att.get('pages', 0)} 页\n"
                
                if att.get('tables'):
                    md += f"- **表格数**: {len(att.get('tables', []))}\n"
                
                if att.get('metrics'):
                    md += "- **检测到的指标**:\n"
                    for metric in att['metrics'][:3]:
                        md += f"  - {metric.get('type', 'Unknown')}: {metric.get('value', 0)}{metric.get('unit', '')}\n"
                
                if att.get('recommendations'):
                    md += "- **💡 建议**:\n"
                    for rec in att['recommendations'][:2]:
                        md += f"  - {rec[:80]}...\n"
                
                # Add text preview snippet
                preview = att.get('text_preview', '')
                if preview:
                    md += f"\n**内容预览**:\n```\n{preview[:500]}...\n```\n"
            
            md += "\n"
        
        return md

# Convenience function for direct use
def parse_attachment(filepath: str) -> Dict:
    """Parse a single attachment file"""
    parser = AttachmentParser()
    return parser.parse_attachment(filepath)

if __name__ == '__main__':
    # Test with existing attachments
    import sys
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            result = parse_attachment(filepath)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"File not found: {filepath}")
    else:
        # Test with sample files
        attachments_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'attachments')
        if os.path.exists(attachments_dir):
            for filename in os.listdir(attachments_dir)[:2]:
                filepath = os.path.join(attachments_dir, filename)
                print(f"\n{'='*60}")
                print(f"Parsing: {filename}")
                print('='*60)
                result = parse_attachment(filepath)
                print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
