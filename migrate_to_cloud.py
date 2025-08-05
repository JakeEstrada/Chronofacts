#!/usr/bin/env python3
"""
Migration script to help move from local database to cloud
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3  # For AWS S3
import requests

def export_database_data():
    """Export current database data"""
    try:
        # Connect to local database
        conn = psycopg2.connect(
            host="localhost",
            database="timeline_db",
            user="timeline_user", 
            password="your_password"
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Export all tables
        tables = ['users', 'timelines', 'spans', 'occurrences', 'instances', 'media']
        
        for table in tables:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            print(f"Exported {len(rows)} rows from {table}")
            
        cur.close()
        conn.close()
        
        print("Database export completed!")
        
    except Exception as e:
        print(f"Error exporting database: {e}")

def upload_files_to_s3():
    """Upload files from uploads/ to S3"""
    try:
        s3 = boto3.client('s3')
        bucket_name = 'your-timeline-bucket'
        
        uploads_dir = 'uploads'
        for filename in os.listdir(uploads_dir):
            if os.path.isfile(os.path.join(uploads_dir, filename)):
                file_path = os.path.join(uploads_dir, filename)
                
                # Upload to S3
                s3.upload_file(
                    file_path, 
                    bucket_name, 
                    f"uploads/{filename}"
                )
                
                print(f"Uploaded {filename} to S3")
                
    except Exception as e:
        print(f"Error uploading to S3: {e}")

def update_database_urls():
    """Update file_url fields to point to S3"""
    try:
        # Connect to cloud database
        conn = psycopg2.connect(
            host="your-cloud-host",
            database="your-cloud-db",
            user="your-cloud-user",
            password="your-cloud-password"
        )
        
        cur = conn.cursor()
        
        # Update file_urls to point to S3
        cur.execute("""
            UPDATE media 
            SET file_url = REPLACE(file_url, '/uploads/', 'https://your-bucket.s3.amazonaws.com/uploads/')
            WHERE file_url LIKE '/uploads/%'
        """)
        
        updated_rows = cur.rowcount
        print(f"Updated {updated_rows} file URLs")
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error updating URLs: {e}")

if __name__ == "__main__":
    print("Timeline Migration Script")
    print("1. Export database data")
    print("2. Upload files to S3") 
    print("3. Update database URLs")
    
    choice = input("Choose option (1-3): ")
    
    if choice == "1":
        export_database_data()
    elif choice == "2":
        upload_files_to_s3()
    elif choice == "3":
        update_database_urls()
    else:
        print("Invalid choice") 