from django.contrib import admin
from . import models


class AppVersionInline(admin.StackedInline):
    model = models.AppVersion
    extra = 0
    readonly_fields = ('id',)

@admin.register(models.App)
class AppAdmin(admin.ModelAdmin):
    inlines = [
        AppVersionInline
    ]
    readonly_fields = ('id',)
