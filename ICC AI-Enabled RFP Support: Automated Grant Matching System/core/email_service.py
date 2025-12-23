"""
Production Email Service using Gmail API
"""
import os
import base64
import markdown
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage

from config.settings import (
    SCOPES, CREDENTIALS_FILE, TOKEN_FILE, SENDER_EMAIL, 
    CC_RECIPIENTS, EMAIL_TEMPLATE, FACULTY_DIRS
)


class ProductionEmailService:
    def __init__(self):
        self.service = None
        self.logger = logging.getLogger(__name__)
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using production credentials"""
        creds = None
        
        try:
            # Load existing token
            if TOKEN_FILE.exists():
                creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        self.logger.info("Gmail credentials refreshed successfully")
                    except Exception as e:
                        self.logger.warning(f"Token refresh failed: {str(e)}")
                        creds = None
                
                if not creds:
                    if not CREDENTIALS_FILE.exists():
                        self.logger.error(f"Credentials file not found: {CREDENTIALS_FILE}")
                        return
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDENTIALS_FILE), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    self.logger.info("New Gmail credentials obtained")
                
                # Save credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            
            # Build Gmail service
            self.service = build("gmail", "v1", credentials=creds)
            self.logger.info("Gmail API service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Gmail authentication failed: {str(e)}")
            self.service = None
    
    def send_rfp_email(self, faculty_data: Dict, content: str) -> Tuple[bool, Optional[str], Tuple[str, str, str]]:
        """
        Send RFP email with individual faculty folder organization
        Returns: (success, message_id_or_error, (md_path, html_path, folder_path))
        """
        if not self.service:
            return False, "Gmail service not authenticated", (None, None, None)
        
        try:
            # Create individual faculty folder and save files
            file_paths = self._save_faculty_files(faculty_data['email'], content)
            if not file_paths:
                return False, "Failed to save content files", (None, None, None)
            
            md_path, html_path, folder_path = file_paths
            
            # Create and send email
            message = self._create_email_message(faculty_data, html_path)
            if not message:
                return False, "Failed to create email message", file_paths
            
            # Send email
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            create_message = {"raw": encoded_message}
            
            send_message = (
                self.service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            
            message_id = send_message["id"]
            self.logger.info(f"Email sent successfully to {faculty_data['email']}, Message ID: {message_id}")
            
            return True, message_id, file_paths
            
        except HttpError as error:
            error_msg = f"Gmail API error: {str(error)}"
            self.logger.error(f"Email sending failed for {faculty_data['email']}: {error_msg}")
            return False, error_msg, file_paths if 'file_paths' in locals() else (None, None, None)
        
        except Exception as e:
            error_msg = f"Email sending failed: {str(e)}"
            self.logger.error(f"Email sending failed for {faculty_data['email']}: {error_msg}")
            return False, error_msg, file_paths if 'file_paths' in locals() else (None, None, None)
    
    def _extract_table_from_content(self, content: str) -> Optional[str]:
        """Extract just the funding opportunities table from AI-generated content"""
        try:
            # Remove <think> tags if present
            if '<think>' in content and '</think>' in content:
                # Extract content after </think>
                content = content.split('</think>')[-1]
                self.logger.info("Removed <think> block from content")
            
            lines = content.split('\n')
            table_lines = []
            in_table = False
            
            for line in lines:
                # Look for table header - check multiple possible header indicators
                if line.strip().startswith('|') and any(keyword in line for keyword in ['Funding Agency', 'Program Name', 'Agency', 'Deadline']):
                    in_table = True
                    table_lines.append(line)
                    self.logger.debug(f"Found table header: {line[:80]}")
                elif in_table and line.strip().startswith('|'):
                    table_lines.append(line)
                elif in_table and line.strip() == '':
                    # Allow empty lines within table
                    continue
                elif in_table and not line.strip().startswith('|'):
                    # End of table reached
                    self.logger.debug(f"Table ended at line: {line[:50]}")
                    break
            
            if table_lines:
                # Validate we have at least header + separator + data
                if len(table_lines) >= 3:
                    result = '\n'.join(table_lines)
                    self.logger.info(f"Extracted table with {len(table_lines)} lines")
                    return result
                else:
                    self.logger.warning(f"Table too short ({len(table_lines)} lines), may be malformed")
                    return '\n'.join(table_lines) if table_lines else None
            else:
                self.logger.warning("No markdown table found in content")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting table from content: {str(e)}")
            return None

    def _count_opportunities(self, table_markdown: str) -> int:
        """Count the number of funding opportunities in the table"""
        if not table_markdown:
            return 0
        
        lines = table_markdown.split('\n')
        # Count data rows (exclude header and separator)
        data_rows = [line for line in lines if line.strip().startswith('|') and 'Funding Agency' not in line and not line.strip().startswith('|---')]
        return len(data_rows)

    def _save_faculty_files(self, email: str, content: str) -> Optional[Tuple[str, str, str]]:
        """Save content files in individual faculty folders with table extraction"""
        try:
            # Create faculty-specific folder
            username = email.split("@")[0]
            date_string = datetime.now().strftime("%Y-%m-%d")
            
            faculty_folder = FACULTY_DIRS / username
            faculty_folder.mkdir(exist_ok=True)
            
            # Generate filenames
            md_filename = f"{username}_{date_string}.md"
            html_filename = f"{username}_{date_string}.html"
            
            md_path = faculty_folder / md_filename
            html_path = faculty_folder / html_filename
            
            # Save full markdown file (for backup/reference)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Extract just the table from content
            table_markdown = self._extract_table_from_content(content)
            
            if not table_markdown:
                self.logger.error(f"Failed to extract table for {email}")
                self.logger.debug(f"Content preview (first 500 chars): {content[:500]}")
                
                # Try to find any table-like structure
                if '|' in content:
                    self.logger.warning("Content contains '|' but table extraction failed - checking format")
                    # Log first few lines with pipes
                    pipe_lines = [line for line in content.split('\n') if '|' in line][:5]
                    for i, line in enumerate(pipe_lines):
                        self.logger.debug(f"Pipe line {i}: {line[:100]}")
                
                # Use full content as fallback
                table_markdown = content
            else:
                self.logger.info(f"Successfully extracted table for {email} ({len(table_markdown)} chars, {table_markdown.count(chr(10))+1} lines)")
            
            table_html = markdown.markdown(
                table_markdown, 
                extensions=['markdown.extensions.tables']
            )
            
            # Count opportunities for summary
            opportunity_count = self._count_opportunities(table_markdown)
            
            # Create clean, focused HTML with just the table
            clean_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>RFP Opportunities for {username} - {date_string}</title>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 30px; 
            background-color: #f8f9fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ 
            color: #2c3e50; 
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .summary {{
            background-color: #e8f4fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 25px;
            border-left: 4px solid #3498db;
        }}
        table {{ 
            border-collapse: collapse; 
            width: 100%; 
            margin-top: 20px;
            font-size: 14px;
        }}
        th {{ 
            background-color: #34495e; 
            color: white;
            padding: 12px 8px; 
            text-align: left;
            font-weight: 600;
        }}
        td {{ 
            border: 1px solid #ddd; 
            padding: 10px 8px; 
            vertical-align: top;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e3f2fd;
        }}
        a {{
            color: #2980b9;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            color: #3498db;
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
        .deadline-urgent {{
            color: #e74c3c;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>RFP Opportunities for {email}</h1>
        
        <div class="summary">
            <strong> Summary:</strong> {opportunity_count} funding opportunities found<br>
            <strong> Generated:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br>
            <strong> Focus:</strong> Personalized matches based on your research interests
        </div>
        
        {table_html}
        
        <div class="footer">
            <p><em>Generated by ICC Proposal-Enabled AI Support Initiative<br>
            Michigan Technological University<br>
            Institute of Computing and Cybersystems</em></p>
        </div>
    </div>
</body>
</html>"""
            
            # Save the clean HTML file
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(clean_html)
            
            self.logger.info(f"Clean table-focused files saved for {email} in folder: {faculty_folder}")
            
            return str(md_path), str(html_path), str(faculty_folder)
            
        except Exception as e:
            self.logger.error(f"Error saving content files for {email}: {str(e)}")
            return None
    
    def _create_email_message(self, faculty_data: Dict, html_path: str) -> Optional[EmailMessage]:
        """Create professional email message with attachment"""
        try:
            message = EmailMessage()
            
            # Set email content
            message.set_content(EMAIL_TEMPLATE)
            
            # Generate subject and headers
            username = faculty_data['email'].split("@")[0]
            date_string = datetime.now().strftime("%Y-%m-%d")
            
            message["To"] = faculty_data['email']
            message["From"] = SENDER_EMAIL
            message["Subject"] = f"ICC AI-Enabled RFP Results for {username}, {date_string}"
            
            # Add CC recipients
            if CC_RECIPIENTS:
                message['Cc'] = ', '.join(CC_RECIPIENTS)
            
            # Add HTML attachment
            if Path(html_path).exists():
                with open(html_path, "rb") as fp:
                    attachment_data = fp.read()
                
                message.add_attachment(
                    attachment_data, 
                    "text", 
                    "html", 
                    filename=Path(html_path).name
                )
            else:
                self.logger.error(f"HTML file not found: {html_path}")
                return None
            
            return message
            
        except Exception as e:
            self.logger.error(f"Error creating email message: {str(e)}")
            return None
    
    def test_email_connection(self) -> bool:
        """Test Gmail API connection"""
        if not self.service:
            return False
        
        try:
            profile = self.service.users().getProfile(userId="me").execute()
            email = profile.get('emailAddress')
            
            self.logger.info(f"Gmail connection test successful, authenticated as: {email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Gmail connection test failed: {str(e)}")
            return False
    
    def get_service_status(self) -> Dict:
        """Get email service status"""
        if not self.service:
            return {'status': 'error', 'message': 'Service not authenticated'}
        
        try:
            profile = self.service.users().getProfile(userId="me").execute()
            return {
                'status': 'healthy',
                'authenticated_as': profile.get('emailAddress'),
                'sender_email': SENDER_EMAIL,
                'cc_recipients': CC_RECIPIENTS
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
