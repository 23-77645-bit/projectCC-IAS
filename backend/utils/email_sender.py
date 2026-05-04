import os
from flask_mail import Message

def send_qr_email(student_name, student_email, qr_image_path):
    """
    Send QR code image to student via email.
    
    Args:
        student_name: Student's full name
        student_email: Student's email address
        qr_image_path: Path to the QR code image file
    
    Returns:
        bool: True on success, False on failure
    """
    try:
        from app import mail, app
        
        subject = "Your QR Code for Attendance - Batangas State University"
        
        body = f"""Dear {student_name},

Welcome to Batangas State University ARASOF-Nasugbu!

Your unique QR code for attendance tracking has been generated. Please save the attached image and present it when scanning for attendance in your classes.

Instructions:
1. Save the attached QR code image to your device
2. Show this QR code to the scanner when attending class
3. Keep this QR code secure and do not share it with others

If you have any questions, please contact your administrator.

Best regards,
Batangas State University ARASOF-Nasugbu
Attendance System
"""
        
        with app.app_context():
            msg = Message(
                subject=subject,
                recipients=[student_email],
                body=body,
                sender=app.config.get('MAIL_USERNAME')
            )
            
            # Attach QR image
            if os.path.exists(qr_image_path):
                with open(qr_image_path, 'rb') as f:
                    msg.attach(
                        filename=os.path.basename(qr_image_path),
                        content_type='image/png',
                        data=f.read()
                    )
            
            mail.send(msg)
        
        return True
        
    except Exception as e:
        print(f"Error sending email to {student_email}: {str(e)}")
        return False
