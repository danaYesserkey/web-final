from django.contrib import admin
from adminsortable2.admin import SortableStackedInline, SortableAdminBase
from polymorphic.admin import StackedPolymorphicInline, PolymorphicInlineSupportMixin

from apps.courses.models import (
    Course,
    Module,
    Lesson,
    Content,
    ImageContent,
    VideoContent,
    PresentationContent,
    TextContent,
    HeadingContent,
    YoutubeVideoContent,
)
from apps.quizzes.models import Quiz


class ModuleInline(SortableStackedInline):
    model = Module
    extra = 0
    show_change_link = True


@admin.register(Course)
class CourseAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ("id", "course_name", "description")
    search_fields = ("course_name",)
    inlines = [ModuleInline]


class LessonInline(SortableStackedInline):
    model = Lesson
    extra = 0
    fields = ("lesson_name", "order")
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(SortableAdminBase, admin.ModelAdmin):
    list_display = ("id", "module_name", "course", "order")
    search_fields = ("module_name",)
    list_filter = ("course",)
    inlines = [LessonInline]
    fields = (
        "course",
        "module_name",
    )


class ContentInline(StackedPolymorphicInline):
    class TextContentInline(StackedPolymorphicInline.Child):
        model = TextContent
        fields = ("content", "text_type", "order")

    class HeadingContentInline(StackedPolymorphicInline.Child):
        model = HeadingContent
        fields = ("content", "h_level", "order")

    class ImageContentInline(StackedPolymorphicInline.Child):
        model = ImageContent
        fields = ("content_url", "order")

    class VideoContentInline(StackedPolymorphicInline.Child):
        model = VideoContent
        fields = ("content_url", "order")

    class YoutubeVideoContentInline(StackedPolymorphicInline.Child):
        model = YoutubeVideoContent
        fields = ("content_url", "order")

    class PresentationContentInline(StackedPolymorphicInline.Child):
        model = PresentationContent
        fields = ("content_url", "order")

    model = Content
    child_inlines = (
        TextContentInline,
        HeadingContentInline,
        ImageContentInline,
        VideoContentInline,
        YoutubeVideoContentInline,
        PresentationContentInline,
    )

    classes = ["sortable-set"]

    class Media:
        js = (
            "adminsortable2/js/libs/jquery-ui-sortable.min.js",
            "adminsortable2/js/inline-sortable.js",
        )


class QuizInline(admin.TabularInline):
    model = Quiz
    extra = 0
    show_change_link = True


@admin.register(Lesson)
class LessonAdmin(SortableAdminBase, PolymorphicInlineSupportMixin, admin.ModelAdmin):
    list_display = ("id", "lesson_name", "module", "order")

    fieldsets = (
        (
            "Основная информация",
            {"fields": ("module", "lesson_name", "description", "order")},
        ),
    )

    inlines = (QuizInline, ContentInline)
