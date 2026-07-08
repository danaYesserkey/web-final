from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated

from .serializers import QuizSerializer, QuizAttemptSerializer, UserResponseSerializer
from .models import Quiz, Question, MultipleChoiceQuestion, EnterValueQuestion, AnswerOption, QuizAttempt, QuizResults, BirnesheJauaptyqSuraq
from apps.courses.models import Lesson
from apps.users.models import CustomUser
from apps.stats.models import CourseStatistics

from drf_spectacular.utils import extend_schema
from .docs_example import (
    FIRST_ATTEMPT_EXAMPLE,
    LAST_ATTEMPT_EXAMPLE,
    QUIZ_SUBMIT_REQUEST_SCHEMA,
    QUIZ_SUBMIT_RESPONSE_SCHEMA,
    LESSON_RESPONSE_SCHEMA,
    QUIZ_SUBMIT_EXAMPLE,
    QUIZ_RESULT_EXAMPLE,
)


@extend_schema(
    responses={200: LESSON_RESPONSE_SCHEMA},
    examples=[FIRST_ATTEMPT_EXAMPLE, LAST_ATTEMPT_EXAMPLE],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lesson_quiz(request, id):
    lesson = get_object_or_404(Lesson, id=id)

    quiz = get_object_or_404(Quiz, lesson_id=lesson.id)
    questions_count = quiz.questions.count()
    quiz_serializer = QuizSerializer(quiz, context={'questions': questions_count})

    try:
        user = CustomUser.objects.get(id=request.user.id)
        last_attempt = QuizAttempt.objects.filter(user=user, quiz=quiz).order_by("-completed_at").first()
        result_serializer = UserResponseSerializer(last_attempt)
    finally:
        if last_attempt:
            quiz_serializer = QuizSerializer(quiz, context={
                'status': last_attempt.passed,
                'questions': questions_count,
                'score': last_attempt.score,
                'score_percentage': (last_attempt.score * 100) / questions_count
            })

            for i in range(len(quiz_serializer.data["blocks"])):
                for j in range(len(quiz_serializer.data["blocks"][i]["questions"])):
                    question_id = quiz_serializer.data["blocks"][i]["questions"][j]["id"]
                    choice = next((value for value in result_serializer.data["quizresults_set"] if value["question"] == question_id), None)

                    if choice:
                        quiz_serializer.data["blocks"][i]["questions"][j]["user_answer"] = choice["answer"]
                        quiz_serializer.data["blocks"][i]["questions"][j]["is_correct"] = choice["is_correct"]
                        quiz_serializer.data["blocks"][i]["questions"][j]["correct_answer"] = choice["correct_answer"]
            
    return Response(quiz_serializer.data)


class QuizSubmitCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request={'application/json': QUIZ_SUBMIT_REQUEST_SCHEMA},
        responses={200: QUIZ_SUBMIT_RESPONSE_SCHEMA},
        examples=[QUIZ_SUBMIT_EXAMPLE, QUIZ_RESULT_EXAMPLE],
    )
    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)

        serializer = QuizAttemptSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)
        
        user = get_object_or_404(CustomUser, id=request.user.id)

        try:
            completed_quiz = QuizAttempt.objects.filter(quiz=quiz, user=user, passed=True)
        finally:
            if completed_quiz:
                return Response({"message": "Successfully passed quiz before"})

        answers = serializer.validated_data['answers']
        question_ids = [ans['question_id'] for ans in answers]
        valid_questions = Question.objects.filter(
            quiz_id=quiz_id
        ).values_list('id', flat=True)

        if len(valid_questions) != len(set(question_ids)):
            return Response({"error": "One or more questions don't belong to this quiz!"}, status=status.HTTP_400_BAD_REQUEST)
        
        results, score, user_answers = self._calculate_score(quiz_id, answers)
        passed = False
        score_percentage = (score * 100) / len(valid_questions)
        if score_percentage >= 90:
            passed = True
            course = quiz.lesson.module.course
            module = quiz.lesson.module
            try:
                CourseStatistics.objects.create(lesson=quiz.lesson, course=course, module=module, user=user, completed=True)
            except Exception as e:
                print(e)

        with transaction.atomic():
            attempt = QuizAttempt.objects.create(
                user=user,
                quiz=quiz,
                score=score,
                passed=passed,
                completed_at=timezone.now()
            )
        
        user_results = []
        for u in user_answers:
            user_results.append(QuizResults(
                attempt=attempt,
                question=u["q"],
                answer=u["a"],
                correct_answer=u["correct_answer"],
                is_correct=u["is_correct"])
            )
            
            print(u["a"])
        
        QuizResults.objects.bulk_create(user_results)

        return Response({
            "quiz": attempt.quiz_id,
            "total_questions": len(valid_questions),
            "score": score,
            "score_percentage": score_percentage,
            "completed_at": attempt.completed_at,
            "passed": attempt.passed,
            "results": results,
        })
    
    def _calculate_score(self, quiz_id, answers):
        total_score = 0
        results = []
        user_answers = []

        for answer in answers:
            question_id = answer['question_id']
            question_type = answer['question_type']

            question = get_object_or_404(Question, id=question_id, quiz_id=quiz_id)

            if question_type == 'mcq':
                is_correct, points, correct_answer = self._score_mcq(question, answer['user_answer'])
                user_response = answer['user_answer']
            elif question_type == 'birneshe':
                is_correct, points, correct_answer = self._score_birneshe_jauaptyq(question, answer['user_answer'])
                user_response = answer['user_answer']
            elif question_type == 'text':
                is_correct, points, correct_answer = self._score_text(question, answer['user_answer'])
                user_response = answer['user_answer']
            else:
                is_correct, points, correct_answer = False, 0, None
                user_response = None
            
            total_score += points

            result = {
                "question_id": question_id,
                "question_type": question_type,
                "text": question.text,
                "is_correct": is_correct,
                "user_answer": user_response,
                "correct_answer": correct_answer,
            }
            results.append(result)

            user_answer = {"q": question, "a": user_response, "is_correct": is_correct, "correct_answer": correct_answer}
            user_answers.append(user_answer)
        
        return results, total_score, user_answers
    
    def _score_mcq(self, question, selected_choice):
        if not isinstance(question, MultipleChoiceQuestion):
            return False, 0, None
        
        correct_option = AnswerOption.objects.get(question_id=question.id, is_correct=True)

        is_correct = selected_choice == correct_option.id
        points = 1 if is_correct else 0
        
        return is_correct, points, correct_option.id
    
    def _score_birneshe_jauaptyq(self, question, selected_choices):
        if not isinstance(question, BirnesheJauaptyqSuraq):
            return False, 0, None
        
        correct_options = set(
            AnswerOption.objects.filter(
                question_id=question.id,
                is_correct=True
            ).values_list('id', flat=True)
        )

        selected_set = set(selected_choices)
        is_correct = selected_set == correct_options
        if is_correct:
            points = 1
        else:
            points = 0
        
        return is_correct, points, list(correct_options)

    def _score_text(self, question, text_response):
        if not isinstance(question, EnterValueQuestion):
            return False, 0, None
        
        is_correct = text_response.strip().lower() == question.correct_value.lower()
        points = 1 if is_correct else 0
        
        return is_correct, points, question.correct_value


@api_view(['POST'])
def reset_quiz(request, id):
    quiz = get_object_or_404(Quiz, id=id)
    user = get_object_or_404(CustomUser, id=request.user.id)

    try:
        QuizAttempt.objects.filter(user=user, quiz=quiz).delete()
        return Response({"message": "quiz reseted!"})
    except Exception as e:
        return Response({"error": e})