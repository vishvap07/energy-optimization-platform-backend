import re
from fuzzywuzzy import fuzz

def auto_assign_priority(title, description, category):
    """
    Automatically assigns a priority level based on keywords and category.
    Uses fuzzy matching to handle typos (e.g., 'faliure' -> 'failure').
    """
    text = (title + " " + description).lower()
    words = text.split()
    
    # Critical Keywords
    critical_keywords = ['fire', 'smoke', 'explosion', 'dangerous', 'emergency', 'shock', 'leak', 'hazard', 'outage', 'blackout']
    
    # High Keywords
    high_keywords = ['broken', 'failure', 'crashed', 'stuck', 'urgent', 'immediate', 'error', 'stop', 'down']
    
    # Medium Keywords
    medium_keywords = ['slow', 'problem', 'issue', 'incorrect', 'update', 'change', 'request', 'help']

    # 1. Check Category first
    if category.lower() in ['safety', 'fire safety', 'emergency']:
        return 'critical'
    if category.lower() in ['system failure', 'hardware failure']:
        return 'high'
    
    # Helper to check fuzzy match in text
    def has_match(word_list, target_text, threshold=85):
        # Check exact matches first
        for kw in word_list:
            if kw in target_text:
                return True
        # Check fuzzy matches for each word in input
        for word in words:
            for kw in word_list:
                if fuzz.ratio(word, kw) >= threshold:
                    return True
        return False

    # 2. Check for Critical keywords
    if has_match(critical_keywords, text):
        return 'critical'
            
    # 3. Check for High keywords
    if has_match(high_keywords, text):
        return 'high'
            
    # 4. Check for Medium keywords
    if has_match(medium_keywords, text):
        return 'medium'
            
    # Default
    return 'low'
