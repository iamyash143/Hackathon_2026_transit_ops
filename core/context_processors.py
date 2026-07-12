def user_role(request):
    """Expose the authenticated user's primary group name to all templates."""
    if request.user.is_authenticated:
        group = request.user.groups.first()
        return {'user_role': group.name if group else 'Admin'}
    return {'user_role': None}
