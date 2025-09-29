import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GarminDataProcessor:
    def __init__(self):
        self.surf_relevant_activities = [
            'swimming', 'pool_swimming', 'open_water_swimming',
            'surfing', 'sup', 'kayaking', 'running', 'cardio',
            'strength_training', 'yoga', 'breathwork', 'cycling'
        ]
    
    def process_activities_by_type(self, raw_activities, client=None):
            """Transform activities into type-specific datasets"""
            activity_datasets = {
                'surfing': [],
                'swimming': [],
                'running': [],
                'strength': [],
                'breathwork': [],
                'recovery': []
            }
            
            for activity in raw_activities:
                try:
                    # Determine activity type
                    activity_type = self._categorize_activity(activity)
                    
                    if activity_type == 'other':
                        logger.debug(f"Skipping uncategorized activity: {activity.get('activityType', {}).get('typeKey', 'unknown')}")
                        continue
                    
                    # Get enhanced activity details if client is provided
                    if client:
                        activity_id = activity.get('activityId')
                        type_key = activity.get('activityType', {}).get('typeKey', '')
                        enhanced_activity = client.get_activity_details_by_type(activity_id, type_key)
                        if enhanced_activity:
                            activity.update(enhanced_activity)
                    
                    # Process based on type
                    processed = self._process_by_type(activity, activity_type)
                    if processed:
                        activity_datasets[activity_type].append(processed)
                        
                except Exception as e:
                    logger.error(f"Error processing activity {activity.get('activityId')}: {e}")
            
            # Log summary
            for activity_type, activities in activity_datasets.items():
                if activities:
                    logger.info(f"Processed {len(activities)} {activity_type} activities")
            
            return activity_datasets

    def _categorize_activity(self, activity):
        """Determine which category this activity belongs to"""
        type_key = activity.get('activityType', {}).get('typeKey', '').lower()
        activity_name = activity.get('activityName', '').lower()
        
        # Surfing
        if 'surfing' in type_key or 'sup' in type_key:
            return 'surfing'
        
        # Swimming (pool and open water)
        elif any(swim_type in type_key for swim_type in ['swimming', 'pool_swim', 'open_water']):
            return 'swimming'
        
        # Running (treadmill and outdoor)
        elif 'running' in type_key or 'treadmill' in type_key:
            return 'running'
        
        # Strength training
        elif any(strength_type in type_key for strength_type in ['strength', 'weight', 'bodyweight']):
            return 'strength'
        
        # Breathwork and wellness
        elif any(breath_type in type_key or breath_type in activity_name 
                for breath_type in ['breathwork', 'breathing', 'meditation', 'whm', 'yoga', 'wellness']):
            return 'breathwork'
        
        # Recovery activities (sauna, steam, etc.)
        elif any(recovery_type in type_key or recovery_type in activity_name 
                for recovery_type in ['sauna', 'steam', 'ice_bath', 'recovery']):
            return 'recovery'
        
        else:
            return 'other'

    def _process_by_type(self, activity, activity_type):
        """Process activity data based on its type"""
        try:
            if activity_type == 'surfing':
                return self._process_surfing_activity(activity)
            elif activity_type == 'swimming':
                return self._process_swimming_activity(activity)
            elif activity_type == 'running':
                return self._process_running_activity(activity)
            elif activity_type == 'strength':
                return self._process_strength_activity(activity)
            elif activity_type == 'breathwork':
                return self._process_breathwork_activity(activity)
            elif activity_type == 'recovery':
                return self._process_recovery_activity(activity)
            else:
                return None
        except Exception as e:
            logger.error(f"Error processing {activity_type} activity: {e}")
            return None
    
    def _process_surfing_activity(self, activity):
        """Process surfing-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add surfing-specific fields
        processed.update({
            'distance_meters': activity.get('distance', 0),
            'max_speed_kmh': activity.get('max_speed_kmh') or activity.get('maxSpeed'),
            'avg_speed_kmh': activity.get('avg_speed_kmh') or activity.get('avgSpeed'),
            'total_waves': activity.get('total_waves'),
            'longest_wave_seconds': activity.get('longest_wave_seconds'),
            'total_surf_time_seconds': activity.get('total_surf_time_seconds'),
            'paddle_time_seconds': activity.get('paddle_time_seconds'),
            'avg_wave_speed': None,  # Calculate if we have data
            'avg_wave_distance': None,  # Calculate if we have data
            'wave_frequency_per_hour': None,  # Calculate if we have data
            'surf_vs_paddle_ratio': None,  # Calculate if we have data
            'session_rating': None  # Could be added from subjective data later
        })
        
        # Calculate derived metrics
        duration_hours = processed['duration_seconds'] / 3600 if processed['duration_seconds'] else 0
        
        if processed['total_waves'] and duration_hours > 0:
            processed['wave_frequency_per_hour'] = round(processed['total_waves'] / duration_hours, 1)
        
        if processed['total_surf_time_seconds'] and processed['paddle_time_seconds']:
            total_active = processed['total_surf_time_seconds'] + processed['paddle_time_seconds']
            if total_active > 0:
                processed['surf_vs_paddle_ratio'] = round(processed['total_surf_time_seconds'] / total_active, 2)
        
        if processed['total_waves'] and processed['distance_meters']:
            processed['avg_wave_distance'] = round(processed['distance_meters'] / processed['total_waves'], 1)
        
        return processed
    
    def _process_swimming_activity(self, activity):
        """Process swimming-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add swimming-specific fields
        processed.update({
            'distance_meters': activity.get('distance', 0),
            'pool_size_meters': activity.get('pool_size_meters') or activity.get('poolLength'),
            'total_strokes': activity.get('total_strokes') or activity.get('strokes'),
            'avg_swolf': activity.get('avg_swolf') or activity.get('avgSwolf'),
            'avg_stroke_rate_spm': activity.get('avg_stroke_rate_spm') or activity.get('avgStrokeRate'),
            'avg_distance_per_stroke': activity.get('avg_distance_per_stroke') or self._calculate_distance_per_stroke(activity),
            'stroke_type_primary': activity.get('stroke_type_primary') or activity.get('strokeType'),
            'total_lengths': activity.get('total_lengths'),
            'total_intervals': activity.get('total_intervals'),
            'rest_time_seconds': activity.get('rest_time_seconds', 0),
            'drill_time_seconds': activity.get('drill_time_seconds', 0),
            'avg_pace_per_100m': self._calculate_swim_pace_per_100m(activity),
            'css_pace_per_100m': None,  # Would need additional calculation
            'stroke_efficiency_score': None,  # Could be derived from SWOLF
            'is_open_water': activity.get('is_open_water', False)
        })
        
        # Calculate stroke efficiency score from SWOLF (lower is better, normalize to 0-100)
        if processed['avg_swolf']:
            # Typical SWOLF range is 30-80, with 40-50 being good
            swolf_score = max(0, 100 - (processed['avg_swolf'] - 30) * 2)
            processed['stroke_efficiency_score'] = min(100, max(0, swolf_score))
        
        return processed
    
    def _process_running_activity(self, activity):
        """Process running-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add running-specific fields
        processed.update({
            'distance_meters': activity.get('distance', 0),
            'avg_pace_per_km': activity.get('avg_pace_per_km') or self._calculate_pace_per_km(activity),
            'avg_cadence_spm': activity.get('avg_cadence_spm') or activity.get('avgRunCadence'),
            'avg_stride_length': activity.get('avg_stride_length') or activity.get('avgStrideLength'),
            'vertical_oscillation_cm': activity.get('vertical_oscillation_cm'),
            'ground_contact_time_ms': activity.get('ground_contact_time_ms'),
            'running_power_watts': activity.get('running_power_watts') or activity.get('avgPower'),
            'elevation_gain_meters': activity.get('elevation_gain_meters') or activity.get('elevationGain'),
            'elevation_loss_meters': activity.get('elevation_loss_meters') or activity.get('elevationLoss'),
            'avg_temperature': activity.get('avgTemperature'),
            'lactate_threshold_hr': activity.get('lactateThresholdHeartRate'),
            'running_dynamics_score': activity.get('running_dynamics_score'),
            'is_treadmill': activity.get('is_treadmill', 'treadmill' in activity.get('activityType', {}).get('typeKey', '').lower())
        })
        
        return processed
    
    def _process_strength_activity(self, activity):
        """Process strength training-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add strength-specific fields
        processed.update({
            'total_sets': activity.get('total_sets') or activity.get('totalSets'),
            'total_reps': activity.get('total_reps') or activity.get('totalReps'),
            'total_volume_kg': activity.get('total_volume_kg', 0),
            'avg_rest_seconds': activity.get('avg_rest_seconds') or activity.get('avgRestTime'),
            'max_weight_kg': activity.get('max_weight_kg') or activity.get('maxWeight'),
            'primary_muscle_groups': activity.get('primary_muscle_groups', ''),
            'exercise_count': activity.get('exercise_count', 0),
            'workout_type': self._determine_workout_type(activity),
            'compound_vs_isolation_ratio': activity.get('compound_vs_isolation_ratio'),
            'training_focus': self._determine_training_focus(activity)
        })
        
        return processed
    
    def _process_breathwork_activity(self, activity):
        """Process breathwork-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add breathwork-specific fields
        processed.update({
            'whm_rounds_total': activity.get('whm_rounds_total'),
            'whm_total_breaths': activity.get('whm_total_breaths'),
            'whm_max_breath_hold': activity.get('whm_max_breath_hold'),
            'whm_max_breath_hold_stage2': activity.get('whm_max_breath_hold_stage2'),
            'whm_round_details': activity.get('whm_round_details'),
            'avg_respiration_rate': activity.get('avg_respiration_rate') or activity.get('avgRespirationRate'),
            'min_respiration_rate': activity.get('min_respiration_rate') or activity.get('minRespirationRate'),
            'max_respiration_rate': activity.get('max_respiration_rate') or activity.get('maxRespirationRate'),
            'technique_type': activity.get('technique_type', 'General Breathwork'),
            'breath_hold_improvement': None,  # Could be calculated vs. previous sessions
            'session_intensity': self._calculate_breathwork_intensity(activity)
        })
        
        return processed
    
    def _process_recovery_activity(self, activity):
        """Process recovery session-specific activity data"""
        processed = self._get_core_activity_data(activity)
        
        # Add recovery-specific fields (mostly manual entry for now)
        processed.update({
            'session_type': self._determine_recovery_type(activity),
            'temperature_celsius': activity.get('temperature_celsius'),
            'humidity_percent': activity.get('humidity_percent'),
            'rounds_completed': activity.get('rounds_completed'),
            'total_heat_time_seconds': activity.get('total_heat_time_seconds'),
            'total_cool_time_seconds': activity.get('total_cool_time_seconds'),
            'avg_temperature': activity.get('avgTemperature'),
            'recovery_rating': activity.get('recovery_rating'),
            'hydration_level': activity.get('hydration_level'),
            'location': activity.get('location')
        })
        
        return processed
    
    def _get_core_activity_data(self, activity):
        """Extract core data fields present in all activity types"""
        return {
            'date': activity.get('startTimeLocal', '')[:10],
            'activity_id': activity.get('activityId'),
            'activity_type': activity.get('activityType', {}).get('typeKey', 'unknown'),
            'duration_seconds': activity.get('duration', 0),
            'calories': activity.get('calories', 0),
            'avg_hr': activity.get('averageHR'),
            'max_hr': activity.get('maxHR'),
            'hr_zone_1_time': self._extract_zone_time(activity, 1),
            'hr_zone_2_time': self._extract_zone_time(activity, 2),
            'hr_zone_3_time': self._extract_zone_time(activity, 3),
            'hr_zone_4_time': self._extract_zone_time(activity, 4),
            'hr_zone_5_time': self._extract_zone_time(activity, 5),
            'training_effect_aerobic': activity.get('aerobicTrainingEffect'),
            'training_effect_anaerobic': activity.get('anaerobicTrainingEffect'),
            'recovery_time_hrs': activity.get('recoveryTime', 0) / 3600 if activity.get('recoveryTime') else 0,
            'stress_start': activity.get('startStress'),
            'stress_end': activity.get('endStress'),
            'stress_change': activity.get('differenceStress'),
            'body_battery_impact': activity.get('differenceBodyBattery')
        }
    
    def _calculate_pace_per_km(self, activity):
        """Calculate pace per km from duration and distance"""
        try:
            duration = activity.get('duration', 0)  # seconds
            distance = activity.get('distance', 0)  # meters
            
            if distance > 0 and duration > 0:
                pace_per_km = (duration / (distance / 1000)) / 60  # minutes per km
                return round(pace_per_km, 2)
        except:
            pass
        return None
    
    def _determine_workout_type(self, activity):
        """Determine the type of strength workout"""
        activity_name = activity.get('activityName', '').lower()
        
        if 'upper' in activity_name:
            return 'Upper Body'
        elif 'lower' in activity_name:
            return 'Lower Body'
        elif 'full' in activity_name or 'total' in activity_name:
            return 'Full Body'
        elif 'cardio' in activity_name:
            return 'Cardio Strength'
        else:
            return 'General Strength'
    
    def _determine_training_focus(self, activity):
        """Determine the training focus based on volume and intensity"""
        total_sets = activity.get('total_sets', 0) or 0
        avg_rest = activity.get('avg_rest_seconds', 0) or 0
        
        if avg_rest > 180:  # Long rest = strength focus
            return 'Strength'
        elif avg_rest < 60:  # Short rest = endurance focus
            return 'Endurance'
        elif total_sets > 20:  # High volume = hypertrophy
            return 'Hypertrophy'
        else:
            return 'General'
    
    def _calculate_breathwork_intensity(self, activity):
        """Calculate breathwork session intensity based on metrics"""
        try:
            # Use stress change as primary indicator
            stress_change = activity.get('differenceStress', 0)
            duration_minutes = activity.get('duration', 0) / 60
            
            if abs(stress_change) > 20 and duration_minutes > 10:
                return 'High'
            elif abs(stress_change) > 10 or duration_minutes > 15:
                return 'Moderate'
            else:
                return 'Light'
        except:
            return 'Unknown'
    
    def _determine_recovery_type(self, activity):
        """Determine recovery session type from activity name"""
        activity_name = activity.get('activityName', '').lower()
        activity_type = activity.get('activityType', {}).get('typeKey', '').lower()
        
        if 'sauna' in activity_name or 'sauna' in activity_type:
            return 'Sauna'
        elif 'steam' in activity_name:
            return 'Steam Room'
        elif 'ice' in activity_name or 'cold' in activity_name:
            return 'Ice Bath'
        elif 'hot' in activity_name or 'tub' in activity_name:
            return 'Hot Tub'
        else:
            return 'General Recovery'

    def _format_hr_zones(self, activity):
        """Format HR zones as comma-separated string"""
        # Try different possible field names for HR zones
        hr_zones = []
        
        # Method 1: timeInHeartRateZones array
        zones_array = activity.get('timeInHeartRateZones', [])
        if zones_array and len(zones_array) >= 5:
            return f"{zones_array[0]},{zones_array[1]},{zones_array[2]},{zones_array[3]},{zones_array[4]}"
        
        # Method 2: Individual zone fields (as seen in debug output)
        zone_fields = ['hrTimeInZone_1', 'hrTimeInZone_2', 'hrTimeInZone_3', 'hrTimeInZone_4', 'hrTimeInZone_5']
        hr_zones = []
        for field in zone_fields:
            value = activity.get(field, 0)
            hr_zones.append(str(int(value)) if value else "0")
        
        if any(zone != "0" for zone in hr_zones):
            return ",".join(hr_zones)
        
        return "0,0,0,0,0"
    
    def _extract_zone_time(self, activity, zone_number):
        """Extract time in specific HR zone in seconds"""
        # Try direct field access first
        zone_field = f'hrTimeInZone_{zone_number}'
        if zone_field in activity:
            return activity.get(zone_field, 0)
        
        # Try zones array
        zones_array = activity.get('timeInHeartRateZones', [])
        if zones_array and len(zones_array) >= zone_number:
            return zones_array[zone_number - 1]
        
        return 0
    
    def _calculate_swim_pace_per_100m(self, activity):
        """Calculate swimming pace per 100m in seconds"""
        try:
            duration = activity.get('duration', 0)  # in seconds
            distance = activity.get('distance', 0)  # in meters
            
            if distance > 0 and duration > 0:
                # Calculate pace per 100m
                pace_per_100m = (duration / distance) * 100
                return round(pace_per_100m, 2)
        except:
            pass
        return None
    
    def _calculate_distance_per_stroke(self, activity):
        """Calculate average distance per stroke in meters"""
        try:
            distance = activity.get('distance', 0)  # in meters
            strokes = activity.get('strokes', 0)
            
            if strokes > 0 and distance > 0:
                return round(distance / strokes, 2)
        except:
            pass
        return None
    
    def process_daily_health(self, health_data, is_current_day=False):
        """Process daily health metrics"""
        processed = {
            'date': health_data['date'],
            'body_battery_start': None,
            'body_battery_end': None,
            'body_battery_charged': None,
            'body_battery_drained': None,
            'sleep_score': None,
            'deep_sleep_minutes': None,
            'rem_sleep_minutes': None,
            'light_sleep_minutes': None,
            'awake_minutes': None,
            'sleep_efficiency': None,
            'sleep_start_time': None,
            'sleep_end_time': None,
            'hrv_during_sleep': None,
            'hrv_status': None,
            'hrv_overnight_avg': None,
            'hrv_weekly_avg': None,
            'hrv_7_day_trend': None,
            'stress_avg': None,
            'stress_max': None,
            'steps': None,
            'floors_climbed': None,
            'active_calories': None,
            'avg_respiration_rate': None,
            'spo2_avg': None,
            'resting_heart_rate': None,
            'sleep_need_baseline': None,
            'sleep_need_actual': None,
            'sleep_feedback': None,
            'breathing_disruption_severity': None,
            # Enhanced respiration fields
            'detailed_avg_sleep_respiration': None,
            'detailed_avg_waking_respiration': None,
            'detailed_highest_respiration': None,
            'detailed_lowest_respiration': None,
            'respiration_range': None
        }
        
        # Process body battery
        if 'body_battery' in health_data and health_data['body_battery']:
            bb_data = health_data['body_battery']
            if isinstance(bb_data, list) and len(bb_data) > 0:
                bb = bb_data[0]  # Take the first (should be only) entry
                
                # Extract body battery values with proper timestamp sorting
                bb_values_array = bb.get('bodyBatteryValuesArray', [])
                if bb_values_array and len(bb_values_array) > 0:
                    # Sort by timestamp (index 0) to ensure chronological order
                    sorted_values = sorted(bb_values_array, key=lambda x: x[0] if len(x) > 0 else 0)
                    
                    # New approach: Find daily max (post-sleep peak), then min after that
                    if len(sorted_values) >= 2:
                        # Filter out values with None or invalid data, then find the maximum
                        valid_values = [val for val in sorted_values if len(val) > 1 and val[1] is not None]
                        
                        if len(valid_values) >= 2:
                            # Find the maximum value in the day (represents post-sleep peak)
                            max_value = max(valid_values, key=lambda x: x[1])
                            max_timestamp = max_value[0]
                            max_bb_value = max_value[1]
                            
                            # Find values that occur after the max (awake period)
                            post_max_values = [val for val in valid_values if val[0] > max_timestamp]
                            
                            if post_max_values:
                                # Min value after the daily max (end of day drain)
                                min_post_max = min(post_max_values, key=lambda x: x[1])
                                min_bb_value = min_post_max[1]
                                
                                processed['body_battery_start'] = max_bb_value  # Post-sleep peak
                                
                                # For current day, only set end value if we have enough data points
                                # indicating the day is mostly complete
                                if is_current_day:
                                    # Check if we have recent data (last few hours) to ensure day completion
                                    # For current day, be more conservative about setting end value
                                    import time
                                    current_timestamp = int(time.time() * 1000)  # Current time in milliseconds
                                    latest_timestamp = max(val[0] for val in post_max_values)
                                    
                                    # If latest data is from more than 4 hours ago, don't set end value yet
                                    hours_since_latest = (current_timestamp - latest_timestamp) / (1000 * 60 * 60)
                                    
                                    if hours_since_latest <= 4:  # Recent data suggests day is progressing
                                        processed['body_battery_end'] = min_bb_value    # End of day low
                                    else:
                                        logger.info(f"Current day ({health_data.get('date')}): Skipping body_battery_end as latest data is {hours_since_latest:.1f} hours old")
                                    # else: leave body_battery_end as None for incomplete current day
                                else:
                                    processed['body_battery_end'] = min_bb_value    # End of day low
                            else:
                                # No post-max values, just set start
                                processed['body_battery_start'] = max_bb_value
                                if not is_current_day and len(valid_values) > 0:
                                    processed['body_battery_end'] = valid_values[-1][1]
                                elif is_current_day:
                                    logger.info(f"Current day ({health_data.get('date')}): Skipping body_battery_end - no post-max values")
                        else:
                            # Fallback: if insufficient valid values, use what we have
                            if len(valid_values) > 0:
                                processed['body_battery_start'] = valid_values[0][1]
                                if not is_current_day:
                                    processed['body_battery_end'] = valid_values[-1][1]
                                else:
                                    logger.info(f"Current day ({health_data.get('date')}): Skipping body_battery_end - insufficient valid data points")
                
                processed['body_battery_charged'] = bb.get('charged')
                processed['body_battery_drained'] = bb.get('drained')
                
                # Validate body battery logic (now represents post-sleep peak to end-of-day low)
                if (processed['body_battery_start'] is not None and 
                    processed['body_battery_end'] is not None):
                    
                    daily_drain = processed['body_battery_start'] - processed['body_battery_end']
                    
                    # Ensure daily_drain is not None before comparisons
                    if daily_drain is not None:
                        # Log patterns for analysis
                        if daily_drain < 0:
                            logger.warning(f"Unusual: Body battery increased from daily peak: {processed['body_battery_start']} → {processed['body_battery_end']} for date {health_data.get('date')} (this shouldn't happen with new logic)")
                        elif daily_drain > 60:
                            logger.info(f"High daily drain: {processed['body_battery_start']} → {processed['body_battery_end']} ({daily_drain} points) for date {health_data.get('date')} (stressful day)")
                        elif daily_drain < 20:
                            logger.info(f"Low daily drain: {processed['body_battery_start']} → {processed['body_battery_end']} ({daily_drain} points) for date {health_data.get('date')} (restorative day)")
                        else:
                            logger.debug(f"Normal daily drain: {daily_drain} points for date {health_data.get('date')}")
                    
                    # Validate against charged/drained values if available (less reliable with new approach)
                    charged = processed.get('body_battery_charged') or 0
                    drained = processed.get('body_battery_drained') or 0
                    
                    # Ensure charged and drained are not None before calculation
                    if charged is not None and drained is not None:
                        expected_end = processed['body_battery_start'] + charged - drained
                        
                        # Only do the comparison if both expected_end and body_battery_end are not None
                        if (expected_end is not None and 
                            processed['body_battery_end'] is not None and 
                            abs(processed['body_battery_end'] - expected_end) > 10):
                            logger.warning(f"Body battery calculation mismatch for {health_data.get('date')}: start={processed['body_battery_start']}, end={processed['body_battery_end']}, expected_end={expected_end} (charged={charged}, drained={drained})")
                
            elif isinstance(bb_data, dict):
                processed['body_battery_start'] = bb_data.get('startValue')
                end_value = bb_data.get('endValue')
                
                # For current day, only set end value if it's not None (day is complete)
                if is_current_day and end_value is None:
                    logger.info(f"Current day ({health_data.get('date')}): Skipping body_battery_end - day not yet complete")
                    # Leave body_battery_end as None
                else:
                    processed['body_battery_end'] = end_value
                    
                processed['body_battery_charged'] = bb_data.get('totalCharged')
                processed['body_battery_drained'] = bb_data.get('totalDrained')
        
        # Process sleep
        if 'sleep' in health_data and health_data['sleep']:
            sleep = health_data['sleep']
            if isinstance(sleep, dict):
                # Get sleep data from dailySleepDTO
                daily_sleep = sleep.get('dailySleepDTO', {})
                if daily_sleep:
                    # Extract sleep scores
                    sleep_scores = daily_sleep.get('sleepScores', {})
                    overall_score = sleep_scores.get('overall', {})
                    processed['sleep_score'] = overall_score.get('value')
                    
                    # Extract sleep stages (already in seconds, convert to minutes)
                    deep_sleep_sec = daily_sleep.get('deepSleepSeconds', 0) or 0
                    rem_sleep_sec = daily_sleep.get('remSleepSeconds', 0) or 0
                    light_sleep_sec = daily_sleep.get('lightSleepSeconds', 0) or 0
                    awake_sec = daily_sleep.get('awakeSleepSeconds', 0) or 0
                    
                    processed['deep_sleep_minutes'] = deep_sleep_sec / 60
                    processed['rem_sleep_minutes'] = rem_sleep_sec / 60
                    processed['light_sleep_minutes'] = light_sleep_sec / 60
                    processed['awake_minutes'] = awake_sec / 60
                    
                    # Calculate sleep efficiency
                    total_sleep_time = processed['deep_sleep_minutes'] + processed['rem_sleep_minutes'] + processed['light_sleep_minutes']
                    total_time_in_bed = total_sleep_time + processed['awake_minutes']
                    if total_time_in_bed > 0:
                        processed['sleep_efficiency'] = round((total_sleep_time / total_time_in_bed) * 100, 1)
                    
                    # Sleep timing
                    processed['sleep_start_time'] = daily_sleep.get('sleepStartTimestampLocal')
                    processed['sleep_end_time'] = daily_sleep.get('sleepEndTimestampLocal')
                    
                    # Sleep need information
                    sleep_need = daily_sleep.get('sleepNeed', {})
                    if sleep_need:
                        processed['sleep_need_baseline'] = sleep_need.get('baseline')
                        processed['sleep_need_actual'] = sleep_need.get('actual')
                        processed['sleep_feedback'] = sleep_need.get('feedback')
                    
                    # Breathing disruption
                    processed['breathing_disruption_severity'] = daily_sleep.get('breathingDisruptionSeverity')
                
                # Enhanced HRV data
                processed['hrv_overnight_avg'] = sleep.get('avgOvernightHrv')
                processed['hrv_status'] = sleep.get('hrvStatus')
                processed['resting_heart_rate'] = sleep.get('restingHeartRate')
                
                # Legacy HRV field for backward compatibility
                processed['hrv_during_sleep'] = sleep.get('avgOvernightHrv')
                
                # HRV weekly data (if available)
                hrv_weekly_data = sleep.get('hrvWeeklyAvg')
                if hrv_weekly_data:
                    processed['hrv_weekly_avg'] = hrv_weekly_data.get('weeklyAvg')
                    processed['hrv_7_day_trend'] = hrv_weekly_data.get('trendDirection')
        
        # Process stress
        if 'stress' in health_data and health_data['stress']:
            stress = health_data['stress']
            if isinstance(stress, dict):
                processed['stress_avg'] = stress.get('avgStressLevel')
                processed['stress_max'] = stress.get('maxStressLevel')
        
        # Process summary data
        if 'summary' in health_data and health_data['summary']:
            summary = health_data['summary']
            if isinstance(summary, dict):
                processed['steps'] = summary.get('totalSteps')
                processed['floors_climbed'] = summary.get('floorsAscended')
                processed['active_calories'] = summary.get('activeKilocalories')
                # Additional fields that might be useful
                processed['avg_respiration_rate'] = summary.get('avgWakingRespirationValue')
                processed['spo2_avg'] = summary.get('averageSpo2')
        
        # Process detailed respiration data
        if 'respiration' in health_data and health_data['respiration']:
            resp_data = health_data['respiration']
            if isinstance(resp_data, dict):
                processed['detailed_avg_sleep_respiration'] = resp_data.get('avgSleepRespirationValue')
                processed['detailed_avg_waking_respiration'] = resp_data.get('avgWakingRespirationValue')
                processed['detailed_highest_respiration'] = resp_data.get('highestRespirationValue')
                processed['detailed_lowest_respiration'] = resp_data.get('lowestRespirationValue')
                
                # Calculate respiration range
                if (processed['detailed_highest_respiration'] is not None and 
                    processed['detailed_lowest_respiration'] is not None):
                    processed['respiration_range'] = (processed['detailed_highest_respiration'] - 
                                                    processed['detailed_lowest_respiration'])
        
        return processed
    
    def process_physiological_metrics(self, phys_data):
        """Process physiological metrics"""
        processed = {
            'date': phys_data['date'],
            'vo2_max_running': None,
            'vo2_max_cycling': None,
            'fitness_age': None,
            'training_status': None,
            'training_load_7day': None,
            'training_load_focus': None,
            'recovery_advisor': None,
            'performance_condition': None,
            'training_load_aerobic_low': None,
            'training_load_aerobic_high': None,
            'training_load_anaerobic': None,
            'training_load_aerobic_low_target_min': None,
            'training_load_aerobic_low_target_max': None,
            'training_load_aerobic_high_target_min': None,
            'training_load_aerobic_high_target_max': None,
            'training_load_anaerobic_target_min': None,
            'training_load_anaerobic_target_max': None,
            'training_balance_feedback': None,
            'altitude_acclimatization': None,
            'heat_acclimatization': None
        }
        
        # Process max metrics (VO2 max, fitness age)
        if 'max_metrics' in phys_data and phys_data['max_metrics']:
            max_metrics = phys_data['max_metrics']
            if isinstance(max_metrics, dict):
                processed['vo2_max_running'] = max_metrics.get('vo2MaxRunning')
                processed['vo2_max_cycling'] = max_metrics.get('vo2MaxCycling')
                processed['fitness_age'] = max_metrics.get('fitnessAge')
        
        # Process training status - Updated structure
        if 'training_status' in phys_data and phys_data['training_status']:
            ts = phys_data['training_status']
            if isinstance(ts, dict):
                # Try to extract VO2 max from mostRecentVO2Max
                vo2_data = ts.get('mostRecentVO2Max', {})
                if vo2_data:
                    processed['vo2_max_running'] = vo2_data.get('generic') or vo2_data.get('running')
                    processed['vo2_max_cycling'] = vo2_data.get('cycling')
                    
                    # Heat and altitude acclimatization
                    heat_alt = vo2_data.get('heatAltitudeAcclimation', {})
                    if heat_alt:
                        processed['altitude_acclimatization'] = heat_alt.get('acclimationPercentage')
                        processed['heat_acclimatization'] = heat_alt.get('heatAcclimationPercentage')
                
                # Extract training status from mostRecentTrainingStatus
                recent_status = ts.get('mostRecentTrainingStatus', {})
                if recent_status:
                    processed['training_status'] = recent_status.get('trainingStatusType')
                    processed['training_load_7day'] = recent_status.get('trainingLoad')
                    processed['training_load_focus'] = recent_status.get('focusType')
                
                # Extract detailed training load balance information
                load_balance = ts.get('mostRecentTrainingLoadBalance', {})
                if load_balance:
                    metrics_map = load_balance.get('metricsTrainingLoadBalanceDTOMap', {})
                    # Get the first device's data (primary training device)
                    for device_id, device_data in metrics_map.items():
                        if device_data.get('primaryTrainingDevice', False):
                            # Current training loads
                            processed['training_load_aerobic_low'] = device_data.get('monthlyLoadAerobicLow')
                            processed['training_load_aerobic_high'] = device_data.get('monthlyLoadAerobicHigh')
                            processed['training_load_anaerobic'] = device_data.get('monthlyLoadAnaerobic')
                            
                            # Target ranges
                            processed['training_load_aerobic_low_target_min'] = device_data.get('monthlyLoadAerobicLowTargetMin')
                            processed['training_load_aerobic_low_target_max'] = device_data.get('monthlyLoadAerobicLowTargetMax')
                            processed['training_load_aerobic_high_target_min'] = device_data.get('monthlyLoadAerobicHighTargetMin')
                            processed['training_load_aerobic_high_target_max'] = device_data.get('monthlyLoadAerobicHighTargetMax')
                            processed['training_load_anaerobic_target_min'] = device_data.get('monthlyLoadAnaerobicTargetMin')
                            processed['training_load_anaerobic_target_max'] = device_data.get('monthlyLoadAnaerobicTargetMax')
                            
                            # Feedback
                            processed['training_balance_feedback'] = device_data.get('trainingBalanceFeedbackPhrase')
                            break
        
        # Process training readiness (if available)
        if 'training_readiness' in phys_data and phys_data['training_readiness']:
            readiness = phys_data['training_readiness']
            if isinstance(readiness, dict):
                processed['recovery_advisor'] = readiness.get('trainingReadinessLevel')
                processed['performance_condition'] = readiness.get('performanceCondition')
        
        # Process recovery time (if available)
        if 'recovery_time' in phys_data and phys_data['recovery_time']:
            recovery = phys_data['recovery_time']
            if isinstance(recovery, dict):
                if not processed['recovery_advisor']:  # Only if not set by training readiness
                    processed['recovery_advisor'] = recovery.get('recoveryTimeInHours')
        
        return processed
    
    def process_weekly_training_zones(self, weekly_data):
        """Process weekly training zone distribution"""
        processed = {
            'week_start_date': weekly_data.get('week_start'),
            'week_end_date': weekly_data.get('week_end'),
            'total_training_time_minutes': 0,
            'zone_1_time_minutes': 0,
            'zone_1_percentage': 0,
            'zone_2_time_minutes': 0,
            'zone_2_percentage': 0,
            'zone_3_time_minutes': 0,
            'zone_3_percentage': 0,
            'zone_4_time_minutes': 0,
            'zone_4_percentage': 0,
            'zone_5_time_minutes': 0,
            'zone_5_percentage': 0,
            'total_swimming_time': 0,
            'total_strength_time': 0,
            'total_aerobic_time': 0,
            'weekly_training_load': 0,
            'weekly_training_stress': 0
        }
        
        # Process activities to calculate zone distribution
        activities = weekly_data.get('activities', [])
        total_zone_time = 0
        zone_times = [0, 0, 0, 0, 0]  # zones 1-5
        
        for activity in activities:
            try:
                duration = activity.get('duration', 0) / 60  # convert to minutes
                activity_type = activity.get('activityType', {}).get('typeKey', '').lower()
                
                processed['total_training_time_minutes'] += duration
                
                # Categorize activity types
                if 'swim' in activity_type:
                    processed['total_swimming_time'] += duration
                elif 'strength' in activity_type or 'weight' in activity_type:
                    processed['total_strength_time'] += duration
                elif activity_type in ['running', 'cycling', 'cardio']:
                    processed['total_aerobic_time'] += duration
                
                # Extract HR zone times
                for i in range(5):
                    zone_field = f'hrTimeInZone_{i+1}'
                    zone_time = activity.get(zone_field, 0) / 60  # convert to minutes
                    zone_times[i] += zone_time
                    total_zone_time += zone_time
                
                # Add to training load
                processed['weekly_training_load'] += activity.get('aerobicTrainingEffect', 0) + activity.get('anaerobicTrainingEffect', 0)
                
            except Exception as e:
                logger.error(f"Error processing activity in weekly zones: {e}")
        
        # Calculate zone percentages
        if total_zone_time > 0:
            for i in range(5):
                processed[f'zone_{i+1}_time_minutes'] = round(zone_times[i], 1)
                processed[f'zone_{i+1}_percentage'] = round((zone_times[i] / total_zone_time) * 100, 1)
        
        return processed
    
    def process_recovery_trends(self, hrv_data, health_history):
        """Process recovery trends over time"""
        processed = {
            'date': hrv_data.get('date'),
            'hrv_7_day_avg': None,
            'hrv_14_day_avg': None,
            'hrv_30_day_avg': None,
            'hrv_trend_direction': None,
            'sleep_efficiency_7_day_avg': None,
            'sleep_efficiency_14_day_avg': None,
            'sleep_score_7_day_avg': None,
            'sleep_score_14_day_avg': None,
            'rhr_7_day_avg': None,
            'rhr_14_day_avg': None,
            'rhr_trend_direction': None,
            'body_battery_avg_7_day': None,
            'stress_avg_7_day': None,
            'recovery_score': None,
            'training_readiness': None
        }
        
        if not health_history:
            return processed
        
        try:
            # Calculate HRV trends
            hrv_values = [h.get('hrv_overnight_avg') for h in health_history if h.get('hrv_overnight_avg') is not None]
            if len(hrv_values) >= 7:
                processed['hrv_7_day_avg'] = round(sum(hrv_values[-7:]) / 7, 1)
            if len(hrv_values) >= 14:
                processed['hrv_14_day_avg'] = round(sum(hrv_values[-14:]) / 14, 1)
            if len(hrv_values) >= 30:
                processed['hrv_30_day_avg'] = round(sum(hrv_values[-30:]) / 30, 1)
            
            # Calculate HRV trend direction
            if len(hrv_values) >= 14:
                recent_avg = sum(hrv_values[-7:]) / 7
                previous_avg = sum(hrv_values[-14:-7]) / 7
                
                # Ensure averages are not None before comparison
                if recent_avg is not None and previous_avg is not None:
                    if recent_avg > previous_avg * 1.05:
                        processed['hrv_trend_direction'] = 'INCREASING'
                    elif recent_avg < previous_avg * 0.95:
                        processed['hrv_trend_direction'] = 'DECREASING'
                    else:
                        processed['hrv_trend_direction'] = 'STABLE'
            
            # Calculate sleep trends
            sleep_scores = [h.get('sleep_score') for h in health_history if h.get('sleep_score')]
            if len(sleep_scores) >= 7:
                processed['sleep_score_7_day_avg'] = round(sum(sleep_scores[-7:]) / 7, 1)
            if len(sleep_scores) >= 14:
                processed['sleep_score_14_day_avg'] = round(sum(sleep_scores[-14:]) / 14, 1)
            
            # Calculate RHR trends
            rhr_values = [h.get('resting_heart_rate') for h in health_history if h.get('resting_heart_rate') is not None]
            if len(rhr_values) >= 7:
                processed['rhr_7_day_avg'] = round(sum(rhr_values[-7:]) / 7, 1)
            if len(rhr_values) >= 14:
                processed['rhr_14_day_avg'] = round(sum(rhr_values[-14:]) / 14, 1)
                
                # RHR trend direction
                recent_rhr = sum(rhr_values[-7:]) / 7
                previous_rhr = sum(rhr_values[-14:-7]) / 7
                
                # Ensure averages are not None before comparison
                if recent_rhr is not None and previous_rhr is not None:
                    if recent_rhr < previous_rhr * 0.97:
                        processed['rhr_trend_direction'] = 'IMPROVING'
                    elif recent_rhr > previous_rhr * 1.03:
                        processed['rhr_trend_direction'] = 'DECLINING'
                    else:
                        processed['rhr_trend_direction'] = 'STABLE'
            
            # Body battery and stress trends
            bb_values = [h.get('body_battery_end') for h in health_history if h.get('body_battery_end')]
            if len(bb_values) >= 7:
                processed['body_battery_avg_7_day'] = round(sum(bb_values[-7:]) / 7, 1)
            
            stress_values = [h.get('stress_avg') for h in health_history if h.get('stress_avg')]
            if len(stress_values) >= 7:
                processed['stress_avg_7_day'] = round(sum(stress_values[-7:]) / 7, 1)
            
            # Calculate composite recovery score (0-100)
            recovery_factors = []
            if processed['hrv_trend_direction'] == 'INCREASING':
                recovery_factors.append(20)
            elif processed['hrv_trend_direction'] == 'STABLE':
                recovery_factors.append(15)
            else:
                recovery_factors.append(5)
            
            if processed['rhr_trend_direction'] == 'IMPROVING':
                recovery_factors.append(20)
            elif processed['rhr_trend_direction'] == 'STABLE':
                recovery_factors.append(15)
            else:
                recovery_factors.append(5)
            
            if processed['sleep_score_7_day_avg'] and processed['sleep_score_7_day_avg'] > 75:
                recovery_factors.append(20)
            elif processed['sleep_score_7_day_avg'] and processed['sleep_score_7_day_avg'] > 60:
                recovery_factors.append(15)
            else:
                recovery_factors.append(5)
            
            if processed['body_battery_avg_7_day'] and processed['body_battery_avg_7_day'] > 70:
                recovery_factors.append(20)
            elif processed['body_battery_avg_7_day'] and processed['body_battery_avg_7_day'] > 50:
                recovery_factors.append(15)
            else:
                recovery_factors.append(5)
            
            if processed['stress_avg_7_day'] and processed['stress_avg_7_day'] < 30:
                recovery_factors.append(20)
            elif processed['stress_avg_7_day'] and processed['stress_avg_7_day'] < 50:
                recovery_factors.append(15)
            else:
                recovery_factors.append(5)
            
            if recovery_factors:
                processed['recovery_score'] = sum(recovery_factors)
                
                # Determine training readiness
                if processed['recovery_score'] >= 85:
                    processed['training_readiness'] = 'OPTIMAL'
                elif processed['recovery_score'] >= 70:
                    processed['training_readiness'] = 'GOOD'
                elif processed['recovery_score'] >= 50:
                    processed['training_readiness'] = 'MODERATE'
                else:
                    processed['training_readiness'] = 'LOW'
        
        except Exception as e:
            logger.error(f"Error processing recovery trends: {e}")
        
        return processed
    
    def process_strength_exercises(self, activity_data):
        """Process detailed strength training exercise sets (RAW GARMIN DATA ONLY)"""
        exercises = []
        
        if not activity_data.get('exercise_sets'):
            return exercises
        
        activity_id = activity_data.get('activityId')
        activity_date = activity_data.get('startTimeLocal', '')[:10]
        
        try:
            exercise_sets = activity_data['exercise_sets']
            
            for exercise in exercise_sets:
                exercise_name = exercise.get('exerciseName', 'Unknown')
                exercise_category = exercise.get('category', 'Unknown')
                
                # Process each set within the exercise
                sets = exercise.get('sets', [])
                for idx, set_data in enumerate(sets, 1):
                    
                    # Calculate basic volume (this is our only derived field)
                    weight = set_data.get('weight', 0) or 0
                    reps = set_data.get('reps', 0) or 0
                    volume = weight * reps if weight and reps else 0
                    
                    # ONLY raw Garmin data + basic volume calculation
                    exercise_record = {
                        'date': activity_date,
                        'activity_id': activity_id,
                        'exercise_name': exercise_name,
                        'exercise_category': exercise_category,  # This is from Garmin
                        'set_number': idx,
                        'weight_kg': weight,
                        'reps': reps,
                        'duration_seconds': set_data.get('duration', 0),
                        'rest_seconds': set_data.get('restTime', 0),
                        'difficulty_level': set_data.get('difficulty'),
                        'volume_kg': volume,  # Simple calculation: weight × reps
                        'equipment_used': exercise.get('equipment', ''),
                        'exercise_notes': exercise.get('notes', '')
                    }
                    
                    exercises.append(exercise_record)
                    
        except Exception as e:
            logger.error(f"Error processing strength exercises for activity {activity_id}: {e}")
        
        return exercises
    
    def _extract_whm_connectiq_data(self, iq_measurements):
        """Extract WHM-specific data from Connect IQ measurements"""
        whm_data = {
            'whm_rounds_total': None,
            'whm_total_breaths': None,
            'whm_max_breath_hold': None,
            'whm_max_breath_hold_stage2': None,
            'whm_round_details': []
        }
        
        try:
            # Map field numbers to data types based on WHM Connect IQ app structure
            field_mapping = {
                0: 'rounds_total',          # Field 0: Number of rounds (e.g., "6.0")
                1: 'total_breaths',         # Field 1: Total breaths in session (e.g., "337.0")
                2: 'max_breath_hold',       # Field 2: Max breath hold time (e.g., "1:03")
                3: 'max_breath_hold_stage2' # Field 3: Max breath hold stage 2 time (e.g., "0:15")
                # Fields 11-16: Round details "breaths / hold_time / hold_time_stage2"
            }
            
            round_details = []
            
            for measurement in iq_measurements:
                field_num = measurement.get('developerFieldNumber')
                value = measurement.get('value')
                
                if field_num in field_mapping:
                    if field_num == 0:  # Rounds total
                        try:
                            whm_data['whm_rounds_total'] = int(float(value))
                        except:
                            pass
                    elif field_num == 1:  # Total breaths
                        try:
                            whm_data['whm_total_breaths'] = int(float(value))
                        except:
                            pass
                    elif field_num == 2:  # Max breath hold
                        whm_data['whm_max_breath_hold'] = value
                    elif field_num == 3:  # Max breath hold stage 2
                        whm_data['whm_max_breath_hold_stage2'] = value
                
                # Fields 11-16 appear to be round-specific data: "breaths / hold_time / hold_time_stage2"
                elif field_num >= 11 and field_num <= 16:
                    try:
                        round_number = field_num - 10  # Convert field number to round number
                        if '/' in value:
                            parts = value.split(' / ')
                            if len(parts) == 3:
                                round_info = {
                                    'round_number': round_number,
                                    'breaths': int(parts[0]),
                                    'hold_time': parts[1],  # e.g., "1:03"
                                    'hold_time_stage2': parts[2]  # e.g., "15" (seconds)
                                }
                                round_details.append(round_info)
                    except:
                        pass
            
            # Store round details as JSON string for CSV compatibility
            if round_details:
                import json
                whm_data['whm_round_details'] = json.dumps(round_details)
            
        except Exception as e:
            logger.warning(f"Error extracting WHM Connect IQ data: {e}")
        
        return whm_data
