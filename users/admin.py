from django.contrib import admin
from .models import Profile, LoginRole, SiteSettings

admin.site.register(Profile)
admin.site.register(LoginRole)
admin.site.register(SiteSettings)