from rest_framework import serializers
from polymorphic.contrib.drf.serializers import PolymorphicSerializer

from .models import (
    Quiz,
    Question,
    MultipleChoiceQuestion,
    EnterValueQuestion,
    AnswerOption,
    QuizContext,
    WithQuizContext,
    WithoutQuizContext,
    QuizResults,
    QuizAttempt,
    BirnesheJauaptyqSuraq,
)


class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ('id', 'text',)

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'text',)

class MultipChoiceSerializer(serializers.ModelSerializer):
    answer_options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = MultipleChoiceQuestion
        fields = ('id', 'text', 'answer_options',)

class BirnesheJauaptyqSerializer(serializers.ModelSerializer):
    answer_options = AnswerOptionSerializer(many=True, read_only=True)

    class Meta:
        model = BirnesheJauaptyqSuraq
        fields = ('id', 'text', 'answer_options')

class EnterValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnterValueQuestion
        fields = ('id', 'text',)

class QuestionPolymorphicSerializer(PolymorphicSerializer):
    resource_type_field_name = 'question_type'
    model_serializer_mapping = {
        Question: QuestionSerializer,
        MultipleChoiceQuestion: MultipChoiceSerializer,
        BirnesheJauaptyqSuraq: BirnesheJauaptyqSerializer,
        EnterValueQuestion: EnterValueSerializer,
    }

    def to_resource_type(self, model_or_instance):
        name = model_or_instance._meta.object_name.lower()

        if name == "multiplechoicequestion":
            return "mcq"
        elif name == "entervaluequestion":
            return "text"
        elif name == "birneshejauaptyqsuraq":
            return "birneshe"

        return name

class ContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizContext
        fields = '__all__'

class WithContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithQuizContext
        fields = ('title', 'text', 'dataset_file',)

class WithoutContextSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithoutQuizContext
        fields = '__all__'

class QuizContextSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
        QuizContext: ContextSerializer,
        WithQuizContext: WithContextSerializer,
        WithoutQuizContext: WithoutContextSerializer,
    }

class QuizSerializer(serializers.ModelSerializer):
    blocks = serializers.SerializerMethodField()
    passed = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()
    score_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = '__all__'
    
    def get_passed(self, obj):
        status = self.context.get('status')
        if status == True:
            return True
        return False
    
    def get_total_questions(self, obj):
        questions = self.context.get('questions')
        return questions
    
    def get_score(self, obj):
        score = self.context.get('score')
        return score
    
    def get_score_percentage(self, obj):
        score_percentage = self.context.get('score_percentage')
        return score_percentage

    def get_blocks(self, obj):
        blocks = []

        for context in obj.contexts.all():
            context_data = QuizContextSerializer(context).data
            questions = QuestionPolymorphicSerializer(context.questions.all(), many=True).data

            if context_data['resourcetype'] == 'WithoutQuizContext':
                blocks.append({'context': None, 'questions': questions})
            else:
                del context_data['resourcetype']
                blocks.append({'context': context_data, 'questions': questions})

        return blocks

class MCQAnswerSerializer(serializers.Serializer):
    question_type = serializers.CharField(default='mcq')
    question_id = serializers.IntegerField()
    user_answer = serializers.IntegerField()

class BirnesheJauaptyqAnswerSerializer(serializers.Serializer):
    question_type = serializers.CharField(default="birneshe")
    question_id = serializers.IntegerField()
    user_answer = serializers.ListField(child=serializers.IntegerField())

class EnterValueAnswerSerializer(serializers.Serializer):
    question_type = serializers.CharField(default='text')
    question_id = serializers.IntegerField()
    user_answer = serializers.CharField()

class AnswerSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        answer_type = data.get('question_type')

        if answer_type == 'mcq':
            serializer = MCQAnswerSerializer(data=data)
        elif answer_type == 'text':
            serializer = EnterValueAnswerSerializer(data=data)
        elif answer_type == 'birneshe':
            serializer = BirnesheJauaptyqAnswerSerializer(data=data)
        else:
            raise serializers.ValidationError(f"Invalid type: {answer_type}")
        
        if not serializer.is_valid():
            raise serializers.ValidationError(serializer.errors)
        
        return serializer.validated_data

class QuizAttemptSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)

class QuizResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizResults
        fields= ("question", "answer", "correct_answer", "is_correct",)

class UserResponseSerializer(serializers.ModelSerializer):
    quizresults_set = QuizResultSerializer(many=True, read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ("quizresults_set",)