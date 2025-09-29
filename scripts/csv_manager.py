import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CSVManager:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.ensure_directories()
    

    def ensure_directories(self):
            """Create directory structure if it doesn't exist"""
            (self.data_dir / "activities").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "health").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "physiological").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "training_zones").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "recovery_trends").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "breathing").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "subjective").mkdir(parents=True, exist_ok=True) 
            (self.data_dir / "lifestyle").mkdir(parents=True, exist_ok=True)
            (self.data_dir / "body_composition").mkdir(parents=True, exist_ok=True)  # NEW
            (self.data_dir / "metadata").mkdir(parents=True, exist_ok=True)

    def append_to_csv(self, data, filename, subdir=None):
        """Append new data to CSV, updating existing records and avoiding duplicates"""
        if not data:
            return 0
            
        if subdir:
            filepath = self.data_dir / subdir / filename
        else:
            filepath = self.data_dir / filename
        
        df_new = pd.DataFrame(data)
        
        if filepath.exists():
            df_existing = pd.read_csv(filepath)
            existing_count = len(df_existing)
            
            # Determine key columns for merging/updating
            if 'activity_id' in df_new.columns:
                # For activities, use date + activity_id as key
                key_cols = ['date', 'activity_id']
            elif 'week_start_date' in df_new.columns:
                # For weekly data, use week_start_date as key
                key_cols = ['week_start_date']
            elif 'date' in df_new.columns:
                # For daily metrics, use date as key
                key_cols = ['date']
            else:
                # Fall back to simple concatenation and deduplication
                df_combined = pd.concat([df_existing, df_new])
                # Remove exact duplicates
                df_combined = df_combined.drop_duplicates()
                df_combined = df_combined.sort_values('date' if 'date' in df_combined.columns else df_combined.columns[0]).reset_index(drop=True)
                df_combined.to_csv(filepath, index=False)
                return len(df_combined) - existing_count
                # Fall back to simple concatenation
                df_combined = pd.concat([df_existing, df_new])
                df_combined = df_combined.sort_values('date' if 'date' in df_combined.columns else df_combined.columns[0]).reset_index(drop=True)
                df_combined.to_csv(filepath, index=False)
                return len(df_combined) - existing_count
            
            # Update existing records and add new ones
            # First, identify which records are updates vs new
            df_merged = df_existing.set_index(key_cols)
            df_new_indexed = df_new.set_index(key_cols)
            
            # Update existing records with new data
            df_merged.update(df_new_indexed)
            
            # Add completely new records
            new_records_mask = ~df_new_indexed.index.isin(df_merged.index)
            df_new_records = df_new_indexed[new_records_mask]
            
            # Combine updated existing + new records
            df_combined = pd.concat([df_merged, df_new_records]).reset_index()
            
        else:
            df_combined = df_new
            existing_count = 0
        
        # Sort by date field if it exists
        if 'date' in df_combined.columns:
            df_combined = df_combined.sort_values('date').reset_index(drop=True)
        elif 'week_start_date' in df_combined.columns:
            df_combined = df_combined.sort_values('week_start_date').reset_index(drop=True)
        else:
            df_combined = df_combined.reset_index(drop=True)
            
        df_combined.to_csv(filepath, index=False)
        
        new_records = len(df_combined) - existing_count
        logger.info(f"Updated {filepath}: {new_records} net new/updated records")
        return new_records
    
    def get_last_sync_date(self, data_type):
        """Get the last date we successfully synced data"""
        sync_log = self.data_dir / "metadata" / "sync_log.csv"
        if sync_log.exists():
            df = pd.read_csv(sync_log)
            filtered = df[df['data_type'] == data_type]
            if not filtered.empty:
                last_sync = filtered['last_sync_date'].max()
                return pd.to_datetime(last_sync).date() if pd.notna(last_sync) else None
        return None
    
    def log_sync(self, data_type, last_sync_date, records_added, status, error_message=None):
        """Log sync operation results"""
        sync_log = self.data_dir / "metadata" / "sync_log.csv"
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'data_type': data_type,
            'last_sync_date': last_sync_date.isoformat() if last_sync_date else None,
            'records_added': records_added,
            'status': status,
            'error_message': error_message
        }
        
        if sync_log.exists():
            df = pd.read_csv(sync_log)
            df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        else:
            df = pd.DataFrame([log_entry])
        
        df.to_csv(sync_log, index=False)
    
    def append_weekly_training_zones(self, data):
        """Append weekly training zone data"""
        if not data:
            return 0
        return self.append_to_csv(data, "weekly_training_zones.csv", "training_zones")
    
    def append_recovery_trends(self, data):
        """Append recovery trends data"""
        if not data:
            return 0
        return self.append_to_csv(data, "recovery_trends.csv", "recovery_trends")
    
    def get_health_history(self, days=30):
        """Get health data history for trend calculations"""
        try:
            health_file = self.data_dir / "health" / "daily_metrics.csv"
            if health_file.exists():
                df = pd.read_csv(health_file)
                df = df.sort_values('date').tail(days)
                return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error reading health history: {e}")
        return []

    def append_activities_by_type(self, activity_datasets):
            """Save activities to type-specific CSV files"""
            from config.data_schema import ACTIVITY_TYPE_MAPPING
            
            total_records_added = 0
            
            for activity_type, activities in activity_datasets.items():
                if not activities:
                    continue
                
                try:
                    # Get filename and columns for this activity type
                    if activity_type in ACTIVITY_TYPE_MAPPING:
                        filename, expected_columns = ACTIVITY_TYPE_MAPPING[activity_type]
                        
                        # Ensure all activities have all expected columns
                        normalized_activities = []
                        for activity in activities:
                            normalized_activity = {}
                            for col in expected_columns:
                                normalized_activity[col] = activity.get(col)
                            normalized_activities.append(normalized_activity)
                        
                        # Save to CSV
                        records_added = self.append_to_csv(
                            normalized_activities, 
                            filename, 
                            "activities"
                        )
                        total_records_added += records_added
                        
                        logger.info(f"Added {records_added} {activity_type} activities to {filename}")
                        
                    else:
                        logger.warning(f"Unknown activity type: {activity_type}")
                        
                except Exception as e:
                    logger.error(f"Error saving {activity_type} activities: {e}")
            
            return total_records_added
    
    def append_body_composition_data(self, body_data):
        """Append body composition data from Eufy scale"""
        if not body_data:
            return 0
        return self.append_to_csv(body_data, "daily_body_metrics.csv", "body_composition")
    
    def append_coding_activity_data(self, coding_data):
        """Append GitHub coding activity data"""
        if not coding_data:
            return 0
        return self.append_to_csv(coding_data, "daily_coding_metrics.csv", "lifestyle")
    
    def get_activity_summary(self):
        """Get summary of all activity data"""
        from config.data_schema import ACTIVITY_TYPE_MAPPING
        
        summary = {}
        
        for activity_type, (filename, _) in ACTIVITY_TYPE_MAPPING.items():
            filepath = self.data_dir / "activities" / filename
            
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath)
                    summary[activity_type] = {
                        'total_activities': len(df),
                        'date_range': f"{df['date'].min()} to {df['date'].max()}" if not df.empty else "No data",
                        'latest_activity': df['date'].max() if not df.empty else None
                    }
                except Exception as e:
                    summary[activity_type] = {'error': str(e)}
        
        return summary
    
    def clean_legacy_activity_data(self):
        """Remove old single activities.csv and breathing_activities.csv files"""
        legacy_files = [
            self.data_dir / "activities" / "activities.csv",
            self.data_dir / "breathing" / "breathing_activities.csv"
        ]
        
        removed_files = []
        for filepath in legacy_files:
            if filepath.exists():
                try:
                    # Create backup before deleting
                    backup_path = filepath.with_suffix('.csv.backup')
                    filepath.rename(backup_path)
                    removed_files.append(str(filepath))
                    logger.info(f"Backed up legacy file: {filepath} -> {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup legacy file {filepath}: {e}")
        
        return removed_files
