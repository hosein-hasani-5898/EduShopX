from rest_framework import serializers
from main.models import (
    Course, Enrollment, Article, Book, 
    Order, OrderItem, Comment, VideoCourse, Cart, CartItem
    )
from account_app.models import Student, Teacher, User, University, EducationStudy
from django.contrib.contenttypes.models import ContentType
from main.models import ShortLink
from django.contrib.admin.models import LogEntry



class EducationStudySerializer(serializers.ModelSerializer):
    """
    Serializer for the EducationStudy model.
    
    Fields:
        id (int): Unique identifier of the education study.
        name_edu (str): Name of the education study.
    """
    class Meta:
        model = EducationStudy
        fields = ['id', 'name_edu']


class UniversitySetSerializer(serializers.ModelSerializer):
    """
    Serializer for the University model.

    Fields:
        id (int): Unique identifier of the university.
        name_uni (str): Name of the university.
        city (str): City where the university is located.
    """
    class Meta:
        model = University
        fields = ['id', 'name_uni', 'city']


class UserSetSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    Fields:
        id (int): Unique identifier of the user.
        username (str): Username of the user.
        first_name (str): First name.
        last_name (str): Last name.
        email (str): Email address.
        phone_number (str): phone number.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number']


class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer for the Student model.

    Includes nested serializers for user, university, and education study.
    """
    user = UserSetSerializer()
    university = UniversitySetSerializer()
    education_study = EducationStudySerializer()

    class Meta:
        model = Student
        fields = ['id', 'created_at', 'updated_at', 'phone_number', 'university', 'user', 'education_study']


class TeacherSerializer(serializers.ModelSerializer):
    """
    Serializer for the Teacher model.

    Includes nested user serializer and list of universities.
    """
    user = UserSetSerializer()
    university = UniversitySetSerializer(many=True)

    class Meta:
        model = Teacher
        fields = '__all__'



class CoursesUserSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying course information for users.

    Adds a read-only field `count_students` showing the number of enrolled users.
    """
    count_students = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'description_course', 'is_free', 'price', 'count_students']


class CoursesCreateUserSerializer(serializers.ModelSerializer):
    """
    Serializer for creating or updating courses by teacher users.

    Fields:
        name (str): Name of the course (required).
        description_course (str): Description of the course (required).
        is_free (bool): Whether the course is free (default True).
        price (int): Price of the course (default 0).
        videos (list of int): List of VideoCourse IDs (optional).
    """
    class Meta:
        model = Course
        fields = ['name', 'description_course', 'is_free', 'price']

    def validate_name(self, value):
        """
        Validate that the course name is unique for the teacher.

        Raises:
            serializers.ValidationError: If the course name already exists for the teacher.
        """
        user = self.context['request'].user
        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            raise serializers.ValidationError("Teacher not found.")

        qs = Course.objects.filter(name=value, teacher=teacher)

        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError(
                "This course name has already been taken for this instructor."
            )

        return value



