"""BrandShield AI Impersonation Campaign Graph Configuration.

Defines qualifying indicator types, generic domain exclusions, and ethical disclaimer templates.
All graph relationships represent POTENTIAL COORDINATION only; they never prove common ownership.
"""

from typing import Set

# Qualifying indicator types
INDICATOR_EXACT_DOMAIN = "exact_normalized_domain"
INDICATOR_PUBLISHER_ID = "publisher_id"
INDICATOR_PERCEPTUAL_HASH = "perceptual_hash"
INDICATOR_CONTACT_EMAIL = "contact_email"
INDICATOR_CONTACT_PHONE = "contact_phone"

QUALIFYING_INDICATOR_TYPES = [
    INDICATOR_EXACT_DOMAIN,
    INDICATOR_PUBLISHER_ID,
    INDICATOR_PERCEPTUAL_HASH,
    INDICATOR_CONTACT_EMAIL,
    INDICATOR_CONTACT_PHONE,
]

# Generic domain exclusion list:
# Common hosting providers, URL shorteners, link aggregators, and public services
# that must NEVER be used to link two candidates together into a campaign group.
GENERIC_EXCLUDED_DOMAINS: Set[str] = {
    # Synthetic dataset test generic domains
    "linkhub.example",
    "shortn.example",
    "sites-free.example",
    # Link shorteners & aggregators
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "goo.gl",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "linktr.ee",
    "bio.link",
    "carrd.co",
    # Free web hosts & cloud app platforms
    "github.io",
    "vercel.app",
    "webflow.io",
    "firebaseapp.com",
    "herokuapp.com",
    "netlify.app",
    "pages.dev",
    "blogspot.com",
    "wordpress.com",
    "wixsite.com",
    "weebly.com",
    # Major public platforms & app stores
    "google.com",
    "apple.com",
    "apps.apple.com",
    "play.google.com",
    "bsky.app",
    "twitter.com",
    "x.com",
    "instagram.com",
    "facebook.com",
    "linkedin.com",
    "t.me",
    "telegram.me",
    "whatsapp.com",
    "medium.com",
}

CAMPAIGN_DISCLAIMER = (
    "Campaign groupings are derived strictly from concrete shared indicators "
    "(such as exact domains, contact details, or publisher IDs). Groups represent "
    "POTENTIAL_COORDINATION only and do not assert confirmed common ownership or criminal coordination."
)
