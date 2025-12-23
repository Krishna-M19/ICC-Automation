"""
Production RFP System - Main Entry Point
Michigan Technological University - Institute of Computing and Cybersystems

Single entry point for all system operations with comprehensive logging and monitoring
"""
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from core.processor import ProductionRFPProcessor
from utils.monitoring import ProductionMonitor
from utils.admin_tools import ProductionAdminTools
from config.settings import LOGS_DIR


def setup_logging():
    """Setup comprehensive logging for production use"""
    # Create logs directory
    LOGS_DIR.mkdir(exist_ok=True)
    
    # Configure logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # File handler for all logs
    file_handler = logging.FileHandler(
        LOGS_DIR / f"rfp_system_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Console handler for important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )
    
    return logging.getLogger(__name__)


def run_full_automation():
    """Run complete automation pipeline"""
    logger = logging.getLogger(__name__)
    processor = ProductionRFPProcessor()
    
    logger.info("=== RFP Production System - Full Automation Started ===")
    start_time = datetime.now()
    
    try:
        # Step 1: Sync faculty data from Google Sheets
        logger.info("Step 1: Syncing faculty data from Google Sheets")
        sync_stats = processor.sync_faculty_data()
        
        if 'error' in sync_stats:
            logger.error(f"Data sync failed: {sync_stats['error']}")
            return False
        
        logger.info(f"Data sync completed: {sync_stats}")
        
        # Step 2: Process faculty due for emails
        logger.info("Step 2: Processing faculty due for emails")
        process_stats = processor.process_due_faculty()
        
        if 'error' in process_stats:
            logger.error(f"Faculty processing failed: {process_stats['error']}")
            return False
        
        logger.info(f"Faculty processing completed: {process_stats}")
        
        # Step 3: Generate system status
        logger.info("Step 3: Generating system status")
        system_status = processor.get_system_status()
        
        # Log final summary
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"=== Full Automation Completed Successfully in {processing_time:.2f}s ===")
        logger.info(f"Summary: {sync_stats['processed']} faculty synced, {process_stats['sent']} emails sent")
        
        return True
        
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Critical error in full automation after {processing_time:.2f}s: {str(e)}")
        return False


def process_single_faculty(email: str):
    """Process specific faculty member"""
    logger = logging.getLogger(__name__)
    processor = ProductionRFPProcessor()
    
    logger.info(f"Processing single faculty member: {email}")
    
    try:
        result = processor.process_specific_faculty(email)
        
        logger.info(f"Result for {email}: {result['status']}")
        if result['status'] == 'sent':
            logger.info(f"Email sent successfully - Message ID: {result.get('message_id', 'N/A')}")
        elif result['status'] == 'failed':
            logger.error(f"Processing failed: {result.get('reason', 'Unknown error')}")
        elif result['status'] == 'skipped':
            logger.info(f"Email skipped: {result.get('reason', 'Unknown reason')}")
        
        return result['status'] == 'sent'
        
    except Exception as e:
        logger.error(f"Error processing {email}: {str(e)}")
        return False


def show_system_status():
    """Display comprehensive system status"""
    logger = logging.getLogger(__name__)
    processor = ProductionRFPProcessor()
    monitor = ProductionMonitor()
    
    try:
        print("\n" + "="*60)
        print("RFP PRODUCTION SYSTEM STATUS")
        print("="*60)
        
        # System status
        status = processor.get_system_status()
        
        if 'error' in status:
            print(f" System Error: {status['error']}")
            return
        
        # Database statistics
        db_stats = status.get('database', {})
        print(f"\n DATABASE STATISTICS:")
        print(f"   Total Faculty: {db_stats.get('total_faculty', 0)}")
        print(f"   Active Faculty: {db_stats.get('active_faculty', 0)}")
        print(f"   Emails Today: {db_stats.get('emails_today', 0)}")
        print(f"   Successful Today: {db_stats.get('successful_today', 0)}")
        print(f"   Failed Schedules: {db_stats.get('failed_schedules', 0)}")
        
        # Due faculty
        due_count = status.get('due_faculty_count', 0)
        print(f"\n SCHEDULING:")
        print(f"   Faculty Due Today: {due_count}")
        
        if status.get('due_faculty_emails'):
            print("   Due Faculty:")
            for email in status['due_faculty_emails']:
                print(f"     - {email}")
        
        # Service status
        ai_status = status.get('ai_service', {})
        email_status = status.get('email_service', {})
        
        print(f"\n SERVICE STATUS:")
        print(f"   AI Service: {' Healthy' if ai_status.get('status') == 'healthy' else 'Error'}")
        print(f"   Email Service: {' Healthy' if email_status.get('status') == 'healthy' else 'Error'}")
        
        # System health
        health = monitor.get_system_health()
        health_score = health.get('health_score', 0)
        
        print(f"\n SYSTEM HEALTH:")
        print(f"   Health Score: {health_score}/100")
        print(f"   Recent Errors: {health.get('recent_errors', 0)}")
        print(f"   Overdue Emails: {health.get('overdue_emails', 0)}")
        
        print(f"\n Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error showing system status: {str(e)}")
        print(f" Error retrieving system status: {str(e)}")


