from django import template
from ..models import Vote

register = template.Library()

@register.filter
def vote_count(message, vote_type):
    return message.votes.filter(value=1 if vote_type == 'like' else -1).count()

@register.filter
def user_voted(message, user):
    if not user.is_authenticated:
        return False
    vote = message.votes.filter(user=user).first()
    if vote:
        return 'like' if vote.value > 0 else 'dislike'
    return False