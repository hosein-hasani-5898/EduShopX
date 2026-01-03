from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from main.models import ShortLink, Course, Book, OrderItem, VideoCourse, Article, Comment, Order
from django.core.cache import cache


def update_order_total(order):
    """
    Calculate and update the total price of an order 
    based on its items.
    """
    total = sum(item.price * item.quantity for item in order.items.all())
    order.total_price = total
    order.save(update_fields=["total_price"])


@receiver(post_save, sender=OrderItem)
def update_total_on_save(sender, instance, **kwargs):
    """
    Update the order total after saving an OrderItem.
    """
    update_order_total(instance.order)


@receiver(post_delete, sender=OrderItem)
def update_total_on_delete(sender, instance, **kwargs):
    """
    Update the order total after deleting an OrderItem.
    """
    update_order_total(instance.order)


@receiver(post_save, sender=Course)
def create_course_shortlink(sender, instance, created, **kwargs):
    """
    Automatically create a ShortLink for a new Course.
    """
    if created:
        ShortLink.objects.create(
            content_type=ContentType.objects.get_for_model(Course),
            object_id=instance.id
        )


@receiver(post_save, sender=Book)
def create_book_shortlink(sender, instance, created, **kwargs):
    """
    Automatically create a ShortLink for a new Book.
    """
    if created:
        ShortLink.objects.create(
            content_type=ContentType.objects.get_for_model(Book),
            object_id=instance.id
        )


@receiver([post_save, post_delete], sender=Course)
def invalidate_courses_list_cache(sender, instance, **kwargs):
    """
    Invalidate cache for all courses list whenever a course
    is created, updated, or deleted.
    """
    cache.delete("courses:all")


@receiver(m2m_changed, sender=Course.users.through)
def invalidate_student_courses_cache(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate cache for students whenever the many-to-many relation
    between Course and User changes (add/remove students).
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        for user_id in pk_set:
            cache.delete(f"courses:student:{user_id}")


@receiver([post_save, post_delete], sender=VideoCourse)
def invalidate_video_cache(sender, instance, **kwargs):
    course_id = instance.course_id
    users = instance.course.users.all()
    for user in users:
        cache.delete(f"videos:course:{course_id}:user:{user.id}")
    cache.delete(f"videos:course:{course_id}:user:None")


@receiver([post_save, post_delete], sender=Article)
def invalidate_article_cache(sender, instance, **kwargs):
    cache.delete(f"articles:user:{instance.owner_id}")
    cache.delete("articles:published")


@receiver([post_save, post_delete], sender=Comment)
def invalidate_public_comments_cache(sender, instance, **kwargs):
    if instance.public_comment:
        cache.delete("comments:public")



@receiver([post_save, post_delete], sender=Book)
def invalidate_stock_books_cache(sender, instance, **kwargs):
    cache.delete("books:stock")


@receiver([post_save, post_delete], sender=Order)
def invalidate_order_cache(sender, instance, **kwargs):
    cache.delete(f"orders:user:{instance.buyer_id}")

