from django.db import models
from django.contrib.auth.models import AbstractUser
import re
from django.core.exceptions import ValidationError


class User(AbstractUser):
    """
    Custom user model with role choices.
    """
    class Role(models.TextChoices):
        TEACHER = "TR", "Teacher"
        STUDENT = "ST", "Student"

    role = models.CharField(max_length=2, choices=Role.choices)
    phone_number = models.CharField(max_length=11, unique=True)

    def clean(self):
        """
        Validate that the phone number matches the Iranian mobile format.
        """
        pattern = r"^(0)?9\d{9}$"
        if not re.match(pattern, self.phone_number):
            raise ValidationError({"phone_number": "The mobile number is not valid."})

    def __str__(self):
        return self.username


class CommonInfo(models.Model):
    """
    Abstract base model with common timestamps.
    """
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]



class University(models.Model):
    """
    University model.
    """
    name_uni = models.CharField(max_length=360)
    city = models.CharField(max_length=360)

    def __str__(self):
        return self.name_uni


class EducationStudy(models.Model):
    """
    Educational field or study program.
    """
    name_edu = models.CharField(max_length=360)

    def __str__(self):
        return self.name_edu


class Student(CommonInfo):
    """
    Student profile linked to a user and university.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE)
    education_study = models.ForeignKey(EducationStudy, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "university"], name="unique_students_university")
        ]

    def __str__(self):
        return self.user.get_full_name()


class Teacher(CommonInfo):
    """
    Teacher profile linked to a user and multiple universities.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    university = models.ManyToManyField(University)

    def __str__(self):
        return self.user.get_full_name()
