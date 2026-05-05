import base64
import numpy as np
import cv2
import os
import pymysql

def get_db_connection():
    import os
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD', ''),
        'database': os.getenv('MYSQL_DATABASE', 'attendance_db'),
        'cursorclass': pymysql.cursors.DictCursor
    }
    return pymysql.connect(**db_config)

def process_simultaneous_scan(frame_base64, qr_data):
    """
    Process a simultaneous QR and face scan from a single camera frame.
    
    Args:
        frame_base64: Base64 encoded image string from webcam
        qr_data: QR code data already decoded by html5-qrcode on frontend
    
    Returns:
        dict with success status and verification details
    """
    try:
        # Try to import face_recognition, fall back gracefully if not available
        try:
            import face_recognition
            face_recognition_available = True
        except ImportError:
            face_recognition_available = False
        
        # Decode base64 image to numpy array
        try:
            # Handle both with and without prefix
            if frame_base64.startswith('data:image'):
                frame_base64 = frame_base64.split(',')[1]
            
            image_bytes = base64.b64decode(frame_base64)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return {
                    "success": False,
                    "error": "invalid_image",
                    "message": "Could not decode image frame"
                }
        except Exception as e:
            return {
                "success": False,
                "error": "decode_error",
                "message": f"Failed to decode frame: {str(e)}"
            }
        
        # Face detection and recognition (if library available)
        if face_recognition_available:
            try:
                # Convert BGR to RGB for face_recognition
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect face locations
                face_locations = face_recognition.face_locations(rgb_frame)
                
                if len(face_locations) == 0:
                    return {
                        "success": False,
                        "error": "no_face",
                        "message": "Please face the camera directly"
                    }
                
                # Get face encodings
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
                
                if len(face_encodings) == 0:
                    return {
                        "success": False,
                        "error": "no_face_encoding",
                        "message": "Could not encode detected face"
                    }
                
                live_face_encoding = face_encodings[0]
                
            except Exception as e:
                return {
                    "success": False,
                    "error": "face_detection_error",
                    "message": f"Face detection failed: {str(e)}"
                }
        else:
            # face_recognition not installed - will use QR-only mode
            live_face_encoding = None
        
        # Query database for student using qr_data
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.id, s.name, s.course_id, c.name as course_name
                FROM students s
                LEFT JOIN courses c ON s.course_id = c.id
                WHERE s.qr_data = %s
            ''', (qr_data,))
            
            student = cursor.fetchone()
            
            if not student:
                return {
                    "success": False,
                    "error": "invalid_qr",
                    "message": "QR code not recognized"
                }
            
            student_id = student['id']
            student_name = student['name']
            course_name = student['course_name']
            
            # Check if stored face exists
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            face_image_path = os.path.join(base_dir, 'frontend', 'static', 'images', 'faces', f'{student_id}.png')
            
            if not os.path.exists(face_image_path) or not face_recognition_available:
                # No face registered or face_recognition not available - QR only mode
                return {
                    "success": True,
                    "skip_face": True,
                    "student_id": student_id,
                    "student_name": student_name,
                    "course_name": course_name,
                    "message": "No face registered — QR only mode"
                }
            
            # Load stored face and compare
            try:
                stored_image = face_recognition.load_image_file(face_image_path)
                stored_face_encodings = face_recognition.face_encodings(stored_image)
                
                if len(stored_face_encodings) == 0:
                    return {
                        "success": True,
                        "skip_face": True,
                        "student_id": student_id,
                        "student_name": student_name,
                        "course_name": course_name,
                        "message": "No valid face stored — QR only mode"
                    }
                
                stored_face_encoding = stored_face_encodings[0]
                
                # Compare faces with tolerance
                matches = face_recognition.compare_faces(
                    [stored_face_encoding], 
                    live_face_encoding, 
                    tolerance=0.5
                )
                
                if matches[0]:
                    return {
                        "success": True,
                        "verified": True,
                        "student_id": student_id,
                        "student_name": student_name,
                        "course_name": course_name,
                        "message": "Identity verified by QR and Face"
                    }
                else:
                    return {
                        "success": False,
                        "error": "face_mismatch",
                        "message": "Face does not match this QR code"
                    }
                    
            except Exception as e:
                return {
                    "success": True,
                    "skip_face": True,
                    "student_id": student_id,
                    "student_name": student_name,
                    "course_name": course_name,
                    "message": f"Face comparison error — QR only mode: {str(e)}"
                }
                
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                
    except Exception as e:
        return {
            "success": False,
            "error": "processing_error",
            "message": f"Scan processing failed: {str(e)}"
        }
