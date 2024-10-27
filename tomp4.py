from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import subprocess
import uuid
from io import BytesIO
import magic

def convert_to_mp4(video_file):
    """
    Convert uploaded video file to MP4 format using FFmpeg and return as FileStorage.
    Supports various input formats including: MOV, AVI, WMV, FLV, MKV, WEBM, etc.
    
    Args:
        video_file: FileStorage object from request.files
        
    Returns:
        tuple: (FileStorage, size) of converted MP4 file if successful, None if failed
    """
    temp_path = None
    output_path = None
    
    try:
        # Create temporary directory if it doesn't exist
        temp_dir = 'temp_uploads'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate secure filenames
        temp_filename = str(uuid.uuid4()) + '_' + secure_filename(video_file.filename)
        output_filename = os.path.splitext(temp_filename)[0] + '.mp4'
        
        temp_path = os.path.join(temp_dir, temp_filename)
        output_path = os.path.join(temp_dir, output_filename)
        
        # Save uploaded file temporarily
        video_file.save(temp_path)
        
        # Check if the file is actually a video
        mime = magic.Magic(mime=True)
        file_mime = mime.from_file(temp_path)
        
        if not file_mime.startswith('video/'):
            raise Exception(f"Uploaded file is not a video. Detected MIME type: {file_mime}")
        
        # Convert video to MP4 using FFmpeg with more robust settings
        command = [
            'ffmpeg',
            '-i', temp_path,
            '-c:v', 'libx264',     # Video codec
            '-preset', 'medium',   # Compression preset
            '-crf', '23',          # Constant Rate Factor (quality)
            '-c:a', 'aac',         # Audio codec
            '-b:a', '128k',        # Audio bitrate
            '-movflags', '+faststart',  # Enable streaming
            '-y',                  # Overwrite output file if exists
            output_path
        ]
        
        # Run FFmpeg command with timeout
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300  # 5 minute timeout
        )
        
        # Check if conversion was successful
        if result.returncode != 0:
            raise Exception(f"FFmpeg conversion failed: {result.stderr.decode()}")
        
        # Verify the output file exists and has size
        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise Exception("Conversion failed: Output file is empty or missing")
        
        # Create FileStorage object from the converted file
        with open(output_path, 'rb') as f:
            file_data = BytesIO(f.read())
            
        converted_file = FileStorage(
            stream=file_data,
            filename=output_filename,
            content_type='video/mp4'
        )

        # get the size of the converted file
        try:
            converted_file_size = os.path.getsize(output_path)
        except:
            converted_file_size = None
        
        return converted_file, converted_file_size
        
    except subprocess.TimeoutExpired:
        print("Conversion timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return None
        
    finally:
        # Clean up temporary files
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass

def video_size_save(video_file):
    temp_path = None
    try:
        # Create temporary directory if it doesn't exist
        temp_dir = 'temp_uploads'
        os.makedirs(temp_dir, exist_ok=True)

        temp_filename = str(uuid.uuid4()) + '_' + secure_filename(video_file.filename)
        temp_path = os.path.join(temp_dir, temp_filename)

        # Save uploaded file temporarily
        video_file.save(temp_path)

        return os.path.getsize(temp_path)
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass