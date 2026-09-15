#!/usr/bin/env python3
"""Luqi AI v24 -- Branding & Corporate Identity Module

Central branding management for Luqi AI and parent company
Limitless Telecoms. Provides brand assets, colors, company info,
and logo URLs for consistent branding across the platform.

Usage:
    from backend.branding import branding, CompanyInfo, BrandColors
    logo_url = branding.logo_url
    info = branding.company_info.to_dict()
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict, List

logger = logging.getLogger("luqi.branding")


@dataclass
class BrandColors:
    """Luqi AI and Limitless Telecoms brand color palette."""

    # Primary — Luqi AI
    primary: str = "#2D7D46"
    primary_light: str = "#4CAF7A"
    primary_dark: str = "#1B5E2E"

    # Secondary — Limitless Telecoms
    secondary: str = "#5BA8E6"
    secondary_light: str = "#8EC8F0"
    secondary_dark: str = "#3A7BBF"

    # Accent
    accent: str = "#F5A623"
    accent_light: str = "#F7C162"

    # Backgrounds
    bg_main: str = "#F7F9F4"
    bg_card: str = "#FFFFFF"
    bg_dark: str = "#1A1F1C"

    # Text
    text_primary: str = "#2C3E2D"
    text_secondary: str = "#5A6B5C"
    text_muted: str = "#8A9A8C"

    # Status
    success: str = "#2D7D46"
    info: str = "#5BA8E6"
    warning: str = "#F5A623"
    danger: str = "#E74C3C"

    # Wellness fatigue colors
    fatigue_fresh: str = "#2D7D46"
    fatigue_mild: str = "#5BA8E6"
    fatigue_moderate: str = "#F5A623"
    fatigue_high: str = "#E67E22"
    fatigue_critical: str = "#E74C3C"

    # Limitless Telecoms corporate
    lt_primary: str = "#1565C0"
    lt_secondary: str = "#0D47A1"
    lt_accent: str = "#00BCD4"

    def to_css_variables(self) -> str:
        return f""":root {{
  --color-primary: {self.primary};
  --color-primary-light: {self.primary_light};
  --color-primary-dark: {self.primary_dark};
  --color-secondary: {self.secondary};
  --color-bg: {self.bg_main};
  --color-bg-card: {self.bg_card};
  --color-text: {self.text_primary};
  --color-success: {self.success};
  --color-info: {self.info};
  --color-warning: {self.warning};
  --color-danger: {self.danger};
  --color-lt-primary: {self.lt_primary};
  --color-lt-secondary: {self.lt_secondary};
  --color-lt-accent: {self.lt_accent};
}}"""

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class CompanyInfo:
    """Corporate identity information."""

    product_name: str = "Luqi AI"
    product_tagline: str = "World-Class AI for Africa and Beyond"
    product_version: str = "24.3.0"
    product_url: str = "https://luqi-ai.com"
    product_description: str = (
        "A comprehensive AI SaaS platform offering intelligent assistance, "
        "education, workspace collaboration, and digital wellness — "
        "built for Africa and the world."
    )

    parent_company: str = "Limitless Telecoms"
    parent_tagline: str = "Connecting the Future"
    parent_url: str = "https://limitlesstelecoms.com"
    parent_description: str = (
        "Limitless Telecoms is a leading telecommunications company "
        "providing innovative connectivity solutions across Africa. "
        "Through its subsidiary Luqi AI, it delivers cutting-edge "
        "artificial intelligence services to individuals, businesses, "
        "and institutions."
    )
    parent_founded: str = "2020"
    parent_headquarters: str = "Africa"
    parent_industry: str = "Telecommunications & AI Technology"

    powered_by_text: str = "Powered by Limitless Telecoms"
    copyright_text: str = "© 2026 Limitless Telecoms. All rights reserved."
    support_email: str = "support@luqi-ai.com"
    github_url: str = "https://github.com/ttmodupe-hash/omega-super-ai"
    docs_url: str = "https://docs.luqi-ai.com"

    def to_dict(self) -> Dict[str, str]:
        return asdict(self)


@dataclass
class LogoRegistry:
    """All logo variants and their paths."""

    logo_jpeg: str = "/web/icons/luqi-logo.jpeg"
    logo_png: str = "/web/icons/luqi-logo.png"
    favicon_16: str = "/web/icons/favicon-16x16.png"
    favicon_32: str = "/web/icons/favicon-32x32.png"
    icon_48: str = "/web/icons/icon-48x48.png"
    icon_72: str = "/web/icons/icon-72x72.png"
    icon_96: str = "/web/icons/icon-96x96.png"
    icon_128: str = "/web/icons/icon-128x128.png"
    icon_144: str = "/web/icons/icon-144x144.png"
    icon_152: str = "/web/icons/icon-152x152.png"
    icon_192: str = "/web/icons/icon-192x192.png"
    icon_384: str = "/web/icons/icon-384x384.png"
    icon_512: str = "/web/icons/icon-512x512.png"
    apple_touch_icon: str = "/web/icons/apple-touch-icon.png"
    og_image: str = "/web/icons/luqi-logo-og.png"

    def get_manifest_icons(self) -> List[Dict[str, Any]]:
        sizes = [
            (48, self.icon_48), (72, self.icon_72), (96, self.icon_96),
            (128, self.icon_128), (144, self.icon_144), (152, self.icon_152),
            (192, self.icon_192), (384, self.icon_384), (512, self.icon_512),
        ]
        return [
            {"src": path, "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any maskable"}
            for s, path in sizes
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {**asdict(self), "manifest_icons": self.get_manifest_icons()}


class BrandingManager:
    """Central branding management for Luqi AI and Limitless Telecoms."""

    def __init__(self) -> None:
        self.colors = BrandColors()
        self.company_info = CompanyInfo()
        self.logos = LogoRegistry()

    @property
    def logo_url(self) -> str:
        return self.logos.logo_png

    @property
    def parent_company(self) -> str:
        return self.company_info.parent_company

    @property
    def product_name(self) -> str:
        return self.company_info.product_name

    def get_html_header(self) -> str:
        ci = self.company_info
        lr = self.logos
        return f"""<link rel="icon" type="image/png" sizes="16x16" href="{lr.favicon_16}">
