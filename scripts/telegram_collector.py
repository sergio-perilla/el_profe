#!/usr/bin/env python3
"""
Simple Telegram message collector for daily batch processing
Replaces the complex real-time bot with simple API calls

Supports:
- Performance ratings (work, social, cognitive clarity)
- Caffeine intake (espresso shots)
- Alcohol intake (standard drinks)
- Supplement intake (any supplement with dosage)
- Food intake tracking
- Daily notes
"""

import requests
import re
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class TelegramCollector:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def get_updates(self, offset: Optional[int] = None) -> List[Dict]:
        """Get unprocessed messages from Telegram"""
        try:
            params = {'timeout': 10}
            if offset:
                params['offset'] = offset
            
            response = requests.get(f"{self.base_url}/getUpdates", params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get('ok'):
                return data.get('result', [])
            else:
                logger.error(f"Telegram API error: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get Telegram updates: {e}")
            return []
    
    def parse_message_type(self, text: str) -> str:
        """Determine what type of data this message contains"""
        text = text.strip().lower()
        
        # Check for food entries (most specific patterns first)
        if re.search(r'^(food|comida):', text):
            return 'food'
        
        # Check for notes
        if re.search(r'^note:', text):
            return 'note'
        
        # Check for supplement intake
        if self._looks_like_supplement(text):
            return 'supplement'
        
        # Check for alcohol
        alcohol_keywords = ['drink', 'drinks', 'beer', 'wine', 'alcohol', 'whiskey', 'vodka', 'rum', 'gin']
        # Distinguish between alcohol shot and espresso shot
        if any(keyword in text for keyword in alcohol_keywords):
            return 'alcohol'
        elif 'shot' in text and not any(caf in text for caf in ['espresso', 'coffee', 'caffeine']):
            return 'alcohol'
        
        # Check for caffeine
        caffeine_keywords = ['espresso', 'coffee', 'caffeine', 'café']
        if any(keyword in text for keyword in caffeine_keywords) or ('shot' in text and any(caf in text for caf in ['espresso', 'coffee'])):
            return 'caffeine'
        
        # Check for performance ratings (3 numbers pattern)
        if self._looks_like_rating(text):
            return 'rating'
        
        return 'unknown'

    def _looks_like_supplement(self, text: str) -> bool:
        """Check if text looks like supplement intake"""
        # Common supplement keywords
        supplement_keywords = [
            'mg', 'gram', 'grams', 'iu', 'mcg', 'supplement', 'vitamin', 
            'creatine', 'magnesium', 'zinc', 'iron', 'calcium', 'potassium',
            'vitamin d', 'vitamin c', 'vitamin b', 'omega', 'fish oil',
            'protein', 'bcaa', 'glutamine', 'beta-alanine', 'citrulline',
            'ashwagandha', 'turmeric', 'curcumin', 'ginkgo', 'ginseng',
            'melatonin', 'probiotics', 'multivitamin', 'gummy', 'gummies',
            'tablet', 'tablets', 'capsule', 'capsules', 'pill', 'pills'
        ]
        
        # Check for supplement keywords + dosage pattern
        has_supplement_keyword = any(keyword in text for keyword in supplement_keywords)
        has_dosage_pattern = bool(re.search(r'\d+\s*(mg|gram|grams|g|iu|mcg|ml)', text))
        
        return has_supplement_keyword and has_dosage_pattern

    def parse_supplement(self, text: str) -> Optional[Dict]:
        """Parse supplement intake from text - generalized for any supplement"""
        text = text.strip().lower()
        
        # Pattern to extract supplement name, amount, and unit
        # Examples: "creatine 5g", "magnesium 400mg", "vitamin d 2000iu", "ashwagandha 300mg"
        patterns = [
            r'(\w+(?:\s+\w+)*)\s+(\d+)\s*(mg|gram|grams|g|iu|mcg|ml)',  # "supplement name 500mg"
            r'(\d+)\s*(mg|gram|grams|g|iu|mcg|ml)\s+(\w+(?:\s+\w+)*)',  # "500mg supplement name"
            r'(\d+)\s*(mg|gram|grams|g|iu|mcg|ml)\s+of\s+(\w+(?:\s+\w+)*)',  # "500mg of supplement"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                
                # Determine which group is amount, unit, supplement
                if len(groups) == 3:
                    if groups[1].isdigit():  # Pattern 1: name amount unit
                        supplement_name, amount_str, unit = groups
                        amount = int(amount_str)
                    else:  # Pattern 2 or 3: amount unit name
                        amount_str, unit, supplement_name = groups
                        amount = int(amount_str)
                        
                    # Normalize unit
                    unit = unit.lower()
                    if unit in ['gram', 'grams', 'g']:
                        unit = 'g'
                        amount = amount * 1000 if unit == 'g' and amount < 50 else amount  # Convert g to mg for small amounts
                        unit = 'mg'
                    elif unit in ['iu']:
                        unit = 'IU'
                    elif unit in ['mcg']:
                        unit = 'mcg'
                    else:
                        unit = 'mg'
                    
                    # Clean supplement name
                    supplement_name = supplement_name.strip()
                    supplement_name = re.sub(r'\b(tablet|tablets|capsule|capsules|pill|pills|gummy|gummies)\b', '', supplement_name).strip()
                    
                    # Validate reasonable ranges
                    if 1 <= amount <= 50000:  # Reasonable supplement range
                        # Extract notes (remove the matched part)
                        notes = re.sub(pattern, '', text).strip()
                        notes = re.sub(r'\s+', ' ', notes)
                        
                        return {
                            'supplement_name': supplement_name.title(),
                            'amount': amount,
                            'unit': unit,
                            'notes': notes if notes else ''
                        }
        
        # Fallback: look for common supplement names with numbers
        supplement_fallbacks = {
            'creatine': ('creatine', 'mg'),
            'magnesium': ('magnesium', 'mg'),
            'zinc': ('zinc', 'mg'),
            'vitamin d': ('vitamin d', 'IU'),
            'vitamin c': ('vitamin c', 'mg'),
            'omega': ('omega-3', 'mg'),
            'fish oil': ('fish oil', 'mg'),
            'protein': ('protein powder', 'g'),
            'melatonin': ('melatonin', 'mg'),
            'ashwagandha': ('ashwagandha', 'mg'),
            'turmeric': ('turmeric', 'mg'),
            'multivitamin': ('multivitamin', 'tablet')
        }
        
        for supplement_key, (supplement_name, default_unit) in supplement_fallbacks.items():
            if supplement_key in text:
                # Extract number near the supplement name
                numbers = re.findall(r'\d+', text)
                if numbers:
                    amount = int(numbers[0])
                    if 1 <= amount <= 50000:
                        return {
                            'supplement_name': supplement_name.title(),
                            'amount': amount,
                            'unit': default_unit,
                            'notes': ''
                        }
        
        return None

    def parse_food(self, text: str) -> Optional[Dict]:
        """Parse food intake from text"""
        text = text.strip()
        original_text = text  # Keep original case for meal description
        text_lower = text.lower()
        
        # Patterns for food entries
        patterns = [
            r'^food:\s*(.+)$',
            r'^comida:\s*(.+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                meal_description = match.group(1).strip()
                if meal_description:
                    # Extract from original text to preserve case
                    original_match = re.search(pattern, original_text, re.IGNORECASE)
                    if original_match:
                        meal_description = original_match.group(1).strip()
                    
                    # Simple meal type estimation based on keywords
                    estimated_meal_type = self._estimate_meal_type(text_lower)
                    
                    return {
                        'meal_description': meal_description,
                        'estimated_meal_type': estimated_meal_type,
                        'notes': ''
                    }
        
        return None

    def parse_note(self, text: str) -> Optional[Dict]:
        """Parse notes from text"""
        text = text.strip()
        original_text = text  # Keep original case for note content
        text_lower = text.lower()
        
        # Pattern for notes
        pattern = r'^note:\s*(.+)$'
        match = re.search(pattern, text_lower)
        
        if match:
            note_content = match.group(1).strip()
            if note_content:
                # Extract from original text to preserve case
                original_match = re.search(pattern, original_text, re.IGNORECASE)
                if original_match:
                    note_content = original_match.group(1).strip()
                
                # Simple mood indicator detection
                mood_indicators = self._detect_mood_indicators(text_lower)
                
                return {
                    'note_content': note_content,
                    'potential_mood_indicators': mood_indicators
                }
        
        return None

    def _estimate_meal_type(self, text: str) -> str:
        """Estimate meal type based on keywords and timing"""
        breakfast_keywords = ['breakfast', 'desayuno', 'cereal', 'oatmeal', 'eggs', 'toast', 'coffee']
        lunch_keywords = ['lunch', 'almuerzo', 'sandwich', 'salad', 'ensalada']
        dinner_keywords = ['dinner', 'cena', 'pasta', 'rice', 'arroz', 'meat', 'chicken', 'fish']
        snack_keywords = ['snack', 'merienda', 'fruit', 'nuts', 'bar']
        
        if any(keyword in text for keyword in breakfast_keywords):
            return 'breakfast'
        elif any(keyword in text for keyword in lunch_keywords):
            return 'lunch'
        elif any(keyword in text for keyword in dinner_keywords):
            return 'dinner'
        elif any(keyword in text for keyword in snack_keywords):
            return 'snack'
        else:
            return 'unknown'

    def _detect_mood_indicators(self, text: str) -> str:
        """Detect potential mood indicators in notes"""
        positive_keywords = ['good', 'great', 'amazing', 'happy', 'excited', 'calm', 'focused', 'clarity', 'energized']
        negative_keywords = ['tired', 'anxious', 'stressed', 'frustrated', 'sad', 'angry', 'worried', 'confused']
        neutral_keywords = ['okay', 'normal', 'fine', 'average']
        
        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)
        neutral_count = sum(1 for keyword in neutral_keywords if keyword in text)
        
        if positive_count > negative_count and positive_count > neutral_count:
            return 'positive'
        elif negative_count > positive_count and negative_count > neutral_count:
            return 'negative'
        elif neutral_count > 0:
            return 'neutral'
        else:
            return 'unknown'

    def _looks_like_rating(self, text: str) -> bool:
        """Check if text looks like a performance rating"""
        # Simple three numbers pattern
        if re.search(r'(\d+)[\s,\-]+(\d+)[\s,\-]+(\d+)', text):
            return True
        
        # Named format
        work_match = re.search(r'work:?\s*(\d+)', text)
        social_match = re.search(r'social:?\s*(\d+)', text)
        clarity_match = re.search(r'(?:clarity|focus|mental):?\s*(\d+)', text)
        
        return bool(work_match and social_match and clarity_match)
    
    def parse_rating(self, text: str) -> Optional[Dict]:
        """Parse performance rating from text"""
        text = text.strip().lower()
        
        # Pattern 1: Simple three numbers
        simple_pattern = r'(\d+)[\s,\-]+(\d+)[\s,\-]+(\d+)'
        match = re.search(simple_pattern, text)
        if match:
            return {
                'work_motivation': int(match.group(1)),
                'social_energy': int(match.group(2)),
                'cognitive_clarity': int(match.group(3)),
                'notes': ''
            }
        
        # Pattern 2: Named format
        work_match = re.search(r'work:?\s*(\d+)', text)
        social_match = re.search(r'social:?\s*(\d+)', text)
        clarity_match = re.search(r'(?:clarity|focus|mental):?\s*(\d+)', text)
        
        if work_match and social_match and clarity_match:
            return {
                'work_motivation': int(work_match.group(1)),
                'social_energy': int(social_match.group(1)),
                'cognitive_clarity': int(clarity_match.group(1)),
                'notes': ''
            }
        
        # Pattern 3: Just numbers in order
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 3:
            return {
                'work_motivation': int(numbers[0]),
                'social_energy': int(numbers[1]),
                'cognitive_clarity': int(numbers[2]),
                'notes': ''
            }
        
        return None
    
    def parse_caffeine(self, text: str) -> Optional[Dict]:
        """Parse caffeine intake from text"""
        text = text.strip().lower()
        
        # Patterns for espresso/coffee
        patterns = [
            r'(\d+)\s*(?:espresso|espressos)',
            r'(\d+)\s*(?:shot|shots)',  # Only if coffee context
            r'(\d+)\s*(?:café|coffee|caffeine)',
            r'espresso\s*(\d+)',
            r'shot\s*(\d+)'  # Only if coffee context
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                shots = int(match.group(1))
                if 1 <= shots <= 20:  # Reasonable range
                    # Extract notes (remove the matched part)
                    notes = re.sub(pattern, '', text).strip()
                    notes = re.sub(r'\s+', ' ', notes)  # Clean up spaces
                    return {
                        'espresso_shots': shots,
                        'notes': notes if notes else ''
                    }
        
        return None
    
    def parse_alcohol(self, text: str) -> Optional[Dict]:
        """Parse alcohol intake from text"""
        text = text.strip().lower()
        
        # Patterns for standard drinks
        patterns = [
            r'(\d+)\s*(?:drink|drinks)',
            r'(\d+)\s*(?:beer|beers)',
            r'(\d+)\s*(?:wine|wines|glass|glasses)',
            r'(\d+)\s*(?:shot|shots)(?!\s*(?:espresso|coffee))',  # Not coffee shots
            r'(\d+)\s*(?:whiskey|vodka|rum|gin|bourbon)',
            r'drink\s*(\d+)',
            r'beer\s*(\d+)',
            r'wine\s*(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                drinks = int(match.group(1))
                if 1 <= drinks <= 20:  # Reasonable range
                    # Extract notes
                    notes = re.sub(pattern, '', text).strip()
                    notes = re.sub(r'\s+', ' ', notes)
                    return {
                        'standard_drinks': drinks,
                        'notes': notes if notes else ''
                    }
        
        # Check for alcohol keywords with numbers
        if any(keyword in text for keyword in ['alcohol', 'drink', 'beer', 'wine']):
            numbers = re.findall(r'\d+', text)
            if numbers:
                drinks = int(numbers[0])
                if 1 <= drinks <= 20:
                    return {
                        'standard_drinks': drinks,
                        'notes': ''
                    }
        
        return None
    
    def collect_daily_messages(self) -> Dict[str, List[Dict]]:
        """Collect and parse all unprocessed messages"""
        updates = self.get_updates()
        
        data = {
            'ratings': [],
            'caffeine': [],
            'alcohol': [],
            'supplements': [], 
            'food': [],
            'notes': []
        }
        
        processed_count = {'ratings': 0, 'caffeine': 0, 'alcohol': 0, 'supplements': 0, 'food': 0, 'notes': 0, 'unknown': 0}
        
        for update in updates:
            try:
                message = update.get('message', {})
                text = message.get('text', '').strip()
                user_id = message.get('from', {}).get('id')
                
                # Convert Telegram timestamp to datetime
                from datetime import timezone, timedelta
                # Convert UTC to Pacific Time (UTC-7 for PDT, UTC-8 for PST)
                timestamp = datetime.fromtimestamp(message.get('date', 0), tz=timezone.utc)
                pacific_offset = timedelta(hours=-7)  # PDT offset
                timestamp = timestamp + pacific_offset
                
                if not text or not user_id:
                    continue
                
                message_type = self.parse_message_type(text)
                
                if message_type == 'rating':
                    rating_data = self.parse_rating(text)
                    if rating_data:
                        # Validate ranges
                        if all(1 <= val <= 10 for val in rating_data.values() if isinstance(val, int)):
                            rating_data.update({
                                'date': timestamp.date().isoformat(),
                                'timestamp': timestamp.isoformat(),
                                'user_id': str(user_id)
                            })
                            data['ratings'].append(rating_data)
                            processed_count['ratings'] += 1
                
                elif message_type == 'caffeine':
                    caffeine_data = self.parse_caffeine(text)
                    if caffeine_data:
                        caffeine_data.update({
                            'date': timestamp.date().isoformat(),
                            'timestamp': timestamp.isoformat(),
                            'user_id': str(user_id)
                        })
                        data['caffeine'].append(caffeine_data)
                        processed_count['caffeine'] += 1
                
                elif message_type == 'alcohol':
                    alcohol_data = self.parse_alcohol(text)
                    if alcohol_data:
                        alcohol_data.update({
                            'date': timestamp.date().isoformat(),
                            'timestamp': timestamp.isoformat(),
                            'user_id': str(user_id)
                        })
                        data['alcohol'].append(alcohol_data)
                        processed_count['alcohol'] += 1
                
                elif message_type == 'supplement': 
                    supplement_data = self.parse_supplement(text)
                    if supplement_data:
                        supplement_data.update({
                            'date': timestamp.date().isoformat(),
                            'timestamp': timestamp.isoformat(),
                            'user_id': str(user_id)
                        })
                        data['supplements'].append(supplement_data)
                        processed_count['supplements'] += 1
                
                elif message_type == 'food':
                    food_data = self.parse_food(text)
                    if food_data:
                        food_data.update({
                            'date': timestamp.date().isoformat(),
                            'timestamp': timestamp.isoformat(),
                            'user_id': str(user_id)
                        })
                        data['food'].append(food_data)
                        processed_count['food'] += 1
                
                elif message_type == 'note':
                    note_data = self.parse_note(text)
                    if note_data:
                        note_data.update({
                            'date': timestamp.date().isoformat(),
                            'timestamp': timestamp.isoformat(),
                            'user_id': str(user_id)
                        })
                        data['notes'].append(note_data)
                        processed_count['notes'] += 1
                
                else:
                    processed_count['unknown'] += 1
                    logger.debug(f"Unknown message type: '{text}'")
                    
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        # Log summary
        total_processed = sum(processed_count.values())
        if total_processed > 0:
            logger.info(f"📱 Processed {total_processed} Telegram messages:")
            for data_type, count in processed_count.items():
                if count > 0:
                    logger.info(f"  {data_type}: {count}")
        else:
            logger.info("📱 No new Telegram messages found")
        
        return data


def collect_telegram_data(bot_token: str) -> Dict[str, List[Dict]]:
    """Main function to collect all Telegram data"""
    if not bot_token:
        logger.warning("No Telegram bot token provided")
        return {'ratings': [], 'caffeine': [], 'alcohol': [], 'supplements': []}
    
    collector = TelegramCollector(bot_token)
    return collector.collect_daily_messages()


if __name__ == "__main__":
    import os
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Please set TELEGRAM_BOT_TOKEN environment variable")
        exit(1)
    
    # Test the collector
    data = collect_telegram_data(token)
    print(f"Collected data: {data}")