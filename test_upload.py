#!/usr/bin/env python3
"""
Test script to verify the upload process works correctly.
This simulates uploading a video file to test the transcoding and orientation fixing.
"""

import requests
import os
import time

def test_video_upload():
    """Test uploading a video file to verify the process works"""
    
    # Check if we have a test video file
    test_video = "uploads/ede8684d-e4d8-4800-b371-57e8f782d459_Mom_and_dad_with_Eliott.mp4"
    
    if not os.path.exists(test_video):
        print("No test video found. Please upload a video through the web interface first.")
        return
    
    print("Testing video upload process...")
    print(f"Using test video: {test_video}")
    
    # Prepare the upload
    url = "http://127.0.0.1:5001/upload"
    
    with open(test_video, 'rb') as f:
        files = {'file': ('test_video.mp4', f, 'video/mp4')}
        
        print("Uploading video...")
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Upload successful!")
            print(f"File URL: {result.get('url')}")
            print(f"File size: {result.get('size')} bytes")
            print(f"File type: {result.get('type')}")
            
            # Check if the file was transcoded
            if '_web' in result.get('url', ''):
                print("✅ Video was transcoded to web-compatible format")
            else:
                print("⚠️ Video was not transcoded (using original)")
                
            # Check if the file was orientation-fixed
            if '_fixed' in result.get('url', ''):
                print("✅ Video orientation was fixed")
            else:
                print("⚠️ Video orientation was not fixed")
                
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(response.text)

def check_server_status():
    """Check if the Flask server is running"""
    try:
        response = requests.get("http://127.0.0.1:5001/")
        if response.status_code == 200:
            print("✅ Flask server is running")
            return True
        else:
            print(f"⚠️ Flask server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Flask server is not running")
        print("Please start the server with: flask run --port 5001")
        return False

if __name__ == "__main__":
    print("=== Video Upload Test ===")
    
    if not check_server_status():
        exit(1)
    
    test_video_upload()
    
    print("\n=== Test Complete ===")
    print("If the upload was successful, you should see:")
    print("1. A new video file in the uploads directory")
    print("2. The video should play correctly in your timeline app")
    print("3. The video should have correct orientation") 