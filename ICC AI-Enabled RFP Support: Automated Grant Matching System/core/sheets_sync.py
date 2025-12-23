"""
Production Google Sheets Synchronization
"""
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, List
import logging

from googleapiclient.discovery import build
from config.settings import GOOGLE_SHEETS_ID, GOOGLE_SHEETS_RANGE, COLUMN_MAPPING, FREQUENCY_MAPPING


class ProductionSheetsSync:
    def __init__(self, credentials):
        self.credentials = credentials
        self.service = None
        self.logger = logging.getLogger(__name__)
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Sheets service with error handling"""
        try:
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.logger.info("Google Sheets API service initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            self.service = None
    
    def test_connection(self) -> bool:
        """Test connection to Google Sheets"""
        if not self.service:
            return False
        
        try:
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=GOOGLE_SHEETS_ID
            ).execute()
            
            sheet_title = sheet_metadata.get('properties', {}).get('title', 'Unknown')
            self.logger.info(f"Successfully connected to sheet: {sheet_title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Google Sheets connection test failed: {str(e)}")
            return False
    
    def fetch_faculty_data(self) -> Optional[pd.DataFrame]:
        """Fetch and process faculty data from Google Sheets"""
        if not self.service:
            self.logger.error("Google Sheets service not available")
            return None
        
        try:
            self.logger.info(f"Fetching data from Google Sheets: {GOOGLE_SHEETS_ID}")
            
            # Try configured range first
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=GOOGLE_SHEETS_ID,
                    range=GOOGLE_SHEETS_RANGE
                ).execute()
                values = result.get('values', [])
                
            except Exception as range_error:
                self.logger.warning(f"Configured range failed: {str(range_error)}")
                self.logger.info("Attempting auto-detection...")
                
                # Auto-detect sheet and range
                sheet_metadata = self.service.spreadsheets().get(
                    spreadsheetId=GOOGLE_SHEETS_ID
                ).execute()
                
                sheets = sheet_metadata.get('sheets', [])
                if not sheets:
                    self.logger.error("No sheets found in spreadsheet")
                    return None
                
                # Try first sheet with broader range
                first_sheet = sheets[0]
                sheet_title = first_sheet['properties']['title']
                auto_range = f"'{sheet_title}'!A:Z"
                
                self.logger.info(f"Trying auto-detected range: {auto_range}")
                
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=GOOGLE_SHEETS_ID,
                    range=auto_range
                ).execute()
                values = result.get('values', [])
            
            if not values or len(values) < 2:
                self.logger.warning("Insufficient data in Google Sheets")
                return None
            
            # Process data into DataFrame
            df = self._process_sheet_data(values)
            
            if df is not None:
                self.logger.info(f"Successfully processed {len(df)} faculty records from Google Sheets")
                return df
            else:
                self.logger.error("Failed to process sheet data")
                return None
                
        except Exception as e:
            self.logger.error(f"Error fetching data from Google Sheets: {str(e)}")
            return None
    
    def _process_sheet_data(self, values: List[List]) -> Optional[pd.DataFrame]:
        """Process raw sheet data into structured DataFrame"""
        try:
            headers = values[0]
            data_rows = values[1:]
            
            # Normalize row lengths
            max_cols = len(headers)
            normalized_rows = []
            
            for row in data_rows:
                # Skip empty rows
                if not any(cell.strip() for cell in row if cell):
                    continue
                
                # Pad or truncate row to match headers
                normalized_row = row + [''] * (max_cols - len(row))
                normalized_row = normalized_row[:max_cols]
                normalized_rows.append(normalized_row)
            
            if not normalized_rows:
                self.logger.warning("No valid data rows found")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(normalized_rows, columns=headers)
            df.columns = df.columns.str.strip()
            
            # Extract and validate faculty data
            processed_data = []
            for index, row in df.iterrows():
                faculty_data = self._extract_faculty_data(row)
                
                # Validate required fields
                if faculty_data['email'] and '@' in faculty_data['email']:
                    processed_data.append(faculty_data)
                else:
                    self.logger.warning(f"Skipping row {index + 2}: invalid or missing email")
            
            if not processed_data:
                self.logger.error("No valid faculty data found")
                return None
            
            return pd.DataFrame(processed_data)
            
        except Exception as e:
            self.logger.error(f"Error processing sheet data: {str(e)}")
            return None
    
    def _extract_faculty_data(self, row: pd.Series) -> Dict:
        """Extract and normalize faculty data from sheet row"""
        
        # Extract email
        email = str(row.get(COLUMN_MAPPING['email'], '')).strip().lower()
        
        # Extract and clean other fields
        research_area = str(row.get(COLUMN_MAPPING['research_area'], '')).strip()
        keywords = str(row.get(COLUMN_MAPPING['keywords'], '')).strip()
        eligibility_constraints = str(row.get(COLUMN_MAPPING['eligibility_constraints'], 'No constraints specified')).strip()
        early_career = str(row.get(COLUMN_MAPPING['early_career'], 'Not specified')).strip()
        funding_types = str(row.get(COLUMN_MAPPING['funding_types'], 'General research grants')).strip()
        rfp_size = str(row.get(COLUMN_MAPPING['rfp_size'], 'Any size')).strip()
        submission_timeline = str(row.get(COLUMN_MAPPING['submission_timeline'], 'Flexible timeline')).strip()
        preferred_funding_sources = str(row.get(COLUMN_MAPPING['preferred_funding_sources'], 'Federal agencies (NSF, NIH, etc.)')).strip()
        additional_info = str(row.get(COLUMN_MAPPING['additional_info'], '')).strip()
        documents_info = str(row.get(COLUMN_MAPPING['documents'], '')).strip()
        
        # Extract and normalize frequency
        raw_frequency = str(row.get(COLUMN_MAPPING['frequency'], 'biweekly')).lower().strip()
        frequency = self._normalize_frequency(raw_frequency)
        
        # Extract timestamp if available
        timestamp_str = str(row.get(COLUMN_MAPPING['timestamp'], '')).strip()
        timestamp = self._parse_timestamp(timestamp_str)
        
        return {
            'email': email,
            'research_area': research_area,
            'keywords': keywords,
            'eligibility_constraints': eligibility_constraints,
            'early_career': early_career,
            'funding_types': funding_types,
            'rfp_size': rfp_size,
            'submission_timeline': submission_timeline,
            'preferred_funding_sources': preferred_funding_sources,
            'frequency': frequency,
            'additional_info': additional_info,
            'documents_info': documents_info,
            'timestamp': timestamp
        }
    
    def _normalize_frequency(self, raw_frequency: str) -> str:
        """Normalize frequency values to standard options
        
        IMPORTANT: Check longer strings FIRST to avoid substring matching issues.
        For example, 'biweekly' contains 'weekly', so we must check 'biweekly' first.
        """
        if not raw_frequency or raw_frequency.strip() == '':
            return 'biweekly'
            
        raw_frequency = raw_frequency.lower().strip()
        
        # Check in order from most specific to least specific
        # This prevents 'weekly' from matching inside 'biweekly'
        if 'biweekly' in raw_frequency or 'bi-weekly' in raw_frequency or 'bi weekly' in raw_frequency:
            return 'biweekly'
        elif 'one response' in raw_frequency or 'one-response' in raw_frequency:
            return 'one response'
        elif 'monthly' in raw_frequency:
            return 'monthly'
        elif 'weekly' in raw_frequency:
            return 'weekly'
         
        # Default fallback
        self.logger.warning(f"Unknown frequency value: '{raw_frequency}', defaulting to biweekly")
        return 'biweekly'
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp_str:
            return datetime.now()
        
        # Common Google Sheets timestamp formats
        formats = [
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S', 
            '%m/%d/%Y',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # If parsing fails, return current time
        self.logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return datetime.now()
