from garminconnect import Garmin
from datetime import date, datetime, timedelta
import os
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GarminDataClient:
    def __init__(self):
        self.api = None
        
    def authenticate(self, email, password):
        """Authenticate with Garmin Connect"""
        try:
            self.api = Garmin(email, password)
            self.api.login()
            logger.info("Successfully authenticated with Garmin Connect")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_activities_daterange(self, start_date, end_date):
        """Get all activities in date range"""
        try:
            activities = self.api.get_activities_by_date(
                start_date.isoformat(), 
                end_date.isoformat()
            )
            logger.info(f"Retrieved {len(activities)} activities from {start_date} to {end_date}")
            return activities
        except Exception as e:
            logger.error(f"Failed to get activities: {e}")
            return []

    def get_activity_details_by_type(self, activity_id, activity_type):
            """Get detailed activity data optimized by activity type"""
            try:
                # Get base activity details
                base_details = self.get_activity_details_enhanced(activity_id)
                
                # Add type-specific data extraction
                if 'surfing' in activity_type.lower():
                    return self._extract_surfing_metrics(base_details)
                elif any(swim_type in activity_type.lower() for swim_type in ['swimming', 'pool', 'open_water']):
                    return self._extract_swimming_metrics(base_details)
                elif 'running' in activity_type.lower() or 'treadmill' in activity_type.lower():
                    return self._extract_running_metrics(base_details)
                elif 'strength' in activity_type.lower() or 'weight' in activity_type.lower():
                    return self._extract_strength_metrics(base_details)
                elif 'breathwork' in activity_type.lower() or 'meditation' in activity_type.lower():
                    return self._extract_breathwork_metrics(base_details)
                else:
                    return base_details
                    
            except Exception as e:
                logger.error(f"Failed to get type-specific details for activity {activity_id}: {e}")
                return {}

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

    def _extract_surfing_metrics(self, activity_details):
        """Extract surfing-specific metrics from activity details"""
        try:
            surfing_data = activity_details.copy()
            
            # Extract surfing-specific fields from summaryDTO
            if 'summaryDTO' in activity_details:
                summary = activity_details['summaryDTO']
                
                # Look for surfing-specific fields (these may vary by device/app)
                surfing_data.update({
                    'total_waves': summary.get('totalWaves'),
                    'longest_wave_seconds': summary.get('longestWaveTime'),
                    'total_surf_time_seconds': summary.get('surfTime'),
                    'paddle_time_seconds': summary.get('paddleTime'),
                    'max_speed_kmh': summary.get('maxSpeed'),
                    'avg_speed_kmh': summary.get('avgSpeed')
                })
            
            # Extract Connect IQ data if available (Surf Tracker app data)
            if 'connectIQMeasurements' in activity_details:
                iq_data = self._extract_surfing_connectiq_data(activity_details['connectIQMeasurements'])
                surfing_data.update(iq_data)
            
            return surfing_data
            
        except Exception as e:
            logger.warning(f"Error extracting surfing metrics: {e}")
            return activity_details
    
    def _extract_swimming_metrics(self, activity_details):
        """Extract swimming-specific metrics from activity details"""
        try:
            swimming_data = activity_details.copy()
            
            if 'summaryDTO' in activity_details:
                summary = activity_details['summaryDTO']
                
                # Swimming-specific fields
                swimming_data.update({
                    'total_strokes': summary.get('strokes'),
                    'avg_swolf': summary.get('avgSwolf'),
                    'avg_stroke_rate_spm': summary.get('avgStrokeRate'),
                    'avg_distance_per_stroke': summary.get('avgDistancePerStroke'),
                    'stroke_type_primary': summary.get('primaryStrokeType'),
                    'total_lengths': summary.get('totalLengths'),
                    'pool_size_meters': summary.get('poolLength'),
                    'is_open_water': summary.get('activityType', {}).get('typeKey', '').lower() == 'open_water_swimming'
                })
                
                # Calculate swimming-specific metrics
                if summary.get('totalSets'):
                    swimming_data['total_intervals'] = summary.get('totalSets')
                
                # Rest time calculation
                total_time = summary.get('elapsedDuration', 0)
                active_time = summary.get('activeDuration', 0)
                swimming_data['rest_time_seconds'] = max(0, total_time - active_time)
            
            return swimming_data
            
        except Exception as e:
            logger.warning(f"Error extracting swimming metrics: {e}")
            return activity_details
    
    def _extract_running_metrics(self, activity_details):
        """Extract running-specific metrics from activity details"""
        try:
            running_data = activity_details.copy()
            
            if 'summaryDTO' in activity_details:
                summary = activity_details['summaryDTO']
                
                # Running-specific fields
                running_data.update({
                    'avg_pace_per_km': summary.get('avgPace'),
                    'avg_cadence_spm': summary.get('avgRunCadence'),
                    'avg_stride_length': summary.get('avgStrideLength'),
                    'vertical_oscillation_cm': summary.get('avgVerticalOscillation'),
                    'ground_contact_time_ms': summary.get('avgGroundContactTime'),
                    'running_power_watts': summary.get('avgPower'),
                    'elevation_gain_meters': summary.get('elevationGain'),
                    'elevation_loss_meters': summary.get('elevationLoss'),
                    'is_treadmill': 'treadmill' in summary.get('activityType', {}).get('typeKey', '').lower()
                })
                
                # Calculate running dynamics score if we have the data
                if all(running_data.get(field) for field in ['avg_cadence_spm', 'vertical_oscillation_cm', 'ground_contact_time_ms']):
                    running_data['running_dynamics_score'] = self._calculate_running_dynamics_score(
                        running_data['avg_cadence_spm'],
                        running_data['vertical_oscillation_cm'],
                        running_data['ground_contact_time_ms']
                    )
            
            return running_data
            
        except Exception as e:
            logger.warning(f"Error extracting running metrics: {e}")
            return activity_details
    
    def _extract_strength_metrics(self, activity_details):
        """Extract strength training-specific metrics from activity details"""
        try:
            strength_data = activity_details.copy()
            
            if 'summaryDTO' in activity_details:
                summary = activity_details['summaryDTO']
                
                # Basic strength metrics
                strength_data.update({
                    'total_sets': summary.get('totalSets'),
                    'total_reps': summary.get('totalReps'),
                    'max_weight_kg': summary.get('maxWeight'),
                    'avg_rest_seconds': summary.get('avgRestTime')
                })
            
            # Extract detailed exercise data if available
            if 'exercise_sets' in activity_details:
                exercise_data = self._calculate_strength_summary(activity_details['exercise_sets'])
                strength_data.update(exercise_data)
            
            return strength_data
            
        except Exception as e:
            logger.warning(f"Error extracting strength metrics: {e}")
            return activity_details
    
    def _extract_breathwork_metrics(self, activity_details):
        """Extract breathwork-specific metrics from activity details"""
        try:
            breathwork_data = activity_details.copy()
            
            # Use existing WHM Connect IQ data extraction
            if 'connectIQMeasurements' in activity_details:
                whm_data = self._extract_whm_connectiq_data(activity_details['connectIQMeasurements'])
                breathwork_data.update(whm_data)
            
            # Add respiration data
            if 'summaryDTO' in activity_details:
                summary = activity_details['summaryDTO']
                breathwork_data.update({
                    'avg_respiration_rate': summary.get('avgRespirationRate'),
                    'min_respiration_rate': summary.get('minRespirationRate'),
                    'max_respiration_rate': summary.get('maxRespirationRate')
                })
                
                # Determine technique type
                activity_name = summary.get('activityName', '').lower()
                if 'whm' in activity_name:
                    breathwork_data['technique_type'] = 'WHM'
                elif 'box' in activity_name:
                    breathwork_data['technique_type'] = 'Box Breathing'
                elif '478' in activity_name:
                    breathwork_data['technique_type'] = '4-7-8 Breathing'
                else:
                    breathwork_data['technique_type'] = 'General Breathwork'
            
            return breathwork_data
            
        except Exception as e:
            logger.warning(f"Error extracting breathwork metrics: {e}")
            return activity_details
    
    def _extract_surfing_connectiq_data(self, iq_measurements):
        """Extract surfing-specific data from Connect IQ measurements (Surf Tracker app)"""
        surfing_connectiq_data = {}
        
        try:
            for measurement in iq_measurements:
                field_num = measurement.get('developerFieldNumber')
                value = measurement.get('value')
                
                # Map based on common surfing apps
                if field_num == 0:  # Total waves
                    try:
                        surfing_connectiq_data['total_waves'] = int(float(value))
                    except: pass
                elif field_num == 1:  # Longest wave
                    surfing_connectiq_data['longest_wave_seconds'] = value
                elif field_num == 2:  # Max speed
                    try:
                        surfing_connectiq_data['max_speed_kmh'] = float(value)
                    except: pass
                elif field_num == 3:  # Total surf time
                    surfing_connectiq_data['total_surf_time_seconds'] = value
                
        except Exception as e:
            logger.warning(f"Error extracting surfing Connect IQ data: {e}")
        
        return surfing_connectiq_data
    
    def _calculate_running_dynamics_score(self, cadence, vertical_osc, ground_contact):
        """Calculate a running dynamics efficiency score (0-100)"""
        try:
            # Optimal ranges (based on research)
            optimal_cadence = 180
            optimal_vertical_osc = 8.0  # cm
            optimal_ground_contact = 220  # ms
            
            # Calculate deviations from optimal (normalize to 0-1)
            cadence_score = max(0, 1 - abs(cadence - optimal_cadence) / optimal_cadence)
            vertical_score = max(0, 1 - abs(vertical_osc - optimal_vertical_osc) / optimal_vertical_osc)
            contact_score = max(0, 1 - abs(ground_contact - optimal_ground_contact) / optimal_ground_contact)
            
            # Weighted average (cadence most important)
            dynamics_score = (cadence_score * 0.5 + vertical_score * 0.3 + contact_score * 0.2) * 100
            
            return round(dynamics_score, 1)
        except:
            return None
    
    def _calculate_strength_summary(self, exercise_sets):
        """Calculate summary metrics from detailed strength exercise sets"""
        try:
            total_volume = 0
            total_exercises = len(exercise_sets)
            muscle_groups = set()
            compound_exercises = 0
            
            for exercise in exercise_sets:
                exercise_name = exercise.get('exerciseName', '').lower()
                
                # Track muscle groups
                category = exercise.get('category', '')
                if category:
                    muscle_groups.add(category)
                
                # Identify compound vs isolation movements
                compound_keywords = ['squat', 'deadlift', 'bench', 'row', 'pull', 'press', 'clean']
                if any(keyword in exercise_name for keyword in compound_keywords):
                    compound_exercises += 1
                
                # Calculate volume for this exercise
                sets = exercise.get('sets', [])
                for set_data in sets:
                    weight = set_data.get('weight', 0) or 0
                    reps = set_data.get('reps', 0) or 0
                    total_volume += weight * reps
            
            return {
                'total_volume_kg': total_volume,
                'exercise_count': total_exercises,
                'primary_muscle_groups': ','.join(muscle_groups)[:100],  # Truncate for CSV
                'compound_vs_isolation_ratio': round(compound_exercises / max(1, total_exercises), 2)
            }
            
        except Exception as e:
            logger.warning(f"Error calculating strength summary: {e}")
            return {}

    def get_activity_details(self, activity_id):
        """Get detailed metrics for specific activity"""
        try:
            return self.api.get_activity(activity_id)
        except Exception as e:
            logger.error(f"Failed to get activity details for {activity_id}: {e}")
            return {}
    
    def get_daily_health_metrics(self, target_date):
        """Get comprehensive health data for specific date"""
        iso_date = target_date.isoformat()
        health_data = {'date': iso_date}
        
        try:
            health_data['summary'] = self.api.get_user_summary(iso_date)
        except: pass
        
        try:
            health_data['sleep'] = self.api.get_sleep_data(iso_date)
        except: pass
        
        try:
            health_data['body_battery'] = self.api.get_body_battery(iso_date)
        except: pass
        
        try:
            health_data['stress'] = self.api.get_stress_data(iso_date)
        except: pass
        
        try:
            health_data['steps'] = self.api.get_steps_data(iso_date)
        except: pass
        
        try:
            health_data['heart_rate'] = self.api.get_heart_rate(iso_date)
        except: pass
        
        try:
            health_data['respiration'] = self.api.get_respiration_data(iso_date)
        except: pass
        
        return health_data
    
    def get_physiological_metrics(self, target_date):
        """Get training and fitness metrics"""
        iso_date = target_date.isoformat()
        phys_data = {'date': iso_date}
        
        try:
            phys_data['max_metrics'] = self.api.get_max_metrics(iso_date)
        except: pass
        
        try:
            phys_data['training_status'] = self.api.get_training_status(iso_date)
        except: pass
        
        try:
            phys_data['training_readiness'] = self.api.get_training_readiness(iso_date)
        except: pass
        
        try:
            phys_data['recovery_time'] = self.api.get_recovery_time(iso_date)
        except: pass
        
        try:
            phys_data['race_predictor'] = self.api.get_race_predictor()
        except: pass
        
        return phys_data
    
    def get_activity_details_enhanced(self, activity_id):
        """Get enhanced activity details including swimming and power metrics"""
        try:
            # Get basic activity details
            activity = self.api.get_activity(activity_id)
            
            # Get detailed activity data including splits and laps
            try:
                activity['splits'] = self.api.get_activity_splits(activity_id)
            except: pass
            
            try:
                activity['laps'] = self.api.get_activity_laps(activity_id)
            except: pass
            
            # Get exercise sets for strength training activities
            try:
                if 'strength' in activity.get('activityType', {}).get('typeKey', '').lower():
                    activity['exercise_sets'] = self.api.get_activity_exercise_sets(activity_id)
                    logger.info(f"Retrieved exercise sets for strength training activity {activity_id}")
            except Exception as e:
                logger.warning(f"Could not get exercise sets for activity {activity_id}: {e}")
            
            return activity
        except Exception as e:
            logger.error(f"Failed to get enhanced activity details for {activity_id}: {e}")
            return {}
    
    def get_hrv_trends(self, start_date, end_date):
        """Get HRV data over a date range for trend analysis"""
        try:
            hrv_data = []
            current_date = start_date
            while current_date <= end_date:
                iso_date = current_date.isoformat()
                try:
                    daily_hrv = self.api.get_hrv_data(iso_date)
                    if daily_hrv:
                        hrv_data.append({
                            'date': iso_date,
                            'hrv_data': daily_hrv
                        })
                except: pass
                current_date += timedelta(days=1)
            return hrv_data
        except Exception as e:
            logger.error(f"Failed to get HRV trends: {e}")
            return []
    
    def get_weekly_training_zones(self, start_date, end_date):
        """Get weekly training zone distribution"""
        try:
            activities = self.get_activities_daterange(start_date, end_date)
            weekly_data = {
                'week_start': start_date.isoformat(),
                'week_end': end_date.isoformat(),
                'activities': activities,
                'zone_distribution': {}
            }
            
            # Calculate zone distribution from activities
            for activity in activities:
                try:
                    details = self.get_activity_details_enhanced(activity.get('activityId'))
                    if details.get('timeInHrZones'):
                        weekly_data['zone_distribution'][activity.get('activityId')] = details.get('timeInHrZones')
                except: pass
            
            return weekly_data
        except Exception as e:
            logger.error(f"Failed to get weekly training zones: {e}")
            return {}
    
    def get_breathing_activities(self, start_date, end_date):
        """Get breathing and wellness activities specifically"""
        try:
            activities = self.get_activities_daterange(start_date, end_date)
            breathing_activities = []
            
            for activity in activities:
                activity_type = activity.get('activityType', {}).get('typeKey', '').lower()
                activity_name = activity.get('activityName', '').lower()
                
                # Look for breathing, wellness, and recovery activities
                if any(keyword in activity_type or keyword in activity_name for keyword in 
                       ['breath', 'meditation', 'yoga', 'wellness', 'recovery', 'whm']):
                    
                    # Get detailed activity data
                    detailed = self.get_activity_details_enhanced(activity.get('activityId'))
                    breathing_activities.append({
                        'activity_id': activity.get('activityId'),
                        'date': activity.get('startTimeLocal', '')[:10],
                        'activity_name': activity.get('activityName'),
                        'activity_type': activity_type,
                        'duration_minutes': activity.get('duration', 0) / 60000 if activity.get('duration') else 0,
                        'calories': activity.get('calories'),
                        'avg_heart_rate': activity.get('averageHR'),
                        'max_heart_rate': activity.get('maxHR'),
                        'start_time': activity.get('startTimeLocal'),
                        'activity_details': detailed
                    })
            
            logger.info(f"Found {len(breathing_activities)} breathing/wellness activities")
            return breathing_activities
        except Exception as e:
            logger.error(f"Failed to get breathing activities: {e}")
            return []
    
    def get_detailed_respiration(self, target_date):
        """Get comprehensive respiration data for a specific date"""
        try:
            iso_date = target_date.isoformat()
            resp_data = self.api.get_respiration_data(iso_date)
            
            if not resp_data:
                return None
                
            return {
                'date': iso_date,
                'avg_sleep_respiration': resp_data.get('avgSleepRespirationValue'),
                'avg_waking_respiration': resp_data.get('avgWakingRespirationValue'),
                'highest_respiration': resp_data.get('highestRespirationValue'),
                'lowest_respiration': resp_data.get('lowestRespirationValue'),
                'respiration_range': resp_data.get('highestRespirationValue', 0) - resp_data.get('lowestRespirationValue', 0) if resp_data.get('highestRespirationValue') and resp_data.get('lowestRespirationValue') else None,
                'respiration_values_array': resp_data.get('respirationValuesArray', []),
                'respiration_averages_array': resp_data.get('respirationAveragesValuesArray', [])
            }
        except Exception as e:
            logger.warning(f"Could not get detailed respiration for {target_date}: {e}")
            return None
