import os
import tempfile
import shutil  # <--- Added to copy the file
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import StreamingHttpResponse
from yt_dlp import YoutubeDL

def homepage(request):
    return render(request, 'master/homepage.html')

def search_results(request):
    query = request.GET.get('query')
    results = []
    if query:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            }
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                results = search_results.get('entries', [])
        except Exception as e:
            print(f"Search Error: {e}")
            
    return render(request, 'master/results.html', {'results': results, 'query': query})

def stream_and_delete(file_path, temp_cookie_path=None):
    """
    Generator to stream file and delete both the video and the temp cookie file.
    """
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        print(f"Error streaming file: {e}")
    finally:
        # 1. Delete the video file
        if os.path.exists(file_path):
            os.remove(file_path)
        # 2. Delete the temporary cookie file
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)

def download_video(request):
    video_url = request.GET.get('url')
    
    if not video_url:
        return redirect('homepage')

    # 1. SETUP PATHS
    temp_dir = tempfile.gettempdir()
    
    # Identify where the read-only source cookies are
    render_secret_path = '/etc/secrets/cookies.txt'
    local_path = os.path.join(settings.BASE_DIR, 'cookies.txt')
    
    source_cookies = None
    if os.path.exists(render_secret_path):
        source_cookies = render_secret_path
    elif os.path.exists(local_path):
        source_cookies = local_path

    # 2. COPY COOKIES TO TEMP (Crucial Fix)
    writable_cookie_path = None
    if source_cookies:
        try:
            # Create a temp file path (e.g., /tmp/cookies_12345.txt)
            writable_cookie_path = os.path.join(temp_dir, f"cookies_{os.getpid()}.txt")
            # Copy the read-only file to the writable temp location
            shutil.copyfile(source_cookies, writable_cookie_path)
        except Exception as e:
            print(f"Error copying cookies: {e}")

    # 3. CONFIGURE YT-DLP
    ydl_opts = {
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'format': 'best[ext=mp4]/best',
        
        # Point to the WRITABLE temp file, not the read-only source
        'cookiefile': writable_cookie_path,
        
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'source_address': '0.0.0.0',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['dash', 'hls'], 
            }
        },
    }

    try:
        file_path = None
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            
            # Sanity check for filename changes
            if not os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        file_path = base + ext
                        break

        # 4. STREAM
        if file_path and os.path.exists(file_path):
            filename = os.path.basename(file_path)
            # Pass both file_path AND writable_cookie_path to cleanup function
            response = StreamingHttpResponse(
                stream_and_delete(file_path, writable_cookie_path), 
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            raise Exception("File not found on server.")

    except Exception as e:
        # Cleanup cookies if download fails before streaming starts
        if writable_cookie_path and os.path.exists(writable_cookie_path):
            os.remove(writable_cookie_path)
            
        return render(request, 'master/results.html', {
            'error': f"Download Failed: {str(e)}",
            'query': request.GET.get('query', '')
        })