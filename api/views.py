from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from yt_dlp import YoutubeDL
import os

# Create your views here.

def example_view(request):
    return JsonResponse({"message": "This is an example API response."})

class YouTubeSearchAPIView(APIView):
    def get(self, request):
        query = request.GET.get('query', '')
        if not query:
            return Response({"error": "Query parameter is required."}, status=400)

        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                videos = [
                    {
                        'title': entry['title'],
                        'url': entry['url'],
                        'id': entry['id']
                    }
                    for entry in search_results.get('entries', [])
                ]
                return Response({"videos": videos})
            except Exception as e:
                return Response({"error": str(e)}, status=500)

class YouTubeDownloadAPIView(APIView):
    def post(self, request):
        title = request.data.get('title', '')
        if not title:
            return Response({"error": "Title parameter is required."}, status=400)

        ydl_opts = {
            'quiet': True,
            'format': 'best',
            'outtmpl': os.path.join('downloads', '%(title)s.%(ext)s')
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                search_results = ydl.extract_info(f"ytsearch:{title}", download=True)
                video_info = search_results['entries'][0] if 'entries' in search_results else search_results
                file_path = os.path.join('downloads', f"{video_info['title']}.{video_info['ext']}")

                # Return the file as a response for direct download
                response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"{video_info['title']}.{video_info['ext']}")
                return response
            except Exception as e:
                return Response({"error": str(e)}, status=500)