def show_faculty_list():
    """Display faculty list with status"""
    logger = logging.getLogger(__name__)
    admin = ProductionAdminTools()
    
    try:
        faculty_list = admin.list_all_faculty(active_only=False)
        
        print("\n" + "="*80)
        print("FACULTY LIST")
        print("="*80)
        
        if not faculty_list:
            print("No faculty found in database")
            return
        
        for faculty in faculty_list:
            status_icon = "✅" if faculty.get('active') else "❌"
            email = faculty['email']
            frequency = faculty.get('frequency', 'Not set')
            next_due = faculty.get('next_due_date', 'Not scheduled')
            total_emails = faculty.get('total_emails_sent', 0)
            
            print(f"{status_icon} {email}")
            print(f"    Frequency: {frequency} | Next Due: {next_due} | Emails Sent: {total_emails}")
            print(f"    Research: {faculty.get('research_area', 'Not specified')[:60]}...")
            print()
        
        print(f"Total: {len(faculty_list)} faculty members")
        print("="*80)
        
    except Exception as e:
        logger.error(f"Error showing faculty list: {str(e)}")
        print(f"Error retrieving faculty list: {str(e)}")


def generate_daily_report():
    """Generate and display daily report"""
    logger = logging.getLogger(__name__)
    monitor = ProductionMonitor()
    
    try:
        report = monitor.generate_daily_report()
        
        if 'error' in report:
            print(f"Error generating report: {report['error']}")
            return
        
        print("\n" + "="*60)
        print(f"DAILY REPORT - {report['date']}")
        print("="*60)
        
        # Email statistics
        email_stats = report.get('email_stats', {})
        print(f"\n EMAIL STATISTICS:")
        print(f"   Total Emails: {email_stats.get('total_emails', 0)}")
        print(f"   Successful: {email_stats.get('successful', 0)}")
        print(f"   Failed: {email_stats.get('failed', 0)}")
        print(f"   Skipped: {email_stats.get('skipped', 0)}")
        avg_time = email_stats.get('avg_processing_time', 0) or 0
        print(f"   Avg Processing Time: {avg_time:.2f}s")
        print(f"   Total RFPs Sent: {email_stats.get('total_rfps_sent', 0)}")
        
        # Faculty statistics
        faculty_stats = report.get('faculty_stats', {})
        print(f"\n FACULTY STATISTICS:")
        print(f"   Total Faculty: {faculty_stats.get('total_faculty', 0)}")
        print(f"   Active Faculty: {faculty_stats.get('active_faculty', 0)}")
        print(f"   New Submissions: {faculty_stats.get('new_submissions', 0)}")
        
        # Schedule statistics
        schedule_stats = report.get('schedule_stats', {})
        print(f"\n SCHEDULE STATISTICS:")
        print(f"   Due Today: {schedule_stats.get('due_today', 0)}")
        print(f"   Overdue: {schedule_stats.get('overdue', 0)}")
        print(f"   Failed Schedules: {schedule_stats.get('failed_schedules', 0)}")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error generating daily report: {str(e)}")
        print(f"Error generating daily report: {str(e)}")


def main():
    """Main entry point with command-line interface"""
    parser = argparse.ArgumentParser(
        description="RFP Production System - Michigan Technological University",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run full automation
  python main.py --faculty email@mtu.edu # Process specific faculty
  python main.py --status                # Show system status
  python main.py --list                  # List all faculty
  python main.py --report                # Generate daily report
  python main.py --sync-only             # Only sync faculty data, do not process emails
        """
    )
    
    parser.add_argument(
        '--faculty', 
        metavar='EMAIL',
        help='Process specific faculty member by email'
    )
    parser.add_argument(
        '--status', 
        action='store_true',
        help='Show comprehensive system status'
    )
    parser.add_argument(
        '--list', 
        action='store_true',
        help='List all faculty members'
    )
    parser.add_argument(
        '--report', 
        action='store_true',
        help='Generate daily report'
    )
    parser.add_argument(
        '--sync-only', 
        action='store_true',
        help='Only sync faculty data, do not process emails'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging()
    
    try:
        if args.faculty:
            # Process specific faculty
            success = process_single_faculty(args.faculty)
            sys.exit(0 if success else 1)
            
        elif args.status:
            # Show system status
            show_system_status()
            
        elif args.list:
            # List faculty
            show_faculty_list()
            
        elif args.report:
            # Generate daily report
            generate_daily_report()
            
        elif args.sync_only:
            # Sync data only
            processor = ProductionRFPProcessor()
            sync_stats = processor.sync_faculty_data()
            
            if 'error' in sync_stats:
                logger.error(f"Data sync failed: {sync_stats['error']}")
                sys.exit(1)
            else:
                logger.info(f"Data sync completed: {sync_stats}")
                sys.exit(0)
                
        else:
            # Run full automation
            success = run_full_automation()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
