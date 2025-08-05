from flask import Flask, request, jsonify, send_from_directory, render_template_string, session, redirect, url_for
from flask_cors import CORS
from db import get_db_connection
from psycopg2.extras import RealDictCursor
import traceback
import bcrypt
import jwt
import datetime
import os
import uuid
from werkzeug.utils import secure_filename


print("Starting Flask server...")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Required for sessions
CORS(app)  # Enable CORS for all routes

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.method == 'GET':
                return redirect('/login')
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/timelines", methods=["GET", "POST"])
@require_auth
def timelines():
    if request.method == "GET":
        try:
            print("Attempting to connect to database...")
            conn = get_db_connection()
            print("Database connection successful")
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, title, description, start_date::text, end_date::text FROM timelines;")
            timelines = cur.fetchall()
            cur.close()
            conn.close()
            
            # Convert RealDictRow objects to regular dictionaries
            timeline_list = [dict(timeline) for timeline in timelines]
            print(f"Returning {len(timeline_list)} timelines")
            return jsonify(timeline_list)
        except Exception as e:
            print(f"Error fetching timelines: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return jsonify([])  # Return empty array on error
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                INSERT INTO timelines (title, description, start_date, end_date, user_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (data['title'], data['description'], data['start_date'], data['end_date'], 1))
            
            new_timeline = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify(dict(new_timeline))
        except Exception as e:
            print(f"Error creating timeline: {e}")
            return jsonify({"error": str(e)}), 500

@app.route("/timelines/<int:timeline_id>", methods=["PATCH", "DELETE"])
@require_auth
def update_timeline(timeline_id):
    if request.method == "PATCH":
        try:
            data = request.get_json()
            fields = []
            values = []
            for key in ["title", "description", "start_date", "end_date"]:
                if key in data:
                    fields.append(f"{key} = %s")
                    values.append(data[key])
            if not fields:
                return jsonify({"error": "No fields to update."}), 400
            values.append(timeline_id)
            set_clause = ", ".join(fields)
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(f"UPDATE timelines SET {set_clause} WHERE id = %s RETURNING *", values)
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            if updated:
                return jsonify(dict(updated))
            else:
                return jsonify({"error": "Timeline not found."}), 404
        except Exception as e:
            print(f"Error updating timeline: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == "DELETE":
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Delete related occurrences and spans first
            cur.execute("DELETE FROM occurrences WHERE timeline_id = %s", (timeline_id,))
            cur.execute("DELETE FROM spans WHERE timeline_id = %s", (timeline_id,))
            
            # Delete the timeline
            cur.execute("DELETE FROM timelines WHERE id = %s", (timeline_id,))
            
            if cur.rowcount == 0:
                return jsonify({"error": "Timeline not found."}), 404
                
            conn.commit()
            cur.close()
            conn.close()
            return '', 204
        except Exception as e:
            print(f"Error deleting timeline: {e}")
            return jsonify({"error": str(e)}), 500

@app.route("/occurrences", methods=["GET", "POST"])
@require_auth
def occurrences():
    if request.method == "GET":
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get occurrences
            cur.execute("SELECT *, 'occurrence' as type FROM occurrences;")
            occurrences = cur.fetchall()
            
            # Get spans
            cur.execute("SELECT *, 'span' as type FROM spans;")
            spans = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Combine and format results
            result = []
            
            # Add occurrences with is_span=false
            for occ in occurrences:
                occ_dict = dict(occ)
                occ_dict['is_span'] = False
                result.append(occ_dict)
            
            # Add spans with is_span=true
            for span in spans:
                span_dict = dict(span)
                span_dict['is_span'] = True
                span_dict['span'] = True  # For frontend compatibility
                result.append(span_dict)
            
            return jsonify(result)
        except Exception as e:
            print(f"Error fetching occurrences: {e}")
            return jsonify([])
    
    elif request.method == "POST":
        try:
            data = request.get_json()
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check if this is a span or occurrence
            if data.get('is_span'):
                # Insert as span
                cur.execute("""
                    INSERT INTO spans (timeline_id, title, start_date, end_date, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (data['timeline_id'], data['title'], data.get('start_date'), data.get('end_date'), data.get('description')))
            else:
                # Insert as occurrence
                cur.execute("""
                    INSERT INTO occurrences (timeline_id, title, date, description)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                """, (data['timeline_id'], data['title'], data.get('date'), data.get('description')))
            
            new_occurrence = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            
            return jsonify(dict(new_occurrence))
        except Exception as e:
            print(f"Error creating occurrence: {e}")
            return jsonify({"error": str(e)}), 500



@app.route("/occurrences/<int:occurrence_id>", methods=["PATCH", "DELETE"])
@require_auth
def update_or_delete_occurrence(occurrence_id):
    if request.method == "PATCH":
        try:
            data = request.get_json()
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Check if it's a span or occurrence
            cur.execute("SELECT id FROM spans WHERE id = %s", (occurrence_id,))
            is_span = cur.fetchone() is not None
            
            if is_span:
                # Update span
                fields = []
                values = []
                for key in ["title", "start_date", "end_date", "description"]:
                    if key in data:
                        fields.append(f"{key} = %s")
                        values.append(data[key])
                if not fields:
                    return jsonify({"error": "No fields to update."}), 400
                values.append(occurrence_id)
                set_clause = ", ".join(fields)
                cur.execute(f"UPDATE spans SET {set_clause} WHERE id = %s RETURNING *", values)
            else:
                # Update occurrence
                fields = []
                values = []
                for key in ["title", "date", "description"]:
                    if key in data:
                        fields.append(f"{key} = %s")
                        values.append(data[key])
                if not fields:
                    return jsonify({"error": "No fields to update."}), 400
                values.append(occurrence_id)
                set_clause = ", ".join(fields)
                cur.execute(f"UPDATE occurrences SET {set_clause} WHERE id = %s RETURNING *", values)
            
            updated = cur.fetchone()
            conn.commit()
            cur.close()
            conn.close()
            if updated:
                return jsonify(dict(updated))
            else:
                return jsonify({"error": "Item not found."}), 404
        except Exception as e:
            print(f"Error updating item: {e}")
            return jsonify({"error": str(e)}), 500
    elif request.method == "DELETE":
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Try to delete from spans first
            cur.execute("DELETE FROM spans WHERE id = %s", (occurrence_id,))
            if cur.rowcount == 0:
                # If not found in spans, try occurrences
                cur.execute("DELETE FROM occurrences WHERE id = %s", (occurrence_id,))
            
            conn.commit()
            cur.close()
            conn.close()
            return '', 204
        except Exception as e:
            print(f"Error deleting item: {e}")
            return jsonify({"error": str(e)}), 500



@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({'error': 'Invalid username or password'}), 401
        # Assign role
        role = 'admin' if user['username'] == 'admin' else 'viewer'
        # Create JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'username': user['username'],
            'role': role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=12)
        }, app.config.get('SECRET_KEY', 'supersecretkey'), algorithm='HS256')
        
        # Set session data
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = role
        
        return jsonify({'token': token, 'role': role, 'success': True})
    except Exception as e:
        print(f"Error in /login: {e}")
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500

# Add more routes like /occurrences, /events, /messages here

@app.route('/')
def index():
    """Redirect to login if not authenticated, otherwise serve timeline"""
    if 'user_id' not in session:
        return redirect('/login')
    try:
        with open('timeline.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Timeline application not found", 404

@app.route('/login')
def login_page():
    """Serve the login page"""
    if 'user_id' in session:
        return redirect('/')
    try:
        with open('login.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Login page not found", 404

@app.route('/timeline')
@require_auth
def timeline_page():
    """Serve the timeline page (requires authentication)"""
    try:
        with open('timeline.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Timeline page not found", 404

@app.route('/logout')
def logout():
    """Logout user and clear session"""
    session.clear()
    return redirect('/login')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to prevent 404 errors"""
    return '', 204  # Return no content

@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files from the media directory"""
    try:
        return send_from_directory('media', filename)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

@app.route('/upload', methods=['POST'])
@require_auth
def upload_file():
    """Handle file uploads with optimized video processing"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Create uploads directory if it doesn't exist
        uploads_dir = 'uploads'
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Save file to uploads directory
        upload_path = os.path.join(uploads_dir, unique_filename)
        file.save(upload_path)
        
        # Check if it's a video file
        if file.content_type and file.content_type.startswith('video/'):
            print(f"Video uploaded: {unique_filename}, type: {file.content_type}")
            
            # Quick check if video is already web-compatible
            try:
                import subprocess
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-select_streams', 'v:0', 
                    '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', upload_path
                ], capture_output=True, text=True, timeout=5)
                
                codec = result.stdout.strip()
                print(f"Video codec: {codec}")
                
                # If it's already H.264, skip transcoding
                if codec == 'h264':
                    print(f"Video is already H.264, skipping transcoding")
                    file_url = f"/uploads/{unique_filename}"
                    file_size = os.path.getsize(upload_path)
                else:
                    # Only transcode if necessary (HEVC/H.265)
                    if codec in ['hevc', 'h265']:
                        print(f"Transcoding HEVC video to H.264...")
                        try:
                            from transcode_video import transcode_video
                            transcoded_path = transcode_video(upload_path)
                            if transcoded_path:
                                transcoded_filename = os.path.basename(transcoded_path)
                                print(f"Successfully transcoded video to: {transcoded_filename}")
                                
                                # Quick orientation fix if needed
                                try:
                                    from fix_video_orientation import fix_video_orientation
                                    fixed_path = fix_video_orientation(transcoded_path)
                                    if fixed_path:
                                        fixed_filename = os.path.basename(fixed_path)
                                        print(f"Successfully fixed video orientation to: {fixed_filename}")
                                        file_url = f"/uploads/{fixed_filename}"
                                        file_size = os.path.getsize(fixed_path)
                                    else:
                                        file_url = f"/uploads/{transcoded_filename}"
                                        file_size = os.path.getsize(transcoded_path)
                                except Exception as e:
                                    print(f"Error during orientation fixing: {e}")
                                    file_url = f"/uploads/{transcoded_filename}"
                                    file_size = os.path.getsize(transcoded_path)
                            else:
                                print(f"Failed to transcode video, using original")
                                file_url = f"/uploads/{unique_filename}"
                                file_size = os.path.getsize(upload_path)
                        except Exception as e:
                            print(f"Error during video transcoding: {e}")
                            file_url = f"/uploads/{unique_filename}"
                            file_size = os.path.getsize(upload_path)
                    else:
                        # For other codecs, just use the original
                        print(f"Using original video (codec: {codec})")
                        file_url = f"/uploads/{unique_filename}"
                        file_size = os.path.getsize(upload_path)
                        
            except Exception as e:
                print(f"Error checking video codec: {e}")
                # Fallback to original file
                file_url = f"/uploads/{unique_filename}"
                file_size = os.path.getsize(upload_path)
        else:
            # Non-video file
            file_url = f"/uploads/{unique_filename}"
            file_size = os.path.getsize(upload_path)
        
        # Return file info immediately
        return jsonify({
            "success": True,
            "filename": filename,
            "url": file_url,
            "type": file.content_type,
            "size": file_size
        })
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/uploads/<path:filename>', methods=['GET', 'DELETE'])
def serve_uploads(filename):
    """Serve uploaded files from the uploads directory with proper headers"""
    if request.method == 'DELETE':
        return delete_uploaded_file(filename)
    
    try:
        # Remove cache-busting parameter if present
        if '?' in filename:
            filename = filename.split('?')[0]
        
        # Set proper headers for video files
        response = send_from_directory('uploads', filename)
        
        # Add CORS headers for video files
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range'
        
        # Set proper content type for video files
        if filename.lower().endswith(('.mp4', '.webm', '.ogg', '.mov', '.avi', '.mkv')):
            response.headers['Content-Type'] = 'video/mp4'
            # Enable range requests for video streaming
            response.headers['Accept-Ranges'] = 'bytes'
            # Add cache control headers
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        
        return response
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

def delete_uploaded_file(filename):
    """Delete an uploaded file from disk and database"""
    try:
        print(f"Attempting to delete file: {filename}")
        
        # Clean the filename
        clean_filename = filename.split('?')[0]
        file_path = os.path.join('uploads', clean_filename)
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return jsonify({"error": "File not found"}), 404
        
        # Delete the file from disk
        os.remove(file_path)
        print(f"Successfully deleted file from disk: {file_path}")
        
        # Also try to delete all related versions of the file
        base_name = clean_filename.replace('_web_fixed.mp4', '').replace('_web.mp4', '').replace('.mp4', '')
        
        # Delete original file
        original_filename = f"{base_name}.mp4"
        original_path = os.path.join('uploads', original_filename)
        if os.path.exists(original_path) and original_filename != clean_filename:
            os.remove(original_path)
            print(f"Also deleted original file: {original_filename}")
        
        # Delete transcoded file
        transcoded_filename = f"{base_name}_web.mp4"
        transcoded_path = os.path.join('uploads', transcoded_filename)
        if os.path.exists(transcoded_path) and transcoded_filename != clean_filename:
            os.remove(transcoded_path)
            print(f"Also deleted transcoded file: {transcoded_filename}")
        
        # Delete fixed file
        fixed_filename = f"{base_name}_web_fixed.mp4"
        fixed_path = os.path.join('uploads', fixed_filename)
        if os.path.exists(fixed_path) and fixed_filename != clean_filename:
            os.remove(fixed_path)
            print(f"Also deleted fixed file: {fixed_filename}")
        
        # Also delete from database
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First find the instance_id for this file
        cur.execute("""
            SELECT instance_id FROM media WHERE file_url = %s
        """, (f'/uploads/{clean_filename}',))
        
        instance_result = cur.fetchone()
        if instance_result:
            instance_id = instance_result[0]
            print(f"Found instance_id: {instance_id}")
            
            # Delete from media table first (due to foreign key constraint)
            cur.execute("""
                DELETE FROM media WHERE file_url = %s
            """, (f'/uploads/{clean_filename}',))
            
            media_deleted = cur.rowcount
            
            # Then delete from instances table
            cur.execute("""
                DELETE FROM instances WHERE id = %s
            """, (instance_id,))
            
            instances_deleted = cur.rowcount
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"Deleted {media_deleted} media records and {instances_deleted} instances")
            
            return jsonify({
                "success": True, 
                "message": "File deleted successfully",
                "file": clean_filename,
                "media_deleted": media_deleted,
                "instances_deleted": instances_deleted
            })
        else:
            print(f"No media record found for file: {clean_filename}")
            conn.close()
            return jsonify({
                "success": True, 
                "message": "File deleted from disk (no database record found)",
                "file": clean_filename,
                "media_deleted": 0,
                "instances_deleted": 0
            })
        
    except Exception as e:
        print(f"Error deleting file {filename}: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/messages/<int:occurrence_id>/files', methods=['POST'])
@require_auth
def attach_file_to_message(occurrence_id):
    """Attach a file to a message"""
    try:
        print(f"Attaching file to occurrence {occurrence_id}")
        data = request.get_json()
        print(f"Request data: {data}")
        
        file_url = data.get('file_url')
        file_type = data.get('file_type')
        file_size = data.get('file_size', 0)
        
        if not file_url:
            print("No file URL provided")
            return jsonify({"error": "No file URL provided"}), 400
        
        print(f"File URL: {file_url}")
        print(f"File type: {file_type}")
        print(f"File size: {file_size}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if occurrence exists
        cur.execute("SELECT id FROM occurrences WHERE id = %s", (occurrence_id,))
        occurrence = cur.fetchone()
        if not occurrence:
            print(f"Occurrence {occurrence_id} not found")
            return jsonify({"error": "Occurrence not found"}), 404
        
        print(f"Occurrence {occurrence_id} found")
        
        # Create instance for the file
        print("Creating instance...")
        cur.execute("""
            INSERT INTO instances (occurrence_id, content) 
            VALUES (%s, %s) 
            RETURNING id
        """, (occurrence_id, f"File: {file_url}"))
        
        instance_id = cur.fetchone()[0]
        print(f"Created instance {instance_id}")
        
        # Create media record with additional metadata
        print("Creating media record...")
        cur.execute("""
            INSERT INTO media (instance_id, file_url, file_type) 
            VALUES (%s, %s, %s)
            RETURNING id
        """, (instance_id, file_url, file_type))
        
        media_id = cur.fetchone()[0]
        print(f"Created media record {media_id}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        result = {
            "success": True, 
            "instance_id": instance_id,
            "media_id": media_id,
            "file_url": file_url,
            "file_type": file_type,
            "file_size": file_size
        }
        print(f"Returning result: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error attaching file: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/occurrences/<int:occurrence_id>/messages', methods=['GET'])
@require_auth
def get_occurrence_messages(occurrence_id):
    """Get messages and files for a specific occurrence"""
    try:
        print(f"Fetching messages for occurrence {occurrence_id}")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get instances (messages and files) for this occurrence
        cur.execute("""
            SELECT i.id, i.content, i.created_at, m.file_url, m.file_type
            FROM instances i
            LEFT JOIN media m ON i.id = m.instance_id
            WHERE i.occurrence_id = %s
            ORDER BY i.created_at
        """, (occurrence_id,))
        
        instances = cur.fetchall()
        print(f"Found {len(instances)} instances for occurrence {occurrence_id}")
        
        cur.close()
        conn.close()
        
        # Format the results
        result = []
        for instance in instances:
            print(f"Processing instance: {instance}")
            if instance['file_url']:
                # This is a file attachment
                file_data = {
                    'type': instance['file_type'] or '',
                    'name': os.path.basename(instance['file_url']),
                    'url': instance['file_url'],
                    'timestamp': instance['created_at'].isoformat(),
                    'size': os.path.getsize(os.path.join('uploads', os.path.basename(instance['file_url']))) if os.path.exists(os.path.join('uploads', os.path.basename(instance['file_url']))) else 0,
                    'media_id': instance['id']  # This is the instance_id, which is what we need for the old delete endpoint
                }
                print(f"Adding file: {file_data}")
                result.append(file_data)
            else:
                # This is a text message
                message_data = {
                    'type': 'message',
                    'text': instance['content'],
                    'timestamp': instance['created_at'].isoformat()
                }
                print(f"Adding message: {message_data}")
                result.append(message_data)
        
        print(f"Returning {len(result)} items")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error fetching messages: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify([])

@app.route('/messages/<int:occurrence_id>/files/<int:instance_id>', methods=['DELETE'])
@require_auth
def delete_file(occurrence_id, instance_id):
    try:
        print(f"DELETE REQUEST RECEIVED: Deleting file instance {instance_id} from occurrence {occurrence_id}")
        print(f"Session data: {session}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"User authenticated: {'user_id' in session}")
        print(f"URL parameters: occurrence_id={occurrence_id}, instance_id={instance_id}")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get the file info before deleting
        print(f"Checking database for instance {instance_id} in occurrence {occurrence_id}")
        cur.execute("""
            SELECT m.file_url, i.occurrence_id, i.id as instance_id, m.id as media_id
            FROM instances i
            LEFT JOIN media m ON i.id = m.instance_id
            WHERE i.id = %s AND i.occurrence_id = %s
        """, (instance_id, occurrence_id))
        
        file_info = cur.fetchone()
        print(f"Database query result: {file_info}")
        if not file_info:
            print(f"No file found in database for instance {instance_id}")
            return jsonify({"error": "File not found"}), 404
        
        # Delete from media table first
        print(f"Deleting from media table where instance_id = {instance_id}")
        cur.execute("DELETE FROM media WHERE instance_id = %s", (instance_id,))
        media_deleted = cur.rowcount
        print(f"Deleted {media_deleted} media records")
        
        # Delete from instances table
        print(f"Deleting from instances table where id = {instance_id} AND occurrence_id = {occurrence_id}")
        cur.execute("DELETE FROM instances WHERE id = %s AND occurrence_id = %s", (instance_id, occurrence_id))
        instances_deleted = cur.rowcount
        print(f"Deleted {instances_deleted} instance records")
        
        if instances_deleted == 0:
            print(f"No instances deleted - file not found")
            return jsonify({"error": "File not found"}), 404
        
        # Delete the actual file from uploads folder
        if file_info['file_url']:
            file_path = os.path.join('uploads', os.path.basename(file_info['file_url']))
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"Successfully deleted file instance {instance_id}")
        return jsonify({"success": True, "message": "File deleted successfully"})
        
    except Exception as e:
        print(f"Error deleting file: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@app.route('/clear-session')
def clear_session():
    """Force clear session and redirect to login"""
    session.clear()
    response = redirect('/login')
    response.delete_cookie('session')
    return response

if __name__ == "__main__":
    try:
        print("Starting Flask development server...")
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"Flask crashed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
