import os
import uuid
import mimetypes

from django.utils.text import slugify
from django.db import models
from polymorphic.models import PolymorphicModel

def get_course_file_upload_path(instance, filename):
    """Генерирует уникальный путь для загрузки файлов"""
    name, ext = os.path.splitext(filename)
    safe_name = slugify(name) or "material"
    unique_filename = f"{uuid.uuid4().hex[:10]}_{safe_name}{ext}"
    
    # Безопасно поднимаемся по связям: Урок -> Модуль -> Курс
    lesson = instance.lesson
    module = lesson.module if hasattr(lesson, 'module') else None
    module_id = module.id if module else 'unknown'
    course_id = module.course_id if (module and hasattr(module, 'course_id')) else 'unknown'
    
    return f"courses/course_{course_id}/modules/module_{module_id}/lessons/lesson_{lesson.id}/{unique_filename}"

class Course(models.Model):
    # Оставляем имя поля как на схеме (course_name)
    course_name = models.CharField(max_length=255)
    # Поле необязательное (на схеме нет NN)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.course_name


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    module_name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order"]

    def save(self, *args, **kwargs):
        if not self.order:
            last_module = Module.objects.filter(course=self.course).order_by("-order").first()
            self.order = last_module.order + 1 if last_module else 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.module_name


class Lesson(models.Model):
    # Делаем связь ОБЯЗАТЕЛЬНОЙ. Урок не может существовать без модуля.
    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    # Имя поля со схемы
    lesson_name = models.CharField(max_length=255)
    # Имя поля со схемы
    description = models.TextField(blank=True, null=True)
    order = models.IntegerField()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.lesson_name

class Content(PolymorphicModel):
    lesson = models.ForeignKey(Lesson, related_name="contents", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, blank=False, null=False)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.lesson} content"

class TextContent(Content):
    class TextTypeChoices(models.TextChoices):
        IMPORTANT = 'important', 'Маңызды ақпарат'
        DANGER = 'danger', 'Сақтық ақпарат'
        TIP = 'tip', 'Кеңес'
        BASE = 'base', 'Қарапайым мәтін'
    
    content = models.TextField()
    text_type = models.TextField(choices=TextTypeChoices.choices, default=TextTypeChoices.BASE)

    def __str__(self):
        if len(self.content) > 90:
            return f"Мәтін - {self.content[:90]}..."
        return f"Мәтін - {self.content}"

class HeadingContent(Content):
    class LevelChoices(models.IntegerChoices):
        H1 = 1, '1-деңгейлі'
        H2 = 2, '2-деңгейлі'
        H3 = 3, '3-деңгейлі'
        H4 = 4, '4-деңгейлі'
        H5 = 5, '5-деңгейлі'
        H6 = 6, '6-деңгейлі'
    
    content = models.TextField()
    h_level = models.SmallIntegerField(choices=LevelChoices.choices, default=LevelChoices.H2)

    def __str__(self):
        if len(self.content) > 90:
            return f"Тақырып - {self.content[:90]}..."
        return f"Тақырып - {self.content}"

class ImageContent(Content):
    content_url = models.FileField(upload_to=get_course_file_upload_path, verbose_name="Сурет")

    def __str__(self):
        return f"Сурет - {self.content_url}"

class VideoContent(Content):
    content_url = models.FileField(upload_to=get_course_file_upload_path, verbose_name="Бейне")

    def __str__(self):
        return f"Бейне - {self.content_url}"

class YoutubeVideoContent(Content):
    content_url = models.TextField()

    def __str__(self):
        return f"YouTube сілтемесі - {self.content_url}"

class PresentationContent(Content):
    content_url = models.FileField(upload_to=get_course_file_upload_path, verbose_name="Презентация")

    def __str__(self):
        return f"Презентация - {self.content_url}"