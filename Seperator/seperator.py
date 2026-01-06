import subprocess
import os
from pathlib import Path
import json

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def check_ffmpeg():
    """
    Check if ffmpeg is installed and available in PATH
    
    Returns:
        bool: True if ffmpeg is available, False otherwise
    """
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def check_ffprobe():
    """
    Check if ffprobe is installed and available in PATH
    
    Returns:
        bool: True if ffprobe is available, False otherwise
    """
    try:
        subprocess.run(['ffprobe', '-version'], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def validate_input_file(input_file):
    """
    Validate that input file exists
    
    Args:
        input_file (str): Path to input file
        
    Returns:
        bool: True if file exists, False otherwise
    """
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file '{input_file}' not found")
        return False
    return True

def get_media_info(input_file):
    """
    Get detailed information about media file streams
    
    Args:
        input_file (str): Path to media file
        
    Returns:
        dict: Media information or None if error
    """
    if not validate_input_file(input_file):
        return None
    
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        input_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"❌ Error getting media info: {e}")
        return None

def print_media_info(input_file):
    """
    Print human-readable media information
    
    Args:
        input_file (str): Path to media file
    """
    info = get_media_info(input_file)
    if not info:
        return
    
    print("\n" + "="*70)
    print("MEDIA INFORMATION")
    print("="*70)
    
    # Format info
    if 'format' in info:
        fmt = info['format']
        print(f"\nFile: {fmt.get('filename', 'Unknown')}")
        print(f"Format: {fmt.get('format_long_name', 'Unknown')}")
        print(f"Duration: {float(fmt.get('duration', 0)):.2f} seconds")
        print(f"Size: {int(fmt.get('size', 0)) / (1024*1024):.2f} MB")
        print(f"Bitrate: {int(fmt.get('bit_rate', 0)) / 1000:.0f} kbps")
    
    # Stream info
    if 'streams' in info:
        video_count = 0
        audio_count = 0
        subtitle_count = 0
        
        for stream in info['streams']:
            codec_type = stream.get('codec_type', '')
            
            if codec_type == 'video':
                video_count += 1
                print(f"\nVideo Stream #{video_count}:")
                print(f"  Codec: {stream.get('codec_long_name', 'Unknown')}")
                print(f"  Resolution: {stream.get('width', 0)}x{stream.get('height', 0)}")
                print(f"  FPS: {eval(stream.get('r_frame_rate', '0/1')):.2f}")
                
            elif codec_type == 'audio':
                audio_count += 1
                print(f"\nAudio Stream #{audio_count}:")
                print(f"  Codec: {stream.get('codec_long_name', 'Unknown')}")
                print(f"  Sample Rate: {stream.get('sample_rate', 'Unknown')} Hz")
                print(f"  Channels: {stream.get('channels', 'Unknown')}")
                
            elif codec_type == 'subtitle':
                subtitle_count += 1
                print(f"\nSubtitle Stream #{subtitle_count}:")
                print(f"  Codec: {stream.get('codec_long_name', 'Unknown')}")
        
        print("\n" + "="*70)
        print(f"Total: {video_count} video, {audio_count} audio, {subtitle_count} subtitle streams")
        print("="*70)

# ============================================================================
# AUDIO EXTRACTION FUNCTIONS
# ============================================================================

def extract_audio(input_file, output_audio=None, audio_format='mp3', audio_quality='192k'):
    """
    Extract audio stream from video file
    
    Args:
        input_file (str): Path to video file
        output_audio (str, optional): Output audio file path. Auto-generated if None
        audio_format (str): Output format ('mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a')
        audio_quality (str): Bitrate for lossy formats ('128k', '192k', '256k', '320k')
        
    Returns:
        str: Path to output audio file, or None if error
    """
    if not validate_input_file(input_file):
        return None
    
    # Auto-generate output filename
    if output_audio is None:
        base = Path(input_file).stem
        output_audio = f"{base}_audio.{audio_format}"
    
    print(f"\n{'='*70}")
    print("EXTRACTING AUDIO")
    print(f"{'='*70}")
    print(f"Input: {input_file}")
    print(f"Output: {output_audio}")
    print(f"Format: {audio_format}, Quality: {audio_quality}")
    
    # Build ffmpeg command based on format
    cmd = ['ffmpeg', '-i', input_file]
    
    if audio_format == 'mp3':
        cmd.extend(['-vn', '-acodec', 'libmp3lame', '-b:a', audio_quality])
    elif audio_format == 'wav':
        cmd.extend(['-vn', '-acodec', 'pcm_s16le'])
    elif audio_format == 'aac' or audio_format == 'm4a':
        cmd.extend(['-vn', '-acodec', 'aac', '-b:a', audio_quality])
    elif audio_format == 'flac':
        cmd.extend(['-vn', '-acodec', 'flac'])
    elif audio_format == 'ogg':
        cmd.extend(['-vn', '-acodec', 'libvorbis', '-b:a', audio_quality])
    else:
        cmd.extend(['-vn', '-acodec', 'copy'])
    
    cmd.extend(['-y', output_audio])
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Audio extracted successfully: {output_audio}")
        print("="*70)
        return output_audio
    except subprocess.CalledProcessError as e:
        print(f"❌ Error extracting audio: {e.stderr}")
        print("="*70)
        return None

