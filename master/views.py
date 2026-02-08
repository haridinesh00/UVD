import os
import tempfile
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import FileResponse, StreamingHttpResponse
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
            # Use Android client for search to avoid blocking
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

def stream_and_delete(file_path):
    """
    Generator function to read a file chunk by chunk and delete it 
    from the server once the download is complete or connection closes.
    """
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)  # Read 8KB chunks
                if not chunk:
                    break
                yield chunk
    except Exception as e:
        print(f"Error streaming file: {e}")
    finally:
        # This block runs whether the download succeeds or fails
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Cleaned up temp file: {file_path}")

def download_video(request):
    video_url = request.GET.get('url')
    
    if not video_url:
        return redirect('homepage')

    # 1. SETUP PATHS
    # Use system temp directory to ensure write permissions on Render
    temp_dir = tempfile.gettempdir()
    
    # Check for cookies in Render secrets (prod) or local project folder (dev)
    render_secret_path = '/etc/secrets/cookies.txt'
    local_path = os.path.join(settings.BASE_DIR, 'cookies.txt')

    cookies_path = None
    if os.path.exists(render_secret_path):
        cookies_path = render_secret_path
    elif os.path.exists(local_path):
        cookies_path = local_path

    # 2. CONFIGURE YT-DLP
    ydl_opts = {
        # OUTPUT: Save to temp folder with a safe filename
        'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,  # ASCII-only filenames
        
        # FORMAT: Force single file (best video+audio combo)
        # This avoids using FFmpeg to merge streams, which often fails on servers
        'format': 'best[ext=mp4]/best', 
        
        # AUTHENTICATION
        'cookiefile': cookies_path,

        # ANTI-BLOCKING & NETWORK
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True, # Ignore SSL errors
        'source_address': '0.0.0.0', # Force IPv4
        
        # CRITICAL FIX: Pretend to be an Android app
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
                'skip': ['dash', 'hls'], 
            }
        },
    }

    try:
        # 3. EXECUTE DOWNLOAD TO SERVER
        file_path = None
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            
            # Sanity check: verify file exists (sometimes extension changes)
            if not os.path.exists(file_path):
                # Try to find the file with common extensions if prepare_filename was wrong
                base, _ = os.path.splitext(file_path)
                for ext in ['.mp4', '.mkv', '.webm']:
                    if os.path.exists(base + ext):
                        file_path = base + ext
                        break

        # 4. STREAM TO USER AND DELETE
        if file_path and os.path.exists(file_path):
            filename = os.path.basename(file_path)
            response = StreamingHttpResponse(
                stream_and_delete(file_path), 
                content_type='application/octet-stream'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        else:
            raise Exception("File not found on server after download.")

    except Exception as e:
        print(f"Download Error: {e}")
        return render(request, 'master/results.html', {
            'error': f"Download Failed: {str(e)}",
            'query': request.GET.get('query', '')
        })