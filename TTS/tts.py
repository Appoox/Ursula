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
from gtts import gTTS
from pydub import AudioSegment
from pydub.effects import speedup
import os

def parse_timestamp_to_ms(timestamp_str):
    """Convert '00:00:00.000' format to milliseconds"""
    h, m, s = timestamp_str.split(':')
    s, ms = s.split('.')
    return (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)

def time_stretch_audio(audio_segment, target_duration_ms, max_speedup=1.5):
    """
    Time-stretch audio to fit target duration
    
    Parameters:
    - audio_segment: pydub AudioSegment
    - target_duration_ms: desired duration in milliseconds
    - max_speedup: maximum speedup factor (1.5 = 50% faster)
    
    Returns stretched audio segment
    """
    current_duration = len(audio_segment)
    
    if current_duration <= target_duration_ms:
        # Audio is shorter or equal, no stretching needed
        return audio_segment
    
    # Calculate required speedup factor
    speedup_factor = current_duration / target_duration_ms
    
    # Limit speedup to avoid chipmunk effect
    if speedup_factor > max_speedup:
        print(f"    Warning: Required speedup {speedup_factor:.2f}x exceeds max {max_speedup}x")
        speedup_factor = max_speedup
    
    # Apply speedup
    stretched = speedup(audio_segment, playback_speed=speedup_factor)
    
    print(f"    Stretched from {current_duration}ms to {len(stretched)}ms (factor: {speedup_factor:.2f}x)")
    
    return stretched