<link rel="icon" type="image/png" sizes="32x32" href="{lr.favicon_32}">
<link rel="apple-touch-icon" sizes="180x180" href="{lr.apple_touch_icon}">
<meta property="og:title" content="{ci.product_name} — {ci.product_tagline}">
<meta property="og:description" content="{ci.product_description}">
<meta property="og:image" content="{ci.product_url}{lr.og_image}">
<meta property="og:type" content="website">
<meta name="theme-color" content="{self.colors.primary}">
<meta name="description" content="{ci.product_description}">
<meta name="author" content="{ci.parent_company}">"""

    def get_footer_html(self) -> str:
        ci = self.company_info
        return f"""<footer class="brand-footer">
  <div class="footer-content">
    <div class="footer-brand">
      <img src="{self.logos.logo_png}" alt="{ci.product_name}" class="footer-logo" width="32">
      <span class="product-name">{ci.product_name}</span>
      <span class="version">v{ci.product_version}</span>
    </div>
    <div class="footer-parent">
      <a href="{ci.parent_url}" target="_blank" class="parent-link">{ci.powered_by_text}</a>
    </div>
    <div class="footer-copyright">{ci.copyright_text}</div>
  </div>
</footer>"""

    def get_manifest_json(self) -> Dict[str, Any]:
        ci = self.company_info
        return {
            "name": f"{ci.product_name} — {ci.parent_company}",
            "short_name": ci.product_name,
            "description": ci.product_description,
            "version": ci.product_version,
            "start_url": "/",
            "display": "standalone",
            "background_color": self.colors.bg_main,
            "theme_color": self.colors.primary,
            "icons": self.logos.get_manifest_icons(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company": self.company_info.to_dict(),
            "colors": self.colors.to_dict(),
            "logos": self.logos.to_dict(),
            "logo_url": self.logo_url,
            "primary_color": self.colors.primary,
            "theme_color": self.colors.primary,
        }


branding = BrandingManager()

def get_branding() -> BrandingManager:
    return branding
