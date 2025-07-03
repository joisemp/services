def is_central_admin(user):
    return hasattr(user, 'profile') and user.profile.user_type == 'central_admin'