def create_perfectly_synced_tts(json_file, output_audio="synced_output.mp3", 
                                language='ml', tts_engine='gtts', 
                                max_speedup=1.5, use_original=False):
    """
    Generate TTS that EXACTLY matches the original audio duration.
    
    Features:
    - Every segment starts at the exact original timestamp
    - Audio is time-stretched if too long to fit
    - Dynamic silence fills gaps perfectly
    - Final output duration = original audio duration
    
    Parameters:
    - json_file: path to transcription JSON
    - output_audio: output file path
    - language: TTS language code ('ml', 'en', etc.)
    - tts_engine: 'gtts' or 'edge'
    - max_speedup: maximum speedup factor (1.5 = 50% faster max)
    - use_original: use original_text instead of translated text
    """
    
    print(f"Loading transcription from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get original audio duration
    last_segment = data['transcription'][-1]
    original_duration_ms = parse_timestamp_to_ms(last_segment['end_time'])
    
    print(f"\nOriginal audio duration: {original_duration_ms/1000:.2f}s")
    print(f"Total segments: {len(data['transcription'])}")
    print(f"Generating synchronized TTS...")
    
    # Step 1: Generate all TTS segments
    temp_dir = "temp_tts_sync"
    os.makedirs(temp_dir, exist_ok=True)
    
    segments_data = []
    
    for item in data['transcription']:
        text_key = 'original_text' if use_original else 'text'
        text = item.get(text_key, item.get('text', ''))
        
        if not text or text in ['[UNINTELLIGIBLE]', '[ERROR]', '']:
            continue
        
        segment_num = item['segment']
        temp_file = os.path.join(temp_dir, f"seg_{segment_num}.mp3")
        
        try:
            if tts_engine == 'gtts':
                tts = gTTS(text=text, lang=language, slow=False)
                tts.save(temp_file)
            
            elif tts_engine == 'edge':
                import edge_tts
                import asyncio
                
                voice_map = {
                    'ml': 'ml-IN-SobhanaNeural',
                    'en': 'en-US-JennyNeural',
                    'hi': 'hi-IN-SwaraNeural',
                    'ta': 'ta-IN-PallaviNeural',
                    'te': 'te-IN-ShrutiNeural',
                }
                voice = voice_map.get(language, f'{language}-Neural')
                
                async def generate_edge():
                    communicate = edge_tts.Communicate(text, voice)
                    await communicate.save(temp_file)
                
                asyncio.run(generate_edge())
            
            segments_data.append({
                'segment_num': segment_num,
                'start_ms': parse_timestamp_to_ms(item['start_time']),
                'end_ms': parse_timestamp_to_ms(item['end_time']),
                'target_duration': parse_timestamp_to_ms(item['end_time']) - parse_timestamp_to_ms(item['start_time']),
                'file': temp_file,
                'text': text[:50] + '...' if len(text) > 50 else text
            })
            
            print(f"  ✓ Segment {segment_num}: {text[:50]}...")
            
        except Exception as e:
            print(f"  ✗ Error on segment {segment_num}: {e}")
    
    print(f"\n{'='*70}")
    print("Building synchronized timeline...")
    print(f"{'='*70}")
    
    # Step 2: Build perfectly synchronized timeline
    final_audio = AudioSegment.empty()
    
    for idx, seg in enumerate(segments_data):
        current_position = len(final_audio)
        target_start = seg['start_ms']
        target_end = seg['end_ms']
        target_duration = seg['target_duration']
        
        print(f"\nSegment {seg['segment_num']}:")
        print(f"  Current position: {current_position}ms")
        print(f"  Target start: {target_start}ms")
        print(f"  Target duration: {target_duration}ms")
        
        # Add silence to reach target start time
        silence_needed = target_start - current_position
        
        if silence_needed > 0:
            final_audio += AudioSegment.silent(duration=silence_needed)
            print(f"  Added silence: {silence_needed}ms")
        elif silence_needed < 0:
            print(f"  Warning: Behind schedule by {-silence_needed}ms")
        
        # Load and process TTS audio
        seg_audio = AudioSegment.from_mp3(seg['file'])
        original_tts_duration = len(seg_audio)
        
        print(f"  TTS duration: {original_tts_duration}ms (target: {target_duration}ms)")
        
        # Time-stretch if needed to fit exactly
        if original_tts_duration > target_duration:
            seg_audio = time_stretch_audio(seg_audio, target_duration, max_speedup)
        
        # Add the audio
        final_audio += seg_audio
        
        # If TTS is shorter than target, pad with silence at the end
        actual_duration = len(seg_audio)
        if actual_duration < target_duration:
            padding = target_duration - actual_duration
            final_audio += AudioSegment.silent(duration=padding)
            print(f"  Added padding: {padding}ms")
    
    # Step 3: Ensure final duration matches original exactly
    final_duration = len(final_audio)
    duration_diff = original_duration_ms - final_duration
    
    print(f"\n{'='*70}")
    print(f"Final duration: {final_duration/1000:.2f}s")
    print(f"Original duration: {original_duration_ms/1000:.2f}s")
    print(f"Difference: {duration_diff}ms")
    
    if duration_diff > 0:
        # Add silence to reach exact original duration
        final_audio += AudioSegment.silent(duration=duration_diff)
        print(f"Added final padding: {duration_diff}ms")
    elif duration_diff < 0:
        # Trim excess (shouldn't happen with proper time stretching)
        final_audio = final_audio[:original_duration_ms]
        print(f"Trimmed excess: {-duration_diff}ms")
    
    print(f"{'='*70}")
    
    # Step 4: Export
    print(f"\nExporting to {output_audio}...")
    final_audio.export(output_audio, format="mp3", bitrate="192k")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"\n{'='*70}")
    print(f"✓ PERFECTLY SYNCHRONIZED TTS COMPLETE!")
    print(f"{'='*70}")
    print(f"Output file: {output_audio}")
    print(f"Duration: {len(final_audio)/1000:.2f}s (matches original exactly)")
    print(f"Segments processed: {len(segments_data)}")
    print(f"{'='*70}")
    
    return output_audio

