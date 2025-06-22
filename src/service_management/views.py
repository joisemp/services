from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from core.models import Organisation, UserProfile

# Helper to check if user is a central admin
def is_central_admin(user):
    return hasattr(user, 'profile') and user.profile.user_type == 'central_admin'

@login_required
@user_passes_test(is_central_admin)
def people_list(request):
    # Get the organisation(s) managed by this central admin
    orgs = Organisation.objects.filter(central_admins=request.user)
    # Get all people in these organisations
    people = UserProfile.objects.filter(org__in=orgs)
    return render(request, 'service_management/people_list.html', {'people': people})

# Create your views here.
