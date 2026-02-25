#!/usr/bin/env python3
"""
Trend Analyzer - For analyzing historical email data trends and patterns
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter
import numpy as np

class TrendAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, 'email_history.json')
        self.trends_file = os.path.join(data_dir, 'trends.json')
        
        os.makedirs(data_dir, exist_ok=True)
    
    def analyze_weekly_trends(self, current_data: Dict) -> Dict:
        """Analyze weekly trends"""
        history = self.load_history()
        
        if not history:
            return {
                'weekly_change': 0,
                'trending_keywords': [],
                'pattern_changes': [],
                'prediction': 'insufficient_data'
            }
        
        weekly_analysis = {
            'email_volume_trend': self.analyze_volume_trend(history, days=7),
            'keyword_trends': self.analyze_keyword_trends(history, days=7),
            'importance_trends': self.analyze_importance_trends(history, days=7),
            'category_trends': self.analyze_category_trends(history, days=7)
        }
        
        return weekly_analysis
    
    def analyze_volume_trend(self, history: List[Dict], days: int = 7) -> Dict:
        """Analyze email volume trend"""
        if len(history) < 2:
            return {'trend': 'stable', 'change_rate': 0}
        
        recent_volumes = [day.get('total_emails', 0) for day in history[-days:]]
        
        if len(recent_volumes) < 2:
            return {'trend': 'stable', 'change_rate': 0}
        
        change_rate = 0
        if len(recent_volumes) >= 2:
            latest = recent_volumes[-1]
            previous = recent_volumes[-2]
            if previous > 0:
                change_rate = ((latest - previous) / previous) * 100
        
        if abs(change_rate) < 5:
            trend = 'stable'
        elif change_rate > 20:
            trend = 'significantly_increasing'
        elif change_rate > 5:
            trend = 'increasing'
        elif change_rate < -20:
            trend = 'significantly_decreasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'change_rate': change_rate,
            'recent_volumes': recent_volumes
        }
    
    def analyze_keyword_trends(self, history: List[Dict], days: int = 7) -> List[Dict]:
        """Analyze keyword trends"""
        if len(history) < 2:
            return []
        
        recent_keywords = []
        previous_keywords = []
        
        for i, day_data in enumerate(history[-days:]):
            keywords = day_data.get('keywords', [])
            if i >= days - 3:
                recent_keywords.extend(keywords)
            else:
                previous_keywords.extend(keywords)
        
        recent_counter = Counter(recent_keywords)
        previous_counter = Counter(previous_keywords)
        
        trending_keywords = []
        for keyword, recent_count in recent_counter.items():
            previous_count = previous_counter.get(keyword, 0)
            if recent_count > previous_count * 1.5 and recent_count >= 2:
                trending_keywords.append({
                    'keyword': keyword,
                    'recent_count': recent_count,
                    'previous_count': previous_count,
                    'trend': 'emerging'
                })
        
        declining_keywords = []
        for keyword, previous_count in previous_counter.items():
            recent_count = recent_counter.get(keyword, 0)
            if recent_count < previous_count * 0.5 and previous_count >= 2:
                declining_keywords.append({
                    'keyword': keyword,
                    'recent_count': recent_count,
                    'previous_count': previous_count,
                    'trend': 'declining'
                })
        
        return trending_keywords + declining_keywords
    
    def analyze_importance_trends(self, history: List[Dict], days: int = 7) -> Dict:
        """Analyze importance trends"""
        if len(history) < 2:
            return {'trend': 'stable'}
        
        recent_importance = []
        for day_data in history[-days:]:
            importance_dist = day_data.get('by_importance', {})
            recent_importance.append(importance_dist)
        
        high_importance_ratios = []
        for imp_dist in recent_importance:
            total = sum(imp_dist.values())
            if total > 0:
                high_ratio = imp_dist.get('high', 0) / total * 100
                high_importance_ratios.append(high_ratio)
        
        if len(high_importance_ratios) < 2:
            return {'trend': 'stable'}
        
        latest_ratio = high_importance_ratios[-1]
        avg_ratio = np.mean(high_importance_ratios[:-1])
        
        if latest_ratio > avg_ratio * 1.2:
            trend = 'increasing_importance'
        elif latest_ratio < avg_ratio * 0.8:
            trend = 'decreasing_importance'
        else:
            trend = 'stable_importance'
        
        return {
            'trend': trend,
            'latest_ratio': latest_ratio,
            'average_ratio': avg_ratio,
            'ratios': high_importance_ratios
        }
    
    def analyze_category_trends(self, history: List[Dict], days: int = 7) -> Dict:
        """Analyze category trends"""
        if len(history) < 2:
            return {'trend': 'stable'}
        
        recent_categories = []
        for day_data in history[-days:]:
            cat_dist = day_data.get('by_category', {})
            recent_categories.append(cat_dist)
        
        category_trends = {}
        categories = ['decisions', 'updates', 'alerts', 'general']
        
        for category in categories:
            category_counts = [cat_dist.get(category, 0) for cat_dist in recent_categories]
            if len(category_counts) >= 2:
                latest = category_counts[-1]
                previous_avg = np.mean(category_counts[:-1]) if len(category_counts) > 1 else latest
                
                if latest > previous_avg * 1.5:
                    trend = 'significantly_increasing'
                elif latest > previous_avg * 1.1:
                    trend = 'increasing'
                elif latest < previous_avg * 0.5:
                    trend = 'significantly_decreasing'
                elif latest < previous_avg * 0.9:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
                
                category_trends[category] = {
                    'trend': trend,
                    'latest_count': latest,
                    'previous_average': previous_avg,
                    'counts': category_counts
                }
        
        return category_trends
    
    def generate_trend_insights(self, analysis: Dict) -> List[str]:
        """Generate trend insights"""
        insights = []
        
        volume_trend = analysis.get('email_volume_trend', {})
        if volume_trend.get('change_rate', 0) > 20:
            insights.append(f"📈 Email volume significantly increased (+{volume_trend['change_rate']:.1f}%), consider optimizing email management")
        elif volume_trend.get('change_rate', 0) < -20:
            insights.append(f"📉 Email volume significantly decreased ({volume_trend['change_rate']:.1f}%), may reflect business activity changes")
        
        importance_trend = analysis.get('importance_trends', {})
        if importance_trend.get('trend') == 'increasing_importance':
            insights.append("⚠️ High-importance email ratio increased, prioritize important items")
        elif importance_trend.get('trend') == 'decreasing_importance':
            insights.append("✅ High-importance email ratio decreased, overall email pressure reduced")
        
        keyword_trends = analysis.get('keyword_trends', [])
        emerging_keywords = [kw for kw in keyword_trends if kw.get('trend') == 'emerging']
        if emerging_keywords:
            top_keywords = [kw['keyword'] for kw in emerging_keywords[:3]]
            insights.append(f"🔍 Emerging keywords: {', '.join(top_keywords)} - reflecting current focus areas")
        
        return insights
    
    def load_history(self) -> List[Dict]:
        """Load historical data"""
        if not os.path.exists(self.history_file):
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load history: {e}")
            return []
    
    def generate_weekly_report(self, current_data: Dict) -> str:
        """Generate weekly trend report"""
        weekly_analysis = self.analyze_weekly_trends(current_data)
        
        report = f"""# Weekly Trend Analysis Report - {datetime.now().strftime('%Y-%m-%d')}