def create_synced_bilingual_tts(json_file, output_audio="bilingual_synced.mp3",
                                original_lang='en', translated_lang='ml',
                                max_speedup=1.5):
    """
    Create bilingual synchronized TTS where total duration matches original
    
    Format per segment:
    [Original Audio] -> [Short Pause] -> [Translated Audio] -> [Next Segment Start]
    
    Each pair is time-stretched to fit within the original segment's timeframe
    """
    
    print(f"Loading transcription from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Get original duration
    last_segment = data['transcription'][-1]
    original_duration_ms = parse_timestamp_to_ms(last_segment['end_time'])
    
    print(f"\nOriginal duration: {original_duration_ms/1000:.2f}s")
    print(f"Generating bilingual synchronized TTS...")
    
    temp_dir = "temp_bilingual_sync"
    os.makedirs(temp_dir, exist_ok=True)
    
    final_audio = AudioSegment.empty()
    inter_language_pause = 300  # 300ms pause between languages
    
    for item in data['transcription']:
        original_text = item.get('original_text', '')
        translated_text = item.get('text', '')
        
        if not original_text or not translated_text:
            continue
        
        segment_num = item['segment']
        start_ms = parse_timestamp_to_ms(item['start_time'])
        end_ms = parse_timestamp_to_ms(item['end_time'])
        available_duration = end_ms - start_ms
        
        print(f"\nSegment {segment_num}: {available_duration}ms available")
        
        # Generate both TTS
        orig_file = os.path.join(temp_dir, f"orig_{segment_num}.mp3")
        trans_file = os.path.join(temp_dir, f"trans_{segment_num}.mp3")
        
        try:
            # Original
            tts_orig = gTTS(text=original_text, lang=original_lang, slow=False)
            tts_orig.save(orig_file)
            orig_audio = AudioSegment.from_mp3(orig_file)
            
            # Translated
            tts_trans = gTTS(text=translated_text, lang=translated_lang, slow=False)
            tts_trans.save(trans_file)
            trans_audio = AudioSegment.from_mp3(trans_file)
            
            # Calculate combined duration
            combined_duration = len(orig_audio) + inter_language_pause + len(trans_audio)
            
            print(f"  Original: {len(orig_audio)}ms")
            print(f"  Translated: {len(trans_audio)}ms")
            print(f"  Combined: {combined_duration}ms (target: {available_duration}ms)")
            
            # Add silence to reach segment start
            current_pos = len(final_audio)
            if current_pos < start_ms:
                final_audio += AudioSegment.silent(duration=start_ms - current_pos)
            
            # Time-stretch if combined audio is too long
            if combined_duration > available_duration:
                speedup_factor = combined_duration / available_duration
                speedup_factor = min(speedup_factor, max_speedup)
                
                orig_audio = speedup(orig_audio, playback_speed=speedup_factor)
                trans_audio = speedup(trans_audio, playback_speed=speedup_factor)
                
                print(f"  Applied speedup: {speedup_factor:.2f}x")
            
            # Add the audio
            final_audio += orig_audio
            final_audio += AudioSegment.silent(duration=inter_language_pause)
            final_audio += trans_audio
            
            # Pad to reach next segment if needed
            current_length = len(final_audio)
            if current_length < end_ms:
                padding = end_ms - current_length
                final_audio += AudioSegment.silent(duration=padding)
                print(f"  Added padding: {padding}ms")
            
        except Exception as e:
            print(f"  Error: {e}")
    
    # Match original duration exactly
    if len(final_audio) < original_duration_ms:
        final_audio += AudioSegment.silent(duration=original_duration_ms - len(final_audio))
    elif len(final_audio) > original_duration_ms:
        final_audio = final_audio[:original_duration_ms]
    
    # Export
    print(f"\nExporting to {output_audio}...")
    final_audio.export(output_audio, format="mp3", bitrate="192k")
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"\n✓ Bilingual synchronized TTS complete!")
    print(f"✓ Duration: {len(final_audio)/1000:.2f}s (matches original)")
    
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
