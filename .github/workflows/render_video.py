import json
import base64
import os
import subprocess
from pathlib import Path

def create_video():
    print("🎬 Starting video creation...")
    
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Load video data from n8n
    with open("video_data.json", "r") as f:
        data = json.loads(f.read())
    
    print(f"📊 Processing: {data.get('title', 'Unknown')}")
    print(f"📸 Images: {len(data.get('images', []))}")
    print(f"🎵 Audio: {len(data.get('audio', {}).get('data', ''))} characters")
    
    # Save audio file
    audio_data = base64.b64decode(data['audio']['data'])
    audio_path = "temp_audio.mp3"
    with open(audio_path, "wb") as f:
        f.write(audio_data)
    
    print(f"🎵 Audio saved: {len(audio_data)} bytes")
    
    # Save image files
    image_paths = []
    for i, img in enumerate(data['images']):
        img_data = base64.b64decode(img['data'])
        img_path = f"temp_image_{i:03d}.png"
        with open(img_path, "wb") as f:
            f.write(img_data)
        image_paths.append(img_path)
        print(f"📸 Image {i+1} saved: {len(img_data)} bytes")
    
    # Calculate timing
    duration = float(data.get('duration', 10))
    time_per_image = duration / len(image_paths)
    
    print(f"⏱️ Video duration: {duration}s")
    print(f"⏱️ Time per image: {time_per_image:.2f}s")
    
    # Create FFmpeg concat file
    with open("image_list.txt", "w") as f:
        for img_path in image_paths:
            f.write(f"file '{img_path}'\n")
            f.write(f"duration {time_per_image}\n")
        # Repeat last image to ensure proper ending
        f.write(f"file '{image_paths[-1]}'\n")
    
    # Build output filename
    safe_filename = data.get('filename', 'stoic_video').replace(' ', '_')[:50]
    output_path = output_dir / f"{safe_filename}.mp4"
    
    print(f"🎯 Output file: {output_path}")
    
    # FFmpeg command for high-quality video
    cmd = [
        'ffmpeg', '-y',  # Overwrite output
        '-f', 'concat',  # Use concat demuxer
        '-safe', '0',    # Allow unsafe file paths
        '-i', 'image_list.txt',  # Image slideshow input
        '-i', audio_path,        # Audio input
        '-c:v', 'libx264',       # H.264 video codec
        '-c:a', 'aac',           # AAC audio codec
        '-pix_fmt', 'yuv420p',   # Pixel format for compatibility
        '-r', '30',              # 30 FPS
        '-vf', 'scale=1024:1024:force_original_aspect_ratio=decrease,pad=1024:1024:(ow-iw)/2:(oh-ih)/2:black',  # Resize and pad
        '-shortest',             # Stop when shortest stream ends
        '-movflags', '+faststart',  # Optimize for web playback
        str(output_path)
    ]
    
    print("🎥 Running FFmpeg...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ FFmpeg completed successfully!")
        
        # Verify output file exists
        if output_path.exists():
            file_size = output_path.stat().st_size
            print(f"🎉 Video created: {output_path.name}")
            print(f"📁 File size: {file_size/1024/1024:.1f} MB")
            
            # Create metadata file
            metadata = {
                "success": True,
                "filename": output_path.name,
                "size_bytes": file_size,
                "size_mb": round(file_size/1024/1024, 2),
                "duration": duration,
                "images_count": len(image_paths),
                "title": data.get('title', 'Unknown'),
                "resolution": "1024x1024",
                "fps": 30,
                "codec": "H.264/AAC",
                "created": data.get('created', 'unknown')
            }
            
            with open(output_dir / "video_info.json", "w") as f:
                json.dump(metadata, f, indent=2)
                
            print("📊 Metadata saved")
            return True
            
        else:
            print("❌ Output file was not created")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed with return code: {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        
        # Save error log
        with open(output_dir / "error_log.txt", "w") as f:
            f.write(f"FFmpeg Error:\n")
            f.write(f"Return code: {e.returncode}\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"stdout: {e.stdout}\n")
            f.write(f"stderr: {e.stderr}\n")
        
        return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        with open(output_dir / "error_log.txt", "w") as f:
            f.write(f"Python Error: {str(e)}\n")
        return False
    
    finally:
        # Cleanup temporary files
        temp_files = [audio_path, "image_list.txt"] + image_paths
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                print(f"🧹 Cleaned up: {temp_file}")

if __name__ == "__main__":
    print("🚀 Starting Stoic Video Renderer")
    success = create_video()
    
    if success:
        print("🎉 Video rendering completed successfully!")
        exit(0)
    else:
        print("💥 Video rendering failed!")
        exit(1)
