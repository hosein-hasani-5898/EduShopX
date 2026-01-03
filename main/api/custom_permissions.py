from rest_framework import permissions
from main.models import Blocklist


class IsTeacherUser(permissions.BasePermission):
    """
    Allows access only to authenticated users with role 'TR' (Teacher).
    Object-level permission allows access only if the user owns the teacher instance.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "TR"

    def has_object_permission(self, request, view, obj):
        return obj.teacher.user == request.user


class IsTeacherUserVC(permissions.BasePermission):
    """
    Allows access only to teachers for VideoCourse objects.
    Object-level permission allows access only if the user owns the related course.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "TR"

    def has_object_permission(self, request, view, obj):
        return obj.course.teacher.user == request.user


class IsOwnerArticle(permissions.BasePermission):
    """
    Object-level permission for articles.
    Only the owner of the article can modify it.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class ReadOnly(permissions.BasePermission):
    """
    Grants permission for read-only (GET, HEAD, OPTIONS) requests.
    """
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS


class BlocklistPermission(permissions.BasePermission):
    """
    Denies access for IP addresses present in the blocklist.
    """
    def has_permission(self, request, view):
        ip_addr = request.META['REMOTE_ADDR']
        blocked = Blocklist.objects.filter(ip_addr=ip_addr).exists()
        return not blocked
