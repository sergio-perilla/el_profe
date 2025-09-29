#!/usr/bin/env python3
"""
Rate limit management and analysis for Garmin Connect API
"""

import time
import logging
from datetime import datetime, timedelta
import json
import os

logger = logging.getLogger(__name__)

class GarminRateLimitManager:
    def __init__(self):
        self.request_log_file = "data/metadata/request_log.json"
        self.requests_per_minute_limit = 4200  # Conservative estimate
        self.requests_per_hour_limit = 10000  # Conservative estimate
        self.request_history = []
        self.load_request_history()
    
    def load_request_history(self):
        """Load request history from file"""
        try:
            if os.path.exists(self.request_log_file):
                with open(self.request_log_file, 'r') as f:
                    data = json.load(f)
                    self.request_history = data.get('requests', [])
                    # Clean old entries (older than 24 hours)
                    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
                    self.request_history = [r for r in self.request_history if r['timestamp'] > cutoff]
        except Exception as e:
            logger.warning(f"Could not load request history: {e}")
            self.request_history = []
    
    def save_request_history(self):
        """Save request history to file"""
        try:
            os.makedirs(os.path.dirname(self.request_log_file), exist_ok=True)
            with open(self.request_log_file, 'w') as f:
                json.dump({
                    'requests': self.request_history,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save request history: {e}")
    
    def log_request(self, endpoint, success=True):
        """Log a request to the API"""
        request_entry = {
            'timestamp': datetime.now().isoformat(),
            'endpoint': endpoint,
            'success': success
        }
        self.request_history.append(request_entry)
        self.save_request_history()
    
    def get_request_count(self, minutes=60):
        """Get number of requests in the last N minutes"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        cutoff_iso = cutoff.isoformat()
        recent_requests = [r for r in self.request_history if r['timestamp'] > cutoff_iso]
        return len(recent_requests)
    
    def should_wait(self):
        """Check if we should wait before making more requests"""
        # Check last minute
        requests_last_minute = self.get_request_count(1)
        if requests_last_minute >= self.requests_per_minute_limit:
            return True, f"Rate limit: {requests_last_minute} requests in last minute"
        
        # Check last hour
        requests_last_hour = self.get_request_count(60)
        if requests_last_hour >= self.requests_per_hour_limit:
            return True, f"Rate limit: {requests_last_hour} requests in last hour"
        
        return False, None
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limits"""
        should_wait, reason = self.should_wait()
        if should_wait:
            logger.warning(f"Rate limit reached: {reason}. Waiting 60 seconds...")
            time.sleep(60)
            return True
        return False
    
    def get_rate_limit_status(self):
        """Get current rate limit status"""
        return {
            'requests_last_minute': self.get_request_count(1),
            'requests_last_hour': self.get_request_count(60),
            'requests_last_24h': self.get_request_count(1440),
            'limit_per_minute': self.requests_per_minute_limit,
            'limit_per_hour': self.requests_per_hour_limit,
            'next_reset_minute': (datetime.now() + timedelta(minutes=1)).strftime('%H:%M'),
            'next_reset_hour': (datetime.now() + timedelta(hours=1)).strftime('%H:%M')
        }

def analyze_current_usage():
    """Analyze current API usage"""
    manager = GarminRateLimitManager()
    status = manager.get_rate_limit_status()
    
    print("🔄 GARMIN API RATE LIMIT STATUS")
    print("=" * 40)
    print(f"Requests in last minute: {status['requests_last_minute']}/{status['limit_per_minute']}")
    print(f"Requests in last hour: {status['requests_last_hour']}/{status['limit_per_hour']}")
    print(f"Requests in last 24h: {status['requests_last_24h']}")
    print()
    print(f"Next minute reset: {status['next_reset_minute']}")
    print(f"Next hour reset: {status['next_reset_hour']}")
    print()
    
    should_wait, reason = manager.should_wait()
    if should_wait:
        print(f"⚠️  SHOULD WAIT: {reason}")
    else:
        print("✅ OK TO PROCEED")
    
    return manager

if __name__ == "__main__":
    analyze_current_usage()