class CoursesCreateAdminSerializer(serializers.ModelSerializer):
    """
    Serializer for creating or updating courses by admin users.

    Admins can specify a teacher explicitly.
    """
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.all(), required=False)

    class Meta:
        model = Course
        fields = ['name', 'description_course', 'is_free', 'price', 'teacher']

    def validate_name(self, value):
        """Validate that the course name is unique for the teacher."""
        user = self.context['request'].user
        if self.instance and self.instance.pk:
            teacher = self.instance.teacher
            if Course.objects.filter(name=value, teacher=teacher).exclude(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This course name has already been used for this instructor.")
        else:
            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                raise serializers.ValidationError("Teacher not found.")
            if Course.objects.filter(name=value, teacher=teacher).exists():
                raise serializers.ValidationError("This course name has already been used for this instructor.")
        return value

    def create(self, validated_data):
        """Assign teacher automatically if not specified."""
        teacher = validated_data.pop('teacher', None)
        if not teacher:
            user = self.context['request'].user
            teacher = Teacher.objects.get(user=user)
        validated_data['teacher'] = teacher
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Prevent updating the teacher through this serializer."""
        validated_data.pop('teacher', None)
        return super().update(instance, validated_data)
    


class CourseLiteSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for Course model, used for nested representations.

    Fields:
        id (int): Course ID.
        name (str): Course name.
        is_free (bool): Whether the course is free.
        price (int): Course price.
    """
    class Meta:
        model = Course
        fields = ['id', 'name', 'is_free', 'price']


class VideoCourseSerializer(serializers.ModelSerializer):
    """
    Serializer for VideoCourse model for read operations.

    Fields:
        id (int): VideoCourse ID.
        video_url (str): URL to the video file.
        description (str): Description of the video.
        is_free (bool): Whether the video is free.
        course (CourseLiteSerializer): Nested course information.
    """
    course = CourseLiteSerializer(read_only=True)
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = VideoCourse
        fields = ['id', 'video_url', 'description', 'is_free', 'course']
        read_only_fields = ['id', 'video_url', 'course']

    def get_video_url(self, obj):
        """Return the video file URL, or None if not available."""
        try:
            return obj.video.url
        except Exception:
            return None


class VideoCourseCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating or updating VideoCourse instances.

    Validates that only the teacher of a course can add videos.
    """
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())

    class Meta:
        model = VideoCourse
        fields = ['id', 'video', 'description', 'course', 'is_free']
        read_only_fields = ['id']

    def validate_course(self, value):
        """Ensure that only the course owner (teacher) can add videos."""
        request = self.context.get('request')
        if request and request.user and not request.user.is_staff:
            try:
                teacher = Teacher.objects.get(user=request.user)
            except Teacher.DoesNotExist:
                raise serializers.ValidationError("Only teachers can add videos.")
            if value.teacher != teacher:
                raise serializers.ValidationError("You cannot add a video to a course you do not own.")
        return value

    def validate(self, attrs):
        """Automatically mark video as free if course is free."""
        course = attrs.get('course') or getattr(self.instance, 'course', None)
        if course and course.is_free:
            attrs['is_free'] = True
        return attrs


class UserEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for basic user information in enrollment."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'phone_number']


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for course information in enrollment."""
    teacher_username = serializers.CharField(source='teacher.user.first_name', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'name', 'is_free', 'teacher_username']


class EnrollmentAdminSerializer(serializers.ModelSerializer):
    """Serializer for enrollment details visible to admins."""
    user = UserEnrollmentSerializer()
    course = CourseEnrollmentSerializer()

    class Meta:
        model = Enrollment
        fields = ['user', 'course', 'date_joined']

    def validate(self, attrs):
        """Prevent a teacher from enrolling in their own course."""
        user = attrs.get("user")
        course = attrs.get("course")
        if course.teacher.user == user:
            raise serializers.ValidationError("The teacher cannot register his own course.")
        return attrs


class EnrollmentUserSerializer(serializers.ModelSerializer):
    """Serializer for user-specific enrollments."""
    course = CourseEnrollmentSerializer()

    class Meta:
        model = Enrollment
        fields = ['course', 'date_joined']

    def validate(self, attrs):
        """Prevent a user from enrolling in a course they teach."""
        user = self.context['request'].user
        course = attrs.get("course")
        if course.teacher.user == user:
            raise serializers.ValidationError("You are the instructor of this course and cannot register yourself.")
        return attrs


class UserArticleSerializer(serializers.ModelSerializer):
    """Serializer for basic user information in articles."""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']



class TeacherSerializer(serializers.ModelSerializer):
    """
    Serializer for Teacher model to show university names and cities.

    Fields:
        id (int): Teacher ID.
        university_name (list[str]): Names of associated universities.
        university_city (list[str]): Cities of associated universities.
    """
    university_name = serializers.SlugRelatedField(
        source='university',
        many=True,
        read_only=True,
        slug_field='name_uni'
    )
    university_city = serializers.SlugRelatedField(
        source='university',
        many=True,
        read_only=True,
        slug_field='city'
    )

    class Meta:
        model = Teacher
        fields = ['id', 'university_name', 'university_city']


class StudentSerializer(serializers.ModelSerializer):
    """
    Serializer for Student model to show university and education study details.

    Fields:
        id (int): Student ID.
        university_name (str): Name of the university.
        university_city (str): City of the university.
        education_study (str): Name of the education study.
    """
    university_name = serializers.CharField(source='university.name_uni', read_only=True)
    university_city = serializers.CharField(source='university.city', read_only=True)
    education_study = serializers.CharField(source='education_study.name_edu', read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'university_name', 'university_city', 'education_study']


class ArticleListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing articles with owner, teacher, and student info.

    Fields:
        id (int): Article ID.
        title (str): Article title.
        content (str): Article content.
        video_article (file): Associated video file.
        created_at (datetime): Article creation time.
        updated_at (datetime): Article update time.
        owner (UserArticleSerializer): Owner information.
        student (StudentSerializer): Student details if owner is student.
        teacher (TeacherSerializer): Teacher details if owner is teacher.
    """
    owner = UserArticleSerializer()
    teacher = TeacherSerializer(source='owner.teacher', read_only=True)
    student = StudentSerializer(source='owner.student', read_only=True)

    class Meta:
        model = Article
        fields = ['id', 'title', 'content', 'video_article', 'created_at', 'updated_at', 'owner', 'student', 'teacher']


class ArticleUserSerializer(serializers.ModelSerializer):
    """Serializer for article data visible to regular users."""
    class Meta:
        model = Article
        fields = ['title', 'content', 'video_article', 'is_published']


class CommentUserListSerializer(serializers.ModelSerializer):
    """Serializer for listing public comments."""
    class Meta:
        model = Comment
        fields = ['user_auther', 'article_comment', 'text_comment']


class CommentAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin access to comment data, including public flag."""
    class Meta:
        model = Comment
        fields = ['user_auther', 'article_comment', 'text_comment', 'public_comment']


class CommentUserSerializer(serializers.ModelSerializer):
    """Serializer for users to create or view their own comments."""
    class Meta:
        model = Comment
        fields = ['article_comment', 'text_comment']


class BookAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin access to book data."""
    class Meta:
        model = Book
        fields = ['id', 'name', 'description', 'price', 'stock', 'created_at']


class BookListSerializer(serializers.ModelSerializer):
    """Serializer for listing books to users."""
    class Meta:
        model = Book
        fields = ['id', 'name', 'description', 'price']


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer for individual items in an order."""
    class Meta:
        model = OrderItem
        fields = ['book', 'quantity', 'price']


class OrderSerializer(serializers.ModelSerializer):
    """Serializer for orders including nested order items."""
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'buyer', 'status', 'total_price', 'created_at', 'items']
        read_only_fields = ['id', 'buyer', 'status', 'total_price', 'created_at', 'items']


