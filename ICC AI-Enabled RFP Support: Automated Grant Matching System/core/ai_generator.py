"""
Production AI Content Generator using Perplexity API
"""
import requests
import time
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging
from config.settings import (
    PERPLEXITY_API_URL, PERPLEXITY_API_KEY, PERPLEXITY_MODEL, 
    PERPLEXITY_TEMPERATURE, PROMPT_INSTRUCTIONS, PROMPT_REQUEST,
    INSTITUTION_NAME, MAX_RETRIES, API_TIMEOUT, RETRY_DELAY_BASE
)


class ProductionAIGenerator:
    def __init__(self):
        self.api_url = PERPLEXITY_API_URL
        self.api_key = PERPLEXITY_API_KEY
        self.logger = logging.getLogger(__name__)
        
        # Validate API key
        if not self.api_key or self.api_key.strip() == '':
            self.logger.error("Perplexity API key is not configured")
            raise ValueError("Perplexity API key is required")
        
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json"
        }
    
    def generate_rfp_content(self, faculty_data: Dict) -> Tuple[Optional[str], int, float]:
        """
        Generate RFP content with comprehensive error handling and monitoring
        Returns: (content, tokens_used, processing_time)
        """
        start_time = time.time()
        
        try:
            prompt = self._build_comprehensive_prompt(faculty_data)
            
            payload = {
                "model": PERPLEXITY_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": PERPLEXITY_TEMPERATURE
            }
            
            self.logger.info(f"Generating RFP content for {faculty_data['email']}")
            
            # Retry logic for API calls with improved backoff
            for attempt in range(MAX_RETRIES):
                try:
                    response = requests.post(
                        self.api_url, 
                        headers=self.headers, 
                        json=payload,
                        timeout=(30, API_TIMEOUT)  # 30s connect, 10min read timeout
                    )
                    response.raise_for_status()
                    
                    response_data = response.json()
                    content = response_data['choices'][0]['message']['content']
                    tokens_used = response_data.get('usage', {}).get('total_tokens', 0)
                    
                    processing_time = time.time() - start_time
                    
                    self.logger.info(
                        f"Successfully generated content for {faculty_data['email']} "
                        f"(tokens: {tokens_used}, time: {processing_time:.2f}s)"
                    )
                    
                    return content, tokens_used, processing_time
                    
                except requests.exceptions.Timeout as e:
                    self.logger.warning(
                        f"API timeout on attempt {attempt + 1}/{MAX_RETRIES} for {faculty_data['email']}: {str(e)}"
                    )
                    
                    if attempt < MAX_RETRIES - 1:
                        # Exponential backoff with jitter
                        wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        raise
                        
                except requests.exceptions.RequestException as e:
                    error_details = f"Status: {getattr(e.response, 'status_code', 'Unknown')}, "
                    error_details += f"Response: {getattr(e.response, 'text', 'No response text')[:200]}"
                    
                    self.logger.warning(
                        f"API request attempt {attempt + 1}/{MAX_RETRIES} failed for {faculty_data['email']}: {str(e)} - {error_details}"
                    )
                    
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                        self.logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                  
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error generating RFP content for {faculty_data['email']}: {str(e)}"
            self.logger.error(error_msg)
            return None, 0, processing_time
    
    def _build_comprehensive_prompt(self, faculty_data: Dict) -> str:
        """Build comprehensive prompt using faculty data"""
        
        # Base instructions
        instructions = PROMPT_INSTRUCTIONS
        
        # Faculty-specific context
        faculty_context_parts = []
        
        if faculty_data.get('research_area'):
            faculty_context_parts.append(f"My RFP research area of interest is {faculty_data['research_area']}")
        
        if faculty_data.get('keywords'):
            faculty_context_parts.append(f"My keywords are {faculty_data['keywords']}")
        
        if faculty_data.get('eligibility_constraints'):
            constraints = faculty_data['eligibility_constraints']
            if constraints.lower() not in ['no', 'none', 'no constraints']:
                faculty_context_parts.append(f"My constraints on eligibility are {constraints}")
        
        if faculty_data.get('early_career'):
            faculty_context_parts.append(f"My early career faculty status is {faculty_data['early_career']}")
        
        if faculty_data.get('funding_types'):
            faculty_context_parts.append(f"My funding types are {faculty_data['funding_types']}")
        
        if faculty_data.get('rfp_size'):
            faculty_context_parts.append(f"The size of the RFP I'm interested in are {faculty_data['rfp_size']}")
        
        if faculty_data.get('submission_timeline'):
            faculty_context_parts.append(f"I would like to submit a proposal {faculty_data['submission_timeline']}")
        
        if faculty_data.get('preferred_funding_sources'):
            faculty_context_parts.append(f"Please consider funding sources including {faculty_data['preferred_funding_sources']}")
        
        if faculty_data.get('additional_info'):
            faculty_context_parts.append(f"Additional context: {faculty_data['additional_info']}")
        
        # Combine all parts
        faculty_context = ". ".join(faculty_context_parts) + ". " if faculty_context_parts else ""
        
        # Complete prompt
        complete_prompt = instructions + faculty_context + PROMPT_REQUEST
        
        return complete_prompt
    
    def test_api_connection(self) -> bool:
        """Test Perplexity API connectivity"""
        try:
            test_payload = {
                "model": "sonar-pro",  # Use lighter model for testing
                "messages": [{"role": "user", "content": "Hello, this is a connectivity test."}],
                "stream": False,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=test_payload,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info("Perplexity API connection test successful")
                return True
            else:
                self.logger.error(f"Perplexity API test failed with status {response.status_code}: {response.text}")
                return False
            
        except Exception as e:
            self.logger.error(f"Perplexity API connection test failed: {str(e)}")
            return False
    
    def get_api_status(self) -> Dict:
        """Get API status and usage information"""
        try:
            # Simple test call to check API status
            test_payload = {
                "model": "sonar-pro",
                "messages": [{"role": "user", "content": "API status check"}],
                "stream": False,
                "temperature": 0.1
            }
            
            start_time = time.time()
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                json=test_payload,
                timeout=30
            )
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response_data = response.json()
                tokens_used = response_data.get('usage', {}).get('total_tokens', 0)
                
                return {
                    'status': 'healthy',
                    'response_time': response_time,
                    'tokens_used': tokens_used,
                    'model': PERPLEXITY_MODEL
                }
            else:
                return {
                    'status': 'error',
                    'error_code': response.status_code,
                    'response_time': response_time
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'response_time': None
            }
