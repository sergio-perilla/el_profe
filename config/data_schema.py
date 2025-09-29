# CSV column definitions for activity-specific data structure

# Core fields present in ALL activity types
CORE_ACTIVITY_COLUMNS = [
    'date', 'activity_id', 'activity_type', 'duration_seconds', 'calories',
    'avg_hr', 'max_hr', 'hr_zone_1_time', 'hr_zone_2_time', 'hr_zone_3_time', 
    'hr_zone_4_time', 'hr_zone_5_time', 'training_effect_aerobic', 
    'training_effect_anaerobic', 'recovery_time_hrs', 'stress_start', 
    'stress_end', 'stress_change', 'body_battery_impact'
]

# Activity-specific column definitions
SURFING_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'distance_meters', 'max_speed_kmh', 'avg_speed_kmh',
    'total_waves', 'longest_wave_seconds', 'total_surf_time_seconds',
    'paddle_time_seconds', 'surf_vs_paddle_ratio', 'avg_wave_speed',
    'avg_wave_distance', 'wave_frequency_per_hour', 'session_rating'
]

SWIMMING_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'distance_meters', 'pool_size_meters', 'total_strokes', 'avg_swolf', 
    'avg_stroke_rate_spm', 'avg_distance_per_stroke', 'stroke_type_primary',
    'total_lengths', 'total_intervals', 'rest_time_seconds', 'drill_time_seconds',
    'avg_pace_per_100m', 'css_pace_per_100m', 'stroke_efficiency_score', 'is_open_water'
]

RUNNING_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'distance_meters', 'avg_pace_per_km', 'avg_cadence_spm', 'avg_stride_length',
    'vertical_oscillation_cm', 'ground_contact_time_ms', 'running_power_watts',
    'elevation_gain_meters', 'elevation_loss_meters', 'avg_temperature',
    'lactate_threshold_hr', 'running_dynamics_score', 'is_treadmill'
]

STRENGTH_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'total_sets', 'total_reps', 'total_volume_kg', 'avg_rest_seconds',
    'max_weight_kg', 'primary_muscle_groups', 'exercise_count', 
    'workout_type', 'compound_vs_isolation_ratio', 'training_focus'
]

BREATHWORK_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'whm_rounds_total', 'whm_total_breaths', 'whm_max_breath_hold',
    'whm_max_breath_hold_stage2', 'whm_round_details', 'avg_respiration_rate',
    'min_respiration_rate', 'max_respiration_rate', 'technique_type',
    'breath_hold_improvement', 'session_intensity'
]

RECOVERY_ACTIVITY_COLUMNS = CORE_ACTIVITY_COLUMNS + [
    'session_type', 'temperature_celsius', 'humidity_percent', 'rounds_completed',
    'total_heat_time_seconds', 'total_cool_time_seconds', 'avg_temperature',
    'recovery_rating', 'hydration_level', 'location'
]

# Body composition data (new)
BODY_COMPOSITION_COLUMNS = [
    'date', 'time', 'weight_kg', 'bmi', 'body_fat_percent',
    'muscle_mass_kg', 'bone_mass_kg', 'body_water_percent',
    'visceral_fat_level', 'metabolic_age', 'protein_percent',
    'subcutaneous_fat_percent', 'skeletal_muscle_mass_kg',
    'basal_metabolic_rate', 'body_type', 'measurement_source'
]

# Enhanced GitHub/coding data
CODING_ACTIVITY_COLUMNS = [
    'date', 'commits_count', 'repos_active', 'lines_added', 'lines_deleted',
    'first_commit_time', 'last_commit_time', 'work_span_hours', 'commit_frequency',
    'focus_score', 'primary_language', 'primary_category', 'languages_count',
    'late_night_commits', 'is_weekend', 'repos_list', 'coding_intensity_score'
]

# Existing schemas (unchanged)
DAILY_HEALTH_COLUMNS = [
    'date', 'body_battery_start', 'body_battery_end', 'body_battery_charged',
    'body_battery_drained', 'sleep_score', 'deep_sleep_minutes', 'rem_sleep_minutes',
    'light_sleep_minutes', 'awake_minutes', 'sleep_efficiency', 'sleep_start_time',
    'sleep_end_time', 'hrv_during_sleep', 'hrv_status', 'hrv_overnight_avg', 
    'hrv_weekly_avg', 'hrv_7_day_trend', 'stress_avg', 'stress_max', 'steps', 
    'floors_climbed', 'active_calories', 'avg_respiration_rate', 'spo2_avg',
    'resting_heart_rate', 'sleep_need_baseline', 'sleep_need_actual', 'sleep_feedback',
    'breathing_disruption_severity', 'detailed_avg_sleep_respiration', 
    'detailed_avg_waking_respiration', 'detailed_highest_respiration', 
    'detailed_lowest_respiration', 'respiration_range'
]

