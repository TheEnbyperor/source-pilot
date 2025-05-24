import json
import niquests
import time
import dataclasses
import typing
import zipfile
import tempfile
import django.core.files.storage
from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from . import models

session = niquests.Session(happy_eyeballs=True)
logger = get_task_logger(__name__)

@dataclasses.dataclass
class ADPResult:
    error: typing.Optional[str] = None
    app_version_id: typing.Optional[str] = None

    def to_json(self):
        return dataclasses.asdict(self)

@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=False
)
def process_adp(adp_id: str) -> dict:
    r = session.get(f"https://api.altstore.io/adps/{adp_id}", headers={
        "User-Agent": "SourcePilot"
    })
    if r.status_code == 404:
        r = session.post("https://api.altstore.io/adps", headers={
            "User-Agent": "SourcePilot"
        }, json={
            "adpID": str(adp_id),
        })
        if r.status_code != 202:
            logger.error(f"ADP {adp_id} submission to AltStore failed - {r.status_code} {r.text}")
            return ADPResult(error="AltStore rejected the submission").to_json()
        time.sleep(5)
        r = session.get(f"https://api.altstore.io/adps/{adp_id}", headers={
            "User-Agent": "SourcePilot"
        })

    while True:
        if r.status_code != 200:
            logger.error(f"Querying status of ADP {adp_id} failed - {r.status_code} {r.text}")
            return ADPResult(error="Failed to query ADP information from AltStore").to_json()
        data = r.json()
        if data["status"] == "failure":
            logger.warning(f"Processing ADP {adp_id} failed")
            return ADPResult(error="AltStore was unable to process ADP").to_json()
        elif data["status"] == "success":
            break
        else:
            time.sleep(5)
            r = session.get(f"https://api.altstore.io/adps/{adp_id}", headers={
                "User-Agent": "SourcePilot"
            })

    package_r = session.get(data["downloadURL"], headers={
        "User-Agent": "SourcePilot"
    }, stream=True)
    if not package_r.ok:
        logger.error(f"Downloading ADP {adp_id} failed - {package_r.status_code} {package_r.text}")
        return ADPResult(error="The processed ADP could not be downloaded from AltStore").to_json()

    with tempfile.NamedTemporaryFile(suffix=".zip") as adp_zip_file:
        for chunk in package_r.iter_content(chunk_size=8192):
            adp_zip_file.write(chunk)
        adp_zip_file.flush()
        adp_zip_file.seek(0)
        adp_zip = zipfile.ZipFile(adp_zip_file.name)

        with adp_zip.open("manifest.json") as manifest_f:
            manifest = json.load(manifest_f)
            manifest_version = manifest["manifestSchemaVersion"]
            if manifest_version != "1.0":
                return ADPResult(error=f"ADP manifest version {manifest_version} is not supported").to_json()

            app_obj, _ = models.App.objects.update_or_create(
                bundle_id=manifest["bundleId"],
                defaults={
                    "apple_app_id": manifest["appleItemId"],
                }
            )

            minimum_os_versions = manifest.get("minimumSystemVersions", {})
            maximum_os_versions = manifest.get("maximumSystemVersions", {})

            variant_sizes = [v["variantDetails"]["compressedSize"] for v in manifest.get("variants", [])]

            app_version_obj, created = models.AppVersion.objects.update_or_create(
                app=app_obj,
                bundle_version=manifest["bundleVersion"],
                defaults={
                    "bundle_version_short_string": manifest["shortVersionString"],
                    "minimum_os_version": minimum_os_versions.get("ios") or minimum_os_versions.get("ipados"),
                    "maximum_os_version": maximum_os_versions.get("ios") or maximum_os_versions.get("ipados"),
                    "file_size": max(variant_sizes),
                },
                create_defaults={
                    "date": timezone.now(),
                    "public": False,
                }
            )

            storage = django.core.files.storage.storages["sources"]
            for fn in adp_zip.namelist():
                with adp_zip.open(fn, "r") as sf:
                    df_name = f"adp/{app_version_obj.id}/{fn}"
                    if not storage.exists(df_name):
                        storage.save(df_name, sf)

        update_app.delay(app_version_obj.app.pk)
        return ADPResult(app_version_id=str(app_version_obj.pk)).to_json()


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def generate_source(source_id: str):
    source_obj = models.Source.objects.get(pk=source_id)

    storage = django.core.files.storage.storages["sources"]

    source_json = {
        "name": source_obj.name,
        "subtitle": source_obj.subtitle or None,
        "description": source_obj.description or None,
        "iconURL": source_obj.icon.url if source_obj.icon else None,
        "headerURL": source_obj.header.url if source_obj.header else None,
        "website": source_obj.website or None,
        "tintColor": source_obj.tint_colour or None,
        "featuredApps": [],
        "apps": [],
        "news": []
    }

    for news in source_obj.news.filter(public=True):
        news_json = {
            "title": news.title,
            "identifier": str(news.pk),
            "caption": news.caption,
            "date": news.date.isoformat(),
            "tintColor": news.tint_colour or None,
            "imageURL": news.image.url if news.image else None,
            "notify": news.notify,
            "url": news.url,
            "appID": news.app.bundle_id if news.app else None,
        }
        source_json["news"].append(news_json)

    for app in source_obj.apps.all():
        if app.featured:
            source_json["featuredApps"].append(app.app.bundle_id)

        app_json = {
            "name": app.app.name or "",
            "bundleIdentifier": app.app.bundle_id,
            "marketplaceID": app.app.apple_app_id,
            "developerName": app.app.developer_name,
            "subtitle": app.app.subtitle or None,
            "localizedDescription": app.app.description or "",
            "iconURL": app.app.icon.url if app.app.icon else None,
            "tintColor": app.app.tint_colour or None,
            "category": app.app.category or None,
            "screenshots": {
                "iphone": [],
                "ipad": [],
            },
            "versions": [],
            "appPermissions": {
                "entitlements": [],
                "privacy": {}
            }
        }

        for screenshot in app.app.screenshots.all():
            screenshot_json = {
                "imageURL": screenshot.image.url if screenshot.image else None,
                "width": screenshot.image.width,
                "height": screenshot.image.height,
            }
            if screenshot.iphone:
                app_json["screenshots"]["iphone"].append(screenshot_json)
            if screenshot.ipad:
                app_json["screenshots"]["ipad"].append(screenshot_json)

        for entitlement in app.app.entitlements.all():
            app_json["appPermissions"]["entitlements"].append(entitlement.entitlement)

        for privacy in app.app.privacy.all():
            app_json["appPermissions"]["privacy"][privacy.privacy_key] = privacy.usage_description

        for version in app.app.versions.filter(public=True):
            manifest_name = f"adp/{version.pk}/manifest.json"
            version_json = {
                "version": version.bundle_version_short_string or "",
                "buildVersion": version.bundle_version,
                "marketingVersion": version.marketing_version or None,
                "date": version.date.isoformat(),
                "localizedDescription": version.description or None,
                "minOSVersion": version.minimum_os_version or None,
                "maxOSVersion": version.maximum_os_version or None,
                "downloadURL": storage.url(manifest_name),
                "size": version.file_size,
            }
            app_json["versions"].append(version_json)

        source_json["apps"].append(app_json)

    with storage.open(f"{source_obj.slug}.json", "w") as source_f:
        json.dump(source_json, source_f)


@shared_task(
    autoretry_for=(Exception,), retry_backoff=1, retry_backoff_max=60, max_retries=None, default_retry_delay=3,
    ignore_result=True
)
def update_app(app_id: str):
    app_obj = models.App.objects.get(pk=app_id)
    for app_source in app_obj.sources.all():
        generate_source.delay(app_source.source.pk)
