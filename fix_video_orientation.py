#!/usr/bin/env python3
"""
Fast video orientation fix script
Only applies rotation when necessary
"""

import os
import sys
import subprocess

def fix_video_orientation(input_path):
    """
    Fix video orientation by rotating 180 degrees if needed
    Returns the path to the fixed file, or None if failed
    """
    try:
        if not os.path.exists(input_path):
            print(f"Input file not found: {input_path}")
            return None
        
        # Check if video needs rotation by examining metadata
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-select_streams', 'v:0',
                '-show_entries', 'stream_tags=rotate', '-of', 'csv=p=0', input_path
            ], capture_output=True, text=True, timeout=10)
            
            rotation = result.stdout.strip()
            print(f"Video rotation metadata: {rotation}")
            
            # If no rotation metadata or rotation is 0, skip processing
            if not rotation or rotation == '0':
                print("No rotation needed, using original file")
                return input_path
                
        except Exception as e:
            print(f"Could not check rotation metadata: {e}")
            # Continue with rotation fix anyway
        
        # Generate output filename
        base_name = os.path.splitext(input_path)[0]
        output_path = f"{base_name}_fixed.mp4"
        
        # Fast rotation with optimized settings
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-c:v', 'libx264',           # H.264 codec
            '-preset', 'ultrafast',       # Fastest encoding preset
            '-crf', '23',                 # Good quality
            '-c:a', 'copy',               # Copy audio without re-encoding
            '-vf', 'rotate=PI',           # Rotate 180 degrees
            '-movflags', '+faststart',    # Optimize for web streaming
            '-y',                         # Overwrite output file
            output_path
        ]
        
        print(f"Fixing video orientation: {os.path.basename(input_path)}")
        print(f"Running: {' '.join(cmd)}")
        
        # Run orientation fix with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180  # 3 minute timeout
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            print(f"Orientation fix successful: {os.path.basename(output_path)}")
            return output_path
        else:
            print(f"Orientation fix failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Orientation fix timed out after 3 minutes")
        return None
    except Exception as e:
        print(f"Error during orientation fix: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python fix_video_orientation.py <input_video_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    result = fix_video_orientation(input_path)
    
    if result:
        print(f"Success: {result}")
        sys.exit(0)
    else:
        print("Failed to fix video orientation")
        sys.exit(1) 