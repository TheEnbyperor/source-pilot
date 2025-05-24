import hashlib
import urllib.parse

def gravatar_image(request):
    if request.user.is_authenticated:
        email = request.user.email.lower().encode("utf-8")
        email_hash = hashlib.sha256(email).hexdigest()
    else:
        email_hash = ""

    q = urllib.parse.urlencode({
        "s": "128"
    })
    return {
        "avatar_url": f"https://www.gravatar.com/avatar/{email_hash}?{q}"
    }
