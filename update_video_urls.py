#!/usr/bin/env python3
"""
Script to update video URLs in the database to point to transcoded web-compatible versions.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from pathlib import Path

def get_db_connection():
    """Get database connection"""
    conn = psycopg2.connect(
        dbname="timeline_db",
        user="timeline_user",
        password="Paradox*456*",
        host="localhost"
    )
    return conn

def update_video_urls():
    """
    Update video URLs in the database to point to transcoded web-compatible versions.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get all media records with video files
        cur.execute("""
            SELECT m.id, m.file_url, m.file_type
            FROM media m
            WHERE m.file_type LIKE 'video/%' OR m.file_url LIKE '%.mp4'
        """)
        
        media_records = cur.fetchall()
        print(f"Found {len(media_records)} video records in database")
        
        updated_count = 0
        
        for record in media_records:
            old_url = record['file_url']
            file_name = os.path.basename(old_url)
            
            # Check if transcoded version exists
            transcoded_name = file_name.replace('.mp4', '_web.mp4')
            transcoded_path = f"uploads/{transcoded_name}"
            
            if os.path.exists(transcoded_path):
                new_url = f"/uploads/{transcoded_name}"
                
                # Update the database
                cur.execute("""
                    UPDATE media 
                    SET file_url = %s 
                    WHERE id = %s
                """, (new_url, record['id']))
                
                print(f"Updated media ID {record['id']}: {old_url} -> {new_url}")
                updated_count += 1
            else:
                print(f"No transcoded version found for {file_name}")
        
        conn.commit()
        print(f"\nSuccessfully updated {updated_count} video URLs")
        
    except Exception as e:
        print(f"Error updating video URLs: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def update_to_fixed_videos():
    """
    Update video URLs in the database to point to fixed orientation versions.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Get all media records with video files
        cur.execute("""
            SELECT m.id, m.file_url, m.file_type
            FROM media m
            WHERE m.file_type LIKE 'video/%' OR m.file_url LIKE '%.mp4'
        """)
        
        media_records = cur.fetchall()
        print(f"Found {len(media_records)} video records in database")
        
        updated_count = 0
        
        for record in media_records:
            old_url = record['file_url']
            file_name = os.path.basename(old_url)
            
            # Check if fixed version exists
            if '_web.mp4' in file_name:
                fixed_name = file_name.replace('_web.mp4', '_web_fixed.mp4')
            else:
                fixed_name = file_name.replace('.mp4', '_web_fixed.mp4')
            
            fixed_path = f"uploads/{fixed_name}"
            
            if os.path.exists(fixed_path):
                new_url = f"/uploads/{fixed_name}"
                
                # Update the database
                cur.execute("""
                    UPDATE media 
                    SET file_url = %s 
                    WHERE id = %s
                """, (new_url, record['id']))
                
                print(f"Updated media ID {record['id']}: {old_url} -> {new_url}")
                updated_count += 1
            else:
                print(f"No fixed version found for {file_name}")
        
        conn.commit()
        print(f"\nSuccessfully updated {updated_count} video URLs to fixed orientation")
        
    except Exception as e:
        print(f"Error updating video URLs: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def list_video_files():
    """
    List all video files in the uploads directory and their transcoded versions.
    """
    uploads_dir = Path('uploads')
    if not uploads_dir.exists():
        print("Uploads directory does not exist")
        return
    
    video_files = list(uploads_dir.glob('*.mp4'))
    print(f"Found {len(video_files)} video files:")
    
    for video_file in video_files:
        transcoded_file = video_file.parent / f"{video_file.stem}_web.mp4"
        fixed_file = video_file.parent / f"{video_file.stem}_web_fixed.mp4"
        
        status = "✓" if transcoded_file.exists() else "✗"
        fixed_status = "✓" if fixed_file.exists() else "✗"
        size = video_file.stat().st_size / (1024 * 1024)  # MB
        print(f"{status} {video_file.name} ({size:.1f}MB)")
        if transcoded_file.exists():
            transcoded_size = transcoded_file.stat().st_size / (1024 * 1024)  # MB
            print(f"  └─ {transcoded_file.name} ({transcoded_size:.1f}MB)")
        if fixed_file.exists():
            fixed_size = fixed_file.stat().st_size / (1024 * 1024)  # MB
            print(f"    └─ {fixed_file.name} ({fixed_size:.1f}MB) [FIXED ORIENTATION]")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "list":
            list_video_files()
        elif sys.argv[1] == "fix":
            update_to_fixed_videos()
        else:
            print("Usage: python3 update_video_urls.py [list|fix]")
    else:
        update_video_urls() 