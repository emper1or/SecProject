import json
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from .models import Category, Topic, Message, Vote
from .forms import TopicForm, MessageForm
from django.db import models
from django.db.models import Q
from django.core.paginator import Paginator

def forum_home(request):
    search_query = request.GET.get('q', '')

    if search_query:
        categories = Category.objects.filter(
            Q(name__icontains=search_query)
        ).order_by('order')
    else:
        categories = Category.objects.all().order_by('order')

    return render(request, 'forum/forum_home.html', {
        'categories': categories,
        'search_query': search_query
    })

@staff_member_required
def create_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        # Устанавливаем порядок как последний
        max_order = Category.objects.all().aggregate(models.Max('order'))['order__max'] or 0
        Category.objects.create(name=name, description=description, order=max_order + 1)
        return redirect('forum_home')
    return redirect('forum_home')


@staff_member_required
def update_category(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        category = Category.objects.get(id=category_id)
        category.name = name
        category.description = description
        category.save()
        return redirect('forum_home')
    return redirect('forum_home')


@staff_member_required
def delete_category(request, category_id):
    category = Category.objects.get(id=category_id)
    category.delete()
    return redirect('forum_home')


@staff_member_required
def update_categories_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            order = data.get('order', [])

            for index, category_id in enumerate(order, start=1):
                Category.objects.filter(id=category_id).update(order=index)

            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)


from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Category, Topic
from .forms import TopicForm


def category_topics(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    topics = category.topics.all()

    # Поиск по темам
    search_query = request.GET.get('q', '')
    if search_query:
        topics = topics.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))

    # Фильтр "Ваши темы"
    if request.GET.get('my_topics') and request.user.is_authenticated:
        topics = topics.filter(author=request.user)

    # Пагинация
    paginator = Paginator(topics.order_by('-created_at'), 10)  # 10 тем на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'forum/category_topics.html', {
        'category': category,
        'page_obj': page_obj,
        'search_query': search_query
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

    # Пагинация с сохранением объекта QuerySet для обработки голосов
    paginator = Paginator(forum_messages, 15)  # 15 сообщений на страницу
    page_number = request.GET.get('page')
    paginated_messages = paginator.get_page(page_number)

    # Обрабатываем голоса для сообщений на текущей странице
    messages_to_display = []
    for message in paginated_messages.object_list:
        message.likes_count = message.votes.filter(value=1).count()
        message.dislikes_count = message.votes.filter(value=-1).count()

        if request.user.is_authenticated:
            vote = message.votes.filter(user=request.user).first()
            message.user_vote = 'like' if vote and vote.value > 0 else 'dislike' if vote else None
        else:
            message.user_vote = None

        messages_to_display.append(message)

    return render(request, 'forum/topic_messages.html', {
        'topic': topic,
        'forum_messages': messages_to_display,  # Передаем обработанные сообщения
        'paginated_messages': paginated_messages,  # Передаем объект пагинации
        'request': request
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


@login_required
def delete_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.user.is_superuser or request.user == topic.author:
        topic.delete()
    return redirect('category_topics', category_id=topic.category.id)



@login_required
def add_message(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        parent_id = request.POST.get('parent_id')

        if not content:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Пустое сообщение'}, status=400)
            messages.error(request, 'Сообщение не может быть пустым')
            return redirect('topic_messages', topic_id=topic.id)

        # Для новых сообщений (не ответов)
        if not parent_id:
            message = Message.objects.create(
                topic=topic,
                author=request.user,
                content=content
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Добавляем голосовую информацию для нового сообщения
                message.likes_count = 0
                message.dislikes_count = 0
                message.user_vote = None

                html = render_to_string('forum/message.html', {
                    'message': message,
                    'request': request
                })
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'is_reply': False
                })

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
            # Добавляем голосовую информацию для нового сообщения
            message.likes_count = 0
            message.dislikes_count = 0
            message.user_vote = None

            html = render_to_string('forum/message.html', {
                'message': message,
                'request': request
            })
            return JsonResponse({
                'success': True,
                'html': html,
                'parent_id': parent_id,
                'message_id': message.id,
                'is_reply': True
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