import json
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import os
from datetime import datetime
import json
from gtts import gTTS
from pydub import AudioSegment
import os

import json
import os
import math
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import speedup

def parse_timestamp(ts_string):
    """Convert HH:MM:SS.mmm to milliseconds"""
    h, m, s = ts_string.split(':')
    s, ms = s.split('.')
    return (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)

def speed_change(sound, speed=1.0):
    """
    Change speed of audio.
    Method: specific pydub logic to minimize pitch distortion where possible,
    but falls back to frame rate manipulation for stability.
    """
    if speed <= 1.0:
        return sound
    
    # For small speed changes, pydub's built-in speedup works well
    if speed <= 1.4:
        try:
            return speedup(sound, playback_speed=speed, chunk_size=150, crossfade=25)
        except:
            pass # Fallback to method below if this fails

    # For larger changes, we simply change the frame rate (Chipmunk effect)
    # This is the only way to guarantee it fits without complex DSP libraries
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

def create_synchronized_tts(json_file, original_audio_file, output_audio="synced_output.mp3", language='ml'):
    """
    Creates a dubbed audio file that matches the EXACT length of the original.
    - Fits every sentence into its specific time slot.
    - Speeds up audio if it's too long.
    """
    print(f"Loading transcription from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. Get total duration from original file to set the "Canvas" size
    print(f"Reading original audio duration from: {original_audio_file}")
    original_audio = AudioSegment.from_file(original_audio_file)
    total_duration_ms = len(original_audio)
    
    # Create a silent canvas of the EXACT same length
    final_audio = AudioSegment.silent(duration=total_duration_ms)
    
    temp_dir = "temp_tts_strict"
    os.makedirs(temp_dir, exist_ok=True)
    
    transcription = data['transcription']
    
    print(f"Processing {len(transcription)} segments...")

    for i, item in enumerate(transcription):
        text = item.get('text', '')
        if not text or text in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
            continue
            
        start_ms = parse_timestamp(item['start_time'])
        
        # Calculate the "Time Budget" for this segment
        # It is the time until the NEXT segment starts
        if i < len(transcription) - 1:
            next_start_ms = parse_timestamp(transcription[i+1]['start_time'])
            time_budget = next_start_ms - start_ms
        else:
            # For the last segment, budget is until the end of the file
            time_budget = total_duration_ms - start_ms

        # Safety buffer: Leave a tiny gap (e.g., 100ms) so sentences don't bleed into each other
        time_budget = max(time_budget - 100, 500) # Minimum 500ms budget

        # Generate TTS
        temp_file = os.path.join(temp_dir, f"seg_{i}.mp3")
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(temp_file)
        
        segment_audio = AudioSegment.from_mp3(temp_file)
        original_len = len(segment_audio)
        
        # Check if we need to speed up
        if original_len > time_budget:
            # Calculate required speed
            speed_factor = original_len / time_budget
            print(f"  Seg {i+1}: too long ({original_len}ms > {time_budget}ms). Speeding up {speed_factor:.2f}x")
            
            # Limit extreme speedups (otherwise it sounds like a glitch)
            # If it needs > 2.0x, we cap it and it might overlap slightly, or we let it be fast.
            segment_audio = speed_change(segment_audio, speed=speed_factor)
            
        # Paste onto the canvas
        # position indicates where to overlay this segment
        final_audio = final_audio.overlay(segment_audio, position=start_ms)
        
        print(f".", end="", flush=True)

    # Cleanup
    try:
        import shutil
        shutil.rmtree(temp_dir)
    except:
        pass

    # Force export to exact length
    # (Overlaying shouldn't change length, but just in case)
    final_audio = final_audio[:total_duration_ms]

    print(f"\nExporting to {output_audio}")
    final_audio.export(output_audio, format="mp3")
    
    print(f"✓ Original Duration: {total_duration_ms/1000:.2f}s")
    print(f"✓ New File Duration: {len(final_audio)/1000:.2f}s")
    
    return output_audio

# def create_tts_with_pauses(json_file, output_audio="output_tts.mp3", language='ml', 
#                            use_original=False, tts_engine='gtts'):
#     """
#     Convert transcription JSON to speech with pauses preserved
    
#     Parameters:
#     - json_file: path to translated transcription JSON
#     - output_audio: output audio file path
#     - language: language code for TTS ('ml' for Malayalam, 'en' for English, etc.)
#     - use_original: if True, use original_text instead of translated text
#     - tts_engine: 'gtts' (Google TTS, free) or 'edge' (Edge TTS, better quality)
    
#     Language codes for gTTS:
#     - 'ml': Malayalam
#     - 'en': English
#     - 'hi': Hindi
#     - 'ta': Tamil
#     - 'te': Telugu
#     - 'bn': Bengali
#     """
    
#     print(f"Loading transcription from {json_file}")
    
#     # Load transcription data
#     with open(json_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     print(f"\nGenerating speech for {len(data['transcription'])} segments...")
#     print(f"Language: {language}")
#     print(f"TTS Engine: {tts_engine}")
    
#     # Create directory for temporary audio files
#     temp_dir = "temp_tts_segments"
#     os.makedirs(temp_dir, exist_ok=True)
    
#     # Generate audio for each segment
#     segment_files = []
    
#     for idx, segment in enumerate(data['transcription']):
#         segment_num = segment['segment']
#         text = segment.get('original_text' if use_original else 'text', '')
        
#         if not text or text in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
#             print(f"Segment {segment_num}: Skipping (no content)")
#             continue
        
#         print(f"\nSegment {segment_num}/{len(data['transcription'])}")
#         print(f"  Text: {text[:100]}...")
        
#         # Generate TTS
#         temp_file = os.path.join(temp_dir, f"segment_{segment_num}.mp3")
        
#         try:
#             if tts_engine == 'gtts':
#                 tts = gTTS(text=text, lang=language, slow=False)
#                 tts.save(temp_file)
            
#             elif tts_engine == 'edge':
#                 # Edge TTS has better quality and more voices
#                 import edge_tts
#                 import asyncio
                
#                 # Voice mapping for Edge TTS
#                 voice_map = {
#                     'ml': 'ml-IN-SobhanaNeural',  # Malayalam female voice
#                     'en': 'en-US-JennyNeural',     # English female voice
#                     'hi': 'hi-IN-SwaraNeural',     # Hindi female voice
#                     'ta': 'ta-IN-PallaviNeural',   # Tamil female voice
#                     'te': 'te-IN-ShrutiNeural',    # Telugu female voice
#                 }
                
#                 voice = voice_map.get(language, f'{language}-Neural')
                
#                 async def generate_edge_tts():
#                     communicate = edge_tts.Communicate(text, voice)
#                     await communicate.save(temp_file)
                
#                 asyncio.run(generate_edge_tts())
            
#             else:
#                 raise ValueError(f"Unknown TTS engine: {tts_engine}")
            
#             segment_files.append({
#                 'file': temp_file,
#                 'segment': segment,
#                 'index': idx
#             })
            
#             print(f"  Generated: {temp_file}")
        
#         except Exception as e:
#             print(f"  Error generating TTS: {e}")
    
#     print(f"\n{'='*70}")
#     print("Combining segments with pauses...")
#     print(f"{'='*70}")
    
#     # Combine segments with pauses
#     combined_audio = AudioSegment.empty()
    
#     for idx, seg_info in enumerate(segment_files):
#         segment = seg_info['segment']
#         audio_file = seg_info['file']
        
#         # Load the audio segment
#         audio_segment = AudioSegment.from_mp3(audio_file)
        
#         print(f"\nAdding segment {segment['segment']}: {len(audio_segment)}ms")
#         combined_audio += audio_segment
        
#         # Add pause after segment (if not the last segment)
#         if idx < len(segment_files) - 1:
#             # Find the pause duration
#             pause = next((p for p in data['pauses'] 
#                          if p['after_segment'] == segment['segment']), None)
            
#             if pause:
#                 pause_duration = pause['duration_ms']
#                 silence = AudioSegment.silent(duration=pause_duration)
#                 combined_audio += silence
#                 print(f"  Adding pause: {pause_duration}ms ({pause['duration_seconds']}s)")
    
#     # Export final audio
#     print(f"\n{'='*70}")
#     print(f"Exporting final audio to {output_audio}...")
#     combined_audio.export(output_audio, format="mp3")
    
#     # Clean up temporary files
#     print("Cleaning up temporary files...")
#     for seg_info in segment_files:
#         try:
#             os.remove(seg_info['file'])
#         except:
#             pass
    
#     try:
#         os.rmdir(temp_dir)
#     except:
#         pass
    
#     print(f"\n{'='*70}")
#     print(f"✓ Audio generation complete!")
#     print(f"✓ Output: {output_audio}")
#     print(f"✓ Duration: {len(combined_audio) / 1000:.2f} seconds")
#     print(f"✓ Total segments: {len(segment_files)}")
#     print(f"✓ Total pauses: {len(data['pauses'])}")
#     print(f"{'='*70}")
    
#     return output_audio

# def create_bilingual_tts(json_file, output_audio="bilingual_output.mp3", 
#                         original_lang='en', translated_lang='ml'):
#     """
#     Create bilingual audio: original text followed by translation with pauses
    
#     Example: "Hello" [pause] "നമസ്കാരം" [longer pause] "How are you?" [pause] "സുഖമാണോ?"
#     """
    
#     print(f"Loading transcription from {json_file}")
    
#     with open(json_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
    
#     print(f"\nGenerating bilingual speech...")
#     print(f"Original language: {original_lang}")
#     print(f"Translated language: {translated_lang}")
    
#     temp_dir = "temp_tts_bilingual"
#     os.makedirs(temp_dir, exist_ok=True)
    
#     combined_audio = AudioSegment.empty()
    
#     for idx, segment in enumerate(data['transcription']):
#         segment_num = segment['segment']
#         original_text = segment.get('original_text', '')
#         translated_text = segment.get('text', '')
        
#         if not original_text or not translated_text:
#             continue
        
#         print(f"\nSegment {segment_num}/{len(data['transcription'])}")
        
#         # Generate original TTS
#         if original_text not in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
#             print(f"  Original: {original_text[:50]}...")
#             orig_file = os.path.join(temp_dir, f"orig_{segment_num}.mp3")
#             tts_orig = gTTS(text=original_text, lang=original_lang, slow=False)
#             tts_orig.save(orig_file)
#             combined_audio += AudioSegment.from_mp3(orig_file)
            
#             # Short pause between languages
#             combined_audio += AudioSegment.silent(duration=500)
        
#         # Generate translated TTS
#         if translated_text not in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
#             print(f"  Translated: {translated_text[:50]}...")
#             trans_file = os.path.join(temp_dir, f"trans_{segment_num}.mp3")
#             tts_trans = gTTS(text=translated_text, lang=translated_lang, slow=False)
#             tts_trans.save(trans_file)
#             combined_audio += AudioSegment.from_mp3(trans_file)
        
#         # Add pause after segment pair
#         pause = next((p for p in data['pauses'] 
#                      if p['after_segment'] == segment_num), None)
#         if pause:
#             pause_duration = max(pause['duration_ms'], 1000)  # At least 1 second
#             combined_audio += AudioSegment.silent(duration=pause_duration)
#             print(f"  Pause: {pause_duration}ms")
    
#     # Export
#     print(f"\nExporting bilingual audio to {output_audio}...")
#     combined_audio.export(output_audio, format="mp3")
    
#     # Cleanup
#     print("Cleaning up...")
#     import shutil
#     shutil.rmtree(temp_dir, ignore_errors=True)
    
#     print(f"\n✓ Bilingual audio complete!")
#     print(f"✓ Output: {output_audio}")
#     print(f"✓ Duration: {len(combined_audio) / 1000:.2f} seconds")
    
#     return output_audio
