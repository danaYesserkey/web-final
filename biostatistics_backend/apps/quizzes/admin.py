from django.contrib import admin
from django.forms import ModelForm
from polymorphic.admin import StackedPolymorphicInline, PolymorphicInlineSupportMixin
from nested_admin.nested import NestedTabularInline, NestedStackedInline, NestedModelAdmin

from .models import (
    Quiz,
    Question,
    QuizContext,
    WithQuizContext,
    WithoutQuizContext,
    MultipleChoiceQuestion,
    BirnesheJauaptyqSuraq,
    EnterValueQuestion,
    AnswerOption,
)


class AnswerOptionInline(NestedTabularInline):
    model = AnswerOption

    def get_extra(self, request, obj = ..., **kwargs):
        return 0 if obj else 4

class MultipleChoiceInline(NestedStackedInline):
    model = MultipleChoiceQuestion
    extra = 0
    fields = ('text',)
    inlines = [AnswerOptionInline]

class BirnesheJauaptyqInline(NestedStackedInline):
    model = BirnesheJauaptyqSuraq
    extra = 0
    fields = ('text',)
    inlines = [AnswerOptionInline]

class EnterValueInline(NestedStackedInline):
    model = EnterValueQuestion
    extra = 0
    fields = ('text', 'correct_value',)

class WithoutContextForm(ModelForm):
    class Meta:
        model = WithoutQuizContext
        fields = ()
    
    def has_changed(self):
        if not self.instance.pk:
            return True
        return super().has_changed()

class ContextInline(StackedPolymorphicInline):
    class WithContextInline(StackedPolymorphicInline.Child):
        model = WithQuizContext
        show_change_link = True
        # fields
    
    class WithoutContextInline(StackedPolymorphicInline.Child):
        model = WithoutQuizContext
        show_change_link = True
        form = WithoutContextForm
        fields = ()
    
    model = QuizContext
    child_inlines = (
        WithContextInline,
        WithoutContextInline,
    )

@admin.register(Quiz)
class QuizAdmin(PolymorphicInlineSupportMixin, admin.ModelAdmin):
    inlines = [ContextInline]

class QuestionInline(NestedStackedInline):
    model = Question
    extra = 0

@admin.register(WithQuizContext)
class WithContextAdmin(NestedModelAdmin):
    inlines = [MultipleChoiceInline, BirnesheJauaptyqInline, EnterValueInline]

@admin.register(WithoutQuizContext)
class WithoutContextAdmin(NestedModelAdmin):
    inlines = [MultipleChoiceInline, BirnesheJauaptyqInline, EnterValueInline]
    readonly_fields = ('quiz',)