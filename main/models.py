from django.db import models
from account_app.models import Teacher, User
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from config import settings
import uuid
from main.utils.validators import validate_video_size
from django.conf import settings
from config.settings.base_settings import VIDEO_COURSE_MAX_MB, VIDEO_ARTICLE_MAX_MB


class CommonInfo(models.Model):
    """
    Abstract model that provides created and updated timestamps.
    """
    created_at = models.DateField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Course(models.Model):
    """
    Model representing a course created by a teacher.
    """
    name = models.CharField(max_length=100)
    description_course = models.TextField()
    is_free = models.BooleanField(default=True)
    price = models.PositiveIntegerField(default=0)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    users = models.ManyToManyField(User, through="Enrollment", related_name="related_user")

    def clean(self):
        """
        Ensure that course pricing matches the 'is_free' status.
        """
        super().clean()
        if self.is_free and self.price != 0:
            raise ValidationError("This course is not free")
        if not self.is_free and self.price == 0:
            raise ValidationError("This course is free")
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def short_code(self):
        """
        Get the short link code for the course, if exists.
        """
        try:
            return ShortLink.objects.get(
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id
            ).code
        except ShortLink.DoesNotExist:
            return None
            
    def get_absolute_url(self):
        """
        Returns the frontend URL for this course.
        """
        return f"{settings.FRONTEND_BASE_URL}/courses/{self.id}"

    def __str__(self):
        return f'course: {self.name} - Teacher: {self.teacher.user.first_name} {self.teacher.user.last_name}'


class VideoCourse(models.Model):
    """
    Model representing a video associated with a course.
    """
    video = models.FileField(
        upload_to='media/video/course/',
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4']),
            validate_video_size(VIDEO_COURSE_MAX_MB)
        ]
    )
    description = models.CharField(max_length=360)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, blank=True, null=True)
    is_free = models.BooleanField(default=False)


class Enrollment(models.Model):
    """
    Model representing a user's enrollment in a course.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_joined = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_user_course")
        ]


class PublishedManager(models.Manager):
    """
    Custom manager to return only published articles.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class Article(CommonInfo):
    """
    Model representing an article created by a user.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_article = models.FileField(
        upload_to='media/video/article/',
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4']),
            validate_video_size(VIDEO_ARTICLE_MAX_MB)
        ],
        blank=True, null=True
    )
    is_published = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    objects = models.Manager() 
    published = PublishedManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["title", "owner"], name="unique_title_teacher")
        ]


class Comment(CommonInfo):
    """
    Model representing a comment on an article.
    """
    user_auther = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    article_comment = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    text_comment = models.CharField(max_length=360)
    public_comment = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.user_auther.username} - {self.article_comment}'

class StockManager(models.Manager):
    """Manager for filtering books that are in stock."""

    def get_queryset(self):
        return super().get_queryset().filter(stock__gt=0)


class Book(models.Model):
    """Represents a book product available for purchase."""

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()
    stock_book = StockManager()

    @property
    def short_code(self):
        """Return short link code if exists, otherwise None."""
        try:
            return ShortLink.objects.get(
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id
            ).code
        except ShortLink.DoesNotExist:
            return None

    def get_absolute_url(self):
        """Return frontend URL for this book."""
        return f"{settings.FRONTEND_BASE_URL}/{self.id}/"

    class Meta:
        ordering = ["name"]
        verbose_name = "Book"
        verbose_name_plural = "Books"

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Shopping cart associated with a single user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    """An item inside a user's cart."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'book')


class Order(models.Model):
    """Represents a user's order."""

    STATUS_CHOICES = [
        ('pending', 'Awaiting payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.buyer.username} - {self.status}"


class OrderItem(models.Model):
    """Book item inside an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order", "book"], name="unique_order_book")
        ]


class Payment(models.Model):
    """Stores payment information for a product purchase."""

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    product = GenericForeignKey("content_type", "object_id")
    authority = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.amount} - {self.status}"


class ShortLink(models.Model):
    """Short link for accessing related objects."""

    code = models.CharField(max_length=10, unique=True, db_index=True)
    clicks = models.PositiveIntegerField(default=0)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Generate short code automatically if not provided."""
        if not self.code:
            self.code = uuid.uuid4().hex[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code


class Blocklist(models.Model):
    """Stores blocked IP addresses."""

    ip_addr = models.GenericIPAddressField(unique=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_addr
