from django.views.generic import FormView, TemplateView, View
from django.shortcuts import redirect
from django.urls import reverse_lazy
from .models import PuzzleLevel
from .forms import GuessForm
from .tasks import generate_new_levels # Import your Celery task!

class PlayGameView(FormView):
    template_name = 'rebux/play.html'
    form_class = GuessForm
    success_url = reverse_lazy('play_game')

    def dispatch(self, request, *args, **kwargs):
        # 1. THE FIX: Use Django Sessions instead of a hardcoded User profile
        if 'current_level' not in request.session:
            request.session['current_level'] = 1
            request.session['score'] = 0

        self.current_level = request.session['current_level']
        self.score = request.session['score']
        
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
        return context

    def form_valid(self, form):
        guess = form.cleaned_data['guess']
        
        if self.current_puzzle.check_answer(guess):
            # 4. Correct! Update their private browser session
            self.request.session['current_level'] += 1
            self.request.session['score'] += 100
            
            # 5. Check the global database to see if we need Celery to make more levels
            total_levels = PuzzleLevel.objects.count()
            levels_remaining = total_levels - self.request.session['current_level']
            
            # if levels_remaining < 3:
                # generate_new_levels.delay(5) # Triggers your background worker
                # generate_new_levels(5) # For testing without Celery, call the function directly
                
            return super().form_valid(form)
        else:
            # They got it wrong. Re-render the same page with an error message.
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
        generate_new_levels(3)  # Generate 5 new levels
        return redirect('play_game')