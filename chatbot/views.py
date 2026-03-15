import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from .services import get_agent_response, HAS_LLAMA
from .models import ChatMessage

@csrf_exempt
def health_check(request):
    """Simple health check endpoint for AWS deployment."""
    return JsonResponse({'status': 'healthy'}, status=200)

@csrf_exempt
def debug_db(request):
    """Debug endpoint to check database connectivity."""
    from django.db import connection
    import os
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"
    
    return JsonResponse({
        'db_host': os.environ.get('DB_HOST', 'Not set'),
        'db_status': db_status,
        'has_llama': str(HAS_LLAMA),
        'kb_id_exists': bool(os.getenv("BEDROCK_KNOWLEDGE_BASE_ID")),
        'github_token_exists': bool(os.getenv("GITHUB_TOKEN")),
        'aws_region': os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    })

@login_required
def index(request):
    """Renders the main chat interface. History resets on refresh."""
    return render(request, 'chatbot/index.html')

def register_user(request):
    """Handles new user registration."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@csrf_exempt
def chat_api(request):
    """Handles chat requests. Uses history from request body, saves to DB but won't load it on refresh."""
    from asgiref.sync import async_to_sync
    import traceback
    
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Unauthorized. Please log in again.'}, status=401)
            
        if request.method == 'POST':
            data = json.loads(request.body)
            query = data.get('query')
            chat_history = data.get('chat_history', []) # Getting history from frontend
            
            # Limit history to last 3 exchanges (6 messages total: user + bot)
            # Keeping only last 3 pairs for context as requested
            context_history = chat_history[-6:] if len(chat_history) > 6 else chat_history

            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)
            
            # Call AI
            try:
                answer = async_to_sync(get_agent_response)(query, context_history)
                
                # Save to DB for permanent logs (but we won't load it back in index view)
                ChatMessage.objects.create(
                    user=request.user,
                    query=query,
                    response=answer
                )
                
                return JsonResponse({'answer': answer})
            except Exception as e:
                print(f"Chat API AI Error: {e}")
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
