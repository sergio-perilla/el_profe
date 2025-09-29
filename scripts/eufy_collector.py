#!/usr/bin/env python3
"""
Eufy Smart Scale P3 data collector for automated body composition sync

This replaces the manual CSV import process with automated API collection.
"""

import os
import sys
import requests
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import time
import cloudscraper

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class EufyP3Collector:
    def __init__(self, email: str, password: str):
        self.email = email
        self.password = password
        self.session = cloudscraper.create_scraper()
        self.access_token = None
        self.user_id = None
        self.device_sn = None
        
        # Eufy API endpoints
        self.base_url = "https://mysmart.eufylife.com"
        self.api_base = f"{self.base_url}/api/v1"
        
    def authenticate(self) -> bool:
        """Authenticate with Eufy Life cloud service"""
        try:
            # Step 1: Get login page and session
            login_url = f"{self.base_url}/passport/login"
            response = self.session.get(login_url)
            
            if response.status_code != 200:
                logger.error(f"Failed to access login page: {response.status_code}")
                return False
            
            # Step 2: Login with credentials  
            login_data = {
                'email': self.email,
                'password': self.password,
                'client_id': 'eufyhome-app',
                'client_Secret': 'GQCpr9dSp3uQpsOMgJ4B6o2Ft9x4GAbk',
                'response_type': 'token'
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'EufyHome/2.5.1 (iPhone; iOS 15.0; Scale/3.00)',
                'Accept': 'application/json'
            }
            
            auth_response = self.session.post(
                f"{self.api_base}/user/login",
                json=login_data,
                headers=headers
            )
            
            if auth_response.status_code == 200:
                auth_data = auth_response.json()
                
                if auth_data.get('code') == 0:  # Success code
                    self.access_token = auth_data.get('access_token')
                    self.user_id = auth_data.get('user_id')
                    
                    logger.info("Successfully authenticated with Eufy Life")
                    return True
                else:
                    logger.error(f"Login failed: {auth_data.get('msg', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Authentication request failed: {auth_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def get_devices(self) -> List[Dict]:
        """Get list of connected Eufy devices"""
        if not self.access_token:
            logger.error("Not authenticated")
            return []
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'EufyHome/2.5.1 (iPhone; iOS 15.0; Scale/3.00)'
            }
            
            response = self.session.get(
                f"{self.api_base}/device/list",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    devices = data.get('devices', [])
                    
                    # Find P3 scale devices
                    scales = [d for d in devices if 'scale' in d.get('device_type', '').lower() 
                             or d.get('product_name', '').lower().startswith('smart scale')]
                    
                    if scales:
                        # Use the first scale found
                        self.device_sn = scales[0].get('device_sn')
                        logger.info(f"Found Eufy scale: {scales[0].get('product_name')} (SN: {self.device_sn})")
                        return scales
                    else:
                        logger.warning("No Eufy scales found in device list")
                        return []
                else:
                    logger.error(f"Device list request failed: {data.get('msg')}")
                    return []
            else:
                logger.error(f"Device list request failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []
    
    def get_measurements(self, start_date: date, end_date: date) -> List[Dict]:
        """Get body composition measurements for date range"""
        if not self.access_token or not self.device_sn:
            logger.error("Not authenticated or no device found")
            return []
        
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'EufyHome/2.5.1 (iPhone; iOS 15.0; Scale/3.00)'
            }
            
            # Convert dates to timestamps
            start_timestamp = int(start_date.strftime('%s')) * 1000
            end_timestamp = int((end_date + timedelta(days=1)).strftime('%s')) * 1000
            
            params = {
                'device_sn': self.device_sn,
                'start_time': start_timestamp,
                'end_time': end_timestamp,
                'limit': 100
            }
            
            response = self.session.get(
                f"{self.api_base}/scale/records",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    measurements = data.get('records', [])
                    logger.info(f"Retrieved {len(measurements)} measurements from {start_date} to {end_date}")
                    return measurements
                else:
                    logger.error(f"Measurements request failed: {data.get('msg')}")
                    return []
            else:
                logger.error(f"Measurements request failed: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting measurements: {e}")
            return []
    
    def process_measurements(self, raw_measurements: List[Dict]) -> List[Dict]:
        """Process raw Eufy measurements into standardized format"""
        processed_data = []
        
        for measurement in raw_measurements:
            try:
                # Convert timestamp to datetime
                timestamp_ms = measurement.get('timestamp', 0)
                measurement_datetime = datetime.fromtimestamp(timestamp_ms / 1000)
                
                # Extract measurement data
                data = measurement.get('data', {})
                
                processed_measurement = {
                    'date': measurement_datetime.date().isoformat(),
                    'time': measurement_datetime.time().strftime('%H:%M:%S'),
                    'timestamp': measurement_datetime.isoformat(),
                    
                    # Basic measurements
                    'weight_kg': data.get('weight', 0) / 100 if data.get('weight') else None,  # Convert from grams
                    'bmi': data.get('bmi', 0) / 10 if data.get('bmi') else None,  # Convert from tenths
                    
                    # Body composition
                    'body_fat_percent': data.get('body_fat', 0) / 10 if data.get('body_fat') else None,
                    'muscle_mass_kg': data.get('muscle_mass', 0) / 100 if data.get('muscle_mass') else None,
                    'bone_mass_kg': data.get('bone_mass', 0) / 100 if data.get('bone_mass') else None,
                    'body_water_percent': data.get('body_water', 0) / 10 if data.get('body_water') else None,
                    'visceral_fat_level': data.get('visceral_fat'),
                    'protein_percent': data.get('protein', 0) / 10 if data.get('protein') else None,
                    'subcutaneous_fat_percent': data.get('subcutaneous_fat', 0) / 10 if data.get('subcutaneous_fat') else None,
                    
                    # Derived metrics
                    'basal_metabolic_rate': data.get('bmr'),
                    'metabolic_age': data.get('metabolic_age'),
                    'body_type_score': data.get('body_type'),
                    'skeletal_muscle_mass_kg': data.get('skeletal_muscle', 0) / 100 if data.get('skeletal_muscle') else None,
                    
                    # Metadata
                    'measurement_source': 'eufy_p3_auto',
                    'scale_model': 'P3',
                    'user_profile': measurement.get('user_id', 'unknown'),
                    'measurement_quality': self._assess_measurement_quality(data)
                }
                
                processed_data.append(processed_measurement)
                
            except Exception as e:
                logger.warning(f"Error processing measurement: {e}")
                continue
        
        return processed_data
    
    def _assess_measurement_quality(self, data: Dict) -> str:
        """Assess the quality of a measurement based on completeness"""
        total_fields = 12  # Expected number of body composition fields
        present_fields = sum(1 for key in ['weight', 'body_fat', 'muscle_mass', 'bone_mass',
                                         'body_water', 'visceral_fat', 'protein', 'subcutaneous_fat',
                                         'bmr', 'metabolic_age', 'skeletal_muscle', 'bmi']
                           if data.get(key) is not None)
        
        quality_percentage = (present_fields / total_fields) * 100
        
        if quality_percentage >= 90:
            return 'excellent'
        elif quality_percentage >= 75:
            return 'good'
        elif quality_percentage >= 50:
            return 'fair'
        else:
            return 'poor'
    
    def collect_daily_data(self, days_back: int = 30) -> List[Dict]:
        """Main method to collect Eufy data for the past N days"""
        logger.info(f"⚖️  Collecting Eufy P3 data for the past {days_back} days")
        
        # Authenticate
        if not self.authenticate():
            logger.error("Failed to authenticate with Eufy Life")
            return []
        
        # Get devices
        devices = self.get_devices()
        if not devices:
            logger.error("No Eufy scales found")
            return []
        
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days_back)
        
        # Get measurements
        raw_measurements = self.get_measurements(start_date, end_date)
        if not raw_measurements:
            logger.info("No measurements found in date range")
            return []
        
        # Process measurements
        processed_data = self.process_measurements(raw_measurements)
        
        logger.info(f"✅ Processed {len(processed_data)} Eufy measurements")
        return processed_data


def collect_eufy_data(email: str, password: str, days_back: int = 30) -> List[Dict]:
    """Main function to collect Eufy P3 data"""
    if not email or not password:
        logger.warning("Eufy credentials not provided, skipping body composition collection")
        return []
    
    try:
        collector = EufyP3Collector(email, password)
        return collector.collect_daily_data(days_back)
    except Exception as e:
        logger.error(f"Eufy data collection failed: {e}")
        return []


if __name__ == "__main__":
    # Test script
    import os
    
    email = os.getenv('EUFY_EMAIL')
    password = os.getenv('EUFY_PASSWORD')
    
    if not email or not password:
        print("Please set EUFY_EMAIL and EUFY_PASSWORD environment variables")
        exit(1)
    
    logging.basicConfig(level=logging.INFO)
    data = collect_eufy_data(email, password, days_back=7)
    
    print(f"Collected {len(data)} measurements:")
    for measurement in data[-3:]:  # Show last 3 measurements
        print(f"  {measurement['date']}: {measurement['weight_kg']}kg, {measurement['body_fat_percent']}% BF")