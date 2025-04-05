import json
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
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
    forum_messages = Message.objects.filter(
        topic=topic,
        parent__isnull=True
    ).order_by('created_at').select_related('author').prefetch_related(
        'replies',
        'votes',
        'replies__author',
        'replies__votes'
    )

    # Add vote counts and user vote status to each message
    for message in forum_messages:
        message.likes_count = message.votes.filter(value=1).count()
        message.dislikes_count = message.votes.filter(value=-1).count()

        if request.user.is_authenticated:
            vote = message.votes.filter(user=request.user).first()
            message.user_vote = 'like' if vote and vote.value > 0 else 'dislike' if vote else None
        else:
            message.user_vote = None

    return render(request, 'forum/topic_messages.html', {
        'topic': topic,
        'forum_messages': forum_messages,
        'request': request
    })


@login_required
def add_message(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        parent_id = request.POST.get('parent_id')

        if not content:
            return JsonResponse({'success': False, 'error': 'Пустое сообщение'}, status=400)

        # Для новых сообщений (не ответов)
        if not parent_id:
            Message.objects.create(
                topic=topic,
                author=request.user,
                content=content
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'reload': True})

            return redirect('topic_messages', topic_id=topic.id)

        # Для ответов на сообщения
        parent_message = get_object_or_404(Message, id=parent_id)
        message = Message.objects.create(
            topic=topic,
            author=request.user,
            content=content,
            parent=parent_message
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('forum/message.html', {
                'message': message,
                'request': request
            })
            return JsonResponse({
                'success': True,
                'html': html,
                'parent_id': parent_id,
                'message_id': message.id
            })

        return redirect('topic_messages', topic_id=topic.id)

    return JsonResponse({'success': False}, status=400)

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
            message_was_updated = True
        else:
            # Если нажимает другую кнопку - меняем голос
            current_vote.value = 1 if vote_type == 'like' else -1
            current_vote.save()
            message_was_updated = True
    else:
        # Если голоса не было - создаем новый
        if vote_type in ['like', 'dislike']:
            Vote.objects.create(
                user=request.user,
                message=message,
                value=1 if vote_type == 'like' else -1
            )
            message_was_updated = True

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
        'user_vote': user_vote,
        'message_id': message.id
    })