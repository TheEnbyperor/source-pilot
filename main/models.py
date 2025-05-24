import uuid
import os.path
from django.db import models
from colorfield.fields import ColorField
import django.core.files.storage

def rename_file(folder):
    def path_and_rename(instance, filename):
        ext = filename.split('.')[-1]
        filename = '{}.{}'.format(uuid.uuid4().hex, ext)
        return os.path.join(folder, filename)
    return path_and_rename

rename_file_icons = rename_file("icons")
rename_file_icons.__qualname__ = "rename_file_icons"
rename_file_headers = rename_file("headers")
rename_file_headers.__qualname__ = "rename_file_headers"
rename_file_screenshots = rename_file("screenshots")
rename_file_screenshots.__qualname__ = "rename_file_screenshots"
rename_file_news = rename_file("news")
rename_file_news.__qualname__ = "rename_file_news"


class Source(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=200, unique=True)
    name = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to=rename_file_icons, storage=django.core.files.storage.storages["sources"], null=True, blank=True)
    header = models.ImageField(upload_to=rename_file_headers, storage=django.core.files.storage.storages["sources"], null=True, blank=True)
    website = models.URLField(blank=True, null=True)
    tint_colour = ColorField(blank=True, null=True)


class App(models.Model):
    APP_CATEGORIES = (
        ("developer", "Developer Utilities"),
        ("entertainment", "Entertainment"),
        ("games", "Games"),
        ("lifestyle", "Lifestyle"),
        ("other", "Other"),
        ("photo-video", "Photo & Video"),
        ("social", "Social Networking"),
        ("utilities", "Utilities"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    bundle_id = models.CharField(max_length=255, unique=True, null=True, db_index=True)
    apple_app_id = models.CharField(max_length=255, unique=True, db_index=True)
    developer_name = models.CharField(max_length=255, blank=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to=rename_file_icons, storage=django.core.files.storage.storages["sources"], null=True, blank=True)
    tint_colour = ColorField(blank=True, null=True)
    category = models.CharField(max_length=255, choices=APP_CATEGORIES, default="other")

    def __str__(self):
        return f"{self.bundle_id} ({self.apple_app_id})"


class AppScreenshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="screenshots")
    image = models.ImageField(upload_to=rename_file_screenshots, storage=django.core.files.storage.storages["sources"], null=True, blank=True)
    iphone = models.BooleanField(default=True, blank=True)
    ipad = models.BooleanField(default=True, blank=True)


class AppVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="versions")
    bundle_version_short_string = models.CharField(max_length=255)
    bundle_version = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    marketing_version = models.CharField(max_length=255, blank=True, null=True)
    date = models.DateField()
    minimum_os_version = models.CharField(max_length=255, blank=True, null=True)
    maximum_os_version = models.CharField(max_length=255, blank=True, null=True)
    public = models.BooleanField(default=False, blank=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Version {self.bundle_version} - {self.app}"


class AppEntitlements(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="entitlements")
    entitlement = models.CharField(max_length=255)

    class Meta:
        unique_together = [('app', 'entitlement')]


class AppPrivacy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="privacy")
    privacy_key = models.CharField(max_length=255)
    usage_description = models.TextField()

    class Meta:
        unique_together = [('app', 'privacy_key')]


class SourceApp(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="apps")
    app = models.ForeignKey(App, on_delete=models.CASCADE, related_name="sources")
    featured = models.BooleanField(default=False, blank=True)


class News(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    caption = models.TextField()
    date = models.DateTimeField()
    tint_colour = ColorField(blank=True, null=True)
    image = models.ImageField(upload_to=rename_file_news, storage=django.core.files.storage.storages["sources"], null=True, blank=True)
    notify = models.BooleanField(default=False, blank=True)
    url = models.URLField(blank=True, null=True)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="news")
    app = models.ForeignKey(App, on_delete=models.SET_NULL, related_name="news", blank=True, null=True)
    public = models.BooleanField(default=False, blank=True)
