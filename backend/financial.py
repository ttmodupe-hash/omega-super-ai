#!/usr/bin/env python3
"""
Luqi AI - Financial Analysis Engine
====================================
Financial analysis and advisory functionality.
Handles financial calculations, projections, and insights.

Part of Luqi AI v24.3.0 — Built by Limitless Telecoms
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def analyze_financials(
    data: Dict[str, Any],
    analysis_type: str = "general",
    currency: str = "USD",
) -> Dict[str, Any]:
    """
    Analyze financial data and return insights.
    
    Args:
        data: Financial data (revenue, expenses, assets, liabilities, etc.)
        analysis_type: Type of analysis (general, projection, ratio, cashflow)
        currency: Currency code (USD, EUR, GBP, NGN, ZAR, etc.)
    
    Returns:
        Dict with analysis results, insights, and recommendations
    """
    try:
        revenue = float(data.get("revenue", 0))
        expenses = float(data.get("expenses", 0))
        assets = float(data.get("assets", 0))
        liabilities = float(data.get("liabilities", 0))
        
        # Core calculations
        net_income = revenue - expenses
        profit_margin = (net_income / revenue * 100) if revenue > 0 else 0
        debt_to_asset = (liabilities / assets * 100) if assets > 0 else 0
        current_ratio = assets / liabilities if liabilities > 0 else float('inf')
        roa = (net_income / assets * 100) if assets > 0 else 0
        
        result = {
            "analysis_type": analysis_type,
            "currency": currency,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "net_income": round(net_income, 2),
                "assets": round(assets, 2),
                "liabilities": round(liabilities, 2),
                "equity": round(assets - liabilities, 2),
            },
            "ratios": {
                "profit_margin_pct": round(profit_margin, 2),
                "debt_to_asset_pct": round(debt_to_asset, 2),
                "current_ratio": round(current_ratio, 2),
                "return_on_assets_pct": round(roa, 2),
            },
            "insights": [],
            "recommendations": [],
        }
        
        # Generate insights
        if profit_margin > 20:
            result["insights"].append(
                f"Excellent profit margin of {profit_margin:.1f}%. "
                "Your business is highly profitable."
            )
        elif profit_margin > 10:
            result["insights"].append(
                f"Healthy profit margin of {profit_margin:.1f}%. "
                "Consider strategies to optimize further."
            )
        elif profit_margin > 0:
            result["insights"].append(
                f"Low profit margin of {profit_margin:.1f}%. "
                "Review cost structure and pricing strategy."
            )
        else:
            result["insights"].append(
                f"Negative profit margin ({profit_margin:.1f}%). "
                "Urgent: Revenue does not cover expenses."
            )
        
        if debt_to_asset > 70:
            result["insights"].append(
                f"High debt-to-asset ratio ({debt_to_asset:.1f}%). "
                "Consider debt reduction strategies."
            )
        elif debt_to_asset < 30:
            result["insights"].append(
                f"Low leverage ({debt_to_asset:.1f}%). "
                "You may have capacity for strategic debt."
            )
        
        # Generate recommendations
        if net_income < 0:
            result["recommendations"].extend([
                "Reduce non-essential expenses immediately",
                "Review pricing strategy - consider price increases",
                "Negotiate better terms with suppliers",
                "Focus on highest-margin products/services",
            ])
        
        if current_ratio < 1.0:
            result["recommendations"].extend([
                "Improve cash flow management",
                "Consider short-term financing options",
                "Accelerate accounts receivable collection",
            ])
        
        # Projections
        if analysis_type in ("projection", "general"):
            months = data.get("projection_months", 12)
            monthly_growth = float(data.get("monthly_growth_rate", 0.02))
            projections = []
            
            for month in range(1, months + 1):
                projected_revenue = revenue * ((1 + monthly_growth) ** month)
                projected_expenses = expenses * ((1 + monthly_growth * 0.5) ** month)
                projections.append({
                    "month": month,
                    "revenue": round(projected_revenue, 2),
                    "expenses": round(projected_expenses, 2),
                    "net_income": round(projected_revenue - projected_expenses, 2),
                })
            
            result["projections"] = projections
            result["projection_summary"] = {
                "total_projected_revenue": round(sum(p["revenue"] for p in projections), 2),
                "total_projected_expenses": round(sum(p["expenses"] for p in projections), 2),
                "total_projected_net": round(sum(p["net_income"] for p in projections), 2),
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Financial analysis error: {e}")
        return {
            "error": str(e),
            "analysis_type": analysis_type,
            "recommendations": ["Please check your input data format"],
        }


# Backward-compatible alias
analyze_financial = analyze_financials
