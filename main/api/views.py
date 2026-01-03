# region modules and libraries

from main.models import (
    Course, Article, Book, Order,
    OrderItem, Comment, Enrollment, Cart, CartItem, 
    VideoCourse, Payment, ShortLink
)

from account_app.models import User, Student, Teacher
from main.api import serializers
from rest_framework import generics, filters, permissions, status, viewsets
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from main.api.custom_permissions import IsTeacherUser, IsTeacherUserVC
from rest_framework.views import APIView
from main.services import create_order_from_cart
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q, Count, Sum, F
import uuid
from django.contrib.contenttypes.models import ContentType
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
import datetime
from django.http import HttpResponse
from main.tasks import click_plus_task, excel_task, avg_order_task, send_mass_email_task
from celery.result import AsyncResult
from django.contrib.admin.models import LogEntry
from drf_yasg import openapi
from django.core.cache import cache
# endregion


# region UniViews & AdminAcces


class StudentViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing students.

    This endpoint allows administrators to list, retrieve, update,
    and delete student accounts. Creating students via this endpoint
    is disabled and must be done through the dedicated registration API.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.StudentSerializer

    def get_queryset(self):
        """
        Return an optimized queryset of students with related user,
        university, and education study data.
        """
        return Student.objects.select_related(
            "user",
            "university",
            "education_study"
        )

    @swagger_auto_schema(
        operation_summary="Create student (disabled)",
        operation_description=(
            "Student creation is disabled on this endpoint. "
            "Use `/api/register/student/` instead."
        ),
        responses={405: "Method Not Allowed"}
    )
    def create(self, request, *args, **kwargs):
        """
        Disable student creation via this endpoint.
        """
        return Response(
            {"detail": "create account in address /api/register/student/"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )




class TeacherViewSet(viewsets.ModelViewSet):
    """
    Admin-only ViewSet for managing teachers.

    Supports listing, searching, retrieving, updating, and deleting teachers.
    Teacher creation is disabled and handled via a separate registration API.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.TeacherSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['^name', '=staff_id']

    def get_queryset(self):
        """
        Return teachers with related user and university data.

        Optional query parameters:
        - name: Filter by teacher name
        - staff_id: Filter by staff ID
        """
        queryset = Teacher.objects.select_related(
            "user"
        ).prefetch_related(
            "university"
        )
        name = self.request.query_params.get('name')
        staff_id = self.request.query_params.get('staff_id')
        if name:
            queryset = queryset.filter(name=name)
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)
        return queryset
    
    @swagger_auto_schema(
        operation_summary="Create teacher (disabled)",
        operation_description=(
            "Teacher creation is disabled on this endpoint. "
            "Use `/api/register/teacher/` instead."
        ),
        responses={405: "Method Not Allowed"}
    )
    def create(self, request, *args, **kwargs):
        """
        Disable teacher creation via this endpoint.
        """
        return Response(
            {"detail": "create account in address /api/register/teacher/"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )



# endregion
    


# region StoreViews


class CourseTeacherUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for teachers to manage their own courses.

    Teachers can create, update, delete, and view only the courses
    they are assigned to.
    """
    permission_classes = [permissions.IsAuthenticated, IsTeacherUser]

    def get_queryset(self):
        """
        Return courses belonging to the authenticated teacher.
        """
        return Course.objects.filter(teacher__user=self.request.user)


    def get_serializer_class(self):
        """
        Add request object to serializer context.
        """
        if self.action in ["create", "update", "partial_update"]:
            return serializers.CoursesCreateUserSerializer
        return serializers.CoursesUserSerializer
    
    def get_serializer_context(self):
        """
        Add request object to serializer context.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """
        Automatically assign the authenticated teacher
        as the course owner during creation.
        """
        teacher = Teacher.objects.get(user=self.request.user)
        serializer.save(teacher=teacher)


class CourseAdminUserViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for full course management.

    Administrators can manage all courses and their enrolled users.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        """
        Return all courses with prefetched enrolled users.
        """
        return Course.objects.select_related("teacher").annotate(
            count_students=Count("users")
        )


    def get_serializer_class(self):
        """
        Use different serializers for write and read operations.
        """
        if self.action in ["create", "update", "partial_update"]:
            return serializers.CoursesCreateAdminSerializer
        return serializers.CoursesUserSerializer
    
    def get_serializer_context(self):
        """
        Add request object to serializer context.
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class CoursesListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public endpoint for listing all available courses.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.CoursesUserSerializer

    def get_queryset(self):
        return Course.objects.all()

    def list(self, request, *args, **kwargs):
        cache_key = "courses:all"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)



class CoursesStudentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint for students to view courses they are enrolled in.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CoursesUserSerializer

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(users=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"courses:student:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)



class VideoCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for accessing course videos.

    Users can access:
    - Free videos
    - Paid videos of courses they are enrolled in
    """
    serializer_class = serializers.VideoCourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        course_id = self.kwargs.get("course_pk")
        return VideoCourse.objects.filter(
            course_id=course_id
        ).filter(Q(is_free=True) | Q(course__users=user)).distinct()

    def list(self, request, *args, **kwargs):
        user = request.user
        course_id = self.kwargs.get("course_pk")
        cache_key = f"videos:course:{course_id}:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)



class TeacherVideoCourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for teachers to manage video courses related to their own courses.

    Teachers can create, update, delete, and list videos only for courses
    they own. Access to videos of other teachers is forbidden.
    """

    permission_classes = [permissions.IsAuthenticated, IsTeacherUserVC]

    def get_queryset(self):
        """
        Return videos belonging to courses owned by the authenticated teacher.
        """
        user = self.request.user
        return (
            VideoCourse.objects
            .select_related(
                "course",
                "course__teacher",
                "course__teacher__user",
            )
            .filter(course__teacher__user=user)
        )

    def get_serializer_class(self):
        """
        Use write serializer for create/update actions
        and read serializer for list/retrieve actions.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.VideoCourseCreateUpdateSerializer
        return serializers.VideoCourseSerializer

    @swagger_auto_schema(
        operation_summary="Create video for teacher course",
        operation_description=(
            "Allows a teacher to create a video only for courses "
            "they own. Creating videos for other teachers' courses "
            "is not permitted."
        )
    )
    def perform_create(self, serializer):
        """
        Ensure the authenticated teacher owns the course
        before allowing video creation.
        """
        course = serializer.validated_data.get('course')
        if course.teacher.user != self.request.user:
            raise serializers.ValidationError(
                "You cannot add to this video."
            )
        serializer.save()


class AdminVideoCourseViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing all video courses.

    Administrators have full access to create, update, delete,
    and view all video courses in the system.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        """
        Return all video courses without restriction.
        """
        return VideoCourse.objects.all()

    def get_serializer_class(self):
        """
        Use write serializer for create/update actions
        and read serializer for list/retrieve actions.
        """
        if self.action in ['create', 'update', 'partial_update']:
            return serializers.VideoCourseCreateUpdateSerializer
        return serializers.VideoCourseSerializer


class EnrollmentAdminViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing course enrollments.

    Administrators can view and manage all enrollments
    across users and courses.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.EnrollmentAdminSerializer

    queryset = (
        Enrollment.objects
        .select_related(
            "user",
            "course",
            "course__teacher",
            "course__teacher__user",
        )
    )

class EnrollmentUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to manage their own course enrollments.

    Users can view and manage only their personal enrollments.
    Admin users are excluded from this endpoint.
    """
    permission_classes = [permissions.IsAuthenticated, ~permissions.IsAdminUser]
    serializer_class = serializers.EnrollmentUserSerializer

    def get_queryset(self):
        user = self.request.user
        return Enrollment.objects.filter(user=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"enrollments:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        cache.delete(f"enrollments:user:{self.request.user.id}")
        return instance

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(f"enrollments:user:{self.request.user.id}")


class ArticleAdminViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing all articles.

    Administrators have full access to all articles,
    regardless of ownership.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.ArticleListSerializer

    def get_queryset(self):
        """
        Return articles with optimized related data
        for admin usage.
        """
        return Article.objects.select_related(
            'owner',
            'owner__student',
            'owner__student__education_study',
            'owner__teacher'
        ).prefetch_related(
            'owner__student__university',
            'owner__teacher__university'
        )

class ArticleUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to manage their own articles.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.ArticleUserSerializer

    def get_queryset(self):
        user = self.request.user
        return Article.objects.filter(owner=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"articles:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)
        cache.delete(f"articles:user:{self.request.user.id}")
        return instance

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(f"articles:user:{self.request.user.id}")




class ArticleListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public endpoint for listing published articles.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.ArticleListSerializer

    def get_queryset(self):
        return Article.published.select_related(
            'owner', 'owner__student', 'owner__student__education_study', 'owner__teacher'
        ).prefetch_related(
            'owner__student__university', 'owner__teacher__university'
        )

    def list(self, request, *args, **kwargs):
        cache_key = "articles:published"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)


class CommentUserListView(generics.ListAPIView):
    """
    Public endpoint for listing approved comments.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.CommentUserListSerializer

    def get_queryset(self):
        return Comment.objects.filter(public_comment=True)

    def list(self, request, *args, **kwargs):
        cache_key = "comments:public"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)


class CommentAdminViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing all comments.
    """

    queryset = Comment.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.CommentAdminSerializer

class CommentUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to manage their own comments.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = serializers.CommentUserSerializer

    def get_queryset(self):
        user = self.request.user
        return Comment.objects.filter(user_auther=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"comments:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)

    @swagger_auto_schema(
        operation_summary="Create comment",
        operation_description="Create a new comment as the authenticated user."
    )
    def perform_create(self, serializer):
        instance = serializer.save(user_auther=self.request.user)
        cache.delete(f"comments:user:{self.request.user.id}")
        return instance

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(f"comments:user:{self.request.user.id}")



class BookAdminViewSet(viewsets.ModelViewSet):
    """
    Admin ViewSet for managing books.

    Provides full CRUD access to books for admin users.
    """

    queryset = Book.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = serializers.BookAdminSerializer



class BookListViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public endpoint for listing available books in stock.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = serializers.BookListSerializer

    def get_queryset(self):
        return Book.stock_book.all()

    def list(self, request, *args, **kwargs):
        cache_key = "books:stock"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)


class CheckoutView(APIView):
    """
    Create an order from the authenticated user's cart.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Checkout cart",
        operation_description=(
            "Creates an order based on the authenticated user's cart "
            "and returns order details."
        ),
        responses={201: serializers.OrderSerializer}
    )
    def post(self, request):
        """
        Convert user's cart into an order.
        """
        order = create_order_from_cart(request.user)
        serializer = serializers.OrderSerializer(order)
        return Response(serializer.data, status=201)


class CartView(generics.RetrieveAPIView):
    """
    Retrieve the authenticated user's cart.

    If no cart exists, a new one will be created automatically.
    """

    serializer_class = serializers.CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Return the user's cart, creating it if necessary.
        """
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart


class AddToCartView(APIView):
    """
    Add a book to the authenticated user's cart.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Add book to cart",
        operation_description=(
            "Adds a book to the user's cart or increases the quantity "
            "if the book already exists in the cart."
        )
    )
    def post(self, request):
        """
        Add or update a cart item.
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        book_id = request.data.get("book")
        quantity = int(request.data.get("quantity", 1))

        book = get_object_or_404(Book, id=book_id)

        item, created = CartItem.objects.get_or_create(cart=cart, book=book)
        item.quantity += quantity
        item.save()

        return Response({"message": "added to cart"})

class OrderListView(generics.ListAPIView):
    """
    List orders belonging to the authenticated user.
    """
    serializer_class = serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Order.objects.filter(buyer=user)

    def list(self, request, *args, **kwargs):
        user = request.user
        cache_key = f"orders:user:{user.id}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, 300)
        return Response(data)


class OrderDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific order belonging to the authenticated user.
    """

    serializer_class = serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Ensure users can only access their own orders.
        """
        return Order.objects.filter(buyer=self.request.user)


# endregion



# region paymentViews


class PaymentRequestAPIView(APIView):
    """
    Initiate a payment request for a product.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Request payment",
        operation_description=(
            "Creates a payment request and returns a payment URL "
            "for the selected product."
        ),
        request_body=serializers.PaymentRequestSerializer
    )
    def post(self, request):
        """
        Create a payment record and return payment URL.
        """
        serializer = serializers.PaymentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data["product"]
        authority_code = uuid.uuid4().hex

        Payment.objects.create(
            user=request.user,
            amount=product.price,
            product=product,
            authority=authority_code
        )

        return Response({
            "payment_url": f"https://fake-gateway/pay/{authority_code}"
        })





class PaymentVerifyAPIView(APIView):
    """
    Verify payment and finalize product delivery.
    """

    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Verify payment",
        operation_description=(
            "Verifies the payment authority code and applies "
            "post-payment actions such as enrollment or stock update."
        )
    )
    def post(self, request):
        """
        Verify payment and update related resources.
        """
        authority = request.data.get("authority")

        try:
            payment = Payment.objects.get(authority=authority, user=request.user)
        except Payment.DoesNotExist:
            return Response({"detail": "Invalid authority."}, status=404)

        payment.status = "success"
        payment.save()

        product = payment.product

        if isinstance(product, Course):
            Enrollment.objects.get_or_create(user=request.user, course=product)

        if isinstance(product, Book):
            product.stock -= 1
            product.save()

            cart_item = CartItem.objects.filter(
                cart__user=request.user,
                book=product
            ).first()
            if cart_item:
                cart_item.delete()

            order = Order.objects.filter(buyer=request.user).first()
            if order:
                order.status = "paid"
                order.save()

        return Response({"detail": "Payment verified successfully."})


# endregion



# region ReportingViews - AdminAccess

class UserStatsAPIView(APIView):
    """
    Provide basic statistics about users.

    Returns total, active, and inactive user counts.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="User statistics",
        operation_description="Retrieve total, active, and inactive user counts."
    )
    def get(self, request):
        cache_key = "report:user_stats"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        total = User.objects.count()
        active = User.objects.filter(is_active=True).count()
        data = {
            "total_users": total,
            "active_users": active,
            "inactive_users": total - active,
        }
        cache.set(cache_key, data, 60)
        return Response(data)


class SalesReportAPIView(APIView):
    """
    Generate income reports for courses and books.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Sales report",
        operation_description="Return total income for courses, books, and overall."
    )
    def get(self, request):
        cache_key = "report:sales_summary"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        course_income = Payment.objects.filter(
            status="success",
            content_type=ContentType.objects.get_for_model(Course)
        ).aggregate(total=Sum("amount"))["total"] or 0

        book_income = Payment.objects.filter(
            status="success",
            content_type=ContentType.objects.get_for_model(Book)
        ).aggregate(total=Sum("amount"))["total"] or 0

        total_income = Payment.objects.filter(
            status="success"
        ).aggregate(total=Sum("amount"))["total"] or 0

        data = {
            "course_income": course_income,
            "book_income": book_income,
            "total_income": total_income,
        }
        cache.set(cache_key, data, 300)
        return Response(data)


class ProductSalesCountAPIView(APIView):
    """
    Provide sales count for courses and books.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Product sales count",
        operation_description="Return number of enrollments and book sales."
    )
    def get(self, request):
        cache_key = "report:product_sales_count"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        course_sales = list(
            Enrollment.objects.values(
                "course__id",
                "course__name"
            ).annotate(total_students=Count("user"))
        )

        book_sales = list(
            OrderItem.objects
            .filter(order__status="paid", book__isnull=False)
            .values("book__name")
            .annotate(count=Count("id"))
        )

        data = {
            "course_sales": course_sales,
            "book_sales": book_sales,
        }
        cache.set(cache_key, data, 300)
        return Response(data)