def extract_all_audio_tracks(input_file, output_dir=None, audio_format='mp3', audio_quality='192k'):
    """
    Extract all audio tracks from media file as separate files
    
    Args:
        input_file (str): Path to media file
        output_dir (str, optional): Output directory. Created if doesn't exist
        audio_format (str): Output format
        audio_quality (str): Bitrate for lossy formats
        
    Returns:
        list: Paths to extracted audio files
    """
    if not validate_input_file(input_file):
        return []
    
    # Setup output directory
    if output_dir is None:
        base = Path(input_file).stem
        output_dir = f"{base}_audio_tracks"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("EXTRACTING ALL AUDIO TRACKS")
    print(f"{'='*70}")
    
    base_name = Path(input_file).stem
    audio_files = []
    track_num = 0
    
    while True:
        output_file = os.path.join(output_dir, f"{base_name}_audio_track_{track_num}.{audio_format}")
        
        cmd = ['ffmpeg', '-i', input_file, '-map', f'0:a:{track_num}', '-vn']
        
        if audio_format == 'mp3':
            cmd.extend(['-acodec', 'libmp3lame', '-b:a', audio_quality])
        elif audio_format == 'wav':
            cmd.extend(['-acodec', 'pcm_s16le'])
        elif audio_format == 'aac':
            cmd.extend(['-acodec', 'aac', '-b:a', audio_quality])
        
        cmd.extend(['-y', output_file])
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Track {track_num}: {output_file}")
            audio_files.append(output_file)
            track_num += 1
        except subprocess.CalledProcessError:
            break
    
    if audio_files:
        print(f"\n✅ Extracted {len(audio_files)} audio track(s)")
    else:
        print("❌ No audio tracks found")
    
    print("="*70)
    return audio_files

# ============================================================================
# VIDEO EXTRACTION FUNCTIONS
# ============================================================================

def extract_video_no_audio(input_file, output_video=None, video_codec='copy'):
    """
    Extract video stream without audio
    
    Args:
        input_file (str): Path to video file
        output_video (str, optional): Output video file. Auto-generated if None
        video_codec (str): 'copy' (fast, no re-encoding) or codec like 'libx264'
        
    Returns:
        str: Path to output video file, or None if error
    """
    if not validate_input_file(input_file):
        return None
    
    # Auto-generate output filename
    if output_video is None:
        base = Path(input_file).stem
        ext = Path(input_file).suffix
        output_video = f"{base}_video_only{ext}"
    
    print(f"\n{'='*70}")
    print("EXTRACTING VIDEO (NO AUDIO)")
    print(f"{'='*70}")
    print(f"Input: {input_file}")
    print(f"Output: {output_video}")
    print(f"Video Codec: {video_codec}")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-an',  # Remove audio
        '-vcodec', video_codec,
        '-y',
        output_video
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Video extracted successfully: {output_video}")
        print("="*70)
        return output_video
    except subprocess.CalledProcessError as e:
        print(f"❌ Error extracting video: {e.stderr}")
        print("="*70)
        return None

def extract_video_silent(input_file, output_video=None):
    """
    Extract video with silent audio track (useful for some players)
    
    Args:
        input_file (str): Path to video file
        output_video (str, optional): Output video file
        
    Returns:
        str: Path to output video file, or None if error
    """
    if not validate_input_file(input_file):
        return None
    
    if output_video is None:
        base = Path(input_file).stem
        ext = Path(input_file).suffix
        output_video = f"{base}_silent{ext}"
    
    print(f"\n{'='*70}")
    print("EXTRACTING VIDEO WITH SILENT AUDIO")
    print(f"{'='*70}")
    print(f"Input: {input_file}")
    print(f"Output: {output_video}")
    
    cmd = [
        'ffmpeg',
        '-i', input_file,
        '-f', 'lavfi',
        '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        '-y',
        output_video
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Video with silent audio created: {output_video}")
        print("="*70)
        return output_video
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        print("="*70)
        return None

# ============================================================================
# SUBTITLE EXTRACTION FUNCTIONS
# ============================================================================

def extract_all_subtitles(input_file, output_dir=None):
    """
    Extract all subtitle tracks from media file
    
    Args:
        input_file (str): Path to media file
        output_dir (str, optional): Output directory
        
    Returns:
        list: Paths to extracted subtitle files
    """
    if not validate_input_file(input_file):
        return []
    
    if output_dir is None:
        base = Path(input_file).stem
        output_dir = f"{base}_subtitles"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("EXTRACTING ALL SUBTITLES")
    print(f"{'='*70}")
    
    base_name = Path(input_file).stem
    subtitle_files = []
    track_num = 0
    
    while True:
        output_file = os.path.join(output_dir, f"{base_name}_subtitle_{track_num}.srt")
        
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-map', f'0:s:{track_num}',
            '-y',
            output_file
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"✅ Subtitle {track_num}: {output_file}")
            subtitle_files.append(output_file)
            track_num += 1
        except subprocess.CalledProcessError:
            break
    
    if subtitle_files:
        print(f"\n✅ Extracted {len(subtitle_files)} subtitle(s)")
    else:
        print("❌ No subtitles found")
    
    print("="*70)
    return subtitle_files

