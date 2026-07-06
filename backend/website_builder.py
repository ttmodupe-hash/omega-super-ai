"""
Luqi AI — Website Builder Module
================================
Template gallery, component library, page assembler, and AI-powered
website generator.  All data is held in memory (dict/list) so the
module is completely self-contained and requires no database.

Typical usage::
    from website_builder import generate_ai_website, list_templates
    site = generate_ai_website("A modern SaaS landing page with pricing")
"""

from __future__ import annotations

import json
import re
import textwrap
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# 1. Template Gallery — 15 templates
# ---------------------------------------------------------------------------

_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "landing-page",
        "name": "Landing Page",
        "category": "marketing",
        "description": "High-conversion single-page layout with hero, features, social proof, and CTA sections.",
        "preview_image_url": "/static/templates/landing-page.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{title}}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>{{custom_css}}</style>
</head>
<body class="font-sans antialiased">
  <header>{{navbar}}</header>
  <main>
    <section id="hero">{{hero}}</section>
    <section id="features">{{features}}</section>
    <section id="testimonials">{{testimonials}}</section>
    <section id="pricing">{{pricing}}</section>
    <section id="cta">{{cta}}</section>
  </main>
  <footer>{{footer}}</footer>
  <script>{{custom_js}}</script>
</body>
</html>""",
        "default_colors": {"primary": "#4F46E5", "secondary": "#10B981", "accent": "#F59E0B", "bg": "#FFFFFF", "text": "#111827"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "portfolio",
        "name": "Portfolio",
        "category": "creative",
        "description": "Showcase your work with project galleries, case studies, and an about section.",
        "preview_image_url": "/static/templates/portfolio.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-gray-50 font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="gallery">{{gallery}}</section>
  <section id="about">{{about}}</section>
  <section id="contact">{{contact_form}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#000000", "secondary": "#666666", "accent": "#FF3366", "bg": "#FAFAFA", "text": "#1A1A1A"},
        "default_fonts": {"heading": "Playfair Display", "body": "Inter"},
    },
    {
        "id": "saas",
        "name": "SaaS",
        "category": "product",
        "description": "Software-as-a-Service layout with feature grid, pricing tiers, integrations, and signup CTAs.",
        "preview_image_url": "/static/templates/saas.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="features">{{features}}</section>
  <section id="pricing">{{pricing}}</section>
  <section id="integrations">{{integrations}}</section>
  <section id="faq">{{faq}}</section>
  <section id="cta">{{cta}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#6366F1", "secondary": "#8B5CF6", "accent": "#EC4899", "bg": "#FFFFFF", "text": "#0F172A"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "ecommerce",
        "name": "E-Commerce",
        "category": "retail",
        "description": "Product listings, shopping cart layout, category navigation, and promotional banners.",
        "preview_image_url": "/static/templates/ecommerce.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-gray-50 font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="products">{{product_grid}}</section>
  <section id="features">{{features}}</section>
  <section id="testimonials">{{testimonials}}</section>
  <section id="newsletter">{{newsletter}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#0EA5E9", "secondary": "#F97316", "accent": "#EF4444", "bg": "#F8FAFC", "text": "#0F172A"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "blog",
        "name": "Blog",
        "category": "content",
        "description": "Content-focused layout with article cards, sidebar, author bio, and newsletter signup.",
        "preview_image_url": "/static/templates/blog.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-serif">
<header>{{navbar}}</header>
<main class="max-w-7xl mx-auto px-4 py-12 grid grid-cols-1 lg:grid-cols-3 gap-12">
  <section id="articles" class="lg:col-span-2">{{article_list}}</section>
  <aside id="sidebar">{{sidebar}}</aside>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#1E293B", "secondary": "#64748B", "accent": "#D946EF", "bg": "#FFFFFF", "text": "#1E293B"},
        "default_fonts": {"heading": "Merriweather", "body": "Merriweather"},
    },
    {
        "id": "dashboard",
        "name": "Dashboard",
        "category": "app",
        "description": "Admin panel with sidebar navigation, stat cards, data tables, and chart placeholders.",
        "preview_image_url": "/static/templates/dashboard.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-gray-100 font-sans">
<div class="flex h-screen">
  <aside id="sidebar">{{sidebar_nav}}</aside>
  <main class="flex-1 overflow-y-auto p-8">
    <section id="stats">{{stats_row}}</section>
    <section id="charts" class="mt-8">{{charts}}</section>
    <section id="tables" class="mt-8">{{data_table}}</section>
  </main>
</div>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#3B82F6", "secondary": "#10B981", "accent": "#F59E0B", "bg": "#F3F4F6", "text": "#111827"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "agency",
        "name": "Agency",
        "category": "business",
        "description": "Creative agency site with services, team showcase, client logos, and case studies.",
        "preview_image_url": "/static/templates/agency.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="clients">{{logo_cloud}}</section>
  <section id="services">{{services}}</section>
  <section id="work">{{portfolio_grid}}</section>
  <section id="team">{{team}}</section>
  <section id="cta">{{cta}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#0F172A", "secondary": "#475569", "accent": "#F59E0B", "bg": "#FFFFFF", "text": "#0F172A"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "restaurant",
        "name": "Restaurant",
        "category": "hospitality",
        "description": "Restaurant website with menu display, reservation form, gallery, and location map.",
        "preview_image_url": "/static/templates/restaurant.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-stone-50 font-serif">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="menu">{{menu}}</section>
  <section id="gallery">{{gallery}}</section>
  <section id="reservation">{{contact_form}}</section>
  <section id="location">{{map}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#92400E", "secondary": "#A8A29E", "accent": "#DC2626", "bg": "#FAF7F2", "text": "#292524"},
        "default_fonts": {"heading": "Playfair Display", "body": "Inter"},
    },
    {
        "id": "fitness",
        "name": "Fitness",
        "category": "health",
        "description": "Gym and fitness site with class schedules, trainer profiles, BMI calculator, and membership pricing.",
        "preview_image_url": "/static/templates/fitness.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-black text-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="classes">{{schedule}}</section>
  <section id="trainers">{{team}}</section>
  <section id="pricing">{{pricing}}</section>
  <section id="cta">{{cta}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#EF4444", "secondary": "#22C55E", "accent": "#FACC15", "bg": "#000000", "text": "#FFFFFF"},
        "default_fonts": {"heading": "Oswald", "body": "Inter"},
    },
    {
        "id": "education",
        "name": "Education",
        "category": "learning",
        "description": "Online learning platform with course cards, instructor profiles, and curriculum timeline.",
        "preview_image_url": "/static/templates/education.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="courses">{{course_grid}}</section>
  <section id="features">{{features}}</section>
  <section id="instructors">{{team}}</section>
  <section id="testimonials">{{testimonials}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#2563EB", "secondary": "#0891B2", "accent": "#F59E0B", "bg": "#FFFFFF", "text": "#1E3A5F"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "nonprofit",
        "name": "Nonprofit",
        "category": "cause",
        "description": "Charity and nonprofit site with donation CTA, impact stats, volunteer form, and events.",
        "preview_image_url": "/static/templates/nonprofit.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="impact">{{stats}}</section>
  <section id="mission">{{mission}}</section>
  <section id="events">{{events}}</section>
  <section id="donate">{{cta}}</section>
  <section id="volunteer">{{contact_form}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#059669", "secondary": "#0D9488", "accent": "#F59E0B", "bg": "#FFFFFF", "text": "#1C1917"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "event",
        "name": "Event",
        "category": "promotion",
        "description": "Conference or event landing page with schedule, speakers, countdown timer, and ticketing CTA.",
        "preview_image_url": "/static/templates/event.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="countdown">{{countdown}}</section>
  <section id="speakers">{{team}}</section>
  <section id="schedule">{{timeline}}</section>
  <section id="tickets">{{pricing}}</section>
  <section id="cta">{{cta}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#7C3AED", "secondary": "#A78BFA", "accent": "#F43F5E", "bg": "#FFFFFF", "text": "#1E1B4B"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "real-estate",
        "name": "Real Estate",
        "category": "property",
        "description": "Property listing site with search filters, featured listings, agent profiles, and map.",
        "preview_image_url": "/static/templates/real-estate.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-gray-50 font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="search">{{search_bar}}</section>
  <section id="listings">{{property_grid}}</section>
  <section id="features">{{features}}</section>
  <section id="agents">{{team}}</section>
  <section id="contact">{{contact_form}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#0369A1", "secondary": "#0EA5E9", "accent": "#F59E0B", "bg": "#F8FAFC", "text": "#0C4A6E"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "healthcare",
        "name": "Healthcare",
        "category": "medical",
        "description": "Medical practice site with services, doctor profiles, appointment booking, and patient testimonials.",
        "preview_image_url": "/static/templates/healthcare.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="services">{{services}}</section>
  <section id="doctors">{{team}}</section>
  <section id="appointment">{{contact_form}}</section>
  <section id="testimonials">{{testimonials}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#0E7490", "secondary": "#14B8A6", "accent": "#06B6D4", "bg": "#FFFFFF", "text": "#164E63"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
    {
        "id": "startup",
        "name": "Startup",
        "category": "launch",
        "description": "Startup launch page with value prop, traction metrics, team, investor info, and waitlist signup.",
        "preview_image_url": "/static/templates/startup.jpg",
        "html_structure": """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title}}</title><script src="https://cdn.tailwindcss.com"></script><style>{{custom_css}}</style></head>
