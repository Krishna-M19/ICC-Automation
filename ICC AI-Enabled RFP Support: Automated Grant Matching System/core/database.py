"""
Production Database Management for RFP System
"""
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

from config.settings import DATABASE_PATH, FREQUENCY_MAPPING


class ProductionDatabase:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self.init_database()
    
    def init_database(self):
        """Initialize production database with optimized schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Faculty profiles with comprehensive data
                CREATE TABLE IF NOT EXISTS faculty_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    research_area TEXT,
                    keywords TEXT,
                    eligibility_constraints TEXT,
                    early_career TEXT,
                    funding_types TEXT,
                    rfp_size TEXT,
                    submission_timeline TEXT,
                    preferred_funding_sources TEXT,
                    frequency TEXT CHECK(frequency IN ('weekly', 'biweekly', 'monthly', 'one response', 'when high-confidence matches are found')),
                    additional_info TEXT,
                    documents_info TEXT,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_form_submission TIMESTAMP
                );

                -- Email scheduling with tracking
                CREATE TABLE IF NOT EXISTS email_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_email TEXT NOT NULL,
                    last_sent_date DATE,
                    next_due_date DATE,
                    frequency TEXT CHECK(frequency IN ('weekly', 'biweekly', 'monthly', 'one response', 'when high-confidence matches are found')),
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'sent', 'failed', 'paused')),
                    retry_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (faculty_email) REFERENCES faculty_profiles(email) ON DELETE CASCADE
                );

                -- Comprehensive email history
                CREATE TABLE IF NOT EXISTS email_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    faculty_email TEXT NOT NULL,
                    sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    content_hash TEXT,
                    file_path_md TEXT,
                    file_path_html TEXT,
                    faculty_folder TEXT,
                    status TEXT CHECK(status IN ('success', 'failed', 'skipped_duplicate', 'retry')),
                    error_message TEXT,
                    processing_time_seconds REAL,
                    perplexity_tokens_used INTEGER,
                    FOREIGN KEY (faculty_email) REFERENCES faculty_profiles(email) ON DELETE CASCADE
                );

                -- System performance logs
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    log_level TEXT CHECK(log_level IN ('INFO', 'WARNING', 'ERROR', 'CRITICAL')),
                    component TEXT,
                    message TEXT,
                    faculty_email TEXT,
                    execution_time_seconds REAL,
                    details TEXT
                );

                -- Performance indexes
                CREATE INDEX IF NOT EXISTS idx_faculty_email ON faculty_profiles(email);
                CREATE INDEX IF NOT EXISTS idx_faculty_active ON faculty_profiles(active);
                CREATE INDEX IF NOT EXISTS idx_schedule_due_date ON email_schedule(next_due_date);
                CREATE INDEX IF NOT EXISTS idx_schedule_status ON email_schedule(status);
                CREATE INDEX IF NOT EXISTS idx_history_faculty_date ON email_history(faculty_email, sent_date);
                CREATE INDEX IF NOT EXISTS idx_history_status ON email_history(status);
                CREATE INDEX IF NOT EXISTS idx_logs_date_level ON system_logs(log_date, log_level);
            """)
        
        self.logger.info("Production database initialized successfully")
    
    def get_connection(self):
        """Get optimized database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        # PRAGMA is a special SQL command used to modify the operation of the SQLite library or to query internal database settings.
        conn.execute("PRAGMA journal_mode=WAL")  # writeAheadLogging - Better concurrency
        conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
        return conn    

    # upsert --> update if exists, insert if not
    def upsert_faculty_profile(self, faculty_data: Dict) -> bool:
        """Insert or update faculty profile with conflict resolution"""
        try:
            # Convert timestamp to datetime if it's a pandas Timestamp
            timestamp = faculty_data.get('timestamp', datetime.now())
            if hasattr(timestamp, 'to_pydatetime'):
                timestamp = timestamp.to_pydatetime()
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now()
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO faculty_profiles 
                    (email, research_area, keywords, eligibility_constraints, 
                     early_career, funding_types, rfp_size, submission_timeline,
                     preferred_funding_sources, frequency, additional_info, 
                     documents_info, updated_at, last_form_submission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    faculty_data['email'],
                    faculty_data['research_area'],
                    faculty_data['keywords'],
                    faculty_data['eligibility_constraints'],
                    faculty_data['early_career'],
                    faculty_data['funding_types'],
                    faculty_data['rfp_size'],
                    faculty_data['submission_timeline'],
                    faculty_data['preferred_funding_sources'],
                    faculty_data['frequency'],
                    faculty_data['additional_info'],
                    faculty_data.get('documents_info', ''),
                    datetime.now(),
                    timestamp
                ))
                return True
        except Exception as e:
            self.logger.error(f"Error upserting faculty profile {faculty_data.get('email', 'unknown')}: {str(e)}")
            return False
    
    def init_faculty_schedule(self, email: str, frequency: str) -> bool:
        """Initialize email schedule for new faculty"""
        try:
            with self.get_connection() as conn:
                existing = conn.execute(
                    "SELECT id FROM email_schedule WHERE faculty_email = ?", 
                    (email,)
                ).fetchone()
                
                if not existing:
                    next_due = datetime.now().date() + timedelta(days=1)
                    conn.execute("""
                        INSERT INTO email_schedule 
                        (faculty_email, next_due_date, frequency, status)
                        VALUES (?, ?, ?, 'pending')
                    """, (email, next_due, frequency))
                    self.logger.info(f"Initialized schedule for {email}: {frequency}, due {next_due}")
                return True
        except Exception as e:
            self.logger.error(f"Error initializing schedule for {email}: {str(e)}")
            return False
    
    def get_due_faculty(self, limit: Optional[int] = None) -> List[Dict]:
        """Get faculty members due for emails with optional limit"""
        today = datetime.now().date()
        
        query = """
            SELECT f.*, s.next_due_date, s.last_sent_date, s.retry_count
            FROM faculty_profiles f
            JOIN email_schedule s ON f.email = s.faculty_email
            WHERE s.next_due_date <= ? AND f.active = TRUE AND s.status IN ('pending', 'failed')
            ORDER BY s.next_due_date ASC, s.retry_count ASC
        """
        
        params = [today]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_schedule_status(self, email: str, status: str) -> bool:
        """Update schedule status for processing tracking"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE email_schedule 
                    SET status = ?, updated_at = ?
                    WHERE faculty_email = ?
                """, (status, datetime.now(), email))
                return True
        except Exception as e:
            self.logger.error(f"Error updating schedule status for {email}: {str(e)}")
            return False
    
    def update_next_due_date(self, email: str, frequency: str, success: bool = True) -> bool:
        """Update next due date with retry logic"""
        try:
            today = datetime.now().date()
            
            if success:
                days_to_add = FREQUENCY_MAPPING.get(frequency.lower(), 14)
                next_due = today + timedelta(days=days_to_add)
                status = 'pending'
                retry_count = 0
            else:
                # For failures, retry in 1 day
                next_due = today + timedelta(days=1)
                status = 'failed'
                
            with self.get_connection() as conn:
                if success:
                    conn.execute("""
                        UPDATE email_schedule 
                        SET last_sent_date = ?, next_due_date = ?, status = ?, 
                            retry_count = ?, updated_at = ?
                        WHERE faculty_email = ?
                    """, (today, next_due, status, retry_count, datetime.now(), email))
                else:
                    conn.execute("""
                        UPDATE email_schedule 
                        SET next_due_date = ?, status = ?, 
                            retry_count = retry_count + 1, updated_at = ?
                        WHERE faculty_email = ?
                    """, (next_due, status, datetime.now(), email))
                
                return True
        except Exception as e:
            self.logger.error(f"Error updating next due date for {email}: {str(e)}")
            return False
    
    def is_duplicate_content(self, email: str, content: str, days_back: int = 7) -> bool:
        """Check for duplicate content with configurable timeframe"""
        # prevents user from receiving the same email twice within 7 days.
        content_hash = hashlib.md5(content.encode()).hexdigest()  # md5 - messagedigest algorithm
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with self.get_connection() as conn:
            recent_hash = conn.execute("""
                SELECT content_hash FROM email_history 
                WHERE faculty_email = ? AND sent_date > ? AND status = 'success'
                ORDER BY sent_date DESC LIMIT 1
            """, (email, cutoff_date)).fetchone()
            
            return recent_hash and recent_hash['content_hash'] == content_hash
    
    def log_email_history(self, email: str, status: str, content: str = None, 
                          file_paths: Tuple[str, str, str] = None, error_msg: str = None,
                          processing_time: float = 0,
                          tokens_used: int = 0) -> bool:
        """Log comprehensive email history
            This ensures that system can track:
            When and how it was sent
            Whether it succeeded or failed
            What the content was
            What errors occurred (if any)
            How many RFPs were included
            And how many tokens were used (for language model processing)"""

        try:
            content_hash = hashlib.md5(content.encode()).hexdigest() if content else None
            md_path, html_path, folder_path = file_paths if file_paths else (None, None, None)
            
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO email_history 
                    (faculty_email, status, content_hash, file_path_md, file_path_html,
                     faculty_folder, error_message, processing_time_seconds,
                     perplexity_tokens_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (email, status, content_hash, md_path, html_path, folder_path,
                      error_msg, processing_time, tokens_used))
                return True
        except Exception as e:
            self.logger.error(f"Error logging email history for {email}: {str(e)}")
            return False
    
    def log_system_event(self, level: str, component: str, message: str, 
                        faculty_email: str = None, execution_time: float = None,
                        details: str = None) -> bool:
        """Log system events with performance tracking"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO system_logs 
                    (log_level, component, message, faculty_email, execution_time_seconds, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (level, component, message, faculty_email, execution_time, details))
                return True
        except Exception as e:
            print(f"Error logging system event: {str(e)}")
            return False
    
    def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        with self.get_connection() as conn:
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_faculty,
                    SUM(CASE WHEN active = TRUE THEN 1 ELSE 0 END) as active_faculty,
                    (SELECT COUNT(*) FROM email_history WHERE DATE(sent_date) = DATE('now')) as emails_today,
                    (SELECT COUNT(*) FROM email_history WHERE status = 'success' AND DATE(sent_date) = DATE('now')) as successful_today,
                    (SELECT COUNT(*) FROM email_schedule WHERE status = 'failed') as failed_schedules,
                    (SELECT AVG(processing_time_seconds) FROM email_history WHERE status = 'success' AND DATE(sent_date) = DATE('now')) as avg_processing_time
                FROM faculty_profiles
            """).fetchone()
            
            return dict(stats) if stats else {}
    
    def get_faculty_by_email(self, email: str) -> Optional[Dict]:
        """Get specific faculty member with schedule info"""
        with self.get_connection() as conn:
            faculty = conn.execute("""
                SELECT f.*, s.next_due_date, s.last_sent_date, s.status as schedule_status
                FROM faculty_profiles f
                LEFT JOIN email_schedule s ON f.email = s.faculty_email
                WHERE f.email = ?
            """, (email,)).fetchone()
            
            return dict(faculty) if faculty else None
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old logs and maintain database performance"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        with self.get_connection() as conn:
            # Clean old system logs
            logs_deleted = conn.execute(
                "DELETE FROM system_logs WHERE log_date < ?", 
                (cutoff_date,)
            ).rowcount
            
            # Clean old email history (keep successful ones longer)
            history_cutoff = datetime.now() - timedelta(days=days_to_keep * 2)
            history_deleted = conn.execute(
                "DELETE FROM email_history WHERE sent_date < ? AND status != 'success'", 
                (history_cutoff,)
            ).rowcount
            
            # Vacuum database for performance
            conn.execute("VACUUM")
            
            self.logger.info(f"Cleanup completed: {logs_deleted} logs, {history_deleted} history records deleted")
            
            return {'logs_deleted': logs_deleted, 'history_deleted': history_deleted}
