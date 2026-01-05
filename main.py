from STT import stt
from Translation import translate

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
        min_silence_len=590,    # 500ms minimum pause
        silence_thresh=-63,     # silence threshold
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
    
    # Target language - change this to your desired language
    # Examples: 'es' (Spanish), 'fr' (French), 'de' (German), 
    #           'hi' (Hindi), 'zh-CN' (Chinese), 'ja' (Japanese)
    target_language = 'ml'  # Spanish
    
    # Output files
    output_json = f"transcription_translated_{target_language}.json"
    output_srt = f"subtitles_translated_{target_language}.srt"
    output_bilingual_srt = f"subtitles_bilingual_{target_language}.srt"
    
    # Translate the transcription
    translated_data = translate.translate_transcription(
        input_file=input_file,
        output_file=output_json,
        target_language=target_language,
        source_language='en'
    )
    
    # Print summary
    translate.print_translation_summary(translated_data)
    
    # Export to SRT formats
    translate.export_translated_srt(translated_data, output_srt)
    translate.create_bilingual_srt(translated_data, output_bilingual_srt)
    
    print(f"\n✓ Translation complete!")
    print(f"✓ JSON: {output_json}")
    print(f"✓ SRT (translated): {output_srt}")
    print(f"✓ SRT (bilingual): {output_bilingual_srt}")


if __name__ == "__main__":
    main()