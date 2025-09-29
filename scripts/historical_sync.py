#!/usr/bin/env python3
"""
Historical data sync script for comprehensive re-collection of Garmin data

This script re-collects all historical data using the new activity-type-specific structure.
Run this after implementing the new data pipeline to get complete historical dataset.
"""

import os
import sys
from datetime import date, timedelta
import logging
import time

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from garmin_client import GarminDataClient
from data_processor import GarminDataProcessor
from csv_manager import CSVManager
from rate_limit_manager import GarminRateLimitManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HistoricalDataCollector:
    def __init__(self):
        self.client = GarminDataClient()
        self.processor = GarminDataProcessor()
        self.csv_manager = CSVManager()
        self.rate_manager = GarminRateLimitManager()
    
    def authenticate(self):
        """Authenticate with Garmin Connect"""
        email = os.getenv('GARMIN_EMAIL')
        password = os.getenv('GARMIN_PASSWORD')
        
        if not email or password:
            logger.error("GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")
            return False
        
        return self.client.authenticate(email, password)
    
    def collect_historical_activities(self, months_back=6):
        """Re-collect all historical activity data with new structure"""
        end_date = date.today()
        start_date = end_date - timedelta(days=months_back * 30)
        
        logger.info(f"🔄 Historical activity sync: {start_date} to {end_date} ({months_back} months)")
        
        total_activities_processed = 0
        
        # Process in weekly batches to manage rate limits
        current_date = start_date
        week_count = 0
        
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            week_count += 1
            
            logger.info(f"📅 Week {week_count}: {current_date} to {week_end}")
            
            try:
                # Check rate limits before making requests
                self.rate_manager.wait_if_needed()
                
                # Get activities for this week
                activities = self.client.get_activities_daterange(current_date, week_end)
                
                if activities:
                    # Process with enhanced details
                    activity_datasets = self.processor.process_activities_by_type(activities, self.client)
                    
                    # Save to CSV files
                    week_records = self.csv_manager.append_activities_by_type(activity_datasets)
                    total_activities_processed += week_records
                    
                    logger.info(f"  ✅ Processed {week_records} activities this week")
                    
                    # Log progress every 4 weeks
                    if week_count % 4 == 0:
                        logger.info(f"📊 Progress: {total_activities_processed} total activities processed after {week_count} weeks")
                
                # Rate limiting between weeks
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing week {current_date} to {week_end}: {e}")
                # Continue with next week on error
            
            current_date = week_end + timedelta(days=1)
        
        logger.info(f"🎉 Historical activity sync complete: {total_activities_processed} activities processed")
        return total_activities_processed
    
    def collect_historical_health_data(self, months_back=6):
        """Re-collect all historical health data"""
        end_date = date.today()
        start_date = end_date - timedelta(days=months_back * 30)
        
        logger.info(f"💤 Historical health sync: {start_date} to {end_date}")
        
        health_data_batch = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                # Rate limiting
                if len(health_data_batch) % 10 == 0:  # Every 10 days
                    self.rate_manager.wait_if_needed()
                
                health_data = self.client.get_daily_health_metrics(current_date)
                if health_data:
                    is_current_day = (current_date == date.today())
                    processed_health = self.processor.process_daily_health(health_data, is_current_day)
                    health_data_batch.append(processed_health)
                
                current_date += timedelta(days=1)
                
            except Exception as e:
                logger.warning(f"Failed to get health data for {current_date}: {e}")
                current_date += timedelta(days=1)
        
        # Save all health data
        health_records = self.csv_manager.append_to_csv(
            health_data_batch, 
            "daily_metrics.csv", 
            "health"
        )
        
        logger.info(f"💤 Historical health sync complete: {health_records} records processed")
        return health_records
    
    def collect_historical_physiological_data(self, months_back=6):
        """Re-collect all historical physiological data"""
        end_date = date.today()
        start_date = end_date - timedelta(days=months_back * 30)
        
        logger.info(f"📊 Historical physiological sync: {start_date} to {end_date}")
        
        phys_data_batch = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                # Rate limiting
                if len(phys_data_batch) % 10 == 0:
                    self.rate_manager.wait_if_needed()
                
                phys_data = self.client.get_physiological_metrics(current_date)
                if phys_data:
                    processed_phys = self.processor.process_physiological_metrics(phys_data)
                    phys_data_batch.append(processed_phys)
                
                current_date += timedelta(days=1)
                
            except Exception as e:
                logger.warning(f"Failed to get physiological data for {current_date}: {e}")
                current_date += timedelta(days=1)
        
        # Save all physiological data
        phys_records = self.csv_manager.append_to_csv(
            phys_data_batch, 
            "vo2_training_status.csv", 
            "physiological"
        )
        
        logger.info(f"📊 Historical physiological sync complete: {phys_records} records processed")
        return phys_records
    
    def clean_legacy_data(self):
        """Clean up old data files before historical sync"""
        logger.info("🧹 Cleaning up legacy data files...")
        removed_files = self.csv_manager.clean_legacy_activity_data()
        
        for filepath in removed_files:
            logger.info(f"  Backed up: {filepath}")
        
        return len(removed_files)
    
    def full_historical_sync(self, months_back=6, clean_legacy=True):
        """Complete historical data re-collection"""
        logger.info(f"🚀 Starting full historical sync ({months_back} months back)")
        
        # Authenticate first
        if not self.authenticate():
            logger.error("Authentication failed")
            return False
        
        # Clean legacy data if requested
        if clean_legacy:
            self.clean_legacy_data()
        
        try:
            # Collect all data types
            activity_records = self.collect_historical_activities(months_back)
            health_records = self.collect_historical_health_data(months_back)
            phys_records = self.collect_historical_physiological_data(months_back)
            
            total_records = activity_records + health_records + phys_records
            
            logger.info(f"🎉 Full historical sync complete!")
            logger.info(f"📊 Total records: {total_records}")
            logger.info(f"   Activities: {activity_records}")
            logger.info(f"   Health: {health_records}")
            logger.info(f"   Physiological: {phys_records}")
            
            # Show activity breakdown
            activity_summary = self.csv_manager.get_activity_summary()
            logger.info("🏃‍♂️ Activity breakdown:")
            for activity_type, summary in activity_summary.items():
                if 'total_activities' in summary and summary['total_activities'] > 0:
                    logger.info(f"   {activity_type.title()}: {summary['total_activities']} activities")
            
            return True
            
        except Exception as e:
            logger.error(f"Historical sync failed: {e}")
            return False

def main():
    """Main function for running historical sync"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Historical Garmin data sync')
    parser.add_argument('--months', type=int, default=6, 
                        help='Number of months to sync back (default: 6)')
    parser.add_argument('--no-clean', action='store_true', 
                        help='Skip cleaning legacy data files')
    parser.add_argument('--activities-only', action='store_true',
                        help='Only sync activities (skip health and physiological)')
    
    args = parser.parse_args()
    
    collector = HistoricalDataCollector()
    
    if args.activities_only:
        logger.info("🏃‍♂️ Activities-only sync mode")
        if collector.authenticate():
            if not args.no_clean:
                collector.clean_legacy_data()
            collector.collect_historical_activities(args.months)
    else:
        # Full sync
        success = collector.full_historical_sync(
            months_back=args.months,
            clean_legacy=not args.no_clean
        )
        
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()