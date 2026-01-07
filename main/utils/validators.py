from django.core.exceptions import ValidationError

def validate_video_size(max_mb):
    """
    Validator to ensure uploaded size video file.
    """
    def validator(value):
        limit = max_mb * 1024 * 1024
        if value.size > limit:
            raise ValidationError(
                f'The video size must be less than {max_mb} MB.'
            )
    return validator
