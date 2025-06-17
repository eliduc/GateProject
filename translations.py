import os
import pandas as pd

def load_translations(file_path, lang):
    """
    Load translations from the markdown file for the specified language.
    
    Args:
        file_path: Path to the translation markdown file
        lang: Language code (EN, IT, RU, IL, HB)
    
    Returns:
        Dictionary mapping phrase IDs to translations
    """
    try:
        # Normalize Hebrew language code
        if lang == 'HB':
            lang = 'IL'
            
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(script_dir, file_path)
        
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.readlines()

        headers = [h.strip() for h in content[0].split('|') if h.strip()]
        data = []
        for line in content[2:]:  # Skip the header separator line
            row = [cell.strip() for cell in line.split('|') if cell.strip()]
            if len(row) == len(headers):
                data.append(row)

        df = pd.DataFrame(data, columns=headers)
        
        # Check if the requested language exists, otherwise default to English
        if lang not in df.columns:
            print(f"Language '{lang}' not found. Available languages: {list(df.columns)}")
            print(f"Defaulting to English.")
            lang = 'EN'
        
        # Ensure all keys are strings
        translations = dict(zip(df['Phrase ID'].astype(str), df[lang]))
        return translations
    except Exception as e:
        print(f"An error occurred while loading translations: {str(e)}")
        return {}

def get_message(phrase_id, translations):
    """
    Get a translated message by phrase ID.
    
    Args:
        phrase_id: The ID of the phrase to retrieve
        translations: Dictionary of translations
    
    Returns:
        Translated message or error message if not found
    """
    # Convert phrase_id to string to ensure consistent lookup
    phrase_id_str = str(phrase_id)
    return translations.get(phrase_id_str, f"Missing translation for phrase ID {phrase_id}")

# Cache for translations
_translation_cache = {}

def get_translations_cached(file_path, lang):
    """
    Get translations with caching to improve performance.
    This function accepts file_path for compatibility but always uses 'gate_project_translations.md'
    
    Args:
        file_path: Path to translation file (kept for compatibility)
        lang: Language code (EN, IT, RU, IL, HB)
    
    Returns:
        Dictionary of translations
    """
    # Normalize Hebrew language code
    if lang == 'HB':
        lang = 'IL'
        
    if lang not in _translation_cache:
        _translation_cache[lang] = load_translations('gate_project_translations.md', lang)
    return _translation_cache[lang]