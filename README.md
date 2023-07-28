<h1>YouTube to MP3 Converter</h1>
This is a FastAPI application that allows you to convert YouTube videos to MP3 files with custom bitrate options. The application uses yt-dlp to download the audio from YouTube and ffmpeg to convert it to MP3 format. It also includes background tasks to automatically clean up old downloaded files and stores the download history in a local file for persistence across server restarts.

<h3>Features</h3>
Download and convert YouTube videos to MP3 with custom bitrate options (128, 192, 256, 320 kbps).
Background tasks to remove old downloaded files and manage download history.
Easy-to-use API with FastAPI framework.
Customizable paths for ffmpeg and yt-dlp using environment variables.

<h3>Requirements</h3>
Python 3.6 or higher<br>
<a href="https://github.com/FFmpeg/FFmpeg">ffmpeg</a> and <a href="https://github.com/yt-dlp/yt-dlp">yt-dlp</a>

<h3>Deploy</h3>
<a target="_blank" href="https://heroku.com/deploy?template=https://github.com/aatishdumps/yt-to-mp3-fastapi">
  <img src="https://www.herokucdn.com/deploy/button.svg" alt="Deploy">
</a>
