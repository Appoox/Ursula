import whisper
from pydub import AudioSegment
from pydub.silence import detect_silence
import json
from datetime import timedelta
import os

def format_timestamp(milliseconds):
    """Convert milliseconds to readable timestamp format"""
    td = timedelta(milliseconds=milliseconds)
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    seconds = td.seconds % 60
    ms = td.microseconds // 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

def transcribe_with_pauses(audio_file, model_size="base", min_silence_len=500, 
                           silence_thresh=-45, min_segment_len=500, language=None):
    """
    Transcribe audio file with pause detection and timestamps using Whisper
    
    Parameters:
    - audio_file: path to audio file (mp3, wav, etc.)
    - model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
                  tiny: fastest, less accurate
                  base: good balance (recommended)
                  small/medium/large: more accurate, slower
    - min_silence_len: minimum silence length in ms (default 500ms)
    - silence_thresh: silence threshold in dBFS (default -45)
    - min_segment_len: minimum speech segment length in ms (default 500ms)
    - language: language code (e.g., "en", "es", "fr") or None for auto-detect
    """
    
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    print(f"Loading audio file: {audio_file}")
    
    # Load audio file
    audio = AudioSegment.from_file(audio_file)
    
    # Detect non-silent chunks
    print("Detecting speech segments and pauses...")
    silences = detect_silence(audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)
    
    # Convert to speech segments
    speech_segments = []
    prev_end = 0
    
    for silence_start, silence_end in silences:
        if prev_end < silence_start:
            speech_segments.append((prev_end, silence_start))
        prev_end = silence_end
    
    # Add final segment if exists
    if prev_end < len(audio):
        speech_segments.append((prev_end, len(audio)))
    
    # Filter out segments that are too short
    speech_segments = [(start, end) for start, end in speech_segments 
                       if (end - start) >= min_segment_len]
    
    print(f"Found {len(speech_segments)} speech segments (filtered by minimum length)")
    
    # Merge segments that are very close together
    merged_segments = []
    if speech_segments:
        current_start, current_end = speech_segments[0]
        
        for start, end in speech_segments[1:]:
            gap = start - current_end
            if gap < min_silence_len:
                current_end = end
            else:
                merged_segments.append((current_start, current_end))
                current_start, current_end = start, end
        
        merged_segments.append((current_start, current_end))
        speech_segments = merged_segments
    
    print(f"After merging close segments: {len(speech_segments)} segments")
    
    results = []
    
    # Process each segment
    for idx, (start, end) in enumerate(speech_segments):
        print(f"\nProcessing segment {idx + 1}/{len(speech_segments)} ({format_timestamp(start)} - {format_timestamp(end)})")
        
        # Extract segment
        segment = audio[start:end]
        
        # Export to temporary wav
        temp_file = "temp_segment.wav"
        segment.export(temp_file, format="wav")
        
        # Transcribe with Whisper
        try:
            transcribe_options = {"fp16": False}
            if language:
                transcribe_options["language"] = language
            
            result = model.transcribe(temp_file, **transcribe_options)
            text = result["text"].strip()
            
            results.append({
                "segment": idx + 1,
                "start_time": format_timestamp(start),
                "end_time": format_timestamp(end),
                "duration_ms": end - start,
                "text": text,
                "language": result.get("language", "unknown")
            })
            
            print(f"  Text: {text}")
            
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                "segment": idx + 1,
                "start_time": format_timestamp(start),
                "end_time": format_timestamp(end),
                "duration_ms": end - start,
                "text": "[ERROR]",
                "error": str(e)
            })
        
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    # Detect pauses between segments
    pauses = []
    for i in range(len(speech_segments) - 1):
        pause_start = speech_segments[i][1]
        pause_end = speech_segments[i + 1][0]
        pause_duration = pause_end - pause_start
        
        pauses.append({
            "after_segment": i + 1,
            "start_time": format_timestamp(pause_start),
            "end_time": format_timestamp(pause_end),
            "duration_ms": pause_duration,
            "duration_seconds": round(pause_duration / 1000, 2)
        })
    
    return {
        "transcription": results,
        "pauses": pauses,
        "total_segments": len(speech_segments),
        "total_pauses": len(pauses),
        "model_used": model_size
    }

def save_results(results, output_file="transcription_output.json"):
    """Save results to JSON file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {output_file}")

def print_summary(results):
    """Print a formatted summary of the transcription"""
    print("\n" + "="*70)
    print("TRANSCRIPTION SUMMARY")
    print("="*70)
    
    for item in results["transcription"]:
        print(f"\n[Segment {item['segment']}] {item['start_time']} → {item['end_time']}")
        print(f"  {item['text']}")
        
        # Find pause after this segment
        pause = next((p for p in results["pauses"] if p["after_segment"] == item['segment']), None)
        if pause:
            print(f"  [PAUSE: {pause['duration_seconds']}s]")
    
    print(f"\n{'='*70}")
    print(f"Total segments: {results['total_segments']}")
    print(f"Total pauses: {results['total_pauses']}")
    print(f"Model used: {results['model_used']}")
    print("="*70)

def export_to_srt(results, output_file="subtitles.srt"):
    """Export transcription to SRT subtitle format"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for idx, item in enumerate(results["transcription"], 1):
            # SRT format uses different timestamp format
            start = item['start_time'].replace('.', ',')
            end = item['end_time'].replace('.', ',')
            
            f.write(f"{idx}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{item['text']}\n\n")
    
    print(f"SRT subtitles saved to {output_file}")
