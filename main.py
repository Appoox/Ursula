from STT import stt
from Translation import translate
from TTS import tts

def main():
    # Replace with your audio file path
    audio_file = "Charlie-Chaplin.wav"
    
    # Transcribe with Whisper
    # Model sizes: "tiny", "base", "small", "medium", "large"
    # tiny: ~1GB RAM, fastest
    # base: ~1GB RAM, good balance (recommended for most cases)
    # small: ~2GB RAM, better accuracy
    # medium: ~5GB RAM, even better
    # large: ~10GB RAM, best accuracy
    
    results = stt.transcribe_with_pauses(
        audio_file,
        model_size="small",      # Change to "small" or "medium" for better accuracy
        min_silence_len=400,    # 500ms minimum pause
        silence_thresh=-66,     # silence threshold
        # min_segment_len=1000,    # minimum segment length
        language="en"           # Set to None for auto-detect, or "en", "es", "fr", etc.
    )
    
    # Print summary
    stt.print_summary(results)
    
    # Save to JSON
    stt.save_results(results, "transcription_output.json")
    
    # Export to SRT subtitles (optional)
    stt.export_to_srt(results, "subtitles.srt")

    # Input file (your transcription output)
    input_file = "transcription_output.json"
    target_language = 'ml'  # Malayalam
    
    # Choose your translator:
    
    # Option 1: MyMemory (RECOMMENDED for Malayalam - free, good for Indian languages)
    translator = translate.TranslatorType.GOOGLE
    api_key = None
    
    # Option 2: Google Translate (fallback)
    # translator = TranslatorType.GOOGLE
    # api_key = None
    
    # Option 3: Claude/Anthropic (BEST QUALITY - requires API key)
    # translator = TranslatorType.ANTHROPIC
    # api_key = None  # Set via ANTHROPIC_API_KEY environment variable
    
    # Option 4: DeepL (high quality but may not support Malayalam)
    # translator = TranslatorType.DEEPL
    # api_key = "your_deepl_api_key_here"
    
    # Option 5: LibreTranslate (open source)
    # translator = TranslatorType.LIBRE
    # api_key = None  # or your API key if using paid instance
    
    # Output files
    output_json = f"transcription_translated_{target_language}.json"
    output_srt = f"subtitles_translated_{target_language}.srt"
    output_bilingual_srt = f"subtitles_bilingual_{target_language}.srt"
    
    # Translate
    translated_data = translate.translate_transcription(
        input_file=input_file,
        output_file=output_json,
        target_language=target_language,
        source_language='en',
        translator_type=translator,
        api_key=api_key
    )
    
    # Print summary
    translate.print_translation_summary(translated_data)
    
    # Export to SRT
    translate.export_translated_srt(translated_data, output_srt)
    translate.create_bilingual_srt(translated_data, output_bilingual_srt)
    
    print(f"\n✓ Translation complete!")
    print(f"✓ JSON: {output_json}")
    print(f"✓ SRT (translated): {output_srt}")
    print(f"✓ SRT (bilingual): {output_bilingual_srt}")

    json_file = "transcription_translated_ml.json"
    
    # # Option 1: Malayalam TTS with pauses (recommended)
    # print("=" * 70)
    # print("Creating Malayalam TTS with pauses...")
    # print("=" * 70)
    
    # tts.create_tts_with_pauses(
    #     json_file=json_file,
    #     output_audio="malayalam_speech.mp3",
    #     language='ml',
    #     use_original=False,  # Use translated text
    #     tts_engine='gtts'    # Use 'edge' for better quality
    # )
    
    # print("=" * 70)
    # print("Creating Synchronized Malayalam TTS...")
    # print("=" * 70)
    
    # # Use the new function from tts module
    # tts.create_synchronized_tts(
    #     json_file=json_file,
    #     output_audio="malayalam_synced.mp3",
    #     language='ml',
    #     tts_engine='gtts'
    # )

    print("=" * 70)
    print("Creating STRICTLY Synced Audio...")
    print("=" * 70)
    
    tts.create_synchronized_tts(
        json_file="transcription_translated_ml.json", 
        original_audio_file="Charlie-Chaplin.wav",  # Pass the original file here
        output_audio="malayalam_strict_sync.mp3",
        language='ml'
    )

    # Option 2: Original English TTS with pauses
    # print("\n" + "=" * 70)
    # print("Creating English TTS with pauses...")
    # print("=" * 70)
    # 
    # create_tts_with_pauses(
    #     json_file=json_file,
    #     output_audio="english_speech.mp3",
    #     language='en',
    #     use_original=True,
    #     tts_engine='gtts'
    # )
    
    # Option 3: Bilingual (English + Malayalam)
    # print("\n" + "=" * 70)
    # print("Creating bilingual TTS...")
    # print("=" * 70)
    # 
    # create_bilingual_tts(
    #     json_file=json_file,
    #     output_audio="bilingual_speech.mp3",
    #     original_lang='en',
    #     translated_lang='ml'
    # )


if __name__ == "__main__":
    main()