class CartItemSerializer(serializers.ModelSerializer):
    """Serializer for individual items in a user's cart."""
    class Meta:
        model = CartItem
        fields = ['id', 'book', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    """Serializer for a user's cart including nested items."""
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'updated_at']
        read_only_fields = ['user']




class PaymentRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting a payment for a product.

    Fields:
        product_type (str): Type of product ('course' or 'book').
        product_id (int): ID of the product to be paid for.
    """
    product_type = serializers.CharField()
    product_id = serializers.IntegerField()

    def validate(self, data):
        """
        Validate that the product type is valid and the product exists.
        """
        model_map = {
            "course": Course,
            "book": Book,
        }

        if data["product_type"] not in model_map:
            raise serializers.ValidationError("Invalid product type.")

        Model = model_map[data["product_type"]]
        try:
            product = Model.objects.get(id=data["product_id"])
        except Model.DoesNotExist:
            raise serializers.ValidationError("Product not found.")

        data["product"] = product
        return data



class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for admin audit logs.

    Fields:
        id (int): Log entry ID.
        user (str): Username of the user who performed the action.
        action (str): Action performed ('ADD', 'CHANGE', 'DELETE').
        model (str): Model affected by the action.
        object_repr (str): String representation of the object.
        action_time (datetime): Timestamp of the action.
    """
    user = serializers.CharField(source="user.username", read_only=True)
    action = serializers.SerializerMethodField()
    model = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model = LogEntry
        fields = ["id", "user", "action", "model", "object_repr", "action_time"]

    def get_action(self, obj):
        """
        Convert action_flag integer to human-readable string.
        """
        return {
            1: "ADD",
            2: "CHANGE",
            3: "DELETE",
        }.get(obj.action_flag, "UNKNOWN")




class ShortLinkCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a short link for a given model instance.

    Fields:
        model (str): Name of the model.
        object_id (int): ID of the object to create a short link for.
    """
    model = serializers.CharField()
    object_id = serializers.IntegerField()

    def create(self, validated_data):
        """
        Create a ShortLink instance for the given model and object_id.
        """
        model_name = validated_data['model'].lower()
        object_id = validated_data['object_id']
        content_type = ContentType.objects.get(model=model_name)

        return ShortLink.objects.create(
            content_type=content_type,
            object_id=object_id
        )


class ShortLinkSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying short link details.

    Fields:
        code (str): Short code of the link.
        clicks (int): Number of times the link has been accessed.
        created_at (datetime): Timestamp when the link was created.
    """
    class Meta:
        model = ShortLink
        fields = ['code', 'clicks', 'created_at']





class TokenObtainPairResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token obtain response.

    Fields:
        access (str): Access token.
        refresh (str): Refresh token.
    """
    access = serializers.CharField()
    refresh = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token refresh response.

    Fields:
        access (str): New access token.
    """
    access = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class TokenVerifyResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token verification response.
    """
    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


class TokenBlacklistResponseSerializer(serializers.Serializer):
    """
    Serializer for JWT token blacklist response.
    """
    def create(self, validated_data):
        raise NotImplementedError()

    def update(self, instance, validated_data):
        raise NotImplementedError()


