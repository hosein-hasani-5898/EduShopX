from django.contrib import admin
from main.models import (
    Course, Enrollment, Article, Book,
    Order, OrderItem, VideoCourse, Cart,
    CartItem, Payment, ShortLink, Comment
)
import datetime
from datetime import datetime, timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin.models import LogEntry



@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "action_time"]
    list_per_page = 10


class CreatedAtFilter(admin.SimpleListFilter):
    title = 'Creation time'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('last-7-days', 'Last 7 says'),
            ('last-30-days', 'Last 30 days'),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        now = datetime.now()

        if value == 'last-7-days':
            start = datetime(now.year, now.month, now.day)
            return queryset.filter(created_at__gte=start)
        elif value == 'last-7-days':
            start = now - timedelta(days=7)
            return queryset.filter(created_at__gte=start)
        elif value == 'last-30-days':
            start = now - timedelta(days=30)
            return queryset.filter(created_at__gte=start)
        
        return queryset


@admin.register(VideoCourse)
class VideoCourseAdmin(admin.ModelAdmin):
    list_display = ["id", "course"]
    list_per_page = 10

    def get_fields(self, request, obj=None):
        fields = ['course', 'video', 'description'] 

        if obj and not obj.course.is_free:
            fields.append('is_free')

        return fields


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_filter = [CreatedAtFilter]
    list_display = ['id', 'name', 'teacher']
    list_filter = ['teacher']
    list_per_page = 10
    list_select_related = ['teacher']

    
class EnrollmentAdminForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        course = cleaned_data.get('course')
        if user and course and course.teacher.user == user:
            raise ValidationError("The teacher cannot register her own course.")
        return cleaned_data


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    form = EnrollmentAdminForm
    list_display = ['user', 'course', 'date_joined']
    list_filter = ['course']
    list_per_page =10


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'content', 'is_published']
    list_filter = ['is_published']
    list_per_page =10


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['id' ,'name', 'description', 'price', 'stock', 'created_at']
    list_filter = [CreatedAtFilter]
    list_per_page =10
    ist_select_related = ['teacher']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id' ,'user','updated_at']
    list_per_page =10


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id' ,'cart','book', 'quantity']
    list_per_page =10


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    max_num = 1
    raw_id_fields = ["order"]
    can_delete = False
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'created_at']
    radio_fields = {"buyer": admin.VERTICAL}
    list_per_page =10
    inlines = [OrderItemInline]
    ist_select_related = ['teacher']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id' ,'order','quantity']
    list_per_page =10


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id' ,'status', 'user']
    list_per_page =10


@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ['id' ,'code', 'created_at']
    list_per_page =10


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id' ,'public_comment', 'created_at']
    list_per_page =10

