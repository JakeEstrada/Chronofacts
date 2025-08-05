# Video Upload Process

## What Happens When You Upload a New Video

### 1. File Upload
- Video file is saved to the `uploads/` directory with a unique UUID prefix
- Example: `123e4567-e89b-12d3-a456-426614174000_my_video.mp4`

### 2. Automatic Transcoding (if video)
- If the file is a video (content-type starts with 'video/'), it gets automatically transcoded
- Converts from HEVC/H.265 to H.264 for browser compatibility
- Creates: `123e4567-e89b-12d3-a456-426614174000_my_video_web.mp4`

### 3. Automatic Orientation Fix (if video)
- If transcoding succeeds, the video gets orientation correction
- Fixes upside-down videos by applying 180° rotation
- Creates: `123e4567-e89b-12d3-a456-426614174000_my_video_web_fixed.mp4`

### 4. Database Storage
- The URL returned points to the final processed version (fixed orientation)
- If transcoding fails, falls back to original file
- If orientation fixing fails, falls back to transcoded version

### 5. File Management
- All versions are kept on disk for safety
- When deleting, all related versions are cleaned up automatically

## File Naming Convention
- **Original**: `{uuid}_{filename}.mp4`
- **Transcoded**: `{uuid}_{filename}_web.mp4`
- **Fixed**: `{uuid}_{filename}_web_fixed.mp4`

## Error Handling
- If transcoding fails → uses original file
- If orientation fixing fails → uses transcoded file
- If both fail → uses original file
- All errors are logged for debugging

## Testing New Uploads
1. Upload a video through your timeline application
2. Check the server logs for transcoding messages
3. Verify the video plays correctly in the browser
4. Check that orientation is correct

## Manual Processing
If you need to process existing videos manually:
```bash
# Transcode all videos
python3 transcode_video.py

# Fix orientation for all transcoded videos
python3 fix_video_orientation.py

# Update database to use fixed videos
python3 update_video_urls.py fix
``` 