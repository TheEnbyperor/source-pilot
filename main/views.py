import niquests
import datetime
import celery.result
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
import django.core.files.storage

from . import forms, tasks, models

session = niquests.Session(happy_eyeballs=True)


def index(request):
    return render(request, "main/index.html", {})


def sources(request):
    return render(request, "main/sources.html", {
        "sources": models.Source.objects.all(),
    })


def new_source(request):
    if request.method == "POST":
        form = forms.SourceForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            tasks.generate_source.delay(form.instance.pk)
            return redirect("edit_source", source_id=form.instance.pk)
    else:
        form = forms.SourceForm()

    return render(request, "main/new_source.html", {
        "form": form,
    })


def edit_source(request, source_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)
    source_url = django.core.files.storage.storages["sources"].url(f"{source_obj.slug}.json")

    if request.method == "POST":
        form = forms.SourceForm(request.POST, request.FILES, instance=source_obj)
        del form.fields["slug"]
        if form.is_valid():
            form.save()
            tasks.generate_source.delay(source_obj.pk)
    else:
        form = forms.SourceForm(instance=source_obj)

    return render(request, "main/edit_source.html", {
        "source": source_obj,
        "source_url": source_url,
        "form": form,
    })


def delete_source(request, source_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)

    if request.method == "POST" and request.POST.get("action") == "delete":
        source_obj.delete()
        return redirect("sources")

    return render(request, "main/delete_source.html", {
        "source": source_obj,
    })


def source_add_app(request, source_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)

    if request.method == "POST":
        app_id = request.POST.get("app_id")
        app_obj = get_object_or_404(models.App, pk=app_id)
        models.SourceApp.objects.update_or_create(
            source=source_obj,
            app=app_obj,
        )
        tasks.generate_source.delay(source_obj.pk)
        return redirect("edit_source", source_id=source_obj.pk)

    apps_objs = models.App.objects.filter(~Q(sources__source=source_obj))

    return render(request, "main/source_add_app.html", {
        "source": source_obj,
        "apps": apps_objs,
    })


def source_feature_app(request, source_id, app_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)
    source_app_obj = get_object_or_404(models.SourceApp, pk=app_id, source=source_obj)

    if request.method != "POST":
        return redirect("edit_source", source_id=source_obj.pk)

    if request.POST.get("action") == "feature":
        source_app_obj.featured = True
        source_app_obj.save()
        tasks.generate_source.delay(source_obj.pk)

    return redirect("edit_source", source_id=source_obj.pk)

def source_unfeature_app(request, source_id, app_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)
    source_app_obj = get_object_or_404(models.SourceApp, pk=app_id, source=source_obj)

    if request.method != "POST":
        return redirect("edit_source", source_id=source_obj.pk)

    if request.POST.get("action") == "unfeature":
        source_app_obj.featured = False
        source_app_obj.save()
        tasks.generate_source.delay(source_obj.pk)

    return redirect("edit_source", source_id=source_obj.pk)


def source_remove_app(request, source_id, app_id):
    source_obj = get_object_or_404(models.Source, pk=source_id)
    source_app_obj = get_object_or_404(models.SourceApp, pk=app_id, source=source_obj)

    if request.method != "POST":
        return redirect("edit_source", source_id=source_obj.pk)

    if request.POST.get("action") == "remove":
        source_app_obj.delete()
        tasks.generate_source.delay(source_obj.pk)

    return redirect("edit_source", source_id=source_obj.pk)


def apps(request):
    return render(request, "main/apps.html", {
        "apps": models.App.objects.all(),
    })


def edit_app(request, app_id):
    app_obj = get_object_or_404(models.App, pk=app_id)

    if request.method == "POST":
        form = forms.AppForm(request.POST, request.FILES, instance=app_obj)
        if form.is_valid():
            form.save()

            if request.POST.get("entitlements"):
                entitlements = json.loads(request.POST["entitlements"])

                app_obj.entitlements.filter(~Q(entitlement__in=entitlements)).delete()
                models.AppEntitlements.objects.bulk_create([models.AppEntitlements(
                    app=app_obj,
                    entitlement=e,
                ) for e in entitlements], ignore_conflicts=True)

            if request.POST.get("privacy"):
                privacy = json.loads(request.POST["privacy"])

                app_obj.privacy.filter(~Q(privacy_key__in=list(privacy.keys()))).delete()
                models.AppPrivacy.objects.bulk_create(
                    [models.AppPrivacy(
                        app=app_obj,
                        privacy_key=k,
                        usage_description=v
                    ) for k, v in privacy.items()],
                    update_conflicts=True,
                    unique_fields=["app", "privacy_key"],
                    update_fields=["usage_description"]
                )

            tasks.update_app.delay(app_obj.pk)
    else:
        form = forms.AppForm(instance=app_obj)

    return render(request, "main/edit_app.html", {
        "app": app_obj,
        "form": form,
    })


def delete_app(request, app_id):
    app_obj = get_object_or_404(models.App, pk=app_id)

    if request.method == "POST" and request.POST.get("action") == "delete":
        for app_source in app_obj.sources.all():
            tasks.generate_source.delay(app_source.source.pk)
        app_obj.delete()
        return redirect("sources")

    return render(request, "main/delete_app.html", {
        "app": app_obj,
    })


def edit_app_version(request, version_id):
    version_obj = get_object_or_404(models.AppVersion, pk=version_id)

    if request.method == "POST":
        form = forms.AppVersionForm(request.POST, instance=version_obj)
        if form.is_valid():
            form.save()
            tasks.update_app.delay(version_obj.app.pk)
            return redirect("edit_app", app_id=version_obj.app.pk)
    else:
        form = forms.AppVersionForm(instance=version_obj)

    return render(request, "main/edit_app_version.html", {
        "app_version": version_obj,
        "form": form,
    })


def process_adp(request):
    if request.method == "POST":
        form = forms.ProcessADPForm(request.POST)
        if form.is_valid():
            r = tasks.process_adp.delay(form.cleaned_data["adp_id"])
            return redirect('process_adp_task', task_id=r.id)
    else:
        form = forms.ProcessADPForm()

    return render(request, "main/process_adp.html", {
        "form": form
    })


def process_adp_task(request, task_id):
    res = celery.result.AsyncResult(task_id)
    if res.state in ("PENDING", "RETRY"):
        return render(request, "main/process_adp_task.html")
    elif res.state in ("FAILURE", "REVOKED"):
        return render(request, "main/process_adp_task_failed.html", {
            "error": "An unknown error occurred",
        })
    else:
        res = tasks.ADPResult(**res.result)
        if res.error:
            return render(request, "main/process_adp_task_failed.html", {
                "error": res.error,
            })

        return redirect('edit_app_version', version_id=res.app_version_id)


def register_developer(request):
    if request.method == "POST":
        form = forms.RegisterDeveloperForm(request.POST)
        if form.is_valid():
            r = session.post("https://api.altstore.io/register", headers={
                "User-Agent": "SourcePilot"
            }, json={
                "developerID": form.cleaned_data["developer_id"],
                "email": form.cleaned_data["email"],
            })
            if r.status_code == 200:
                data = r.json()
                token = data["token"]
                token_expiration = datetime.datetime.fromisoformat(data["expiration"])
                return render(request, "main/register_developer_success.html", {
                    "token": token,
                    "token_expiry": token_expiration,
                })
            elif r.status_code == 400:
                err = r.json()
                form.add_error(None, err["errorMessage"])
            else:
                form.add_error(None, "An unexpected error occurred")
    else:
        form = forms.RegisterDeveloperForm()

    return render(request, "main/register_developer.html", {
        "form": form
    })
