from django.shortcuts import render
from yt_dlp import YoutubeDL
from django.http import FileResponse
import os

def homepage(request):
    query = request.GET.get('query')
    results = []
    if query:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
            results = search_results.get('entries', [])
    return render(request, 'master/homepage.html', {'results': results})

def download_video(request):
    video_url = request.GET.get('url')
    if video_url:
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info_dict)
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
