from django.contrib import admin
from account_app.models import Student, Teacher, University, EducationStudy, User
from django.utils import timezone
from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
import re


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    exclude = ['last_login', 'groups']
    list_display = ['id' ,'username', 'role', 'email']
    exclude = ['role']
    list_per_page =30


@admin.display(boolean=True, ordering="name", description="new user")
def created_at_before_last_week(self):
    time = timezone.now() - timedelta(days=7)
    return time > self.updated_at


class StudentAdminForm(forms.ModelForm):
    username = forms.CharField()
    phone_number = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = Student
        fields = ['phone_number', 'university', 'education_study',
                  'username', 'email', 'password', 'first_name', 'last_name']
        
    def clean(self):
        cleaned_data = super().clean()

        username = cleaned_data.get('username')
        if username:
            qs = User.objects.filter(username=username)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({"username": "This username has already been used."})

        email = cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError({"email": "This email has already been used."})

        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        if first_name and last_name and first_name == last_name:
            raise ValidationError("First and last names should not be the same.")

        phone_number = cleaned_data.get('phone_number')
        pattern = r"^(0)?9\d{9}$"
        if phone_number and not re.match(pattern, phone_number):
            raise ValidationError({"phone_number": "The mobile number is not valid."})

        if phone_number:
            qs = User.objects.filter(phone_number=phone_number)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    {"phone_number": "This phone number is already registered."}
                )

        return cleaned_data


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['password'].required = False

    def save(self, commit=True):
        student = super().save(commit=False)

        if student.pk:
            user = student.user
            user.username = self.cleaned_data['username']
            user.phone_number = self.cleaned_data['phone_number']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']

            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])

            user.save()

        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                phone_number=self.cleaned_data['phone_number'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role=User.Role.STUDENT
            )
            student.user = user

        if commit:
            student.save()

        return student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    empty_value_display = "-- empty --"
    list_display = ['student_id', 'username', 'email', created_at_before_last_week]
    fields = [
        'username', 'email', 'password', 'first_name', 'last_name',
        'phone_number', 'university', 'education_study'
    ]
    list_per_page = 30
    save_as = True
    show_full_result_count = True

    @admin.display(description='Username')
    def username(self, obj):
        return obj.user.username

    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email
    
    @admin.display(description='ID')
    def student_id(self, obj):
        return obj.user.id 


class TeacherAdminForm(forms.ModelForm):
    username = forms.CharField()
    phone_number = forms.CharField()
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = Teacher
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()

        username = cleaned_data.get('username')
        if username:
            qs = User.objects.filter(username=username)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.user.pk)
            if qs.exists():
                raise ValidationError({"username": "This username has already been used."})

        email = cleaned_data.get('email')
        if email:
            qs = User.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.user.pk)
            if qs.exists():
                raise ValidationError({"email": "This email has already been used."})

        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        if first_name and last_name and first_name == last_name:
            raise ValidationError("First and last names should not be the same.")

        phone_number = cleaned_data.get('phone_number')
        if User.objects.filter(phone_number=phone_number).exists():
            raise ValidationError(
                {"phone_number": "This phone number is already registered."}
            )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields['username'].initial = self.instance.user.username
            self.fields['phone_number'].initial = self.instance.user.phone_number
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['password'].required = False

    def save(self, commit=True):
        teacher = super().save(commit=False)

        if teacher.pk:
            user = teacher.user
            user.username = self.cleaned_data['username']
            user.phone_number = self.cleaned_data['phone_number']
            user.email = self.cleaned_data['email']
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()
        else:
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                phone_number=self.cleaned_data['phone_number'],
                email=self.cleaned_data['email'],
                password=self.cleaned_data['password'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                role=User.Role.TEACHER
            )
            teacher.user = user

        if commit:
            teacher.save()
            teacher.university.set(self.cleaned_data['university'])

        return teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    form = TeacherAdminForm
    empty_value_display = "-- empty --"
    list_display = ['teacher_id' , "username", 'email', created_at_before_last_week]
    fields = [
        'username', 'email', 'password', 'first_name', 'last_name',
        'phone_number', 'university'
    ]
    list_per_page = 30
    save_as = True
    show_full_result_count = True


    @admin.display(description='Username')
    def username(self, obj):
        return obj.user.username
    
    @admin.display(description='Email')
    def email(self, obj):
        return obj.user.email
    
    @admin.display(description='ID')
    def teacher_id(self, obj):
        return obj.user.id 


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ['id' ,'name_uni', 'city']
    list_per_page =10


@admin.register(EducationStudy)
class EducationStudyAdmin(admin.ModelAdmin):
    list_display = ['id' ,'name_edu']
    list_per_page =10
