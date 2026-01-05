from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from account_app.models import User, Student, Teacher, University, EducationStudy
import re
from django.db import transaction



class BaseRegisterSerializer(serializers.Serializer):
    """
    Base serializer for user registration.

    Handles common user fields and shared validations
    between student and teacher registration.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    university = serializers.IntegerField()

    def validate_phone_number(self, value):
        """
        Validate Iranian mobile phone number format.
        """
        pattern = r"^(0)?9\d{9}$"
        if not re.match(pattern, value):
            raise serializers.ValidationError("Mobile number is not valid.")
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "This phone number is already registered."
            )
        return value

    def validate(self, attrs):
        username = attrs.get("username")
        email = attrs.get("email")
        phone_number = attrs.get("phone_number")
        university = attrs.get("university")

        user = self.instance

        if User.objects.filter(username=username).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError(
                {"username": "This username has already been used."}
            )

        if User.objects.filter(email=email).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError(
                {"email": "This email has already been registered."}
            )

        if User.objects.filter(phone_number=phone_number).exclude(pk=user.pk if user else None).exists():
            raise serializers.ValidationError(
                {"phone_number": "This phone number is already registered."}
            )
        
        if not University.objects.filter(id=university).exists():
            raise serializers.ValidationError(
                {"university": "University not found."}
            )

        return attrs



    def create_user(self, validated_data, role):
        """
        Create and return a User instance with the given role.
        """
        return User.objects.create_user(
            username=validated_data["username"],
            phone_number=validated_data["phone_number"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=validated_data["password"],
            role=role,
        )


class StudentRegisterSerializer(BaseRegisterSerializer):
    """
    Serializer for student registration.
    """
    university = serializers.IntegerField()
    education_study = serializers.IntegerField()

    def validate_education_study(self, value):
        """
        Ensure the education study exists.
        """
        if not EducationStudy.objects.filter(id=value).exists():
            raise serializers.ValidationError("EducationStudy not found.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a student user and related student profile.
        """
        user = self.create_user(validated_data, User.Role.STUDENT)
        university = University.objects.get(id=validated_data["university"])
        education_study = EducationStudy.objects.get(
            id=validated_data["education_study"]
        )

        student = Student.objects.create(
            user=user,
            university=university,
            education_study=education_study,
        )

        student.full_clean()
        student.save(update_fields=None)
        return user


class TeacherRegisterSerializer(BaseRegisterSerializer):
    """
    Serializer for teacher registration.
    """
    university = serializers.IntegerField()

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a teacher user and related teacher profile.
        """
        user = self.create_user(validated_data, User.Role.TEACHER)
        university = University.objects.get(id=validated_data["university"])

        teacher = Teacher.objects.create(
            user=user,
        )

        teacher.full_clean()
        teacher.save()
        teacher.university.add(university)
        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that adds extra user fields to the token.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token["role"] = user.role
        token["is_active"] = user.is_active
        token["is_staff"] = user.is_staff

        return token


