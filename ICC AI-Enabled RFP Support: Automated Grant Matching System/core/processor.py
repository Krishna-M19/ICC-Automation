"""
Production RFP Processor - Main orchestration engine
Optimized with batch processing and monitoring
"""
import time
from datetime import datetime
from typing import Dict, List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .database import ProductionDatabase
from .sheets_sync import ProductionSheetsSync
from .ai_generator import ProductionAIGenerator
from .email_service import ProductionEmailService
from config.settings import BATCH_SIZE, PARALLEL_PROCESSING, MAX_RETRIES


class ProductionRFPProcessor:
    def __init__(self):
        self.db = ProductionDatabase()
        self.ai_generator = ProductionAIGenerator()
        self.email_service = ProductionEmailService()
        self.logger = logging.getLogger(__name__)
    
    def sync_faculty_data(self) -> Dict[str, int]:
        """Sync faculty data from Google Sheets with comprehensive error handling"""
        start_time = time.time()
        
        try:
            self.logger.info("Starting faculty data synchronization from Google Sheets")
            
            # Initialize Google Sheets sync
            if not self.email_service.service:
                self.logger.error("Gmail service not available for Sheets authentication")
                return {'error': 'Authentication failed', 'processed': 0, 'new': 0, 'updated': 0}
            
            credentials = self.email_service.service._http.credentials
            sheets_sync = ProductionSheetsSync(credentials)
            
            # Test connection
            if not sheets_sync.test_connection():
                self.logger.error("Google Sheets connection test failed")
                return {'error': 'Sheets connection failed', 'processed': 0, 'new': 0, 'updated': 0}
            
            # Fetch faculty data
            df = sheets_sync.fetch_faculty_data()
            if df is None:
                self.logger.error("Failed to fetch faculty data from Google Sheets")
                return {'error': 'Data fetch failed', 'processed': 0, 'new': 0, 'updated': 0}
            
            # Process faculty data
            stats = {'processed': 0, 'new': 0, 'updated': 0, 'errors': 0}
            
            for index, row in df.iterrows():
                try:
                    faculty_data = dict(row)
                    
                    if not faculty_data.get('email'):
                        self.logger.warning(f"Skipping row {index}: missing email")
                        continue
                    
                    # Check if faculty exists
                    existing_faculty = self.db.get_faculty_by_email(faculty_data['email'])
                    is_new = existing_faculty is None
                    
                    # Upsert faculty profile
                    if self.db.upsert_faculty_profile(faculty_data):
                        if is_new:
                            # Initialize schedule for new faculty
                            self.db.init_faculty_schedule(
                                faculty_data['email'], 
                                faculty_data['frequency']
                            )
                            stats['new'] += 1
                            self.logger.info(f"New faculty added: {faculty_data['email']}")
                        else:
                            stats['updated'] += 1
                            self.logger.info(f"Faculty updated: {faculty_data['email']}")
                        
                        stats['processed'] += 1
                    else:
                        stats['errors'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(f"Error processing faculty row {index}: {str(e)}")
            
            processing_time = time.time() - start_time
            
            self.db.log_system_event(
                'INFO', 'DataSync', 
                f"Faculty sync completed: {stats}",
                execution_time=processing_time
            )
            
            self.logger.info(f"Faculty data sync completed in {processing_time:.2f}s: {stats}")
            return stats
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Critical error in faculty data sync: {str(e)}"
            self.logger.error(error_msg)
            
            self.db.log_system_event(
                'ERROR', 'DataSync', error_msg,
                execution_time=processing_time
            )
            
            return {'error': error_msg, 'processed': 0, 'new': 0, 'updated': 0}
    
    def process_due_faculty(self, limit: Optional[int] = None) -> Dict[str, int]:
        """Process faculty due for emails with batch processing and monitoring"""
        start_time = time.time()
        
        try:
            # Get faculty due for processing
            due_faculty = self.db.get_due_faculty(limit)
            
            if not due_faculty:
                self.logger.info("No faculty due for emails today")
                return {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
            
            self.logger.info(f"Processing {len(due_faculty)} faculty members due for emails")
            
            stats = {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
            
            if PARALLEL_PROCESSING and len(due_faculty) > 1:
                # Process in parallel for better performance
                stats = self._process_faculty_parallel(due_faculty)
            else:
                # Process sequentially
                stats = self._process_faculty_sequential(due_faculty)
            
            processing_time = time.time() - start_time
            
            self.db.log_system_event(
                'INFO', 'FacultyProcessing',
                f"Faculty processing completed: {stats}",
                execution_time=processing_time
            )
            
            self.logger.info(f"Faculty processing completed in {processing_time:.2f}s: {stats}")
            return stats
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Critical error in faculty processing: {str(e)}"
            self.logger.error(error_msg)
            
            self.db.log_system_event(
                'ERROR', 'FacultyProcessing', error_msg,
                execution_time=processing_time
            )
            
            return {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0, 'error': error_msg}
    
    def _process_faculty_sequential(self, faculty_list: List[Dict]) -> Dict[str, int]:
        """Process faculty sequentially"""
        stats = {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
        
        for faculty in faculty_list:
            try:
                result = self.process_single_faculty(faculty)
                stats['processed'] += 1
                
                if result['status'] == 'sent':
                    stats['sent'] += 1
                elif result['status'] == 'failed':
                    stats['failed'] += 1
                elif result['status'] == 'skipped':
                    stats['skipped'] += 1
                    
            except Exception as e:
                stats['failed'] += 1
                self.logger.error(f"Error processing faculty {faculty.get('email', 'unknown')}: {str(e)}")
        
        return stats
    
    def _process_faculty_parallel(self, faculty_list: List[Dict]) -> Dict[str, int]:
        """Process faculty in parallel with controlled concurrency and rate limiting"""
        stats = {'processed': 0, 'sent': 0, 'failed': 0, 'skipped': 0}
        
        # Process in smaller batches to avoid overwhelming APIs
        batch_size = min(BATCH_SIZE, len(faculty_list))
        
        self.logger.info(f"Processing {len(faculty_list)} faculty in batches of {batch_size}")
        
        # Process in batches with delays between batches
        for i in range(0, len(faculty_list), batch_size):
            batch = faculty_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(faculty_list) + batch_size - 1) // batch_size
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} faculty)")
            
            with ThreadPoolExecutor(max_workers=batch_size) as executor:
                # Submit batch for processing with staggered starts
                future_to_faculty = {}
                for idx, faculty in enumerate(batch):
                    # Add small delay between submissions to stagger API calls
                    if idx > 0:
                        time.sleep(2)  # 2 second stagger between starts
                    future = executor.submit(self.process_single_faculty, faculty)
                    future_to_faculty[future] = faculty
                    self.logger.info(f"Submitted {faculty['email']} for processing")
                
                # Collect results
                for future in as_completed(future_to_faculty):
                    faculty = future_to_faculty[future]
                    try:
                        result = future.result()
                        stats['processed'] += 1
                        
                        if result['status'] == 'sent':
                            stats['sent'] += 1
                        elif result['status'] == 'failed':
                            stats['failed'] += 1
                        elif result['status'] == 'skipped':
                            stats['skipped'] += 1
                            
                    except Exception as e:
                        stats['failed'] += 1
                        self.logger.error(f"Error processing faculty {faculty.get('email', 'unknown')}: {str(e)}")
            
            # Add delay between batches to avoid API rate limits
            if i + batch_size < len(faculty_list):
                delay = 10  # 10 second delay between batches
                self.logger.info(f"Waiting {delay}s before next batch...")
                time.sleep(delay)
        
        return stats
    
    def process_single_faculty(self, faculty_data: Dict) -> Dict:
        """Process individual faculty member with comprehensive monitoring"""
        email = faculty_data['email']
        start_time = time.time()
        
        try:
            self.logger.info(f"Processing faculty: {email}")
            
            # Update status to processing
            self.db.update_schedule_status(email, 'processing')
            
            # Generate RFP content
            content, tokens_used, ai_processing_time = self.ai_generator.generate_rfp_content(faculty_data)
            
            if not content:
                self.db.log_email_history(
                    email, 'failed', error_msg="Failed to generate content",
                    processing_time=time.time() - start_time
                )
                self.db.update_next_due_date(email, faculty_data['frequency'], success=False)
                return {'status': 'failed', 'reason': 'Content generation failed'}
            
            # Check for duplicate content
            if self.db.is_duplicate_content(email, content):
                self.logger.info(f"Skipping duplicate content for {email}")
                self.db.log_email_history(
                    email, 'skipped_duplicate', content,
                    processing_time=time.time() - start_time,
                    tokens_used=tokens_used
                )
                self.db.update_next_due_date(email, faculty_data['frequency'], success=True)
                return {'status': 'skipped', 'reason': 'Duplicate content'}
            

            
            # Send email
            success, message_id_or_error, file_paths = self.email_service.send_rfp_email(faculty_data, content)
            
            processing_time = time.time() - start_time
            
            if success:
                # Log success
                self.db.log_email_history(
                    email, 'success', content, file_paths,
                    processing_time=processing_time,
                    tokens_used=tokens_used
                )
                self.db.update_next_due_date(email, faculty_data['frequency'], success=True)
                
                return {
                    'status': 'sent',
                    'message_id': message_id_or_error,
                    'processing_time': processing_time
                }
            else:
                # Log failure
                self.db.log_email_history(
                    email, 'failed', content, file_paths,
                    error_msg=message_id_or_error,
                    processing_time=processing_time, tokens_used=tokens_used
                )
                self.db.update_next_due_date(email, faculty_data['frequency'], success=False)
                
                return {
                    'status': 'failed',
                    'reason': message_id_or_error,
                    'processing_time': processing_time
                }
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error processing {email}: {str(e)}"
            self.logger.error(error_msg)
            
            # Log error and update schedule
            self.db.log_email_history(
                email, 'failed', error_msg=error_msg,
                processing_time=processing_time
            )
            self.db.update_next_due_date(email, faculty_data.get('frequency', 'biweekly'), success=False)
            
            return {'status': 'failed', 'reason': error_msg}
    
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        try:
            # Database stats
            db_stats = self.db.get_system_stats()
            
            # Due faculty
            due_faculty = self.db.get_due_faculty(limit=10)
            
            # API status
            ai_status = self.ai_generator.get_api_status()
            email_status = self.email_service.get_service_status()
            
            return {
                'database': db_stats,
                'due_faculty_count': len(due_faculty),
                'due_faculty_emails': [f['email'] for f in due_faculty[:5]],
                'ai_service': ai_status,
                'email_service': email_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def process_specific_faculty(self, email: str) -> Dict:
        """Process specific faculty member (for testing/manual runs)"""
        try:
            faculty = self.db.get_faculty_by_email(email)
            if not faculty:
                return {'status': 'failed', 'reason': f'Faculty not found: {email}'}
            
            if not faculty.get('active', True):
                return {'status': 'failed', 'reason': f'Faculty inactive: {email}'}
            
            return self.process_single_faculty(faculty)
            
        except Exception as e:
            return {'status': 'failed', 'reason': f'Error processing {email}: {str(e)}'}
