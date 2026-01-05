import json
from deep_translator import GoogleTranslator
import time

def translate_transcription(input_file, output_file, target_language, source_language='en'):
    """
    Translate transcription JSON while preserving timing and pause information
    
    Parameters:
    - input_file: path to transcription JSON file
    - output_file: path for translated output JSON
    - target_language: target language code (e.g., 'es', 'fr', 'de', 'hi', 'zh-CN')
    - source_language: source language code (default: 'en')
    
    Common language codes:
    - 'es': Spanish
    - 'fr': French
    - 'de': German
    - 'it': Italian
    - 'pt': Portuguese
    - 'ru': Russian
    - 'ja': Japanese
    - 'ko': Korean
    - 'zh-CN': Chinese (Simplified)
    - 'zh-TW': Chinese (Traditional)
    - 'ar': Arabic
    - 'hi': Hindi
    - 'bn': Bengali
    - 'ta': Tamil
    - 'te': Telugu
    """
    
    print(f"Loading transcription from {input_file}")
    
    # Load original transcription
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Initialize translator
    translator = GoogleTranslator(source=source_language, target=target_language)
    
    print(f"Translating from {source_language} to {target_language}...")
    print(f"Total segments to translate: {len(data['transcription'])}")
    
    # Translate each segment
    translated_data = data.copy()
    
    for idx, segment in enumerate(translated_data['transcription']):
        print(f"\nTranslating segment {idx + 1}/{len(data['transcription'])}")
        print(f"  Original: {segment['text'][:100]}...")
        
        try:
            # Skip empty or error segments
            if segment['text'] in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
                print(f"  Skipping (no content)")
                continue
            
            # Translate the text
            translated_text = translator.translate(segment['text'])
            
            # Store both original and translated text
            segment['original_text'] = segment['text']
            segment['text'] = translated_text
            segment['translated_language'] = target_language
            
            print(f"  Translated: {translated_text[:100]}...")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  Error translating: {e}")
            segment['translation_error'] = str(e)
    
    # Add translation metadata
    translated_data['translation_info'] = {
        'source_language': source_language,
        'target_language': target_language,
        'translator': 'GoogleTranslator'
    }
    
    # Save translated version
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*70}")
    print(f"Translation complete!")
    print(f"Saved to: {output_file}")
    print(f"{'='*70}")
    
    return translated_data

def export_translated_srt(translated_data, output_file):
    """Export translated transcription to SRT subtitle format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(translated_data["transcription"], 1):
            # SRT format uses comma for milliseconds
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
            
            # Show original text if available
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
    
    print(f"\nTotal segments: {translated_data['total_segments']}")
    print(f"Total pauses: {translated_data['total_pauses']}")
    
    print("\n" + "-"*70)
    print("Sample segments:")
    print("-"*70)
    
    # Show first 3 segments as examples
    for item in translated_data["transcription"][:3]:
        print(f"\n[Segment {item['segment']}] {item['start_time']} → {item['end_time']}")
        
        if 'original_text' in item:
            print(f"  Original: {item['original_text']}")
        print(f"  Translated: {item['text']}")
        
        # Find pause after this segment
        pause = next((p for p in translated_data["pauses"] 
                     if p["after_segment"] == item['segment']), None)
        if pause:
            print(f"  [PAUSE: {pause['duration_seconds']}s]")
    
    print("\n" + "="*70)

# Example usage