<body class="bg-white font-sans">
<header>{{navbar}}</header>
<main>
  <section id="hero">{{hero}}</section>
  <section id="traction">{{stats}}</section>
  <section id="solution">{{features}}</section>
  <section id="team">{{team}}</section>
  <section id="waitlist">{{newsletter}}</section>
</main>
<footer>{{footer}}</footer>
<script>{{custom_js}}</script></body></html>""",
        "default_colors": {"primary": "#4338CA", "secondary": "#6366F1", "accent": "#F43F5E", "bg": "#FFFFFF", "text": "#1E1B4B"},
        "default_fonts": {"heading": "Inter", "body": "Inter"},
    },
]

# Index for O(1) lookup
_TEMPLATE_INDEX: dict[str, dict[str, Any]] = {t["id"]: t for t in _TEMPLATES}


# ---------------------------------------------------------------------------
# 2. Component Library — 25 components
# ---------------------------------------------------------------------------

_COMPONENTS: list[dict[str, Any]] = [
    {
        "id": "hero",
        "name": "Hero Section",
        "category": "layout",
        "html_template": """
<div class="relative overflow-hidden bg-gradient-to-br from-[primary] to-[secondary] text-white py-24 lg:py-32">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <h1 class="text-4xl md:text-6xl font-bold tracking-tight mb-6">{{headline}}</h1>
    <p class="text-lg md:text-xl opacity-90 max-w-2xl mx-auto mb-8">{{subheadline}}</p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <a href="{{cta_primary_url}}" class="px-8 py-3 rounded-lg bg-[accent] text-white font-semibold hover:opacity-90 transition">{{cta_primary_text}}</a>
      <a href="{{cta_secondary_url}}" class="px-8 py-3 rounded-lg border border-white/30 text-white font-semibold hover:bg-white/10 transition">{{cta_secondary_text}}</a>
    </div>
  </div>
</div>""",
        "css_styles": ".hero-gradient { background: linear-gradient(135deg, var(--primary), var(--secondary)); }",
        "js_behavior": "",
    },
    {
        "id": "navbar",
        "name": "Navigation Bar",
        "category": "layout",
        "html_template": """
