#!/usr/bin/env python3
"""Luqi AI v24 -- Branding API Endpoints

Provides brand assets, company info, colors, and logos
for consistent Limitless Telecoms / Luqi AI branding.
Endpoints: 7
"""

from __future__ import annotations

import logging
from fastapi.responses import JSONResponse, PlainTextResponse
from backend.router import app

logger = logging.getLogger("luqi.branding.api")


@app.get("/api/branding")
async def branding_root() -> JSONResponse:
    try:
        from backend.branding import branding
        return JSONResponse({"success": True, "data": branding.to_dict()})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@app.get("/api/branding/company")
async def branding_company() -> JSONResponse:
    try:
        from backend.branding import branding
        return JSONResponse({"success": True, "data": branding.company_info.to_dict()})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@app.get("/api/branding/colors")
async def branding_colors(format: str = "json"):
    try:
        from backend.branding import branding
        if format == "css":
            return PlainTextResponse(content=branding.colors.to_css_variables(), media_type="text/css")
        return JSONResponse({"success": True, "data": branding.colors.to_dict()})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@app.get("/api/branding/logos")
async def branding_logos() -> JSONResponse:
    try:
        from backend.branding import branding
        return JSONResponse({"success": True, "data": branding.logos.to_dict()})
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@app.get("/api/branding/manifest.json")
async def branding_manifest() -> JSONResponse:
    try:
        from backend.branding import branding
        return JSONResponse(branding.get_manifest_json())
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)


@app.get("/api/branding/html/header")
async def branding_html_header() -> PlainTextResponse:
    try:
        from backend.branding import branding
        return PlainTextResponse(content=branding.get_html_header(), media_type="text/html")
    except Exception as exc:
        return PlainTextResponse(content=f"<!-- Error: {exc} -->", media_type="text/html")


@app.get("/api/branding/html/footer")
async def branding_html_footer() -> PlainTextResponse:
    try:
        from backend.branding import branding
        return PlainTextResponse(content=branding.get_footer_html(), media_type="text/html")
    except Exception as exc:
        return PlainTextResponse(content=f"<!-- Error: {exc} -->", media_type="text/html")


logger.info("v24.3.0 Branding endpoints loaded: 7 endpoints")
