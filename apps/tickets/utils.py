import re

def auto_assign_priority(title, description, category):
    """
    Automatically assigns a priority level based on keywords and category.
    """
    text = (title + " " + description).lower()
    
    # Critical Keywords (Safety, Fire, Immediate Danger)
    critical_keywords = [
        r'\bfire\b', r'\bsmoke\b', r'\bexplosion\b', r'\bdangerous\b', 
        r'\bemergency\b', r'\bshock\b', r'\bleak\b', r'\bhazard\b',
        r'\boutage\b', r'\bblackout\b'
    ]
    
    # High Keywords (System failures, broken hardware, urgent issues)
    high_keywords = [
        r'\bbroken\b', r'\bfailure\b', r'\bcrashed\b', r'\bstuck\b', 
        r'\burgent\b', r'\bimmediate\b', r'\bcannot login\b', r'\berror\b',
        r'\bnot working\b', r'\bstop\b', r'\bdown\b'
    ]
    
    # Medium Keywords (Performance issues, minor bugs, help requests)
    medium_keywords = [
        r'\bslow\b', r'\bproblem\b', r'\bissue\b', r'\bincorrect\b', 
        r'\bupdate\b', r'\bchange\b', r'\brequest\b', r'\bhelp\b'
    ]

    # 1. Check Category first (Category takes precedence for certain types)
    if category.lower() in ['safety', 'fire safety', 'emergency']:
        return 'critical'
    if category.lower() in ['system failure', 'hardware failure']:
        return 'high'
    
    # 2. Check for Critical keywords
    for pattern in critical_keywords:
        if re.search(pattern, text):
            return 'critical'
            
    # 3. Check for High keywords
    for pattern in high_keywords:
        if re.search(pattern, text):
            return 'high'
            
    # 4. Check for Medium keywords
    for pattern in medium_keywords:
        if re.search(pattern, text):
            return 'medium'
            
    # Default
    return 'low'
