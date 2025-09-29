# Comprehensive Fitness Data Pipeline

Automated daily sync of multi-source fitness data for comprehensive health and performance analysis.

## Data Sources Integrated

### Core Data (Required)

* **Garmin Connect** : Activities, sleep, HRV, body battery, stress, physiological metrics
* **Eufy Smart Scale P3** : Body composition (weight, body fat %, muscle mass, etc.)

### Optional Data Sources

* **Telegram Bot** : Subjective ratings and notes
* **GitHub** : Coding activity patterns (for knowledge workers)

## Setup Instructions

### 1. Repository Setup

1. Fork this repository
2. Enable GitHub Actions in your repository settings

### 2. Required Environment Variables

Add these secrets in your GitHub repository settings (Settings → Secrets → Actions):

#### Garmin Connect (Required)

```
GARMIN_EMAIL=your-garmin-email@example.com
GARMIN_PASSWORD=your-garmin-password
```

#### Eufy Smart Scale (Required for body composition)

```
EUFY_EMAIL=your-eufy-life-email@example.com
EUFY_PASSWORD=your-eufy-life-password
```

#### Optional Integrations

```
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
_GITHUB_USERNAME=your-github-username
_GITHUB_TOKEN=your-github-personal-access-token
```

### 3. Eufy Smart Scale P3 Setup

1. Ensure your Eufy Smart Scale P3 is set up and connected to the EufyLife app
2. Make regular measurements (the system will automatically collect data from your cloud account)
3. Use the same email/password that you use for the EufyLife mobile app

### 4. First Run (Historical Data Collection)

The system automatically detects if this is your first run and will:

* Collect 30 days of historical data from all sources
* Future runs will only collect the past 14 days for efficiency

### 5. Daily Automation

GitHub Actions will automatically run daily at 1 PM PT to:

* Sync new Garmin activities and health metrics
* Collect new Eufy body composition measurements
* Process and store all data in CSV format
* Commit updates to your repository

## Data Collected

### Training Activities

| Metric              | Description                       | Source |
| ------------------- | --------------------------------- | ------ |
| Activity Type       | Running, swimming, strength, etc. | Garmin |
| Duration & Distance | Time and distance metrics         | Garmin |
| Heart Rate Zones    | Time in zones 1-5                 | Garmin |
| Training Effect     | Aerobic/anaerobic training impact | Garmin |
| Power/Pace          | Performance metrics by sport      | Garmin |

### Recovery & Health Metrics

| Metric                       | Description               | Source |
| ---------------------------- | ------------------------- | ------ |
| HRV (Heart Rate Variability) | 7/14/30 day trends        | Garmin |
| Sleep Score                  | Sleep quality and stages  | Garmin |
| Body Battery                 | Energy reserves tracking  | Garmin |
| Stress Level                 | Daily stress measurements | Garmin |
| Resting Heart Rate           | Recovery indicator        | Garmin |

### Body Composition (Eufy P3)

| Metric        | Description               | Source  |
| ------------- | ------------------------- | ------- |
| Weight        | Daily weight measurements | Eufy P3 |
| Body Fat %    | Body fat percentage       | Eufy P3 |
| Muscle Mass   | Lean muscle mass          | Eufy P3 |
| Bone Mass     | Bone density indicator    | Eufy P3 |
| Body Water %  | Hydration levels          | Eufy P3 |
| Visceral Fat  | Internal fat levels       | Eufy P3 |
| Metabolic Age | Fitness age indicator     | Eufy P3 |
| BMR           | Basal Metabolic Rate      | Eufy P3 |

### Physiological Metrics

| Metric           | Description            | Source |
| ---------------- | ---------------------- | ------ |
| VO2 Max          | Cardiovascular fitness | Garmin |
| Training Status  | Fitness progression    | Garmin |
| Training Load    | Weekly training stress | Garmin |
| Recovery Advisor | Rest recommendations   | Garmin |
| Fitness Age      | Physiological age      | Garmin |

## Optional Data Sources

### Telegram Bot Integration (Optional)

Track subjective data via simple text messages to a Telegram bot:

#### Performance Ratings

```
work: 8, social: 7, clarity: 9
or
8 7 9
```

#### Caffeine Intake

```
2 espresso
3 shots
```

#### Alcohol Intake

```
2 drinks
1 beer
3 wine
```

#### Supplement Intake (Generalized)

```
creatine 5g
magnesium 400mg
vitamin d 2000iu
ashwagandha 300mg
omega-3 1000mg
melatonin 3mg
```

#### Food Tracking

```
food: chicken salad with quinoa
comida: tacos de pollo
```

#### Daily Notes

```
note: feeling great after morning workout, high energy
```

### Data Collected

| Metric              | Description                                              | Example Messages                    |
| ------------------- | -------------------------------------------------------- | ----------------------------------- |
| Performance Ratings | Work motivation, social energy, cognitive clarity (1-10) | `work: 8, social: 7, clarity: 9`  |
| Caffeine Intake     | Espresso shots consumed                                  | `2 espresso`,`3 shots`          |
| Alcohol Intake      | Standard drinks consumed                                 | `2 drinks`,`1 beer`             |
| Supplement Intake   | Any supplement with dosage                               | `creatine 5g`,`magnesium 400mg` |
| Food Intake         | Meal descriptions with type estimation                   | `food: chicken salad`             |
| Daily Notes         | General observations and mood                            | `note: feeling energized`         |

**Supported Supplements:** Creatine, magnesium, vitamin D, zinc, omega-3, protein powder, ashwagandha, turmeric, melatonin, multivitamins, and any supplement with dosage notation (mg, g, IU, mcg).

**Setup:**

1. Create Telegram bot via @BotFather
2. Add `TELEGRAM_BOT_TOKEN` to GitHub secrets
3. Send messages to your bot throughout the day

## File Structure

```
data/
├── activities/           # Sport-specific activity data
│   ├── swimming_activities.csv
│   ├── running_activities.csv
│   ├── strength_activities.csv
│   └── recovery_activities.csv (includes WHM breathwork)
├── health/              # Daily health metrics
│   └── daily_metrics.csv
├── physiological/       # Fitness and training metrics
│   └── vo2_training_status.csv
├── body_composition/    # Eufy scale data
│   └── daily_body_metrics.csv
├── training_zones/      # Weekly training distribution
│   └── weekly_training_zones.csv
├── recovery_trends/     # Recovery analysis
│   └── recovery_trends.csv
└── subjective/          # Optional subjective data
    ├── daily_ratings.csv
    ├── caffeine_intake.csv
    └── daily_notes.csv
```

## Troubleshooting

### Garmin Authentication Issues

* Ensure you can log in to Garmin Connect with your credentials
* Check if your Garmin account has two-factor authentication enabled (may cause issues)

### Eufy Scale Connection Issues

* Verify your scale is connected to WiFi and syncing to the EufyLife app
* Ensure you can see recent measurements in the EufyLife mobile app
* Use the exact same email/password as your EufyLife app account

### Missing Data

* Check the GitHub Actions logs for any error messages
* Verify all required environment variables are set correctly
* The first run collects 30 days of historical data, subsequent runs collect 14 days

## Using with Claude for Analysis

The collected data is structured for easy analysis with Claude:

1. Connect your github repositry to Claude. Make sure to keep .csv linked in github
2. Select relevant CSV files to your Claude conversation
3. Ask Claude to analyze patterns, correlations, and trends in your fitness data

Example analysis prompts:

* "Analyze my HRV trends and their correlation with training load"
* "How does my body composition change relate to my training activities?"
* "What patterns do you see in my recovery metrics and sleep quality?"
