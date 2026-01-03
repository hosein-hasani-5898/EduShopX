from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from main.api import views


router = DefaultRouter()

# ------ Admin Endpoints ------
router.register(r"management/uni/students", views.StudentViewSet, basename="student")
router.register(r"management/uni/teachers", views.TeacherViewSet, basename="teacher")
router.register(r"management/uni/courses", views.CourseAdminUserViewSet, basename="admin-courses")
router.register(r"management/enrollments", views.EnrollmentAdminViewSet, basename="admin-enrollment")
router.register(r"management/articles", views.ArticleAdminViewSet, basename="admin-articles")
router.register(r"management/comments", views.CommentAdminViewSet, basename="admin-comments")
router.register(r"management/books", views.BookAdminViewSet, basename="admin-books")

admin_courses_router = routers.NestedSimpleRouter(router, r"management/uni/courses", lookup="course")
admin_courses_router.register(r"videos", views.AdminVideoCourseViewSet, basename="admin-course-videos")

# ------ Teacher Endpoints ------
router.register(r"teachers/me/courses", views.CourseTeacherUserViewSet, basename="teacher-course")

teacher_courses_router = routers.NestedSimpleRouter(router, r"teachers/me/courses", lookup="course")
teacher_courses_router.register(r"videos", views.TeacherVideoCourseViewSet, basename="teacher-course-videos")

# ------ User Endpoints ------
router.register(r"user/courses", views.CoursesStudentViewSet, basename="user-courses")
router.register(r"store/courses", views.CoursesListViewSet, basename="store-courses")
router.register(r"user/enrollments", views.EnrollmentUserViewSet, basename="user-enrollment")
router.register(r"blog/articles", views.ArticleListViewSet, basename="blog-article")
router.register(r"user/articles", views.ArticleUserViewSet, basename="user-articles")
router.register(r"blog/comments", views.CommentUserViewSet, basename="blog-comments")
router.register(r"store/books", views.BookListViewSet, basename="store-books")

courses_router = routers.NestedSimpleRouter(router, r"store/courses", lookup="course")
courses_router.register(r"videos", views.VideoCourseViewSet, basename="user-course-videos")


app_name = "api"
urlpatterns = [
    path("", include(router.urls)),
    path("", include(teacher_courses_router.urls)),
    path("", include(admin_courses_router.urls)),
    path("", include(courses_router.urls)),

    path('blog/comments/public/', views.CommentUserListView.as_view(), name='public-comments'),
    path("buy/cart/", views.CartView.as_view(), name="cart-detail"),
    path("buy/cart/items/", views.AddToCartView.as_view(), name="cart-items"),
    path("buy/checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("buy/orders/", views.OrderListView.as_view(), name="order-list"),
    path("buy/orders/<int:pk>/", views.OrderDetailView.as_view(), name="order-detail"),
    path("buy/payments/request/", views.PaymentRequestAPIView.as_view(), name="payments-request"),
    path("buy/payments/verify/", views.PaymentVerifyAPIView.as_view(), name="payments-verify"),
    # ------ Admin Endpoints ------
    path("reports/user-stats/", views.UserStatsAPIView.as_view(), name="reports-user-stats"),
    path("reports/sales/", views.SalesReportAPIView.as_view(), name="reports-sales"),
    path("reports/product-sales/", views.ProductSalesCountAPIView.as_view(), name="reports-product-sales"),
    path("reports/order-status/", views.OrderStatusReportAPIView.as_view(), name="reports-order-status"),
    path("reports/chart/", views.SalesChartAPIView.as_view(), name="reports-chart"),
    path("reports/top-teachers/", views.TopTeachersAPIView.as_view(), name="reports-top-teachers"),
    path("reports/new-users-last-30-days/", views.NewUsersLast30DaysAPIView.as_view(), name="new-users-last-30-days"),
    path("reports/avg-payment-time/", views.AveragePaymentTimeAPIView.as_view(), name="avg-payment-time"),
    path("reports/daily-active-users/", views.DailyActiveUsersAPIView.as_view(), name="daily-active-users"),
    path("reports/avg-order-value/", views.AverageOrderValueAPIView.as_view(), name="avg-order-value"),
    path(
        "reports/avg-order-value/result/<str:task_id>/",
        views.AvgOrderResultAPIView.as_view(),
        name="avg-order-value-result"
    ),
    path(
        "reports/high-spender-email-excel/start/",
        views.HighSpenderEmailsExcelAPIView.as_view(),
        name="high_spender_excel_start"
    ),
    path(
        "reports/high-spender-email-excel/download/<str:task_id>/",
        views.DownloadHighSpendersExcel.as_view(),
        name="high_spender_excel_download"
    ),
    path("reports/logs/", views.AdminAuditLogView.as_view(), name="admin-logs"),
    path("management/email/send/", views.SendMassEmailAPIView.as_view(), name="send-mass-email"),
    path("management/email/status/<str:task_id>/", views.MassEmailStatusAPIView.as_view(), name="mass-email-status"),
    # ------ ShortLink Endpoints ------
    path("shortlinks/create/", views.CreateShortLinkAPIView.as_view()),
    path("shortlinks/<code>/stats/", views.ShortLinkStatsAPIView.as_view()),
    path("shortlinks/s/<code>/", views.shortlink_redirect),

]