PHYSIOLOGICAL_COLUMNS = [
    'date', 'vo2_max_running', 'vo2_max_cycling', 'fitness_age', 'training_status',
    'training_load_7day', 'training_load_focus', 'recovery_advisor', 'performance_condition',
    'training_load_aerobic_low', 'training_load_aerobic_high', 'training_load_anaerobic',
    'training_load_aerobic_low_target_min', 'training_load_aerobic_low_target_max',
    'training_load_aerobic_high_target_min', 'training_load_aerobic_high_target_max',
    'training_load_anaerobic_target_min', 'training_load_anaerobic_target_max',
    'training_balance_feedback', 'altitude_acclimatization', 'heat_acclimatization'
]

WEEKLY_TRAINING_ZONES_COLUMNS = [
    'week_start_date', 'week_end_date', 'total_training_time_minutes',
    'zone_1_time_minutes', 'zone_1_percentage', 'zone_2_time_minutes', 'zone_2_percentage',
    'zone_3_time_minutes', 'zone_3_percentage', 'zone_4_time_minutes', 'zone_4_percentage',
    'zone_5_time_minutes', 'zone_5_percentage', 'total_swimming_time', 'total_strength_time',
    'total_aerobic_time', 'weekly_training_load', 'weekly_training_stress'
]

RECOVERY_TRENDS_COLUMNS = [
    'date', 'hrv_7_day_avg', 'hrv_14_day_avg', 'hrv_30_day_avg', 'hrv_trend_direction',
    'sleep_efficiency_7_day_avg', 'sleep_efficiency_14_day_avg', 'sleep_score_7_day_avg',
    'sleep_score_14_day_avg', 'rhr_7_day_avg', 'rhr_14_day_avg', 'rhr_trend_direction',
    'body_battery_avg_7_day', 'stress_avg_7_day', 'recovery_score', 'training_readiness'
]

STRENGTH_EXERCISE_COLUMNS = [
    'date', 'activity_id', 'exercise_name', 'exercise_category', 'set_number', 
    'weight_kg', 'reps', 'duration_seconds', 'rest_seconds', 'difficulty_level',
    'volume_kg', 'equipment_used', 'exercise_notes'
]

SYNC_LOG_COLUMNS = [
    'timestamp', 'data_type', 'last_sync_date', 'records_added', 'status', 'error_message'
]

# Activity type mapping for CSV routing
ACTIVITY_TYPE_MAPPING = {
    'surfing': ('surfing_activities.csv', SURFING_ACTIVITY_COLUMNS),
    'swimming': ('swimming_activities.csv', SWIMMING_ACTIVITY_COLUMNS),
    'running': ('running_activities.csv', RUNNING_ACTIVITY_COLUMNS),
    'strength': ('strength_activities.csv', STRENGTH_ACTIVITY_COLUMNS),
    'breathwork': ('breathwork_activities.csv', BREATHWORK_ACTIVITY_COLUMNS),
    'recovery': ('recovery_activities.csv', RECOVERY_ACTIVITY_COLUMNS)
}

SUPPLEMENT_INTAKE_COLUMNS = [
    'date', 'timestamp', 'supplement_name', 'amount', 'unit', 'notes', 'user_id'
]

# Food intake data
FOOD_INTAKE_COLUMNS = [
    'date', 'timestamp', 'meal_description', 'estimated_meal_type', 'notes', 'user_id'
]

# Daily notes data  
DAILY_NOTES_COLUMNS = [
    'date', 'timestamp', 'note_content', 'potential_mood_indicators', 'user_id'
]

BODY_COMPOSITION_COLUMNS = [
    'date', 'time', 'timestamp', 'weight_kg', 'bmi', 'body_fat_percent',
    'muscle_mass_kg', 'bone_mass_kg', 'body_water_percent',
    'visceral_fat_level', 'metabolic_age', 'protein_percent',
    'subcutaneous_fat_percent', 'skeletal_muscle_mass_kg',
    'basal_metabolic_rate', 'body_type_score', 'measurement_source',
    'scale_model', 'user_profile', 'measurement_quality'
]