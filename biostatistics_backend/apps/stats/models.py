from django.db import models


class CourseStatistics(models.Model):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    module = models.ForeignKey('courses.Module', on_delete=models.CASCADE)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE)
    user = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE)
    completed = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'lesson'],
                name='unique_student_statistics'
            )
        ]