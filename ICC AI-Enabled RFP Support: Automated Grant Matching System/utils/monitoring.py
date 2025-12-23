"""
Production Monitoring and Reporting Tools
Comprehensive system monitoring and performance analytics
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

from config.settings import DATABASE_PATH, LOGS_DIR


class ProductionMonitor:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_daily_report(self, date: Optional[str] = None) -> Dict:
        """Generate comprehensive daily report"""
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with self.get_connection() as conn:
                # Email statistics
                email_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_emails,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                        SUM(CASE WHEN status = 'skipped_duplicate' THEN 1 ELSE 0 END) as skipped,
                        AVG(processing_time_seconds) as avg_processing_time,
                        SUM(perplexity_tokens_used) as total_tokens_used
                    FROM email_history 
                    WHERE DATE(sent_date) = ?
                """, (date,)).fetchone()
                
                # Faculty statistics
                faculty_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_faculty,
                        SUM(CASE WHEN active = TRUE THEN 1 ELSE 0 END) as active_faculty,
                        COUNT(DISTINCT CASE WHEN DATE(last_form_submission) = ? THEN email END) as new_submissions
                    FROM faculty_profiles
                """, (date,)).fetchone()
                
                # Schedule statistics
                schedule_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_schedules,
                        SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_schedules,
                        SUM(CASE WHEN next_due_date = ? THEN 1 ELSE 0 END) as due_today,
                        SUM(CASE WHEN next_due_date < ? THEN 1 ELSE 0 END) as overdue
                    FROM email_schedule
                """, (date, date)).fetchone()
                
                # System errors
                error_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_errors,
                        COUNT(DISTINCT component) as affected_components
                    FROM system_logs 
                    WHERE DATE(log_date) = ? AND log_level = 'ERROR'
                """, (date,)).fetchone()
                
                return {
                    'date': date,
                    'email_stats': dict(email_stats) if email_stats else {},
                    'faculty_stats': dict(faculty_stats) if faculty_stats else {},
                    'schedule_stats': dict(schedule_stats) if schedule_stats else {},
                    'error_stats': dict(error_stats) if error_stats else {},
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error generating daily report: {str(e)}")
            return {'error': str(e), 'date': date}
    
    def get_faculty_performance(self, days_back: int = 30) -> List[Dict]:
        """Get faculty email performance statistics"""
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        try:
            with self.get_connection() as conn:
                faculty_performance = conn.execute("""
                    SELECT 
                        f.email,
                        f.frequency,
                        f.research_area,
                        COUNT(h.id) as total_emails,
                        SUM(CASE WHEN h.status = 'success' THEN 1 ELSE 0 END) as successful_emails,
                        SUM(CASE WHEN h.status = 'failed' THEN 1 ELSE 0 END) as failed_emails,
                        AVG(h.processing_time_seconds) as avg_processing_time,
                        MAX(h.sent_date) as last_email_sent,
                        s.next_due_date
                    FROM faculty_profiles f
                    LEFT JOIN email_history h ON f.email = h.faculty_email AND h.sent_date > ?
                    LEFT JOIN email_schedule s ON f.email = s.faculty_email
                    WHERE f.active = TRUE
                    GROUP BY f.email
                    ORDER BY total_emails DESC, f.email
                """, (cutoff_date,)).fetchall()
                
                return [dict(row) for row in faculty_performance]
                
        except Exception as e:
            self.logger.error(f"Error getting faculty performance: {str(e)}")
            return []
    
    def get_system_health(self) -> Dict:
        """Get comprehensive system health metrics"""
        try:
            with self.get_connection() as conn:
                # Recent errors
                recent_errors = conn.execute("""
                    SELECT COUNT(*) as error_count
                    FROM system_logs 
                    WHERE log_level = 'ERROR' AND log_date > datetime('now', '-1 hour')
                """).fetchone()
                
                # Failed schedules
                failed_schedules = conn.execute("""
                    SELECT COUNT(*) as failed_count
                    FROM email_schedule 
                    WHERE status = 'failed' AND retry_count > 3
                """).fetchone()
                
                # Overdue emails
                overdue_emails = conn.execute("""
                    SELECT COUNT(*) as overdue_count
                    FROM email_schedule 
                    WHERE next_due_date < date('now', '-1 day') AND status = 'pending'
                """).fetchone()
                
                # Database size
                db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
                
                # Performance metrics
                avg_performance = conn.execute("""
                    SELECT 
                        AVG(processing_time_seconds) as avg_processing_time,
                        AVG(perplexity_tokens_used) as avg_tokens_per_email
                    FROM email_history 
                    WHERE sent_date > datetime('now', '-7 days') AND status = 'success'
                """).fetchone()
                
                # Health score calculation
                health_score = 100
                if recent_errors['error_count'] > 5:
                    health_score -= 20
                if failed_schedules['failed_count'] > 0:
                    health_score -= 15
                if overdue_emails['overdue_count'] > 0:
                    health_score -= 10
                
                return {
                    'health_score': max(health_score, 0),
                    'recent_errors': recent_errors['error_count'],
                    'failed_schedules': failed_schedules['failed_count'],
                    'overdue_emails': overdue_emails['overdue_count'],
                    'database_size_mb': round(db_size, 2),
                    'avg_processing_time': round(avg_performance['avg_processing_time'] or 0, 2),
                    'avg_tokens_per_email': round(avg_performance['avg_tokens_per_email'] or 0, 0),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting system health: {str(e)}")
            return {'error': str(e), 'health_score': 0}
    
    def get_usage_trends(self, days_back: int = 30) -> Dict:
        """Get usage trends and analytics"""
        try:
            with self.get_connection() as conn:
                # Daily email volume
                daily_volume = conn.execute("""
                    SELECT 
                        DATE(sent_date) as date,
                        COUNT(*) as email_count,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_count
                    FROM email_history 
                    WHERE sent_date > datetime('now', '-{} days')
                    GROUP BY DATE(sent_date)
                    ORDER BY date DESC
                """.format(days_back)).fetchall()
                
                # Frequency distribution
                frequency_dist = conn.execute("""
                    SELECT 
                        frequency,
                        COUNT(*) as faculty_count
                    FROM faculty_profiles 
                    WHERE active = TRUE
                    GROUP BY frequency
                """).fetchall()
                
                # Token usage trends
                token_usage = conn.execute("""
                    SELECT 
                        DATE(sent_date) as date,
                        SUM(perplexity_tokens_used) as total_tokens,
                        AVG(perplexity_tokens_used) as avg_tokens
                    FROM email_history 
                    WHERE sent_date > datetime('now', '-{} days') AND status = 'success'
                    GROUP BY DATE(sent_date)
                    ORDER BY date DESC
                """.format(days_back)).fetchall()
                
                return {
                    'daily_volume': [dict(row) for row in daily_volume],
                    'frequency_distribution': [dict(row) for row in frequency_dist],
                    'token_usage': [dict(row) for row in token_usage],
                    'analysis_period_days': days_back,
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting usage trends: {str(e)}")
            return {'error': str(e)}
    
    def export_analytics_report(self, output_file: Optional[str] = None) -> str:
        """Export comprehensive analytics report to CSV"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = LOGS_DIR / f"analytics_report_{timestamp}.csv"
        
        try:
            # Get comprehensive data
            faculty_performance = self.get_faculty_performance(30)
            
            if faculty_performance:
                df = pd.DataFrame(faculty_performance)
                df.to_csv(output_file, index=False)
                
                self.logger.info(f"Analytics report exported to: {output_file}")
                return str(output_file)
            else:
                self.logger.warning("No data available for analytics report")
                return None
                
        except Exception as e:
            self.logger.error(f"Error exporting analytics report: {str(e)}")
            return None
    
    def get_error_summary(self, hours_back: int = 24) -> List[Dict]:
        """Get recent error summary for troubleshooting"""
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        try:
            with self.get_connection() as conn:
                errors = conn.execute("""
                    SELECT 
                        log_date,
                        component,
                        message,
                        faculty_email,
                        details
                    FROM system_logs 
                    WHERE log_level = 'ERROR' AND log_date > ?
                    ORDER BY log_date DESC
                    LIMIT 50
                """, (cutoff_time,)).fetchall()
                
                return [dict(row) for row in errors]
                
        except Exception as e:
            self.logger.error(f"Error getting error summary: {str(e)}")
            return []
    
    def cleanup_monitoring_data(self, days_to_keep: int = 90):
        """Clean up old monitoring data"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            with self.get_connection() as conn:
                # Clean old system logs
                logs_deleted = conn.execute(
                    "DELETE FROM system_logs WHERE log_date < ?", 
                    (cutoff_date,)
                ).rowcount
                
                self.logger.info(f"Monitoring cleanup: {logs_deleted} old log entries removed")
                return {'logs_deleted': logs_deleted}
                
        except Exception as e:
            self.logger.error(f"Error during monitoring cleanup: {str(e)}")
            return {'error': str(e)}
