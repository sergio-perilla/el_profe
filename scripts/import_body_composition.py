#!/usr/bin/env python3
"""
Body composition data import script for Eufy Smart Scale data

This script imports body composition data from Eufy Life app CSV exports.
Export process: EufyLife app > Settings > Privacy and Data > Export All Data
"""

import os
import sys
import pandas as pd
from datetime import datetime
import logging

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from csv_manager import CSVManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BodyCompositionImporter:
    def __init__(self):
        self.csv_manager = CSVManager()
    
    def parse_eufy_export(self, csv_file_path):
        """Parse Eufy Life app CSV export"""
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file_path)
            
            # Log the columns found
            logger.info(f"CSV columns found: {list(df.columns)}")
            
            # Map Eufy columns to our schema (may need adjustment based on actual export format)
            column_mapping = {
                'Timestamp': 'timestamp',
                'Weight': 'weight_kg',
                'BMI': 'bmi',
                'Body Fat': 'body_fat_percent',
                'Body Fat Mass': 'body_fat_mass_kg',
                'Muscle Mass': 'muscle_mass_kg',
                'Bone Mass': 'bone_mass_kg',
                'Body Water': 'body_water_percent',
                'Visceral Fat': 'visceral_fat_level',
                'Metabolic Age': 'metabolic_age',
                'Protein': 'protein_percent',
                'Subcutaneous Fat': 'subcutaneous_fat_percent',
                'Skeletal Muscle Mass': 'skeletal_muscle_mass_kg',
                'BMR': 'basal_metabolic_rate',
                'Body Type': 'body_type'
            }
            
            # Rename columns
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
            
            # Process timestamps
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['date'] = df['timestamp'].dt.date.astype(str)
                df['time'] = df['timestamp'].dt.time.astype(str)
            else:
                logger.warning("No timestamp column found, using current date")
                df['date'] = datetime.now().date().isoformat()
                df['time'] = datetime.now().time().strftime('%H:%M:%S')
            
            # Add measurement source
            df['measurement_source'] = 'eufy_scale'
            
            # Select only the columns we want
            from config.data_schema import BODY_COMPOSITION_COLUMNS
            
            processed_data = []
            for _, row in df.iterrows():
                record = {}
                for col in BODY_COMPOSITION_COLUMNS:
                    record[col] = row.get(col)
                processed_data.append(record)
            
            logger.info(f"Processed {len(processed_data)} body composition records")
            return processed_data
            
        except Exception as e:
            logger.error(f"Error parsing Eufy CSV: {e}")
            return []
    
    def import_from_csv(self, csv_file_path):
        """Import body composition data from CSV file"""
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found: {csv_file_path}")
            return False
        
        logger.info(f"Importing body composition data from: {csv_file_path}")
        
        # Parse the data
        body_data = self.parse_eufy_export(csv_file_path)
        
        if not body_data:
            logger.error("No data to import")
            return False
        
        # Save to CSV
        records_added = self.csv_manager.append_body_composition_data(body_data)
        
        if records_added > 0:
            logger.info(f"✅ Successfully imported {records_added} body composition records")
            return True
        else:
            logger.warning("No new records were added (might be duplicates)")
            return False
    
    def validate_data(self, csv_file_path):
        """Validate the structure of the CSV file"""
        try:
            df = pd.read_csv(csv_file_path)
            
            logger.info("📊 CSV File Validation:")
            logger.info(f"  Total rows: {len(df)}")
            logger.info(f"  Columns ({len(df.columns)}): {list(df.columns)}")
            
            # Show sample data
            if len(df) > 0:
                logger.info("📋 Sample data (first row):")
                for col in df.columns:
                    value = df.iloc[0][col]
                    logger.info(f"  {col}: {value}")
            
            # Check for required fields
            required_fields = ['Weight', 'Timestamp']  # Minimum required
            missing_fields = []
            for field in required_fields:
                if field not in df.columns:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"⚠️  Missing recommended fields: {missing_fields}")
            else:
                logger.info("✅ All minimum required fields present")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating CSV: {e}")
            return False
    
    def get_import_instructions(self):
        """Print instructions for exporting data from Eufy Life app"""
        instructions = """
📱 HOW TO EXPORT DATA FROM EUFY LIFE APP:

1. Open the EufyLife app on your phone
2. Go to Settings (usually gear icon)
3. Find "Privacy and Data" or "Data Export" section
4. Select "Export All Data"
5. Enter your password and email address
6. Check your email for the CSV file
7. Save the CSV file and run this script

📋 ALTERNATIVE METHOD (if export not available):
- Use the Android backup method described here:
  https://www.stcase.dev/blog/exporting-eufy-smart-scale-data/

⚠️  NOTE: The CSV column names may vary. Run with --validate first
to check the format of your export file.
        """
        print(instructions)

def main():
    """Main function for importing body composition data"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import body composition data from Eufy scale')
    parser.add_argument('csv_file', nargs='?', help='Path to Eufy CSV export file')
    parser.add_argument('--validate', action='store_true', 
                        help='Only validate the CSV structure without importing')
    parser.add_argument('--instructions', action='store_true',
                        help='Show export instructions for Eufy Life app')
    
    args = parser.parse_args()
    
    importer = BodyCompositionImporter()
    
    if args.instructions:
        importer.get_import_instructions()
        return
    
    if not args.csv_file:
        print("Error: Please provide path to CSV file")
        print("Use --instructions to see how to export data from Eufy Life app")
        sys.exit(1)
    
    if args.validate:
        # Just validate the file structure
        success = importer.validate_data(args.csv_file)
        if success:
            print("\n✅ CSV structure looks good! Run without --validate to import the data.")
    else:
        # Import the data
        success = importer.import_from_csv(args.csv_file)
        if not success:
            print("\n❌ Import failed. Try running with --validate to check file structure.")
            sys.exit(1)
        else:
            print("\n🎉 Body composition data imported successfully!")

if __name__ == "__main__":
    main()