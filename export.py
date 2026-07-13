import json
import db
import os

def export_data():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {"monthlyBudget": 0, "budgets": {}}
        
    # Remove sensitive token from frontend config
    if "telegram_token" in config:
        del config["telegram_token"]
        
    rows = db.all_rows()
    
    js_content = f"window.EXPENSE_DATA = {json.dumps(rows, indent=2)};\n"
    js_content += f"window.EXPENSE_CONFIG = {json.dumps(config, indent=2)};\n"
    
    with open("data.js", "w", encoding="utf-8") as f:
        f.write(js_content)
        
if __name__ == "__main__":
    export_data()
