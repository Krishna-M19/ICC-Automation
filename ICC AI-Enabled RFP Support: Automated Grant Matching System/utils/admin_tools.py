"""
Production Administrative Tools
faculty and system management utilities
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

from config.settings import DATABASE_PATH


class ProductionAdminTools:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def list_all_faculty(self, active_only: bool = True) -> List[Dict]:
        """List all faculty with comprehensive information"""
        try:
            with self.get_connection() as conn:
                query = """
                    SELECT 
                        f.*,
                        s.next_due_date,
                        s.last_sent_date,
                        s.status as schedule_status,
                        s.retry_count,
                        (SELECT COUNT(*) FROM email_history h WHERE h.faculty_email = f.email) as total_emails_sent,
                        (SELECT COUNT(*) FROM email_history h WHERE h.faculty_email = f.email AND h.status = 'success') as successful_emails
                    FROM faculty_profiles f
                    LEFT JOIN email_schedule s ON f.email = s.faculty_email
                """
                
                if active_only:
                    query += " WHERE f.active = TRUE"
                
                query += " ORDER BY f.email"
                
                faculty = conn.execute(query).fetchall()
                return [dict(row) for row in faculty]
                
        except Exception as e:
            self.logger.error(f"Error listing faculty: {str(e)}")
            return []
    
    def get_faculty_details(self, email: str) -> Optional[Dict]:
        """Get detailed information about specific faculty member"""
        try:
            with self.get_connection() as conn:
                # Faculty profile and schedule
                faculty = conn.execute("""
                    SELECT 
                        f.*,
                        s.next_due_date,
                        s.last_sent_date,
                        s.status as schedule_status,
                        s.retry_count
                    FROM faculty_profiles f
                    LEFT JOIN email_schedule s ON f.email = s.faculty_email
                    WHERE f.email = ?
                """, (email,)).fetchone()
                
                if not faculty:
                    return None
                
                faculty_dict = dict(faculty)
                
                # Email history
                email_history = conn.execute("""
                    SELECT 
                        sent_date,
                        status,
                        processing_time_seconds,
                        error_message
                    FROM email_history 
                    WHERE faculty_email = ?
                    ORDER BY sent_date DESC
                    LIMIT 10
                """, (email,)).fetchall()
                
                faculty_dict['recent_email_history'] = [dict(row) for row in email_history]
                
                return faculty_dict
                
        except Exception as e:
            self.logger.error(f"Error getting faculty details for {email}: {str(e)}")
            return None
    
    def update_faculty_status(self, email: str, active: bool) -> bool:
        """Activate or deactivate faculty member"""
        try:
            with self.get_connection() as conn:
                result = conn.execute("""
                    UPDATE faculty_profiles 
                    SET active = ?, updated_at = ?
                    WHERE email = ?
                """, (active, datetime.now(), email))
                
                if result.rowcount > 0:
                    status = "activated" if active else "deactivated"
                    self.logger.info(f"Faculty {email} {status}")
                    return True
                else:
                    self.logger.warning(f"Faculty {email} not found")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error updating faculty status for {email}: {str(e)}")
            return False
    
    def update_faculty_schedule(self, email: str, next_due_date: str, frequency: Optional[str] = None) -> bool:
        """Update faculty email schedule"""
        try:
            due_date = datetime.strptime(next_due_date, '%Y-%m-%d').date()
            
            with self.get_connection() as conn:
                if frequency:
                    # Update both schedule and frequency
                    conn.execute("""
                        UPDATE email_schedule 
                        SET next_due_date = ?, frequency = ?, updated_at = ?
                        WHERE faculty_email = ?
                    """, (due_date, frequency, datetime.now(), email))
                    
                    conn.execute("""
                        UPDATE faculty_profiles 
                        SET frequency = ?, updated_at = ?
                        WHERE email = ?
                    """, (frequency, datetime.now(), email))
                else:
                    # Update only schedule
                    conn.execute("""
                        UPDATE email_schedule 
                        SET next_due_date = ?, updated_at = ?
                        WHERE faculty_email = ?
                    """, (due_date, datetime.now(), email))
                
                self.logger.info(f"Updated schedule for {email}: next due {next_due_date}")
                return True
                
        except ValueError:
            self.logger.error(f"Invalid date format for {email}: {next_due_date}")
            return False
        except Exception as e:
            self.logger.error(f"Error updating schedule for {email}: {str(e)}")
            return False
    
    def reset_faculty_schedule(self, email: str) -> bool:
        """Reset faculty schedule to start fresh"""
        try:
            tomorrow = datetime.now().date() + timedelta(days=1)
            
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE email_schedule 
                    SET next_due_date = ?, last_sent_date = NULL, 
                        status = 'pending', retry_count = 0, updated_at = ?
                    WHERE faculty_email = ?
                """, (tomorrow, datetime.now(), email))
                
                self.logger.info(f"Reset schedule for {email}: next due {tomorrow}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error resetting schedule for {email}: {str(e)}")
            return False
    
    def bulk_update_schedules(self, updates: List[Dict]) -> Dict[str, int]:
        """Bulk update multiple faculty schedules"""
        stats = {'updated': 0, 'failed': 0}
        
        try:
            with self.get_connection() as conn:
                for update in updates:
                    try:
                        email = update['email']
                        next_due = datetime.strptime(update['next_due_date'], '%Y-%m-%d').date()
                        frequency = update.get('frequency')
                        
                        if frequency:
                            conn.execute("""
                                UPDATE email_schedule 
                                SET next_due_date = ?, frequency = ?, updated_at = ?
                                WHERE faculty_email = ?
                            """, (next_due, frequency, datetime.now(), email))
                            
                            conn.execute("""
                                UPDATE faculty_profiles 
                                SET frequency = ?, updated_at = ?
                                WHERE email = ?
                            """, (frequency, datetime.now(), email))
                        else:
                            conn.execute("""
                                UPDATE email_schedule 
                                SET next_due_date = ?, updated_at = ?
                                WHERE faculty_email = ?
                            """, (next_due, datetime.now(), email))
                        
                        stats['updated'] += 1
                        
                    except Exception as e:
                        stats['failed'] += 1
                        self.logger.error(f"Error in bulk update for {update.get('email', 'unknown')}: {str(e)}")
                
                self.logger.info(f"Bulk schedule update completed: {stats}")
                return stats
                
        except Exception as e:
            self.logger.error(f"Error in bulk schedule update: {str(e)}")
            return {'updated': 0, 'failed': len(updates), 'error': str(e)}
    
    def get_overdue_faculty(self) -> List[Dict]:
        """Get faculty with overdue emails"""
        yesterday = datetime.now().date() - timedelta(days=1)
        
        try:
            with self.get_connection() as conn:
                overdue = conn.execute("""
                    SELECT 
                        f.email,
                        f.frequency,
                        s.next_due_date,
                        s.last_sent_date,
                        s.retry_count,
                        julianday('now') - julianday(s.next_due_date) as days_overdue
                    FROM faculty_profiles f
                    JOIN email_schedule s ON f.email = s.faculty_email
                    WHERE f.active = TRUE AND s.next_due_date < ?
                    ORDER BY s.next_due_date ASC
                """, (yesterday,)).fetchall()
                
                return [dict(row) for row in overdue]
                
        except Exception as e:
            self.logger.error(f"Error getting overdue faculty: {str(e)}")
            return []
    
    def get_failed_schedules(self) -> List[Dict]:
        """Get schedules with repeated failures"""
        try:
            with self.get_connection() as conn:
                failed = conn.execute("""
                    SELECT 
                        f.email,
                        f.research_area,
                        s.retry_count,
                        s.next_due_date,
                        s.updated_at,
                        h.error_message
                    FROM faculty_profiles f
                    JOIN email_schedule s ON f.email = s.faculty_email
                    LEFT JOIN email_history h ON f.email = h.faculty_email
                    WHERE s.status = 'failed' AND s.retry_count > 2
                    ORDER BY s.retry_count DESC, s.updated_at ASC
                """).fetchall()
                
                return [dict(row) for row in failed]
                
        except Exception as e:
            self.logger.error(f"Error getting failed schedules: {str(e)}")
            return []
    
    def search_faculty(self, search_term: str) -> List[Dict]:
        """Search faculty by email, research area, or keywords"""
        try:
            with self.get_connection() as conn:
                faculty = conn.execute("""
                    SELECT 
                        f.*,
                        s.next_due_date,
                        s.status as schedule_status
                    FROM faculty_profiles f
                    LEFT JOIN email_schedule s ON f.email = s.faculty_email
                    WHERE f.email LIKE ? OR f.research_area LIKE ? OR f.keywords LIKE ?
                    ORDER BY f.email
                """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%')).fetchall()
                
                return [dict(row) for row in faculty]
                
        except Exception as e:
            self.logger.error(f"Error searching faculty: {str(e)}")
            return []
    
    def export_faculty_data(self, output_file: Optional[str] = None) -> Optional[str]:
        """Export all faculty data to CSV"""
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"faculty_export_{timestamp}.csv"
        
        try:
            import pandas as pd
            
            faculty_data = self.list_all_faculty(active_only=False)
            
            if faculty_data:
                df = pd.DataFrame(faculty_data)
                df.to_csv(output_file, index=False)
                
                self.logger.info(f"Faculty data exported to: {output_file}")
                return output_file
            else:
                self.logger.warning("No faculty data to export")
                return None
                
        except Exception as e:
            self.logger.error(f"Error exporting faculty data: {str(e)}")
            return None
    
    def get_system_summary(self) -> Dict:
        """Get comprehensive system summary for administrators"""
        try:
            with self.get_connection() as conn:
                # Faculty summary
                faculty_summary = conn.execute("""
                    SELECT 
                        COUNT(*) as total_faculty,
                        SUM(CASE WHEN active = TRUE THEN 1 ELSE 0 END) as active_faculty,
                        COUNT(DISTINCT frequency) as frequency_types
                    FROM faculty_profiles
                """).fetchone()
                
                # Schedule summary
                schedule_summary = conn.execute("""
                    SELECT 
                        SUM(CASE WHEN next_due_date = date('now') THEN 1 ELSE 0 END) as due_today,
                        SUM(CASE WHEN next_due_date < date('now') THEN 1 ELSE 0 END) as overdue,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_schedules
                    FROM email_schedule
                """).fetchone()
                
                # Recent activity
                recent_activity = conn.execute("""
                    SELECT 
                        COUNT(*) as emails_last_7_days,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_last_7_days
                    FROM email_history 
                    WHERE sent_date > datetime('now', '-7 days')
                """).fetchone()
                
                return {
                    'faculty_summary': dict(faculty_summary) if faculty_summary else {},
                    'schedule_summary': dict(schedule_summary) if schedule_summary else {},
                    'recent_activity': dict(recent_activity) if recent_activity else {},
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting system summary: {str(e)}")
            return {'error': str(e)}