<nav class="bg-white/90 backdrop-blur border-b border-gray-200 sticky top-0 z-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between items-center h-16">
      <a href="/" class="text-xl font-bold text-[primary]">{{brand_name}}</a>
      <div class="hidden md:flex space-x-8">
        {{#nav_items}}<a href="{{url}}" class="text-gray-700 hover:text-[primary] transition">{{label}}</a>{{/nav_items}}
      </div>
      <button class="md:hidden" onclick="document.getElementById('mobile-menu').classList.toggle('hidden')">☰</button>
    </div>
  </div>
  <div id="mobile-menu" class="hidden md:hidden bg-white border-t px-4 py-2">
    {{#nav_items}}<a href="{{url}}" class="block py-2 text-gray-700 hover:text-[primary]">{{label}}</a>{{/nav_items}}
  </div>
</nav>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "footer",
        "name": "Footer",
        "category": "layout",
        "html_template": """
<footer class="bg-[text] text-white py-12">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 md:grid-cols-4 gap-8">
    <div>
      <h3 class="text-lg font-semibold mb-4">{{brand_name}}</h3>
      <p class="text-gray-400 text-sm">{{brand_description}}</p>
    </div>
    {{#columns}}
    <div>
      <h4 class="font-semibold mb-4">{{title}}</h4>
      <ul class="space-y-2 text-sm text-gray-400">{{#links}}<li><a href="{{url}}" class="hover:text-white">{{label}}</a></li>{{/links}}</ul>
    </div>
    {{/columns}}
  </div>
  <div class="max-w-7xl mx-auto px-4 mt-8 pt-8 border-t border-gray-700 text-center text-sm text-gray-400">
    © {{year}} {{brand_name}}. All rights reserved.
  </div>
</footer>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "features-grid",
        "name": "Features Grid",
        "category": "content",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="text-center mb-16">
      <h2 class="text-3xl font-bold text-[text]">{{title}}</h2>
      <p class="mt-4 text-gray-600">{{subtitle}}</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {{#features}}
      <div class="p-6 rounded-xl border border-gray-100 hover:shadow-lg transition">
        <div class="w-12 h-12 rounded-lg bg-[primary]/10 text-[primary] flex items-center justify-center text-2xl mb-4">{{icon}}</div>
        <h3 class="text-lg font-semibold text-[text] mb-2">{{title}}</h3>
        <p class="text-gray-600 text-sm">{{description}}</p>
      </div>
      {{/features}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "pricing-table",
        "name": "Pricing Table",
        "category": "content",
        "html_template": """
<section class="py-20 bg-gray-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="text-center mb-16">
      <h2 class="text-3xl font-bold text-[text]">{{title}}</h2>
      <p class="mt-4 text-gray-600">{{subtitle}}</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
      {{#plans}}
      <div class="rounded-2xl {{#highlighted}}bg-[primary] text-white{{/highlighted}}{{^highlighted}}bg-white text-[text]{{/highlighted}} p-8 shadow-sm {{#highlighted}}ring-2 ring-[primary]{{/highlighted}}">
        <h3 class="text-lg font-semibold">{{name}}</h3>
        <div class="mt-4"><span class="text-4xl font-bold">{{price}}</span>{{#period}}<span class="text-sm opacity-70">/{{period}}</span>{{/period}}</div>
        <ul class="mt-6 space-y-3 {{#highlighted}}text-white/90{{/highlighted}}{{^highlighted}}text-gray-600{{/highlighted}} text-sm">
          {{#features}}<li class="flex items-center gap-2">✓ {{.}}</li>{{/features}}
        </ul>
        <a href="{{cta_url}}" class="mt-8 block text-center py-3 rounded-lg font-semibold {{#highlighted}}bg-white text-[primary]{{/highlighted}}{{^highlighted}}bg-[primary] text-white{{/highlighted}} hover:opacity-90 transition">{{cta_text}}</a>
      </div>
      {{/plans}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "testimonial",
        "name": "Testimonials",
        "category": "social",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <h2 class="text-3xl font-bold text-center text-[text] mb-16">{{title}}</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      {{#testimonials}}
      <div class="p-6 rounded-xl bg-gray-50">
        <p class="text-gray-700 italic mb-4">"{{quote}}"</p>
        <div class="flex items-center gap-3">
          <img src="{{avatar}}" alt="{{name}}" class="w-10 h-10 rounded-full">
          <div><p class="font-semibold text-[text] text-sm">{{name}}</p><p class="text-gray-500 text-xs">{{role}}</p></div>
        </div>
      </div>
      {{/testimonials}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "cta",
        "name": "Call to Action",
        "category": "conversion",
        "html_template": """
<section class="py-20 bg-[primary]">
  <div class="max-w-4xl mx-auto px-4 text-center text-white">
    <h2 class="text-3xl md:text-4xl font-bold mb-4">{{headline}}</h2>
    <p class="text-lg opacity-90 mb-8">{{description}}</p>
    <a href="{{cta_url}}" class="inline-block px-8 py-4 rounded-lg bg-[accent] text-white font-semibold hover:opacity-90 transition">{{cta_text}}</a>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "contact-form",
        "name": "Contact Form",
        "category": "form",
        "html_template": """
<section class="py-20 bg-gray-50">
  <div class="max-w-2xl mx-auto px-4">
    <div class="text-center mb-12">
      <h2 class="text-3xl font-bold text-[text]">{{title}}</h2>
      <p class="mt-2 text-gray-600">{{subtitle}}</p>
    </div>
    <form class="space-y-6 bg-white p-8 rounded-2xl shadow-sm">
      {{#fields}}
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{label}}</label>
        {{#is_textarea}}<textarea name="{{name}}" rows="4" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[primary] focus:border-transparent outline-none" placeholder="{{placeholder}}"></textarea>{{/is_textarea}}
        {{^is_textarea}}<input type="{{type}}" name="{{name}}" class="w-full px-4 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[primary] focus:border-transparent outline-none" placeholder="{{placeholder}}">{{/is_textarea}}
      </div>
      {{/fields}}
      <button type="submit" class="w-full py-3 rounded-lg bg-[primary] text-white font-semibold hover:opacity-90 transition">{{submit_text}}</button>
    </form>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "document.querySelector('form').addEventListener('submit', e => { e.preventDefault(); alert('Thank you! We will be in touch soon.'); });",
    },
    {
        "id": "faq",
        "name": "FAQ Accordion",
        "category": "content",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-3xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-center text-[text] mb-12">{{title}}</h2>
    <div class="space-y-4">
      {{#items}}
      <details class="group rounded-lg border border-gray-200 overflow-hidden">
        <summary class="flex justify-between items-center px-6 py-4 cursor-pointer bg-gray-50 hover:bg-gray-100 transition">
          <span class="font-medium text-[text]">{{question}}</span>
          <span class="text-gray-400 group-open:rotate-180 transition">▼</span>
        </summary>
        <div class="px-6 py-4 text-gray-600 text-sm">{{answer}}</div>
      </details>
      {{/items}}
    </div>
  </div>
</section>""",
        "css_styles": "details > summary { list-style: none; } details > summary::-webkit-details-marker { display: none; }",
        "js_behavior": "",
    },
    {
        "id": "team",
        "name": "Team Section",
        "category": "social",
        "html_template": """
<section class="py-20 bg-gray-50">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="text-center mb-16">
      <h2 class="text-3xl font-bold text-[text]">{{title}}</h2>
      <p class="mt-4 text-gray-600">{{subtitle}}</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
      {{#members}}
      <div class="text-center">
        <img src="{{photo}}" alt="{{name}}" class="w-24 h-24 rounded-full mx-auto mb-4 object-cover">
        <h3 class="font-semibold text-[text]">{{name}}</h3>
        <p class="text-sm text-[primary]">{{role}}</p>
        <p class="text-sm text-gray-500 mt-2">{{bio}}</p>
      </div>
      {{/members}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "stats-counter",
        "name": "Stats Counter",
        "category": "content",
        "html_template": """
<section class="py-16 bg-[primary]">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center text-white">
      {{#stats}}
      <div>
        <div class="text-4xl md:text-5xl font-bold" data-count="{{value}}">0</div>
        <div class="mt-2 text-sm opacity-80">{{label}}</div>
      </div>
      {{/stats}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": """
const counters = document.querySelectorAll('[data-count]');
counters.forEach(c => {
  const target = +c.getAttribute('data-count');
  const step = target / 60;
  let current = 0;
  const tick = () => {
    current += step;
    if (current < target) { c.textContent = Math.floor(current); requestAnimationFrame(tick); }
    else { c.textContent = target; }
  };
  tick();
});
""",
    },
    {
        "id": "gallery",
        "name": "Image Gallery",
        "category": "media",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <h2 class="text-3xl font-bold text-center text-[text] mb-12">{{title}}</h2>
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {{#images}}
      <div class="aspect-square rounded-xl overflow-hidden hover:opacity-90 transition">
        <img src="{{src}}" alt="{{alt}}" class="w-full h-full object-cover">
      </div>
      {{/images}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "carousel",
        "name": "Image Carousel",
        "category": "media",
        "html_template": """
<section class="py-20 bg-gray-50">
  <div class="max-w-5xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-center text-[text] mb-12">{{title}}</h2>
    <div class="relative overflow-hidden rounded-2xl" id="carousel-{{id}}">
      <div class="flex transition-transform duration-500" id="carousel-track-{{id}}">
        {{#slides}}<div class="w-full flex-shrink-0"><img src="{{src}}" alt="{{alt}}" class="w-full h-96 object-cover"></div>{{/slides}}
      </div>
      <button onclick="slideCarousel('{{id}}', -1)" class="absolute left-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/80 hover:bg-white shadow flex items-center justify-center">‹</button>
      <button onclick="slideCarousel('{{id}}', 1)" class="absolute right-4 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/80 hover:bg-white shadow flex items-center justify-center">›</button>
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": """
const carouselState = {};
function slideCarousel(id, dir) {
  const track = document.getElementById('carousel-track-' + id);
  const count = track.children.length;
  carouselState[id] = (carouselState[id] || 0) + dir;
  if (carouselState[id] < 0) carouselState[id] = count - 1;
  if (carouselState[id] >= count) carouselState[id] = 0;
  track.style.transform = 'translateX(-' + (carouselState[id] * 100) + '%)';
}
""",
    },
    {
        "id": "video-embed",
        "name": "Video Embed",
        "category": "media",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-4xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-center text-[text] mb-8">{{title}}</h2>
    <div class="aspect-video rounded-2xl overflow-hidden bg-gray-900 shadow-lg">
      <iframe src="{{video_url}}" class="w-full h-full" frameborder="0" allow="autoplay; encrypted-media" allowfullscreen></iframe>
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "newsletter",
        "name": "Newsletter Signup",
        "category": "conversion",
        "html_template": """
<section class="py-20 bg-[text]">
  <div class="max-w-2xl mx-auto px-4 text-center text-white">
    <h2 class="text-3xl font-bold mb-4">{{title}}</h2>
    <p class="text-gray-300 mb-8">{{subtitle}}</p>
    <form class="flex flex-col sm:flex-row gap-3" onsubmit="event.preventDefault(); alert('Thanks for subscribing!');">
      <input type="email" required placeholder="{{placeholder}}" class="flex-1 px-4 py-3 rounded-lg text-gray-900 outline-none">
      <button type="submit" class="px-6 py-3 rounded-lg bg-[accent] text-white font-semibold hover:opacity-90 transition">{{button_text}}</button>
    </form>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "social-links",
        "name": "Social Links",
        "category": "social",
        "html_template": """
<div class="flex items-center gap-4">
  {{#links}}
  <a href="{{url}}" target="_blank" rel="noopener" class="w-10 h-10 rounded-full bg-gray-100 hover:bg-[primary] hover:text-white flex items-center justify-center transition text-gray-600">
    <span class="text-sm font-bold">{{icon}}</span>
  </a>
  {{/links}}
</div>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "map-embed",
        "name": "Map Embed",
        "category": "media",
        "html_template": """
<div class="aspect-video rounded-xl overflow-hidden shadow-sm">
  <iframe src="https://maps.google.com/maps?q={{lat}},{{lng}}&z=15&output=embed" class="w-full h-full" frameborder="0"></iframe>
</div>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "countdown",
        "name": "Countdown Timer",
        "category": "interactive",
        "html_template": """
<section class="py-16 bg-[primary] text-white">
  <div class="max-w-4xl mx-auto px-4 text-center">
    <h2 class="text-3xl font-bold mb-8">{{title}}</h2>
    <div class="grid grid-cols-4 gap-4 max-w-lg mx-auto" id="countdown-{{id}}">
      <div class="bg-white/10 rounded-lg p-4"><div class="text-3xl font-bold" data-unit="days">00</div><div class="text-xs opacity-70">Days</div></div>
      <div class="bg-white/10 rounded-lg p-4"><div class="text-3xl font-bold" data-unit="hours">00</div><div class="text-xs opacity-70">Hours</div></div>
      <div class="bg-white/10 rounded-lg p-4"><div class="text-3xl font-bold" data-unit="minutes">00</div><div class="text-xs opacity-70">Mins</div></div>
      <div class="bg-white/10 rounded-lg p-4"><div class="text-3xl font-bold" data-unit="seconds">00</div><div class="text-xs opacity-70">Secs</div></div>
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": """
(function(){
  const target = new Date('{{target_date}}').getTime();
  const el = document.getElementById('countdown-{{id}}');
  setInterval(function(){
    const diff = target - Date.now();
    if (diff <= 0) return;
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff % 86400000) / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    el.querySelector('[data-unit=days]').textContent = String(d).padStart(2, '0');
    el.querySelector('[data-unit=hours]').textContent = String(h).padStart(2, '0');
    el.querySelector('[data-unit=minutes]').textContent = String(m).padStart(2, '0');
    el.querySelector('[data-unit=seconds]').textContent = String(s).padStart(2, '0');
  }, 1000);
})();
""",
    },
    {
        "id": "progress-bar",
        "name": "Progress Bar",
        "category": "interactive",
        "html_template": """
<div class="max-w-xl mx-auto px-4 py-4">
  {{#items}}
  <div class="mb-4">
    <div class="flex justify-between mb-1"><span class="text-sm font-medium text-[text]">{{label}}</span><span class="text-sm text-gray-500">{{value}}%</span></div>
    <div class="w-full bg-gray-200 rounded-full h-2.5"><div class="bg-[primary] h-2.5 rounded-full transition-all" style="width: {{value}}%"></div></div>
  </div>
  {{/items}}
</div>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "timeline",
        "name": "Timeline",
        "category": "content",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-3xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-center text-[text] mb-16">{{title}}</h2>
    <div class="relative border-l-2 border-[primary]/30 ml-4 space-y-12">
      {{#events}}
      <div class="relative pl-8">
        <div class="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-[primary] border-4 border-white shadow"></div>
        <div class="text-sm text-[primary] font-semibold">{{date}}</div>
        <h3 class="text-lg font-semibold text-[text] mt-1">{{title}}</h3>
        <p class="text-gray-600 text-sm mt-2">{{description}}</p>
      </div>
      {{/events}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "comparison-table",
        "name": "Comparison Table",
        "category": "content",
        "html_template": """
<section class="py-20 bg-gray-50">
  <div class="max-w-5xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-center text-[text] mb-12">{{title}}</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="border-b-2 border-[primary]">
          <th class="text-left py-3 px-4">Feature</th>
          {{#columns}}<th class="text-center py-3 px-4">{{name}}</th>{{/columns}}
        </tr></thead>
        <tbody>
          {{#rows}}<tr class="border-b border-gray-200">
            <td class="py-3 px-4 font-medium">{{feature}}</td>
            {{#values}}<td class="text-center py-3 px-4 {{#highlighted}}text-[primary] font-bold{{/highlighted}}{{^highlighted}}text-gray-600{{/highlighted}}">{{.}}</td>{{/values}}
          </tr>{{/rows}}
        </tbody>
      </table>
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "changelog",
        "name": "Changelog",
        "category": "content",
        "html_template": """
<section class="py-20 bg-white">
  <div class="max-w-2xl mx-auto px-4">
    <h2 class="text-3xl font-bold text-[text] mb-12">{{title}}</h2>
    <div class="space-y-8">
      {{#versions}}
      <div class="border-l-4 border-[primary] pl-6">
        <div class="flex items-center gap-3 mb-2">
          <span class="text-lg font-semibold text-[text]">{{version}}</span>
          <span class="text-xs text-gray-500">{{date}}</span>
        </div>
        <ul class="space-y-1 text-sm text-gray-600">
          {{#changes}}<li class="flex items-start gap-2"><span class="text-[primary]">•</span> {{.}}</li>{{/changes}}
        </ul>
      </div>
      {{/versions}}
    </div>
  </div>
</section>""",
        "css_styles": "",
        "js_behavior": "",
    },
    {
        "id": "code-block",
        "name": "Code Block",
        "category": "content",
        "html_template": """
<div class="max-w-3xl mx-auto px-4 py-4">
  <div class="bg-[#1E1E1E] rounded-xl overflow-hidden">
    <div class="flex items-center gap-2 px-4 py-2 bg-[#2D2D2D]">
      <div class="w-3 h-3 rounded-full bg-red-500"></div>
      <div class="w-3 h-3 rounded-full bg-yellow-500"></div>
      <div class="w-3 h-3 rounded-full bg-green-500"></div>
      <span class="ml-2 text-xs text-gray-400">{{language}}</span>
    </div>
    <pre class="p-4 text-sm text-gray-300 overflow-x-auto"><code>{{code}}</code></pre>
  </div>
</div>""",
        "css_styles": "pre { scrollbar-width: thin; scrollbar-color: #555 #1E1E1E; }",
        "js_behavior": "",
    },
    {
        "id": "chat-widget",
        "name": "Chat Widget",
        "category": "interactive",
        "html_template": """
<div class="fixed bottom-6 right-6 z-50">
  <div id="chat-box" class="hidden mb-4 w-80 h-96 bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden">
    <div class="px-4 py-3 bg-[primary] text-white font-semibold text-sm flex justify-between items-center">
      <span>{{title}}</span>
      <button onclick="document.getElementById('chat-box').classList.add('hidden')" class="text-white/70 hover:text-white">✕</button>
    </div>
    <div id="chat-messages" class="flex-1 p-4 overflow-y-auto space-y-3 text-sm">
      <div class="bg-gray-100 rounded-lg p-3 max-w-[80%]">{{welcome_message}}</div>
    </div>
    <form class="p-3 border-t flex gap-2" onsubmit="handleChatSubmit(event)">
      <input type="text" id="chat-input" class="flex-1 px-3 py-2 border rounded-lg text-sm outline-none" placeholder="Type a message...">
      <button type="submit" class="px-4 py-2 bg-[primary] text-white rounded-lg text-sm hover:opacity-90">Send</button>
    </form>
  </div>
  <button onclick="document.getElementById('chat-box').classList.toggle('hidden')" class="w-14 h-14 rounded-full bg-[primary] text-white shadow-lg hover:opacity-90 transition flex items-center justify-center text-2xl">💬</button>
</div>""",
        "css_styles": "",
        "js_behavior": """
function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  const container = document.getElementById('chat-messages');
  container.innerHTML += '<div class="bg-[primary] text-white rounded-lg p-3 max-w-[80%] ml-auto">' + msg + '</div>';
  input.value = '';
  container.scrollTop = container.scrollHeight;
  setTimeout(function() {
    container.innerHTML += '<div class="bg-gray-100 rounded-lg p-3 max-w-[80%]">Thanks for your message! Our team will respond shortly.</div>';
    container.scrollTop = container.scrollHeight;
  }, 1000);
}
""",
    },
    {
        "id": "cookie-banner",
        "name": "Cookie Banner",
        "category": "legal",
        "html_template": """
<div id="cookie-banner" class="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg z-50 px-4 py-4">
  <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
    <p class="text-sm text-gray-600">{{message}}</p>
    <div class="flex gap-3">
      <button onclick="document.getElementById('cookie-banner').style.display='none'" class="px-4 py-2 text-sm text-gray-600 hover:text-[text] transition">{{decline_text}}</button>
      <button onclick="document.getElementById('cookie-banner').style.display='none'" class="px-4 py-2 text-sm bg-[primary] text-white rounded-lg hover:opacity-90 transition">{{accept_text}}</button>
    </div>
  </div>
</div>""",
        "css_styles": "",
        "js_behavior": "",
    },
]

_COMPONENT_INDEX: dict[str, dict[str, Any]] = {c["id"]: c for c in _COMPONENTS}


# ---------------------------------------------------------------------------
# 3. Template engine helpers
# ---------------------------------------------------------------------------

def _simple_render(template: str, data: dict[str, Any]) -> str:
    """Minimal Mustache-style renderer (handles {{var}}, {{#list}}…{{/list}}, {{^invert}})."""
    result = template
    for key, val in data.items():
        if isinstance(val, str):
            result = result.replace(f"{{{{{key}}}}}", val)
            result = result.replace(f"{{{{{{{key}}}}}}}", val)
            result = result.replace(f"{{{{{key}}}}}", val)
    for key, val in data.items():
        if isinstance(val, str):
            result = result.replace(f"{{{{{key}}}}}", val)
    for key, val in data.items():
        if isinstance(val, bool):
            tag = f"{{{{#{key}}}}}"
            end = f"{{{{/{key}}}}}"
            inv = f"{{{{^{key}}}}}"
            if tag in result:
                inner = result[result.find(tag) + len(tag):result.find(end)]
                if val:
                    rendered = _simple_render(inner, data)
                    result = result[:result.find(tag)] + rendered + result[result.find(end) + len(end):]
                else:
                    result = result[:result.find(tag)] + result[result.find(end) + len(end):]
            if inv in result:
                inner = result[result.find(inv) + len(inv):result.find(end)]
                if not val:
                    rendered = _simple_render(inner, data)
                    result = result[:result.find(inv)] + rendered + result[result.find(end) + len(end):]
                else:
                    result = result[:result.find(inv)] + result[result.find(end) + len(end):]
        elif isinstance(val, list):
            tag = f"{{{{#{key}}}}}"
            end = f"{{{{/{key}}}}}"
            if tag in result:
                inner = result[result.find(tag) + len(tag):result.find(end)]
                rendered = ""
                for item in val:
                    if isinstance(item, dict):
                        rendered += _simple_render(inner, item)
                    else:
                        rendered += inner.replace("{{{.}}}", str(item)).replace("{{.}}", str(item))
                result = result[:result.find(tag)] + rendered + result[result.find(end) + len(end):]
    return result


def _resolve_color_refs(template: str, colors: dict[str, str]) -> str:
    """Replace [primary], [secondary], [accent], [bg], [text] placeholders."""
    mapping = {
        "[primary]": colors.get("primary", "#4F46E5"),
        "[secondary]": colors.get("secondary", "#10B981"),
        "[accent]": colors.get("accent", "#F59E0B"),
        "[bg]": colors.get("bg", "#FFFFFF"),
        "[text]": colors.get("text", "#111827"),
    }
    for placeholder, value in mapping.items():
        template = template.replace(placeholder, value)
    return template


# ---------------------------------------------------------------------------
# 4. Public API
# ---------------------------------------------------------------------------

def list_templates() -> list[dict[str, Any]]:
    """Return all 15 template summaries (lightweight — no html_structure)."""
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "category": t["category"],
            "description": t["description"],
            "preview_image_url": t["preview_image_url"],
            "default_colors": t["default_colors"],
            "default_fonts": t["default_fonts"],
        }
        for t in _TEMPLATES
    ]


def get_template(template_id: str) -> dict[str, Any]:
    """Fetch a single template by ID."""
    if template_id not in _TEMPLATE_INDEX:
        raise ValueError(f"Template '{template_id}' not found. Available: {list(_TEMPLATE_INDEX.keys())}")
    return dict(_TEMPLATE_INDEX[template_id])


def list_components() -> list[dict[str, Any]]:
    """Return all 25 component summaries (no html_template for brevity)."""
    return [
        {
            "id": c["id"],
            "name": c["name"],
            "category": c["category"],
        }
        for c in _COMPONENTS
    ]


def get_component(component_id: str) -> dict[str, Any]:
    """Fetch a single component by ID."""
    if component_id not in _COMPONENT_INDEX:
        raise ValueError(f"Component '{component_id}' not found. Available: {list(_COMPONENT_INDEX.keys())}")
    return dict(_COMPONENT_INDEX[component_id])


def generate_site(
    description: str,
    template_id: str = "",
    colors: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate a complete website from a description.

    Returns a dict with::
        - html   : full HTML string
        - css    : combined CSS string
        - js     : combined JS string
        - preview_html : same as html (for iframe embedding)
        - files  : list of {path, content} dicts
    """
    if not template_id:
        template_id = _pick_template(description)

    template = get_template(template_id)
    chosen_colors = {**template["default_colors"], **(colors or {})}

    selected_component_ids = _pick_components(description, template_id)

    assembled_components: dict[str, str] = {}
    all_css: list[str] = []
    all_js: list[str] = []

    for cid in selected_component_ids:
        comp = get_component(cid)
        dummy_data = _make_dummy_data(cid, description)
        rendered_html = _simple_render(comp["html_template"], dummy_data)
        rendered_html = _resolve_color_refs(rendered_html, chosen_colors)
        assembled_components[cid] = rendered_html
        if comp["css_styles"]:
            all_css.append(_resolve_color_refs(comp["css_styles"], chosen_colors))
        if comp["js_behavior"]:
            all_js.append(_resolve_color_refs(comp["js_behavior"], chosen_colors))

    html = _assemble_html(template, assembled_components, chosen_colors, all_css, all_js)
    css = "\n\n".join(all_css)
    js = "\n\n".join(all_js)

    return {
        "html": html,
        "css": css,
        "js": js,
        "preview_html": html,
        "files": [
            {"path": "index.html", "content": html},
            {"path": "styles.css", "content": css},
            {"path": "scripts.js", "content": js},
        ],
    }


def build_page(components: list[dict[str, Any]], settings: dict[str, Any]) -> dict[str, Any]:
    """Assemble a page from an ordered list of component configurations.

    Each item in *components* should have at least ``component_id``.
    Optional keys: ``data`` (dict of template vars), ``colors`` (override).

    *settings* may contain ``title``, ``template_id``, ``colors``.
    """
    template_id = settings.get("template_id", "landing-page")
    template = get_template(template_id)
    base_colors = {**template["default_colors"], **settings.get("colors", {})}

    assembled: dict[str, str] = {}
    all_css: list[str] = []
    all_js: list[str] = []

    for cfg in components:
        cid = cfg["component_id"]
        comp = get_component(cid)
        data = cfg.get("data", _make_dummy_data(cid, ""))
        colors = {**base_colors, **cfg.get("colors", {})}
        rendered = _simple_render(comp["html_template"], data)
        rendered = _resolve_color_refs(rendered, colors)
        assembled[cid] = rendered
        if comp["css_styles"]:
            all_css.append(_resolve_color_refs(comp["css_styles"], colors))
        if comp["js_behavior"]:
            all_js.append(_resolve_color_refs(comp["js_behavior"], colors))

    html = _assemble_html(template, assembled, base_colors, all_css, all_js)
    return {
        "html": html,
        "css": "\n\n".join(all_css),
        "js": "\n\n".join(all_js),
        "components_used": [c["component_id"] for c in components],
    }


def generate_ai_website(description: str) -> dict[str, Any]:
    """Build a complete site from a free-text description.

    This is the highest-level API — it picks the best template, selects
    components, generates dummy content themed to the description, and
    returns everything needed to preview or deploy the site.
    """
    return generate_site(description)


# ---------------------------------------------------------------------------
# 5. Internal helpers
# ---------------------------------------------------------------------------

def _pick_template(description: str) -> str:
    """Heuristic template selection based on keyword matching."""
    desc = description.lower()
    keywords: dict[str, list[str]] = {
        "saas": ["saas", "software", "app", "platform", "tool"],
        "ecommerce": ["shop", "store", "product", "cart", "buy", "sell", "ecommerce", "e-commerce"],
        "portfolio": ["portfolio", "gallery", "art", "design", "creative", "showcase"],
        "blog": ["blog", "article", "news", "content", "post", "writing"],
        "dashboard": ["dashboard", "admin", "panel", "analytics", "metrics"],
        "restaurant": ["restaurant", "food", "menu", "cafe", "dining"],
        "fitness": ["gym", "fitness", "workout", "health", "training", "exercise"],
        "education": ["course", "learn", "education", "school", "academy", "tutorial"],
        "nonprofit": ["charity", "nonprofit", "donate", "cause", "volunteer", "foundation"],
        "event": ["event", "conference", "meetup", "webinar", "summit", "festival"],
        "real-estate": ["property", "real estate", "house", "apartment", "rent", "listing"],
        "healthcare": ["health", "medical", "clinic", "doctor", "hospital", "dental"],
        "startup": ["startup", "launch", "venture", "pitch", "seed"],
        "agency": ["agency", "studio", "consulting", "services", "firm"],
    }
    scores: dict[str, int] = {t["id"]: 0 for t in _TEMPLATES}
    for tid, words in keywords.items():
        if any(w in desc for w in words):
            scores[tid] = scores.get(tid, 0) + 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "landing-page"


def _pick_components(description: str, template_id: str) -> list[str]:
    """Select relevant components for a template + description."""
    mapping: dict[str, list[str]] = {
        "landing-page": ["navbar", "hero", "features-grid", "testimonial", "pricing-table", "cta", "footer"],
        "portfolio": ["navbar", "hero", "gallery", "team", "contact-form", "footer"],
        "saas": ["navbar", "hero", "features-grid", "pricing-table", "faq", "cta", "footer"],
        "ecommerce": ["navbar", "hero", "features-grid", "testimonial", "newsletter", "footer"],
        "blog": ["navbar", "hero", "features-grid", "newsletter", "footer"],
        "dashboard": ["stats-counter", "progress-bar", "timeline"],
        "agency": ["navbar", "hero", "features-grid", "team", "testimonial", "cta", "footer"],
        "restaurant": ["navbar", "hero", "gallery", "contact-form", "map-embed", "footer"],
        "fitness": ["navbar", "hero", "features-grid", "pricing-table", "cta", "footer"],
        "education": ["navbar", "hero", "features-grid", "team", "testimonial", "footer"],
        "nonprofit": ["navbar", "hero", "stats-counter", "cta", "contact-form", "footer"],
        "event": ["navbar", "hero", "countdown", "team", "timeline", "pricing-table", "cta", "footer"],
        "real-estate": ["navbar", "hero", "features-grid", "team", "contact-form", "footer"],
        "healthcare": ["navbar", "hero", "features-grid", "team", "contact-form", "testimonial", "footer"],
        "startup": ["navbar", "hero", "stats-counter", "features-grid", "team", "newsletter", "footer"],
    }
    return mapping.get(template_id, ["navbar", "hero", "features-grid", "cta", "footer"])


def _make_dummy_data(component_id: str, description: str) -> dict[str, Any]:
    """Generate context-aware placeholder data for a component."""
    brand = description.split()[0].title() if description else "Luqi"

    defaults: dict[str, dict[str, Any]] = {
        "hero": {
            "headline": f"Welcome to {brand}",
            "subheadline": "We build amazing digital experiences that drive results and delight users.",
            "cta_primary_text": "Get Started",
            "cta_primary_url": "#signup",
            "cta_secondary_text": "Learn More",
            "cta_secondary_url": "#features",
        },
        "navbar": {
            "brand_name": brand,
            "nav_items": [
                {"label": "Home", "url": "/"},
                {"label": "Features", "url": "#features"},
                {"label": "Pricing", "url": "#pricing"},
                {"label": "Contact", "url": "#contact"},
            ],
        },
        "footer": {
            "brand_name": brand,
            "brand_description": f"{brand} is dedicated to building exceptional digital experiences.",
            "year": str(datetime.now().year),
            "columns": [
                {"title": "Product", "links": [{"label": "Features", "url": "#"}, {"label": "Pricing", "url": "#"}, {"label": "Changelog", "url": "#"}]},
                {"title": "Company", "links": [{"label": "About", "url": "#"}, {"label": "Blog", "url": "#"}, {"label": "Careers", "url": "#"}]},
                {"title": "Support", "links": [{"label": "Help Center", "url": "#"}, {"label": "Contact", "url": "#"}, {"label": "Status", "url": "#"}]},
            ],
        },
        "features-grid": {
            "title": "Why Choose Us",
            "subtitle": "Everything you need to succeed, all in one place.",
            "features": [
                {"icon": "⚡", "title": "Lightning Fast", "description": "Optimized performance for the best user experience."},
                {"icon": "🔒", "title": "Secure by Default", "description": "Enterprise-grade security built into every layer."},
                {"icon": "🎨", "title": "Beautiful Design", "description": "Pixel-perfect interfaces crafted with attention to detail."},
                {"icon": "📱", "title": "Fully Responsive", "description": "Looks great on every device, from mobile to desktop."},
                {"icon": "🔧", "title": "Easy Customization", "description": "Tailor everything to match your brand and needs."},
                {"icon": "📊", "title": "Powerful Analytics", "description": "Data-driven insights to help you grow faster."},
            ],
        },
        "pricing-table": {
            "title": "Simple, Transparent Pricing",
            "subtitle": "Choose the plan that works best for you.",
            "plans": [
                {"name": "Starter", "price": "$9", "period": "month", "highlighted": False, "features": ["1 project", "Basic analytics", "Email support"], "cta_text": "Get Started", "cta_url": "#"},
                {"name": "Pro", "price": "$29", "period": "month", "highlighted": True, "features": ["10 projects", "Advanced analytics", "Priority support", "Custom domain"], "cta_text": "Get Started", "cta_url": "#"},
                {"name": "Enterprise", "price": "$99", "period": "month", "highlighted": False, "features": ["Unlimited projects", "Real-time analytics", "Dedicated support", "SSO & SAML"], "cta_text": "Contact Sales", "cta_url": "#"},
            ],
        },
        "testimonial": {
            "title": "What Our Customers Say",
            "testimonials": [
                {"quote": "This platform transformed how we work. Highly recommended!", "name": "Sarah Chen", "role": "CEO, TechStart", "avatar": "https://i.pravatar.cc/150?u=1"},
                {"quote": "The best investment we made this year. Incredible ROI.", "name": "Marcus Johnson", "role": "CTO, DataFlow", "avatar": "https://i.pravatar.cc/150?u=2"},
                {"quote": "Beautiful design and rock-solid performance. Love it.", "name": "Elena Rodriguez", "role": "Designer, CreativeCo", "avatar": "https://i.pravatar.cc/150?u=3"},
            ],
        },
        "cta": {
            "headline": f"Ready to get started with {brand}?",
            "description": "Join thousands of satisfied customers and take your business to the next level.",
            "cta_text": "Start Your Free Trial",
            "cta_url": "#signup",
        },
        "contact-form": {
            "title": "Get in Touch",
            "subtitle": "We would love to hear from you. Send us a message and we will respond promptly.",
            "fields": [
                {"label": "Name", "name": "name", "type": "text", "placeholder": "Your name", "is_textarea": False},
                {"label": "Email", "name": "email", "type": "email", "placeholder": "you@example.com", "is_textarea": False},
                {"label": "Message", "name": "message", "type": "text", "placeholder": "Your message...", "is_textarea": True},
            ],
            "submit_text": "Send Message",
        },
        "faq": {
            "title": "Frequently Asked Questions",
            "items": [
                {"question": "How do I get started?", "answer": "Simply sign up for an account and follow the onboarding wizard. It takes less than 2 minutes."},
                {"question": "Is there a free trial?", "answer": "Yes! Every plan includes a 14-day free trial with no credit card required."},
                {"question": "Can I cancel anytime?", "answer": "Absolutely. You can cancel your subscription at any time with no questions asked."},
                {"question": "Do you offer refunds?", "answer": "We offer a 30-day money-back guarantee on all paid plans."},
            ],
        },
        "team": {
            "title": "Meet the Team",
            "subtitle": "The passionate people behind the product.",
            "members": [
                {"name": "Alex Rivera", "role": "CEO & Founder", "photo": "https://i.pravatar.cc/150?u=4", "bio": "Visionary leader with 15+ years in tech."},
                {"name": "Jordan Lee", "role": "CTO", "photo": "https://i.pravatar.cc/150?u=5", "bio": "Full-stack engineer and systems architect."},
                {"name": "Taylor Kim", "role": "Head of Design", "photo": "https://i.pravatar.cc/150?u=6", "bio": "Award-winning UX designer."},
                {"name": "Morgan Patel", "role": "Lead Developer", "photo": "https://i.pravatar.cc/150?u=7", "bio": "Open source contributor and mentor."},
            ],
        },
        "stats-counter": {
            "stats": [
                {"value": "10000", "label": "Users"},
                {"value": "500", "label": "Projects"},
                {"value": "99.9", "label": "Uptime %"},
                {"value": "24", "label": "Support"},
            ],
        },
        "gallery": {
            "title": "Gallery",
            "images": [
                {"src": "https://picsum.photos/400/400?random=1", "alt": "Work 1"},
                {"src": "https://picsum.photos/400/400?random=2", "alt": "Work 2"},
                {"src": "https://picsum.photos/400/400?random=3", "alt": "Work 3"},
                {"src": "https://picsum.photos/400/400?random=4", "alt": "Work 4"},
            ],
        },
        "carousel": {
            "id": "main",
            "title": "Highlights",
            "slides": [
                {"src": "https://picsum.photos/800/400?random=5", "alt": "Slide 1"},
                {"src": "https://picsum.photos/800/400?random=6", "alt": "Slide 2"},
                {"src": "https://picsum.photos/800/400?random=7", "alt": "Slide 3"},
            ],
        },
        "video-embed": {
            "title": "Watch Our Story",
            "video_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        },
        "newsletter": {
            "title": "Stay in the Loop",
            "subtitle": "Get the latest updates delivered to your inbox.",
            "placeholder": "Enter your email",
            "button_text": "Subscribe",
        },
        "social-links": {
            "links": [
                {"url": "https://twitter.com", "icon": "X"},
                {"url": "https://github.com", "icon": "GH"},
                {"url": "https://linkedin.com", "icon": "LI"},
                {"url": "https://discord.com", "icon": "DC"},
            ],
        },
        "map-embed": {"lat": "40.7128", "lng": "-74.0060"},
        "countdown": {
            "id": "event",
            "title": "Event Starts In",
            "target_date": "2025-12-31T00:00:00",
        },
        "progress-bar": {
            "items": [
                {"label": "Performance", "value": "92"},
                {"label": "Accessibility", "value": "88"},
                {"label": "SEO", "value": "95"},
                {"label": "Best Practices", "value": "90"},
            ],
        },
        "timeline": {
            "title": "Our Journey",
            "events": [
                {"date": "2023", "title": "Founded", "description": "Started with a vision to change the industry."},
                {"date": "2024", "title": "First 1,000 Users", "description": "Reached our first major milestone."},
                {"date": "2025", "title": "Series A", "description": "Secured funding to accelerate growth."},
            ],
        },
        "comparison-table": {
            "title": "Feature Comparison",
            "columns": [{"name": "Basic"}, {"name": "Pro"}, {"name": "Enterprise"}],
            "rows": [
                {"feature": "Storage", "values": ["10 GB", "100 GB", "Unlimited"], "highlighted": False},
                {"feature": "API Access", "values": ["—", "✓", "✓"], "highlighted": False},
                {"feature": "Priority Support", "values": ["—", "—", "✓"], "highlighted": False},
            ],
        },
        "changelog": {
            "title": "Changelog",
            "versions": [
                {"version": "v2.0", "date": "2025-01-15", "changes": ["New dashboard design", "Improved performance by 40%", "Added dark mode"]},
                {"version": "v1.5", "date": "2024-11-01", "changes": ["Added team collaboration", "New export options"]},
                {"version": "v1.0", "date": "2024-06-01", "changes": ["Initial release"]},
            ],
        },
        "code-block": {
            "language": "python",
            "code": "def hello_world():\n    print('Hello, World!')\n\nhello_world()",
        },
        "chat-widget": {
            "title": "Support Chat",
            "welcome_message": "Hi there! How can we help you today?",
        },
        "cookie-banner": {
            "message": "We use cookies to enhance your browsing experience and analyze our traffic.",
            "accept_text": "Accept",
            "decline_text": "Decline",
        },
    }
    return defaults.get(component_id, {})


def _assemble_html(
    template: dict[str, Any],
    components: dict[str, str],
    colors: dict[str, str],
    css_parts: list[str],
    js_parts: list[str],
) -> str:
    """Fill a template skeleton with rendered components."""
    structure: str = template["html_structure"]

    custom_css = "\n".join(css_parts)
    custom_js = "\n".join(js_parts)

    for key, val in components.items():
        placeholder = "{{" + key + "}}"
        if placeholder in structure:
            structure = structure.replace(placeholder, val)

    structure = structure.replace("{{custom_css}}", custom_css)
    structure = structure.replace("{{custom_js}}", custom_js)
    structure = structure.replace("{{title}}", "Luqi AI Generated Site")

    for key, val in colors.items():
        structure = structure.replace(f"[primary]", colors.get("primary", "#4F46E5"))
        structure = structure.replace(f"[secondary]", colors.get("secondary", "#10B981"))
        structure = structure.replace(f"[accent]", colors.get("accent", "#F59E0B"))
        structure = structure.replace(f"[bg]", colors.get("bg", "#FFFFFF"))
        structure = structure.replace(f"[text]", colors.get("text", "#111827"))

    structure = _resolve_color_refs(structure, colors)
    return structure.strip()
