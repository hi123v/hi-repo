from django.contrib.auth.models import User, Permission

def grant_all_permissions(username):
    user = User.objects.get(username=username)
    permissions = Permission.objects.all()
    for perm in permissions:
        user.user_permissions.add(perm)
    user.save()

if __name__ == "__main__":
    grant_all_permissions('GeorgePatterson12345')