class OrderStatusReportAPIView(APIView):
    """
    Provide order counts grouped by status.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Order status report",
        operation_description="Return count of orders grouped by status."
    )
    def get(self, request):
        cache_key = "report:order_status"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        data = list(
            Order.objects.values("status").annotate(count=Count("id"))
        )
        cache.set(cache_key, data, 120)
        return Response(data)


class SalesChartAPIView(APIView):
    """
    Provide daily and monthly sales statistics.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Sales chart data",
        operation_description="Return daily and monthly aggregated sales data."
    )
    def get(self, request):
        cache_key = "report:sales_chart"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        daily = list(
            Payment.objects.filter(status="success")
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        )

        monthly = list(
            Payment.objects.filter(status="success")
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        data = {
            "daily": daily,
            "monthly": monthly,
        }
        cache.set(cache_key, data, 600)
        return Response(data)


class TopTeachersAPIView(APIView):
    """
    Return top teachers ranked by income.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Top teachers",
        operation_description="Return top teachers based on total course income."
    )
    def get(self, request):
        cache_key = "report:top_teachers"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        course_type = ContentType.objects.get_for_model(Course)

        data = list(
            Payment.objects.filter(
                status="success",
                content_type=course_type
            )
            .values("product__teacher__user__username")
            .annotate(total_income=Sum("amount"))
            .order_by("-total_income")[:10]
        )

        cache.set(cache_key, data, 600)
        return Response(data)


class NewUsersLast30DaysAPIView(APIView):
    """
    Return number of users registered in the last 30 days.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        cache_key = "report:new_users_last_30_days"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        last_30_days = timezone.now() - datetime.timedelta(days=30)
        count = User.objects.filter(
            date_joined__gte=last_30_days
        ).count()
        data = {"new_users_last_30_days": count}

        cache.set(cache_key, data, 300)
        return Response(data)


class AveragePaymentTimeAPIView(APIView):
    """
    Calculate average time between cart creation and payment.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        cache_key = "report:avg_payment_time"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        payments = Payment.objects.filter(status="success")
        durations = []

        for payment in payments:
            try:
                cart_item = Cart.objects.get(
                    user=payment.user
                ).items.get(book=payment.product)
                delta = payment.created_at - cart_item.created_at
                durations.append(delta.total_seconds())
            except Exception:
                continue

        avg_seconds = sum(durations) / len(durations) if durations else 0
        data = {"average_payment_time_seconds": avg_seconds}

        cache.set(cache_key, data, 600)
        return Response(data)


class DailyActiveUsersAPIView(APIView):
    """
    Return daily active users count.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        cache_key = "report:dau"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        today = timezone.now().date()
        dau = User.objects.filter(last_login__date=today).count()
        data = {"daily_active_users": dau}

        cache.set(cache_key, data, 60)
        return Response(data)


class AverageOrderValueAPIView(APIView):
    """
    Trigger asynchronous calculation of average order value.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        task = avg_order_task.apply_async()
        return Response({"task_id": task.id})


class AvgOrderResultAPIView(APIView):
    """
    Retrieve result of average order value calculation.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request, task_id):
        result = avg_order_task.AsyncResult(task_id)

        if not result.ready():
            return Response({"status": result.status})

        return Response({"average_order_value": result.get()})


