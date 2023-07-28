import os
import asyncio
import ffmpeg
import pickle
from urllib.parse import quote_plus, unquote_plus
import time
import subprocess
import re
from fastapi import FastAPI, HTTPException, Body, BackgroundTasks
from fastapi.responses import FileResponse

app = FastAPI()

# Set custom paths for ffmpeg and yt-dlp using environment variables
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
YT_DLP_PATH = os.getenv("YT_DLP_PATH", "yt-dlp")

DOWNLOAD_FOLDER = "./download"

# File to store the downloaded_files dictionary
DOWNLOADED_FILES_FILE = "downloaded_files.pkl"

APP_URL = os.environ.get('APP_URL', '127.0.0.1:8000')

# Dictionary to store downloaded URLs, file paths, and timestamps
downloaded_files = {}

def is_file_downloaded(url: str) -> bool:
    return url in downloaded_files

def get_downloaded_file(url: str) -> str:
    return downloaded_files.get(url, {}).get("file_path")

def mark_file_downloaded(url: str, file_path: str):
    downloaded_files[url] = {"file_path": file_path, "timestamp": time.time()}
    save_downloaded_files()

def remove_file_info(url: str):
    if url in downloaded_files:
        downloaded_files.pop(url)
        save_downloaded_files()

def save_downloaded_files():
    with open(DOWNLOADED_FILES_FILE, "wb") as file:
        pickle.dump(downloaded_files, file)

def load_downloaded_files():
    if os.path.exists(DOWNLOADED_FILES_FILE):
        with open(DOWNLOADED_FILES_FILE, "rb") as file:
            return pickle.load(file)
    return {}

# Load the downloaded_files dictionary from the file (if it exists) when the application starts
downloaded_files = load_downloaded_files()

async def remove_old_files(delay_seconds: int):
    while True:
        for url, info in list(downloaded_files.items()):
            elapsed_time = time.time() - info["timestamp"]
            if elapsed_time > delay_seconds:
                remove_file_info(url)
                file_path = info["file_path"]
                if os.path.exists(file_path):
                    os.remove(file_path)
        await asyncio.sleep(delay_seconds)

def download_audio(url: str) -> str:
    cmd = f"{YT_DLP_PATH} -f 'bestaudio' -o '{DOWNLOAD_FOLDER}/%(title)s.%(ext)s' -- {url}"
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to download audio.")
    
    # Get the downloaded file name
    title = subprocess.check_output([YT_DLP_PATH, "--get-filename", "-o", f"{DOWNLOAD_FOLDER}/%(title)s", url], text=True)
    return title.strip() + ".webm"

def convert_to_mp3(input_file: str, bitrate: int) -> str:
    output_file = f"{os.path.splitext(input_file)[0]}_{bitrate}kbps.mp3"
    try:
        ffmpeg.input(input_file).output(output_file, audio_bitrate=f"{bitrate}k", loglevel="error").run(cmd=FFMPEG_PATH)
    except ffmpeg.Error as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert to MP3: {str(e)}")
    return output_file

def get_download_link(file_path: str) -> str:
    file_name = os.path.basename(file_path)
    encoded_file_name = quote_plus(file_name)
    return f"{APP_URL}/download/{encoded_file_name}"

async def delete_file_after_delay(file_path: str, delay_seconds: int):
    await asyncio.sleep(delay_seconds)
    if os.path.exists(file_path):
        os.remove(file_path)

# Function to create safe filenames by removing or replacing invalid characters
def make_safe_filename(file_name: str) -> str:
    # Remove any characters that are not alphanumeric, space, hyphen, or underscore
    cleaned_name = re.sub(r'[^\w\s-]', '', file_name)
    # Replace spaces with underscores
    cleaned_name = cleaned_name.replace(' ', '_')
    return cleaned_name

@app.post("/convert/")
async def convert_to_mp3_endpoint(youtube_url: str = Body(...), bitrate: int = Body(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    if bitrate not in [128, 192, 256, 320]:
        raise HTTPException(status_code=400, detail="Invalid bitrate. Available options: 128, 192, 256, 320")

    # Check if the file has already been downloaded
    if is_file_downloaded(youtube_url):
        audio_file = get_downloaded_file(youtube_url)
    else:
        # Download the audio from YouTube
        audio_file = download_audio(youtube_url)
        mark_file_downloaded(youtube_url, audio_file)

    # Convert the audio to MP3 at the specified bitrate if not already converted
    mp3_file = f"{os.path.splitext(audio_file)[0]}_{bitrate}kbps.mp3"
    if not os.path.exists(mp3_file):
        mp3_file = convert_to_mp3(audio_file, bitrate)

    # Get the title of the video
    title = os.path.splitext(os.path.basename(audio_file))[0]

    # Create the download link for the converted MP3 file
    safe_file_name = make_safe_filename(title) + f"_{bitrate}kbps.mp3"
    download_link = get_download_link(os.path.join(DOWNLOAD_FOLDER, safe_file_name))

    # Schedule a background task to delete the .webm file after conversion
    background_tasks.add_task(delete_file_after_delay, audio_file, 0)

    return {"title": title, "download_link": download_link}

@app.get("/download/{file_name}")
async def download_mp3(file_name: str):
    decoded_file_name = unquote_plus(file_name)
    safe_file_name = make_safe_filename(decoded_file_name)
    file_path = os.path.join(DOWNLOAD_FOLDER, safe_file_name)

    print("Requested File Name:", decoded_file_name)
    print("Generated Safe File Name:", safe_file_name)
    print("Files in DOWNLOAD_FOLDER:", os.listdir(DOWNLOAD_FOLDER))

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg", headers={"Content-Disposition": f"attachment; filename={safe_file_name}"})
    else:
        raise HTTPException(status_code=404, detail="File not found.")


if __name__ == "__main__":
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # Create the event loop explicitly
    loop = asyncio.get_event_loop()

    # Schedule a background task to remove old files from the dictionary every 15 minutes (900 seconds)
    loop.create_task(remove_old_files(900))

    # Start the FastAPI application using uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