# ============================================================================
# COMBINATION FUNCTIONS
# ============================================================================

def combine_video_audio(video_file, audio_file, output_file=None, 
                       video_codec='copy', audio_codec='aac', audio_bitrate='192k'):
    """
    Combine separate video and audio files into one media file
    
    Args:
        video_file (str): Path to video file
        audio_file (str): Path to audio file
        output_file (str, optional): Output file path
        video_codec (str): Video codec ('copy' or 'libx264', 'libx265', etc.)
        audio_codec (str): Audio codec ('aac', 'mp3', 'copy')
        audio_bitrate (str): Audio bitrate if re-encoding
        
    Returns:
        str: Path to output file, or None if error
    """
    if not validate_input_file(video_file):
        return None
    if not validate_input_file(audio_file):
        return None
    
    # Auto-generate output filename
    if output_file is None:
        base = Path(video_file).stem
        output_file = f"{base}_combined.mp4"
    
    print(f"\n{'='*70}")
    print("COMBINING VIDEO + AUDIO")
    print(f"{'='*70}")
    print(f"Video: {video_file}")
    print(f"Audio: {audio_file}")
    print(f"Output: {output_file}")
    print(f"Video codec: {video_codec}, Audio codec: {audio_codec}")
    
    cmd = [
        'ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', video_codec,
        '-map', '0:v:0',  # Video from first input
        '-map', '1:a:0',  # Audio from second input
    ]
    
    # Audio codec settings
    if audio_codec == 'copy':
        cmd.extend(['-c:a', 'copy'])
    elif audio_codec == 'aac':
        cmd.extend(['-c:a', 'aac', '-b:a', audio_bitrate])
    elif audio_codec == 'mp3':
        cmd.extend(['-c:a', 'libmp3lame', '-b:a', audio_bitrate])
    
    cmd.extend(['-shortest', '-y', output_file])
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"✅ Combined successfully: {output_file}")
        print("="*70)
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"❌ Error combining: {e.stderr}")
        print("="*70)
        return None

def replace_audio(video_file, new_audio_file, output_file=None):
    """
    Replace audio track in video file with new audio
    Convenience wrapper for combine_video_audio
    
    Args:
        video_file (str): Path to video file
        new_audio_file (str): Path to new audio file
        output_file (str, optional): Output file path
        
    Returns:
        str: Path to output file, or None if error
    """
    return combine_video_audio(video_file, new_audio_file, output_file)

# ============================================================================
# BATCH PROCESSING FUNCTIONS
# ============================================================================

def separate_all_streams(input_file, output_dir=None):
    """
    Separate all streams (video, audio, subtitles) into individual files
    
    Args:
        input_file (str): Path to media file
        output_dir (str, optional): Output directory
        
    Returns:
        dict: Dictionary with paths to all extracted files
    """
    if not validate_input_file(input_file):
        return {}
    
    if output_dir is None:
        base = Path(input_file).stem
        output_dir = f"{base}_separated"
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("SEPARATING ALL STREAMS")
    print(f"{'='*70}")
    print(f"Input: {input_file}")
    print(f"Output directory: {output_dir}")
    print("="*70)
    
    results = {}
    
    # Extract video
    video_file = extract_video_no_audio(
        input_file,
        os.path.join(output_dir, f"{Path(input_file).stem}_video.mp4")
    )
    if video_file:
        results['video'] = video_file
    
    # Extract audio tracks
    audio_files = extract_all_audio_tracks(input_file, output_dir)
    if audio_files:
        results['audio'] = audio_files
    
    # Extract subtitles
    subtitle_files = extract_all_subtitles(input_file, output_dir)
    if subtitle_files:
        results['subtitles'] = subtitle_files
    
    # Summary
    print(f"\n{'='*70}")
    print("SEPARATION COMPLETE")
    print(f"{'='*70}")
    print(f"Output directory: {output_dir}")
    print(f"Video: {'Yes' if results.get('video') else 'No'}")
    print(f"Audio tracks: {len(results.get('audio', []))}")
    print(f"Subtitle tracks: {len(results.get('subtitles', []))}")
    print("="*70)
    
    return results

