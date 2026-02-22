from django import forms

class GuessForm(forms.Form):
    guess = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'placeholder': 'What is the answer?',
        'class': 'guess-input',
        'autocomplete': 'off',
        'autofocus': 'autofocus'
    }))