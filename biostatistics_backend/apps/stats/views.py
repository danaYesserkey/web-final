from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets
from django.db.models import Avg, Count, Case, When, FloatField, Value, F

from .models import CourseStatistics
from apps.courses.models import Lesson, Course, Module
from apps.users.models import CustomUser
from apps.quizzes.models import Quiz, QuizAttempt

from .serializers import CourseStatsSerializer


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lesson_score(request, id):
    lesson = get_object_or_404(Lesson, id=id)
    user = get_object_or_404(CustomUser, id=request.user.id)

    try:
        quiz = Quiz.objects.filter(lesson=lesson)
        if quiz:
            print(quiz)
            return Response({"message": "Сабақты аяқтау үшін тест тапсыруыңыз керек"})

        previous_lesson = Lesson.objects.filter(id__lt=lesson.id).order_by('-id').first()
        previous_stats = CourseStatistics.objects.get(lesson=previous_lesson, user=user, course=previous_lesson.module.course)

        if previous_lesson:
            if previous_stats.completed:                
                CourseStatistics.objects.create(course=lesson.module.course, module=lesson.module, lesson=lesson, user=user, completed=True)
                return Response({"message": "Сабақ сәтті аяқталды"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        print(e)
        if not previous_lesson:
            CourseStatistics.objects.create(course=lesson.module.course, module=lesson.module, lesson=lesson, user=user, completed=True)
            return Response({"message": "Сабақ сәтті аяқталды"}, status=status.HTTP_201_CREATED)

    return Response({"message": "Алдыңғы сабақты аяқтаңыз"})


class CourseStatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user

        courses = Course.objects.filter(
            modules__lessons__coursestatistics__user=user
        ).prefetch_related(
            'modules__lessons__quiz'
        ).distinct()

        stats_list = []

        for course in courses:
            modules = Module.objects.filter(course=course)
            total_modules = modules.count()

            lessons = Lesson.objects.filter(module__course=course)
            total_lessons = lessons.count()

            completed_lessons = CourseStatistics.objects.filter(
                user=user,
                course=course,
                completed=True
            ).count()

            total_quizzes = Quiz.objects.filter(
                lesson__module__course=course
            ).count()

            completed_quizzes = QuizAttempt.objects.filter(
                user=user,
                quiz__lesson__module__course=course,
                passed=True,
            ).count()

            quiz_attempts = QuizAttempt.objects.filter(
                user=user,
                quiz__lesson__module__course=course
            ).annotate(
                question_count=Count('quiz__questions', distinct=True)
            ).annotate(
                score_percentage=Case(
                    When(question_count=0, then=Value(0.0)),
                    default=F('score') * 100.0 / F('question_count'),
                    output_field=FloatField()
                )
            )

            average_quiz_score = (
                quiz_attempts.aggregate(avg_score=Avg('score_percentage'))['avg_score'] or 0
            )

            total_items = total_lessons + total_quizzes
            completed_items = completed_lessons + completed_quizzes
            overall_progress = (
                round((completed_items / total_items * 100), 2)
                if total_items > 0
                else 0
            )

            completed_modules = 0
            modules_stats = []

            for module in modules:
                module_lessons = Lesson.objects.filter(module=module).count()
                completed_module_lessons = CourseStatistics.objects.filter(
                    user=user,
                    module=module,
                    completed=True
                ).count()

                module_progress = (
                    round((completed_module_lessons / module_lessons * 100), 2)
                    if module_lessons > 0
                    else 0
                )

                if module_lessons > 0 and module_lessons == completed_module_lessons:
                    completed_modules += 1

                modules_stats.append({
                    'module_id': module.id,
                    'module_name': module.module_name,
                    'module_progress': module_progress,
                    'total_module_lessons': module_lessons,
                    'completed_module_lessons': completed_module_lessons,
                })

            stats_list.append({
                'course_id': course.id,
                'course_name': course.course_name,
                'overall_progress': overall_progress,
                'total_modules': total_modules,
                'completed_modules': completed_modules,
                'total_lessons': total_lessons,
                'completed_lessons': completed_lessons,
                'total_quizzes': total_quizzes,
                'total_quizz_attempts': quiz_attempts.count(),
                'completed_quizzes': completed_quizzes,
                'average_quiz_score': round(average_quiz_score, 2),
                'modules': modules_stats,
            })

        serializer = CourseStatsSerializer(stats_list, many=True)
        return Response(serializer.data)