class HighSpenderEmailsExcelAPIView(APIView):
    """
    Generate Excel file for high-spending users.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        threshold = float(request.query_params.get("threshold", 100000))
        task = excel_task.apply_async(args=[threshold])
        return Response({"task_id": task.id})


class DownloadHighSpendersExcel(APIView):
    """
    Download generated Excel file for high spenders.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request, task_id):
        result = excel_task.AsyncResult(task_id)

        if not result.ready():
            return Response({"status": result.status})

        file_path = result.get()
        with open(file_path, "rb") as f:
            response = HttpResponse(
                f.read(),
                content_type=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )
            response["Content-Disposition"] = (
                'attachment; filename="high_spenders.xlsx"'
            )
            return response


class AdminAuditLogView(generics.ListAPIView):
    """
    List admin audit logs.

    Useful for tracking administrative actions.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = serializers.AuditLogSerializer

    def get_queryset(self):
        return LogEntry.objects.select_related("user", "content_type")


# endregion



# region shortLink



class CreateShortLinkAPIView(APIView):
    """
    Create a new short link for a given target object.
    """

    @swagger_auto_schema(
        operation_summary="Create short link",
        operation_description="Generate a short URL for a given target object.",
        request_body=serializers.ShortLinkCreateSerializer,
        responses={201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "short_url": openapi.Schema(type=openapi.TYPE_STRING)
            }
        )}
    )
    def post(self, request):
        """
        Validate input data and return generated short URL.
        """
        serializer = serializers.ShortLinkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        short_link = serializer.save()
        short_url = request.build_absolute_uri(f"/s/{short_link.code}")

        return Response({"short_url": short_url})



class ShortLinkStatsAPIView(APIView):
    """
    Retrieve statistics for a short link.
    """

    @swagger_auto_schema(
        operation_summary="Short link statistics",
        operation_description="Return click count and target object info."
    )
    def get(self, request, code):
        cache_key = f"shortlink_stats_{code}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        link = get_object_or_404(ShortLink, code=code)
        data = {
            "code": code,
            "clicks": link.clicks,
            "model": link.content_type.model,
            "object_id": link.object_id,
        }
        cache.set(cache_key, data, 30)
        return Response(data)





def shortlink_redirect(request, code):
    """
    Redirect user to target object URL and increment click count asynchronously.
    """
    link = get_object_or_404(ShortLink, code=code)
    click_plus_task.apply_async(args=[link.id])
    return redirect(link.target_object.get_absolute_url())


# endregion



# region SendEmailToAll


class SendMassEmailAPIView(APIView):
    """
    Send an email to all users asynchronously.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    @swagger_auto_schema(
        operation_summary="Send mass email",
        operation_description="Send email to all users using background task.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["subject", "message"],
            properties={
                "subject": openapi.Schema(type=openapi.TYPE_STRING),
                "message": openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )
    def post(self, request):
        """
        Trigger background task for mass email sending.
        """
        subject = request.data.get("subject")
        message = request.data.get("message")

        if not subject or not message:
            return Response(
                {"error": "Subject and message are required"},
                status=400
            )

        task = send_mass_email_task.apply_async(args=[subject, message])
        return Response({"task_id": task.id})


class MassEmailStatusAPIView(APIView):
    """
    Retrieve status of mass email background task.
    """

    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request, task_id):
        """
        Return Celery task execution status.
        """
        result = AsyncResult(task_id)
        return Response({
            "status": result.status,
            "info": result.info
        })



# endregion





# region decorate-token


class DecoratedTokenObtainPairView(TokenObtainPairView):
    """
    JWT token obtain view with documented response schema.
    """

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: serializers.TokenObtainPairResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        """
        Obtain JWT access and refresh tokens.
        """
        return super().post(request, *args, **kwargs)


class DecoratedTokenRefreshView(TokenRefreshView):
    """
    JWT token refresh view with documented response schema.
    """

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: serializers.TokenRefreshResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        """
        Refresh JWT access token.
        """
        return super().post(request, *args, **kwargs)

    
class DecoratedTokenVerifyView(TokenVerifyView):
    """
    JWT token verification view.
    """

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: serializers.TokenVerifyResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        """
        Verify JWT token validity.
        """
        return super().post(request, *args, **kwargs)


class DecoratedTokenBlacklistView(TokenBlacklistView):
    """
    JWT token blacklist view.
    """

    @swagger_auto_schema(
        responses={status.HTTP_200_OK: serializers.TokenBlacklistResponseSerializer}
    )
    def post(self, request, *args, **kwargs):
        """
        Blacklist a refresh token.
        """
        return super().post(request, *args, **kwargs)

    

# endregion



