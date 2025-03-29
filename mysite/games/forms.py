from django import forms
from .models import Developer, Game, GameCover


class DeveloperForm(forms.ModelForm):
    class Meta:
        model = Developer
        fields = ['name', 'bio']


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['title', 'description', 'developer', 'rating']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['developer'].required = False
        self.fields['rating'].widget = forms.Select(choices=[(i, f"{i}/10") for i in range(1, 11)])
        self.fields['rating'].label = "Рейтинг игры"


class GameCoverForm(forms.ModelForm):
    class Meta:
        model = GameCover
        fields = ['cover']