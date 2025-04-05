import json

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Category, Topic, Message, Vote
from .forms import TopicForm, MessageForm


def forum_home(request):
    categories = Category.objects.all()
    return render(request, 'forum/home.html', {'categories': categories})


def category_topics(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    topics = category.topics.all()
    return render(request, 'forum/category_topics.html', {
        'category': category,
        'topics': topics
    })


@login_required
def create_topic(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        form = TopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.category = category
            topic.author = request.user
            topic.save()
            return redirect('topic_messages', topic_id=topic.id)
    else:
        form = TopicForm()
    return render(request, 'forum/create_topic.html', {
        'form': form,
        'category': category
    })


def topic_messages(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    # Получаем корневые сообщения и prefetch related replies и votes
    forum_messages = Message.objects.filter(
        topic=topic,
        parent__isnull=True
    ).order_by('created_at').prefetch_related(
        'replies',
        'votes',
        'likes',
        'dislikes'
    )

    # Получаем голоса текущего пользователя
    user_votes = {}
    if request.user.is_authenticated:
        votes = Vote.objects.filter(
            user=request.user,
            message__in=forum_messages
        ).select_related('message')
        for vote in votes:
            user_votes[vote.message.id] = 'like' if vote.value > 0 else 'dislike'

    return render(request, 'forum/topic_messages.html', {
        'topic': topic,
        'forum_messages': forum_messages,
        'user_votes': user_votes,
        'request': request  # Важно передать request для проверки auth
    })

from django.http import JsonResponse
from django.template.loader import render_to_string


@login_required
def add_message(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            parent_id = request.POST.get('parent_id')
            message = Message.objects.create(
                topic=topic,
                author=request.user,
                content=content,
                parent_id=parent_id if parent_id else None
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('forum/message.html', {
                    'message': message,
                    'request': request
                })
                return JsonResponse({
                    'success': True,
                    'html': html
                })

            return redirect('topic_messages', topic_id=topic.id)

    return JsonResponse({'success': False}, status=400)


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json


@require_POST
@login_required
def vote_message(request, message_id):
    message = get_object_or_404(Message, id=message_id)

    try:
        data = json.loads(request.body)
        vote_type = data.get('vote_type')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    # Проверяем текущий голос пользователя
    current_vote = message.votes.filter(user=request.user).first()

    # Если пользователь нажимает ту же кнопку - отменяем голос
    if current_vote:
        if (current_vote.value == 1 and vote_type == 'like') or (current_vote.value == -1 and vote_type == 'dislike'):
            current_vote.delete()
        else:
            # Если нажимает другую кнопку - меняем голос
            current_vote.value = 1 if vote_type == 'like' else -1
            current_vote.save()
    else:
        # Если голоса не было - создаем новый
        if vote_type in ['like', 'dislike']:
            message.votes.create(
                user=request.user,
                value=1 if vote_type == 'like' else -1
            )

    # Получаем актуальные счетчики
    likes = message.votes.filter(value=1).count()
    dislikes = message.votes.filter(value=-1).count()

    # Проверяем текущий голос пользователя после изменений
    current_vote = message.votes.filter(user=request.user).first()
    user_vote = None
    if current_vote:
        user_vote = 'like' if current_vote.value > 0 else 'dislike'

    return JsonResponse({
        'success': True,
        'likes': likes,
        'dislikes': dislikes,
        'user_vote': user_vote
    })