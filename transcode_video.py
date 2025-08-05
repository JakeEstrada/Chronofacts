#!/usr/bin/env python3
"""
Fast video transcoding script for web compatibility
Optimized for speed while maintaining quality
"""

import os
import sys
import subprocess
import tempfile

def transcode_video(input_path):
    """
    Transcode video to web-compatible H.264 format with optimized settings
    Returns the path to the transcoded file, or None if failed
    """
    try:
        if not os.path.exists(input_path):
            print(f"Input file not found: {input_path}")
            return None
        
        # Get file info
        file_size = os.path.getsize(input_path)
        print(f"Transcoding video: {os.path.basename(input_path)} ({file_size / (1024*1024):.1f} MB)")
        
        # Generate output filename
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_web.mp4"
        
        # Fast transcoding settings optimized for speed
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',           # H.264 codec
            '-preset', 'ultrafast',       # Fastest encoding preset
            '-crf', '23',                 # Good quality, reasonable file size
            '-c:a', 'aac',               # AAC audio codec
            '-b:a', '128k',              # Audio bitrate
            '-movflags', '+faststart',    # Optimize for web streaming
            '-y',                         # Overwrite output file
            output_path
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        # Run transcoding with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            output_size = os.path.getsize(output_path)
            compression_ratio = (1 - output_size / file_size) * 100
            print(f"Transcoding successful: {os.path.basename(output_path)}")
            print(f"Size: {output_size / (1024*1024):.1f} MB ({compression_ratio:.1f}% compression)")
            return output_path
        else:
            print(f"Transcoding failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Transcoding timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"Error during transcoding: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python transcode_video.py <input_video_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    result = transcode_video(input_path)
    
    if result:
        print(f"Success: {result}")
        sys.exit(0)
    else:
        print("Failed to transcode video")
        sys.exit(1) 