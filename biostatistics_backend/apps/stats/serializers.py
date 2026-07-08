from rest_framework import serializers


class ModuleStatsSerializer(serializers.Serializer):
    module_id = serializers.IntegerField()
    module_name = serializers.CharField()
    module_progress = serializers.FloatField()
    total_module_lessons = serializers.IntegerField()
    completed_module_lessons = serializers.IntegerField()


class CourseStatsSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    course_name = serializers.CharField()
    overall_progress = serializers.FloatField()
    total_modules = serializers.IntegerField()
    completed_modules = serializers.IntegerField()
    total_lessons = serializers.IntegerField()
    completed_lessons = serializers.IntegerField()
    total_quizzes = serializers.IntegerField()
    total_quizz_attempts = serializers.IntegerField()
    completed_quizzes = serializers.IntegerField()
    average_quiz_score = serializers.FloatField()
    modules = ModuleStatsSerializer(many=True)