## Weekly Email Trend Overview

### Email Volume Trend
- Trend status: {weekly_analysis.get('email_volume_trend', {}).get('trend', 'unknown')}
- Change rate: {weekly_analysis.get('email_volume_trend', {}).get('change_rate', 0):.1f}%
- Recent volumes: {weekly_analysis.get('email_volume_trend', {}).get('recent_volumes', [])[-3:]}

### Keyword Trends
"""
        
        keyword_trends = weekly_analysis.get('keyword_trends', [])
        if keyword_trends:
            for trend in keyword_trends[:5]:
                report += f"- **{trend['keyword']}**: {trend['trend']} (recent: {trend['recent_count']}, previous: {trend['previous_count']})\n"
        else:
            report += "- Keyword trends relatively stable this week\n"
        
        report += f"""
### Importance Trend
- High-importance email trend: {weekly_analysis.get('importance_trends', {}).get('trend', 'unknown')}
- Current ratio: {weekly_analysis.get('importance_trends', {}).get('latest_ratio', 0):.1f}%
- Average ratio: {weekly_analysis.get('importance_trends', {}).get('average_ratio', 0):.1f}%

### Category Trends
"""
        
        category_trends = weekly_analysis.get('category_trends', {})
        for category, trend_data in category_trends.items():
            report += f"- **{category}**: {trend_data['trend']} (current: {trend_data['latest_count']}, avg: {trend_data['previous_average']:.1f})\n"
        
        insights = self.generate_trend_insights(weekly_analysis)
        if insights:
            report += """
## Trend Insights
"""
            for insight in insights:
                report += f"- {insight}\n"
        
        report += "\n---\n*Report generated by Email Daily Report System*"
        
        return report

if __name__ == '__main__':
    analyzer = TrendAnalyzer('/tmp/email_data')
    
    current_data = {
        'total_emails': 15,
        'by_importance': {'high': 3, 'medium': 8, 'low': 4},
        'by_category': {'decisions': 4, 'updates': 6, 'alerts': 2, 'general': 3},
        'keywords': ['budget', 'strategy', 'AI', 'meeting', 'review'],
        'date': datetime.now().isoformat()
    }
    
    report = analyzer.generate_weekly_report(current_data)
    print(report)
