from flask import Flask, request, jsonify, send_from_directory, render_template_string, session, redirect, url_for
from flask_cors import CORS
from db import get_db_connection
from psycopg2.extras import RealDictCursor
import traceback
import bcrypt
import jwt
import datetime
import os


print("Starting Flask server...")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Required for sessions
CORS(app)  # Enable CORS for all routes

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
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
        # Clear all sessions on startup
        with app.app_context():
            session.clear()
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"Flask crashed with error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
