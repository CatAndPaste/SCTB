import json
import os

def load_locale(language_code):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, '..', 'locale', f'{language_code}.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)
