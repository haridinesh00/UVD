from django.views.generic import FormView, TemplateView, View
from django.shortcuts import redirect
from django.urls import reverse_lazy

from rebux.tasks import generate_new_levels
from .models import PuzzleLevel
from .forms import GuessForm

class PlayGameView(FormView):
    template_name = 'rebux/play.html'
    form_class = GuessForm
    success_url = reverse_lazy('play_game')

    def dispatch(self, request, *args, **kwargs):
        # 1. THE FIX: Use Django Sessions instead of a hardcoded User profile
        if 'current_level' not in request.session:
            request.session['current_level'] = 1
            request.session['score'] = 0
            request.session['failed_attempts'] = 0 # Track failures

        self.current_level = request.session['current_level']
        self.score = request.session['score']
        self.failed_attempts = request.session.get('failed_attempts', 0)
        
        # 2. Check if a puzzle exists for their personal level
        try:
            self.current_puzzle = PuzzleLevel.objects.get(level_number=self.current_level)
        except PuzzleLevel.DoesNotExist:
            return redirect('win_game')
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        # 3. Pass their specific session data into the HTML template
        context = super().get_context_data(**kwargs)
        context['puzzle'] = self.current_puzzle
        context['level'] = self.current_level
        context['score'] = self.score
        
        # If they failed 3 or more times, pass the hint flag to the frontend
        if self.failed_attempts >= 3:
            context['show_hint'] = True
            
        return context

    def form_valid(self, form):
        guess = form.cleaned_data['guess']
        
        if self.current_puzzle.check_answer(guess):
            # 4. Correct! Update their private browser session
            self.request.session['current_level'] += 1
            self.request.session['score'] += 100
            self.request.session['failed_attempts'] = 0 # Reset failures for the next level!
            self.request.session.modified = True 
            
            total_levels = PuzzleLevel.objects.count()
            levels_remaining = total_levels - self.request.session['current_level']
            
            if levels_remaining < 3:
                # from .tasks import generate_new_levels
                generate_new_levels.delay(2)
                # generate_new_levels(3)
                
            return super().form_valid(form)
        else:
            # They guessed wrong. Increase the failure counter!
            self.request.session['failed_attempts'] = self.request.session.get('failed_attempts', 0) + 1
            self.request.session.modified = True
            
            context = self.get_context_data(form=form, message="Incorrect! Try again.")
            return self.render_to_response(context)

class WinGameView(TemplateView):
    template_name = 'rebux/win.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['message'] = "Congratulations! You have beaten all available levels of Rebux!"
        return context
    
class GenerateLevelsView(View):
    def get(self, request, *args, **kwargs):
        # This view can be triggered manually to generate new levels without Celery
        generate_new_levels.delay(2)
        return redirect('play_game')