#!/usr/bin/env python3
"""
Main data collection script for comprehensive fitness data pipeline

Enhanced daily sync approach:
- Collects data from the past 30 days on first run (historical processing)
- Collects data from the past 14 days on subsequent runs
- CSV manager handles duplicate detection and data updates
- Includes automated Eufy P3 body composition sync
"""

import os
import sys
from datetime import date, timedelta
import logging
import pandas as pd

# Add project root to Python path (CRITICAL for GitHub Actions)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from garmin_client import GarminDataClient
from data_processor import GarminDataProcessor
from csv_manager import CSVManager
from telegram_collector import collect_telegram_data
from eufy_collector import collect_eufy_data  # NEW

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_first_run(csv_manager: CSVManager) -> bool:
    """Check if this is the first run by looking for existing data"""
    try:
        # Check if we have any recent health data
        health_file = csv_manager.data_dir / "health" / "daily_metrics.csv"
        if health_file.exists():
            df = pd.read_csv(health_file)
            if len(df) > 0:
                # Check if we have data from the last week
                most_recent = pd.to_datetime(df['date']).max()
                days_since_recent = (pd.Timestamp.now() - most_recent).days
                return days_since_recent > 7
        return True
    except:
        return True

def main():
    # Get credentials from environment variables
    garmin_email = os.getenv('GARMIN_EMAIL')
    garmin_password = os.getenv('GARMIN_PASSWORD')
    eufy_email = os.getenv('EUFY_EMAIL')
    eufy_password = os.getenv('EUFY_PASSWORD')
    
    if not garmin_email or not garmin_password:
        logger.error("GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")
        sys.exit(1)
    
    # Initialize components
    client = GarminDataClient()
    processor = GarminDataProcessor()
    csv_manager = CSVManager()
    
    # Authenticate with Garmin
    if not client.authenticate(garmin_email, garmin_password):
        logger.error("Failed to authenticate with Garmin Connect")
        sys.exit(1)
    
    # Determine if this is first run (historical processing)
    first_run = is_first_run(csv_manager)
    days_back = 30 if first_run else 14
    
    today = date.today()
    sync_start = today - timedelta(days=days_back)
    
    if first_run:
        logger.info(f"🚀 First run detected: Historical processing from {sync_start} to {today} ({days_back} days)")
    else:
        logger.info(f"🔄 Daily sync: Collecting data from {sync_start} to {today} ({days_back}-day window)")
    
    try:
        total_records = 0
        
        # 1. Sync Garmin activity data by type
        logger.info(f"🏃‍♂️ Syncing Garmin activities from {sync_start} to {today}")
        activities = client.get_activities_daterange(sync_start, today)
        
        # Process activities by type with enhanced details
        activity_datasets = processor.process_activities_by_type(activities, client)
        activity_records = csv_manager.append_activities_by_type(activity_datasets)
        csv_manager.log_sync("activities", today, activity_records, "success")
        total_records += activity_records
        
        # 2. Sync Garmin daily health metrics
        logger.info(f"💤 Syncing Garmin health metrics from {sync_start} to {today}")
        health_data_batch = []
        current_date = sync_start
        while current_date <= today:
            health_data = client.get_daily_health_metrics(current_date)
            if health_data:
                is_current_day = (current_date == today)
                processed_health = processor.process_daily_health(health_data, is_current_day)
                health_data_batch.append(processed_health)
            current_date += timedelta(days=1)
        
        health_records = csv_manager.append_to_csv(
            health_data_batch, 
            "daily_metrics.csv", 
            "health"
        )
        csv_manager.log_sync("health", today, health_records, "success")
        total_records += health_records
        
        # 3. Sync Garmin physiological metrics
        logger.info(f"📊 Syncing Garmin physiological metrics from {sync_start} to {today}")
        phys_data_batch = []
        current_date = sync_start
        while current_date <= today:
            phys_data = client.get_physiological_metrics(current_date)
            if phys_data:
                processed_phys = processor.process_physiological_metrics(phys_data)
                phys_data_batch.append(processed_phys)
            current_date += timedelta(days=1)
        
        phys_records = csv_manager.append_to_csv(
            phys_data_batch, 
            "vo2_training_status.csv", 
            "physiological"
        )
        csv_manager.log_sync("physiological", today, phys_records, "success")
        total_records += phys_records
        
        # 4. NEW: Sync Eufy P3 body composition data
        logger.info(f"⚖️  Syncing Eufy P3 body composition data...")
        eufy_records = 0
        try:
            if eufy_email and eufy_password:
                eufy_data = collect_eufy_data(eufy_email, eufy_password, days_back)
                eufy_records = csv_manager.append_body_composition_data(eufy_data)
                csv_manager.log_sync("eufy_body_composition", today, eufy_records, "success")
                logger.info(f"✅ Processed {eufy_records} Eufy body composition records")
            else:
                logger.info("⚖️  Eufy credentials not found, skipping body composition data collection")
        except Exception as e:
            logger.error(f"Failed to sync Eufy data: {e}")
            csv_manager.log_sync("eufy_body_composition", today, 0, "failed", str(e))
        
        total_records += eufy_records
        
        # 5. Sync weekly training zones
        logger.info("🎯 Syncing weekly training zone distribution")
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        zone_records = 0
        weekly_zone_data = client.get_weekly_training_zones(week_start, week_end)
        if weekly_zone_data:
            processed_zones = processor.process_weekly_training_zones(weekly_zone_data)
            zone_records = csv_manager.append_weekly_training_zones([processed_zones])
            csv_manager.log_sync("weekly_training_zones", today, zone_records, "success")
        total_records += zone_records
        
        # 6. Sync recovery trends
        logger.info("📈 Syncing recovery trends")
        recovery_records = 0
        health_history = csv_manager.get_health_history(30)
        if health_history and len(health_history) >= 7:
            recovery_data = {'date': today.isoformat()}
            processed_recovery = processor.process_recovery_trends(recovery_data, health_history)
            recovery_records = csv_manager.append_recovery_trends([processed_recovery])
            csv_manager.log_sync("recovery_trends", today, recovery_records, "success")
        else:
            logger.info("Insufficient historical data for recovery trends (need 7+ days)")
        total_records += recovery_records
        
        # 7. GitHub coding activity sync (if enabled)
        logger.info("🐙 Syncing GitHub coding activity data...")
        github_records = 0
        try:
            github_username = os.getenv('_GITHUB_USERNAME')
            github_token = os.getenv('_GITHUB_TOKEN')
            
            if github_username and github_token:
                from github_collector import collect_github_activity
                github_data = collect_github_activity(github_username, github_token)
                github_records = csv_manager.append_coding_activity_data(github_data)
                csv_manager.log_sync("github_data", today, github_records, "success")
                logger.info(f"✅ Processed {github_records} GitHub activity records")
            else:
                logger.info("🐙 GitHub credentials not found, skipping GitHub data collection")
        except Exception as e:
            logger.error(f"Failed to sync GitHub data: {e}")
            csv_manager.log_sync("github_data", today, 0, "failed", str(e))
        
        total_records += github_records
        
        # 8. Telegram subjective data (if enabled)
        logger.info("📱 Syncing Telegram subjective data...")
        telegram_records = 0
        try:
            telegram_data = collect_telegram_data(os.getenv('TELEGRAM_BOT_TOKEN'))
            
            # Save each data type to appropriate CSV
            ratings_records = csv_manager.append_to_csv(telegram_data['ratings'], "daily_ratings.csv", "subjective")
            caffeine_records = csv_manager.append_to_csv(telegram_data['caffeine'], "caffeine_intake.csv", "subjective") 
            alcohol_records = csv_manager.append_to_csv(telegram_data['alcohol'], "alcohol_intake.csv", "subjective")
            supplement_records = csv_manager.append_to_csv(telegram_data['supplements'], "supplement_intake.csv", "subjective")  # Changed from thc
            food_records = csv_manager.append_to_csv(telegram_data['food'], "food_intake.csv", "subjective")
            notes_records = csv_manager.append_to_csv(telegram_data['notes'], "daily_notes.csv", "subjective")
            
            telegram_records = ratings_records + caffeine_records + alcohol_records + supplement_records + food_records + notes_records
            
            if telegram_records > 0:
                logger.info(f"✅ Processed {telegram_records} Telegram records: {ratings_records} ratings, {caffeine_records} caffeine, {alcohol_records} alcohol, {supplement_records} supplements, {food_records} food, {notes_records} notes")
                csv_manager.log_sync("telegram_data", today, telegram_records, "success")
            else:
                logger.info("📱 No new Telegram messages found")
                
        except Exception as e:
            logger.error(f"Failed to sync Telegram data: {e}")
            csv_manager.log_sync("telegram_data", today, 0, "failed", str(e))
        
        total_records += telegram_records
        
        # Summary
        success_msg = f"✅ Data sync completed successfully! Total records processed: {total_records}"
        if first_run:
            success_msg += " (Historical data collection complete)"
        logger.info(success_msg)
        
        logger.info(f"📊 Breakdown: Activities: {activity_records}, Health: {health_records}, "
                   f"Physiological: {phys_records}, Body Composition: {eufy_records}, "
                   f"Training Zones: {zone_records}, Recovery: {recovery_records}, "
                   f"GitHub: {github_records}, Telegram: {telegram_records}")
        
        # Log activity type breakdown
        activity_summary = csv_manager.get_activity_summary()
        logger.info("🏃‍♂️ Activity breakdown:")
        for activity_type, summary in activity_summary.items():
            if 'total_activities' in summary and summary['total_activities'] > 0:
                logger.info(f"  {activity_type.title()}: {summary['total_activities']} activities")
        
    except Exception as e:
        logger.error(f"Data sync failed: {e}")
        csv_manager.log_sync("all", today, 0, "failed", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()