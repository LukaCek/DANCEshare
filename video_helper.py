import cv2
import os

def extract_frame_at(video_path, time=2):
    """
    Extract a frame from a video file after x seconds and save it as an image.
    
    Parameters:
    video_path (str): Path to the input video file
    """
    # Check if video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found. Path: '{video_path}'.")
        return False
    
    # Create output filename in the same directory as the video
    output_filename = os.path.splitext(video_path)[0] + ".jpg"
    
    # Open the video file
    video = cv2.VideoCapture(video_path)
    
    # Get video FPS
    fps = video.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        print("Error: Could not determine video FPS.")
        video.release()
        return False
    
    # Calculate frame number for {time} seconds
    frame_number = int(fps * time)
    
    # Get total number of frames
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        print("Error: Video appears to be empty or corrupted.")
        video.release()
        return False
    
    # Check if video is long enough
    if frame_number >= total_frames:
        print(f"Warning: Video is shorter than {time} seconds. Using last frame instead.")
        frame_number = total_frames - 1
    
    # Set video to desired frame
    video.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    
    # Read the frame
    success, frame = video.read()
    
    if success:
        # Save the frame
        cv2.imwrite(output_filename, frame)
        print(f"Successfully extracted frame at {time} seconds (frame {frame_number})")
        print(f"Saved as: {output_filename}")
    else:
        print("Error: Could not extract frame")
    
    # Clean up
    video.release()
    
    return success

def video_length(video_path):
    """Get the length of a video in seconds"""
    if video_path:
        video = cv2.VideoCapture(video_path)
        fps = video.get(cv2.CAP_PROP_FPS)
        frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
        length = frames / fps
        video.release()
        return length

def video_size(video_path):
    """Get the size of a video in bytes"""
    if video_path:
        video = cv2.VideoCapture(video_path)
        size = os.path.getsize(video_path)
        video.release()
        return size