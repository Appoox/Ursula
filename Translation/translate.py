import json
import time
from enum import Enum

# Translation backends
class TranslatorType(Enum):
    GOOGLE = "google"
    MYMEMORY = "mymemory"
    LIBRE = "libre"
    DEEPL = "deepl"
    ANTHROPIC = "anthropic"  # Using Claude API
    AI4BHARAT = "ai4bharat"

# def translate_with_ai4bharat(text)

def translate_with_google(text, source_lang, target_lang):
    """Translate using Google Translate (via deep-translator)"""
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source=source_lang, target=target_lang)
    return translator.translate(text)

def translate_with_mymemory(text, source_lang, target_lang):
    """Translate using MyMemory API (better for Indian languages)"""
    from deep_translator import MyMemoryTranslator
    translator = MyMemoryTranslator(source=source_lang, target=target_lang)
    return translator.translate(text)

def translate_with_libre(text, source_lang, target_lang, api_key=None):
    """Translate using LibreTranslate (open source, self-hostable)"""
    from deep_translator import LibreTranslator
    if api_key:
        translator = LibreTranslator(source=source_lang, target=target_lang, api_key=api_key)
    else:
        # Using public instance
        translator = LibreTranslator(source=source_lang, target=target_lang, 
                                     base_url='https://libretranslate.com/')
    return translator.translate(text)

def translate_with_deepl(text, source_lang, target_lang, api_key):
    """Translate using DeepL API (requires API key, very high quality)"""
    import deepl
    translator = deepl.Translator(api_key)
    result = translator.translate_text(text, source_lang=source_lang.upper(), 
                                       target_lang=target_lang.upper())
    return result.text

def translate_with_anthropic(text, source_lang, target_lang):
    """Translate using Claude API (highest quality, requires API access)"""
    import anthropic
    
    client = anthropic.Anthropic()
    
    # Language name mapping
    lang_names = {
        'ml': 'Malayalam',
        'en': 'English',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
        'bn': 'Bengali',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'zh': 'Chinese'
    }
    
    source_name = lang_names.get(source_lang, source_lang)
    target_name = lang_names.get(target_lang, target_lang)
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": f"Translate this {source_name} text to {target_name}. Provide ONLY the translation, no explanations:\n\n{text}"
            }
        ]
    )
    
    return message.content[0].text.strip()

def translate_transcription(input_file, output_file, target_language, 
                           source_language='en', translator_type=TranslatorType.MYMEMORY,
                           api_key=None):
    """
    Translate transcription JSON while preserving timing and pause information
    
    Parameters:
    - input_file: path to transcription JSON file
    - output_file: path for translated output JSON
    - target_language: target language code (e.g., 'ml' for Malayalam)
    - source_language: source language code (default: 'en')
    - translator_type: TranslatorType enum (GOOGLE, MYMEMORY, LIBRE, DEEPL, ANTHROPIC)
    - api_key: API key for DeepL or LibreTranslate (if required)
    
    Recommended for Malayalam:
    - TranslatorType.MYMEMORY (free, good for Indian languages)
    - TranslatorType.ANTHROPIC (best quality, requires Claude API access)
    - TranslatorType.GOOGLE (fallback)
    
    Language codes:
    - 'ml': Malayalam
    - 'hi': Hindi
    - 'ta': Tamil
    - 'te': Telugu
    - 'bn': Bengali
    - 'kn': Kannada
    - 'es': Spanish
    - 'fr': French
    - 'de': German
    """
    
    print(f"Loading transcription from {input_file}")
    
    # Load original transcription
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Select translator
    print(f"\nUsing translator: {translator_type.value}")
    print(f"Translating from {source_language} to {target_language}...")
    print(f"Total segments to translate: {len(data['transcription'])}")
    
    # Translate each segment
    translated_data = data.copy()
    successful_translations = 0
    failed_translations = 0
    
    for idx, segment in enumerate(translated_data['transcription']):
        print(f"\nTranslating segment {idx + 1}/{len(data['transcription'])}")
        print(f"  Original: {segment['text'][:100]}...")
        
        try:
            # Skip empty or error segments
            if segment['text'] in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
                print(f"  Skipping (no content)")
                continue
            
            # Translate based on selected translator
            if translator_type == TranslatorType.GOOGLE:
                translated_text = translate_with_google(segment['text'], source_language, target_language)
            
            elif translator_type == TranslatorType.MYMEMORY:
                translated_text = translate_with_mymemory(segment['text'], source_language, target_language)
            
            elif translator_type == TranslatorType.LIBRE:
                translated_text = translate_with_libre(segment['text'], source_language, target_language, api_key)
            
            elif translator_type == TranslatorType.DEEPL:
                if not api_key:
                    raise ValueError("DeepL requires an API key")
                translated_text = translate_with_deepl(segment['text'], source_language, target_language, api_key)
            
            elif translator_type == TranslatorType.ANTHROPIC:
                translated_text = translate_with_anthropic(segment['text'], source_language, target_language)
            
            else:
                raise ValueError(f"Unknown translator type: {translator_type}")
            
            # Store both original and translated text
            segment['original_text'] = segment['text']
            segment['text'] = translated_text
            segment['translated_language'] = target_language
            segment['translator_used'] = translator_type.value
            
            print(f"  Translated: {translated_text[:100]}...")
            successful_translations += 1
            
            # Delay to avoid rate limiting
            if translator_type in [TranslatorType.GOOGLE, TranslatorType.MYMEMORY]:
                time.sleep(0.5)
            elif translator_type == TranslatorType.ANTHROPIC:
                time.sleep(0.3)
            
        except Exception as e:
            print(f"  Error translating: {e}")
            segment['translation_error'] = str(e)
            failed_translations += 1
    
    # Add translation metadata
    translated_data['translation_info'] = {
        'source_language': source_language,
        'target_language': target_language,
        'translator': translator_type.value,
        'successful_translations': successful_translations,
        'failed_translations': failed_translations
    }
    
    # Save translated version
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"Translation complete!")
    print(f"Successful: {successful_translations}")
    print(f"Failed: {failed_translations}")
    print(f"Saved to: {output_file}")
    print(f"{'='*70}")
    
    return translated_data

def export_translated_srt(translated_data, output_file):
    """Export translated transcription to SRT subtitle format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(translated_data["transcription"], 1):
            start = item['start_time'].replace('.', ',')
            end = item['end_time'].replace('.', ',')
            
            f.write(f"{idx}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{item['text']}\n\n")
    
    print(f"Translated SRT subtitles saved to {output_file}")

def create_bilingual_srt(translated_data, output_file):
    """Create bilingual SRT with original and translated text"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(translated_data["transcription"], 1):
            start = item['start_time'].replace('.', ',')
            end = item['end_time'].replace('.', ',')
            
            f.write(f"{idx}\n")
            f.write(f"{start} --> {end}\n")
            
            if 'original_text' in item:
                f.write(f"{item['original_text']}\n")
                f.write(f"{item['text']}\n\n")
            else:
                f.write(f"{item['text']}\n\n")
    
    print(f"Bilingual SRT subtitles saved to {output_file}")

def print_translation_summary(translated_data):
    """Print a summary of the translated transcription"""
    print("\n" + "="*70)
    print("TRANSLATED TRANSCRIPTION SUMMARY")
    print("="*70)
    
    if 'translation_info' in translated_data:
        info = translated_data['translation_info']
        print(f"\nSource Language: {info.get('source_language', 'N/A')}")
        print(f"Target Language: {info.get('target_language', 'N/A')}")
        print(f"Translator: {info.get('translator', 'N/A')}")
        print(f"Success Rate: {info.get('successful_translations', 0)}/{translated_data['total_segments']}")
    
    print(f"\nTotal segments: {translated_data['total_segments']}")
    print(f"Total pauses: {translated_data['total_pauses']}")
    
    print("\n" + "-"*70)
    print("Sample segments:")
    print("-"*70)
    
    for item in translated_data["transcription"][:3]:
        print(f"\n[Segment {item['segment']}] {item['start_time']} → {item['end_time']}")
        
        if 'original_text' in item:
            print(f"  Original: {item['original_text']}")
        print(f"  Translated: {item['text']}")
        
        pause = next((p for p in translated_data["pauses"] 
                     if p["after_segment"] == item['segment']), None)
        if pause:
            print(f"  [PAUSE: {pause['duration_seconds']}s]")
    
    print("\n" + "="*70)
