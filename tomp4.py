from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os
import subprocess
import uuid
from io import BytesIO
import magic
import shutil

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

# NOT used!!!
def downscale_video(video_file, quality='high'):
    """
    Downscale MP4 video file with different quality presets.
    
    Args:
        video_file: FileStorage object containing MP4 video
        quality: String indicating quality preset ('low', 'medium', 'high')
    
    Returns:
        FileStorage: Downscaled video file if successful, None if failed
    """
    temp_path = None
    output_path = None
    
    try:
        # Get FFmpeg path
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path is None:
            raise Exception("FFmpeg not found. Please install FFmpeg and add it to system PATH")
            
        # Create temporary directory if it doesn't exist
        temp_dir = 'temp_uploads'
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate secure filenames
        temp_filename = str(uuid.uuid4()) + '_' + secure_filename(video_file.filename)
        output_filename = f"downscaled_{secure_filename(video_file.filename)}"
        
        temp_path = os.path.join(temp_dir, temp_filename)
        output_path = os.path.join(temp_dir, output_filename)
        
        # Save uploaded file temporarily
        video_file.save(temp_path)
        
        # Quality presets
        quality_settings = {
            'low': {
                'scale': '640:360',  # 360p
                'bitrate': '800k',
                'audio_bitrate': '96k',
                'crf': '28'
            },
            'medium': {
                'scale': '1280:720',  # 720p
                'bitrate': '2000k',
                'audio_bitrate': '128k',
                'crf': '23'
            },
            'high': {
                'scale': '1920:1080',  # 1080p
                'bitrate': '4000k',
                'audio_bitrate': '192k',
                'crf': '20'
            }
        }
        
        # Get settings for selected quality
        settings = quality_settings.get(quality.lower(), quality_settings['medium'])
        
        # Build FFmpeg command for downscaling
        command = [
            ffmpeg_path,
            '-i', temp_path,
            '-vf', f'scale={settings["scale"]}:force_original_aspect_ratio=decrease,pad={settings["scale"]}:-1:-1:color=black',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', settings['crf'],
            '-maxrate', settings['bitrate'],
            '-bufsize', str(int(settings['bitrate'].replace('k', '')) * 2) + 'k',
            '-c:a', 'aac',
            '-b:a', settings['audio_bitrate'],
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        print(f"Running FFmpeg command: {' '.join(command)}")
        
        # Run FFmpeg command
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
        
        return converted_file
        
    except Exception as e:
        print(f"Error during downscaling: {str(e)}")
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

        # Get file size
        file_size = os.path.getsize(temp_path)

        # Create new FileStorage object
        with open(temp_path, 'rb') as f:
            file_data = BytesIO(f.read())
            
        new_file = FileStorage(
            stream=file_data,
            filename=temp_filename,
            content_type='video/mp4'
        )

        return new_file, file_size
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass