from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('sources/', views.sources, name='sources'),
    path('sources/new/', views.new_source, name='add_source'),
    path('sources/edit/<uuid:source_id>/', views.edit_source, name='edit_source'),
    path('sources/edit/<uuid:source_id>/add_app/', views.source_add_app, name='source_add_app'),
    path('sources/edit/<uuid:source_id>/feature/<uuid:app_id>/', views.source_feature_app, name='source_feature_app'),
    path('sources/edit/<uuid:source_id>/unfeature/<uuid:app_id>/', views.source_unfeature_app, name='source_unfeature_app'),
    path('sources/edit/<uuid:source_id>/remove_app/<uuid:app_id>/', views.source_remove_app, name='source_remove_app'),
    path('sources/edit/<uuid:source_id>/delete/', views.delete_source, name='delete_source'),
    path('app/', views.apps, name='apps'),
    path('app/<uuid:app_id>/', views.edit_app, name='edit_app'),
    path('app/<uuid:app_id>/delete/', views.delete_app, name='delete_app'),
    path('app_version/<uuid:version_id>/', views.edit_app_version, name='edit_app_version'),
    path('utils/process_adp/', views.process_adp, name='process_adp'),
    path('utils/process_adp/<task_id>/', views.process_adp_task, name='process_adp_task'),
    path('utils/register_developer/', views.register_developer, name='register_developer'),
]