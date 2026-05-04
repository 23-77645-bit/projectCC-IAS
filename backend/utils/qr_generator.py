import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def generate_qr(student_id, student_name, qr_data):
    """
    Generate a QR code image with student name below it.
    
    Args:
        student_id: Student ID number
        student_name: Student's full name
        qr_data: Unique QR data string
    
    Returns:
        str: File path to the saved QR image, or None on failure
    """
    try:
        # Define paths
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'frontend', 'static', 'images', 'qrcodes')
        os.makedirs(base_dir, exist_ok=True)
        
        filename = f"{qr_data}.png"
        filepath = os.path.join(base_dir, filename)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        qr_image = qr_image.convert('RGB')
        
        # Add text below QR code using Pillow
        # Calculate new image size with space for text
        qr_width, qr_height = qr_image.size
        text_height = 40
        new_height = qr_height + text_height
        
        # Create new image with white background
        final_image = Image.new('RGB', (qr_width, new_height), 'white')
        final_image.paste(qr_image, (0, 0))
        
        # Draw student name below QR
        draw = ImageDraw.Draw(final_image)
        
        # Try to use a default font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            font = ImageFont.load_default()
        
        # Get text bounding box for centering
        text_bbox = draw.textbbox((0, 0), student_name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (qr_width - text_width) // 2
        text_y = qr_height + 5
        
        draw.text((text_x, text_y), student_name, fill='black', font=font)
        
        # Save the image
        final_image.save(filepath, 'PNG')
        
        return filepath
        
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return None
