from django.urls import path

from .views import QuizSubmitCreateView, reset_quiz


urlpatterns = [
    path('<int:quiz_id>/submit/', QuizSubmitCreateView.as_view()),
    path('<int:id>/reset/', reset_quiz),
]