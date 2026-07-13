import re
import json

def get_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def parse_amount(text):
    text_clean = text.lower().replace(",", "")
    amount_pattern = r"(?:rs\.?|₹)?\s*([\d\.]+)\s*(k|l|rs)?\b"
    matches = list(re.finditer(amount_pattern, text_clean))
    
    if not matches:
        return None, text
        
    match = matches[0]
    val = float(match.group(1))
    modifier = match.group(2)
    
    if modifier == 'k':
        val *= 1000
    elif modifier == 'l':
        val *= 100000
        
    note = text_clean[:match.start()] + text_clean[match.end():]
    note = re.sub(r'\s+', ' ', note).strip()
    return val, note

def get_category(text, config):
    text_lower = text.lower()
    categories = config.get("category_keywords", {})
    for cat, keywords in categories.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "other"

def parse_message(message):
    message_lower = message.lower()
    config = get_config()
    income_kw = config.get("income_keywords", [])
    
    txn_type = "expense"
    if any(kw in message_lower for kw in income_kw):
        txn_type = "income"
        
    amount, note = parse_amount(message_lower)
    if amount is None:
        return None
        
    category = get_category(note, config)
    
    # Check for split
    split_people = []
    if " me, " in note or " me " in note and (" and " in note or "," in note):
        parts = re.split(r'me\s*[,|and]', note)
        if len(parts) > 1:
            people_str = parts[1]
            split_people = [p.strip() for p in re.split(r',|and', people_str) if p.strip()]
            
    return {
        "amount": amount,
        "category": category,
        "note": note,
        "type": txn_type,
        "split_people": split_people
    }
