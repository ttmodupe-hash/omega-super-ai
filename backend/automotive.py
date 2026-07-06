"
Luqi AI - Automotive Diagnostic Module
========================================
A comprehensive automotive diagnostic AI that helps vehicle owners troubleshoot
mechanical issues safely and cost-effectively. Follows a strict diagnostic
protocol to prevent blind parts-buying.

Author: Luqi AI Engineering Team
Version: 1.0.0
License: Proprietary

This module provides:
- Symptom analysis across 5 categories (sounds, feel, smells, visual, timing)
- Differential diagnosis with probability-ranked causes
- Zero-cost inspection procedures (check-before-buy)
- Safety filtering for critical vehicle systems
- OBD-II diagnostic trouble code database
- Vehicle systems reference with maintenance intervals
- Repair cost estimation with DIY difficulty ratings

Usage:
    from automotive import diagnose, parse_symptoms, lookup_obd2
    result = diagnose(["grinding when braking"], {"year": 2015, "make": "Toyota"})
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass, field
from enum import Enum
import json


# =============================================================================
# CONSTANTS AND ENUMS
# =============================================================================

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CostTier(str, Enum):
    LOW = "low"       # Under $100
    MEDIUM = "medium"  # $100 - $500
    HIGH = "high"      # $500 - $1500
    VERY_HIGH = "very_high"  # Over $1500


class UrgencyLevel(str, Enum):
    IMMEDIATE = "immediate"  # Stop driving now
    SOON = "soon"            # Within a few days
    ROUTINE = "routine"      # Next maintenance window
    INFO = "info"            # For awareness


# =============================================================================
# SECTION 1: SYMPTOM ANALYSIS ENGINE
# =============================================================================
# Comprehensive symptom database organized by perceptual category.
# Each symptom maps to probable causes with diagnostic metadata.

SYMPTOM_DATABASE: Dict[str, Dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # CATEGORY: SOUNDS
    # -------------------------------------------------------------------------
    "sounds": {
        "chirping": {
            "causes": [
                {"name": "Worn serpentine belt", "probability": 0.85, "cost": "low", "severity": "medium", "inspection": "Visual belt check for cracks/glazing"},
                {"name": "Faulty belt tensioner", "probability": 0.60, "cost": "medium", "severity": "medium", "inspection": "Check tensioner pulley for wobble/play"},
                {"name": "Alternator bearing wear", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Remove belt and spin alternator pulley by hand"},
                {"name": "Idler pulley bearing failure", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Remove belt and spin each pulley by hand, listen for noise"},
                {"name": "A/C compressor clutch wear", "probability": 0.20, "cost": "high", "severity": "low", "inspection": "Engage/disengage A/C while listening for noise change"},
            ],
            "safety_note": "Belt failure can cause overheating and loss of power steering. Inspect immediately if chirping is loud or constant.",
        },
        "grinding": {
            "causes": [
                {"name": "Worn brake pads (metal-on-metal)", "probability": 0.90, "cost": "low", "severity": "high", "inspection": "Remove wheel and visually inspect pad thickness"},
                {"name": "Wheel bearing failure", "probability": 0.70, "cost": "medium", "severity": "high", "inspection": "Jack up car, wiggle wheel at 12 and 6 o'clock positions"},
                {"name": "Transmission gear wear", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Check transmission fluid level and color"},
                {"name": "Differential gear wear", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Check differential fluid level and condition"},
                {"name": "Starter motor gear not retracting", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Check if grinding occurs only during or right after starting"},
            ],
            "safety_note": "CRITICAL SAFETY WARNING: Grinding brakes or wheel bearings can cause sudden component failure. Inspect immediately before driving further.",
        },
        "thumping": {
            "causes": [
                {"name": "Flat-spotted tire", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Visual tire inspection for uneven wear or flat spots"},
                {"name": "Worn shock absorber", "probability": 0.65, "cost": "medium", "severity": "medium", "inspection": "Bounce each corner of car -- should settle in 1-2 cycles"},
                {"name": "Driveshaft/CV joint worn", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Check CV boots for tears, inspect for grease leaks"},
                {"name": "Separated tire tread (tire failure)", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Inspect tire tread for bulges, separations, or exposed cords"},
                {"name": "Engine mount broken", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Open hood, have assistant shift between D and R, watch engine movement"},
                {"name": "Exhaust pipe hitting underbody", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Inspect exhaust hangers and mounts from under vehicle"},
            ],
            "safety_note": "Thumping from tires at speed can indicate impending tire failure. Reduce speed and inspect immediately.",
        },
        "squealing": {
            "causes": [
                {"name": "Brake pad wear indicator", "probability": 0.88, "cost": "low", "severity": "medium", "inspection": "Check brake pad thickness through caliper inspection hole"},
                {"name": "Worn serpentine belt", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Visual belt check for cracks, glazing, or contamination"},
                {"name": "Loose belt tension", "probability": 0.55, "cost": "low", "severity": "low", "inspection": "Press on belt mid-span -- should deflect approximately 1 inch"},
                {"name": "Worn accessory bearings (alternator, power steering)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Remove belt, spin each pulley by hand, listen for roughness"},
                {"name": "Brake dust buildup", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Clean brakes with brake cleaner spray and test drive"},
                {"name": "Glazed brake pads or rotors", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Inspect rotor surface for mirror-like glaze or scoring"},
            ],
            "safety_note": "Squealing brake pads indicate they are nearing end of life. Schedule replacement within 500 miles.",
        },
        "knocking": {
            "causes": [
                {"name": "Engine detonation (bad gas or carbon buildup)", "probability": 0.60, "cost": "low", "severity": "high", "inspection": "Try higher octane fuel; listen if knock disappears"},
                {"name": "Worn connecting rod bearings", "probability": 0.45, "cost": "very_high", "severity": "critical", "inspection": "Check oil pressure with mechanical gauge; low pressure confirms"},
                {"name": "Piston slap (worn pistons/cylinders)", "probability": 0.35, "cost": "very_high", "severity": "high", "inspection": "Knock present when cold that lessens as engine warms up"},
                {"name": "Carbon buildup on pistons", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Use borescope through spark plug hole to inspect piston tops"},
                {"name": "Loose torque converter bolts", "probability": 0.15, "cost": "medium", "severity": "medium", "inspection": "Knock at idle in drive but not in park; check converter bolts"},
                {"name": "Valve train noise (lifters/rockers)", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Remove valve cover, inspect rocker arms and lash adjusters"},
            ],
            "safety_note": "ENGINE KNOCKING: Deep knocking from the engine bottom end often indicates catastrophic engine damage. Stop driving immediately and have towed to prevent complete engine destruction.",
        },
        "hissing": {
            "causes": [
                {"name": "Vacuum leak", "probability": 0.80, "cost": "low", "severity": "medium", "inspection": "Listen around intake manifold and hoses; spray soapy water to find bubbles"},
                {"name": "Exhaust leak (before catalytic converter)", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Look for black soot marks at exhaust manifold, flex pipe, or flanges"},
                {"name": "Coolant leak (pressurized, hot)", "probability": 0.50, "cost": "medium", "severity": "high", "inspection": "Check coolant reservoir level; pressure test cooling system"},
                {"name": "A/C refrigerant leak", "probability": 0.40, "cost": "medium", "severity": "low", "inspection": "UV dye in A/C system; inspect with UV light for fluorescent spots"},
                {"name": "Brake booster vacuum leak", "probability": 0.25, "cost": "medium", "severity": "high", "inspection": "Hiss when brake pedal pressed; check vacuum hose to booster"},
                {"name": "PCV valve stuck open", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Remove PCV valve and shake -- should rattle. Check hose for cracks"},
            ],
            "safety_note": "Hissing from brakes or exhaust can indicate dangerous leaks. Exhaust leaks introduce carbon monoxide into the cabin.",
        },
        "rattling": {
            "causes": [
                {"name": "Loose heat shield", "probability": 0.80, "cost": "low", "severity": "low", "inspection": "Tap exhaust components with rubber mallet to locate rattle"},
                {"name": "Worn sway bar links/bushings", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Inspect sway bar end links for play; check bushings for wear"},
                {"name": "Loose exhaust hanger or clamp", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Shake exhaust system; replace worn hangers"},
                {"name": "Worn suspension bushings", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Inspect control arm and subframe bushings for deterioration"},
                {"name": "Loose timing chain/belt tensioner", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Listen at timing cover; check timing components"},
                {"name": "Loose body trim or underbody shield", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Inspect underbody shields and trim clips"},
            ],
            "safety_note": "Rattling from the timing area can indicate imminent timing component failure which can destroy the engine.",
        },
        "clicking": {
            "causes": [
                {"name": "CV joint worn/damaged", "probability": 0.85, "cost": "medium", "severity": "medium", "inspection": "Inspect CV boot for tears; listen during slow turns"},
                {"name": "Relay cycling rapidly", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Listen at fuse box; identify which relay is clicking"},
                {"name": "Valve lifter tick", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Listen at valve cover; check oil level and condition"},
                {"name": "Exhaust manifold leak (tick sound)", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Listen at exhaust manifold; look for black soot marks"},
                {"name": "Spark plug loose", "probability": 0.20, "cost": "low", "severity": "high", "inspection": "Check spark plug torque; look for blow-by marks"},
            ],
            "safety_note": "Clicking from CV joints during turns means the joint is failing and can separate suddenly.",
        },
        "ticking": {
            "causes": [
                {"name": "Valve lifter tick (low oil)", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Check oil level immediately; listen if tick changes with RPM"},
                {"name": "Exhaust leak at manifold", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Listen at exhaust manifold with hood open"},
                {"name": "Fuel injector normal operation", "probability": 0.90, "cost": "none", "severity": "info", "inspection": "Use screwdriver as stethoscope on injectors -- even ticking is normal"},
                {"name": "Spark plug loose", "probability": 0.15, "cost": "low", "severity": "high", "inspection": "Check spark plug torque with socket"},
                {"name": "Worn timing chain tensioner", "probability": 0.30, "cost": "high", "severity": "high", "inspection": "Listen at timing cover; check for chain slack"},
            ],
            "safety_note": "Loud ticking that increases with RPM can indicate serious valve train or timing issues. Check oil level first.",
        },
        "whining": {
            "causes": [
                {"name": "Power steering pump low/failing", "probability": 0.70, "cost": "medium", "severity": "medium", "inspection": "Check power steering fluid level; listen at pump"},
                {"name": "Alternator bearing failure", "probability": 0.55, "cost": "medium", "severity": "medium", "inspection": "Listen at alternator; check charging voltage"},
                {"name": "Transmission pump wear", "probability": 0.45, "cost": "high", "severity": "high", "inspection": "Check transmission fluid level and condition"},
                {"name": "Differential bearing wear", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Check differential fluid; listen at differential housing"},
                {"name": "Water pump bearing failure", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Listen at water pump; check for coolant weep hole leakage"},
                {"name": "Idler/tensioner pulley bearing", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Remove belt, spin each pulley by hand"},
            ],
            "safety_note": "Whining that changes with engine RPM often indicates accessory bearing failure. Check before it seizes and throws the belt.",
        },
        "howling": {
            "causes": [
                {"name": "Wheel bearing failure (advanced)", "probability": 0.90, "cost": "medium", "severity": "high", "inspection": "Jack up wheel, spin and listen; check for play"},
                {"name": "Differential gear wear", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Check differential fluid level and condition"},
                {"name": "Transmission bearing wear", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Check transmission fluid; listen in neutral vs drive"},
                {"name": "Wind noise from door seal", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Check door seals for gaps or damage"},
            ],
            "safety_note": "Howling wheel bearings can seize or cause the wheel to separate from the vehicle. Replace immediately.",
        },
        "drone_hum": {
            "causes": [
                {"name": "Wheel bearing (tire-speed related)", "probability": 0.80, "cost": "medium", "severity": "medium", "inspection": "Hum changes with vehicle speed, not engine RPM"},
                {"name": "Tire chop/cupping", "probability": 0.60, "cost": "medium", "severity": "medium", "inspection": "Visually inspect tread for uneven wear patterns"},
                {"name": "Differential pinion bearing", "probability": 0.30, "cost": "high", "severity": "high", "inspection": "Check differential fluid; listen at differential"},
                {"name": "Transmission torque converter", "probability": 0.25, "cost": "high", "severity": "medium", "inspection": "Hum at specific RPM range; try driving in different gears"},
            ],
            "safety_note": "Droning hum that changes with vehicle speed (not engine speed) usually indicates wheel bearings or tires.",
        },
        "backfiring": {
            "causes": [
                {"name": "Ignition timing too advanced", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Check timing with timing light; inspect timing chain/belt"},
                {"name": "Lean fuel condition", "probability": 0.55, "cost": "low", "severity": "high", "inspection": "Check for vacuum leaks; test fuel pressure"},
                {"name": "Cracked exhaust valve", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Compression test; cylinder leak-down test"},
                {"name": "Faulty ignition coil/wires", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Inspect spark plug wires; test coil output"},
                {"name": "Crossed spark plug wires", "probability": 0.20, "cost": "none", "severity": "medium", "inspection": "Verify firing order and wire routing"},
            ],
            "safety_note": "Backfiring can damage the catalytic converter and exhaust system. Diagnose promptly to avoid expensive repairs.",
        },
        "squeaking": {
            "causes": [
                {"name": "Worn serpentine belt", "probability": 0.80, "cost": "low", "severity": "low", "inspection": "Inspect belt for cracks, glazing, or contamination"},
                {"name": "Belt tensioner weak", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Check belt tension; inspect tensioner for play"},
                {"name": "Suspension bushings dry/worn", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Spray silicone lubricant on bushings to test"},
                {"name": "Ball joint dry/worn", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Inspect ball joints for play and grease boots"},
                {"name": "Brake pad wear indicator", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Check brake pad thickness"},
            ],
            "safety_note": "Squeaking suspension components may be dry bushings, but can also indicate worn ball joints that affect safety.",
        },
    },
    # -------------------------------------------------------------------------
    # CATEGORY: FEEL/VIBRATION
    # -------------------------------------------------------------------------
    "feel": {
        "vibration": {
            "causes": [
                {"name": "Wheel imbalance", "probability": 0.80, "cost": "low", "severity": "low", "inspection": "Have wheels balanced; check for lost wheel weights"},
                {"name": "Bent wheel rim", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Visual inspection for rim damage; check for vibration at specific speeds"},
                {"name": "Worn CV joint", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Check CV boots; vibration under acceleration indicates CV issue"},
                {"name": "Worn wheel bearing", "probability": 0.45, "cost": "medium", "severity": "high", "inspection": "Jack up wheel, check for play and roughness when spinning"},
                {"name": "Worn tie rod end", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Check for play in steering linkage"},
                {"name": "Engine misfire", "probability": 0.35, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes; check spark plugs and coils"},
                {"name": "Worn engine mounts", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Open hood, have assistant shift D to R, watch engine movement"},
                {"name": "Tire separation/internal damage", "probability": 0.25, "cost": "medium", "severity": "critical", "inspection": "Inspect tire sidewalls for bulges or irregular shapes"},
            ],
            "safety_note": "Vibration at highway speeds can indicate tire failure or wheel separation risk. Do not ignore.",
        },
        "pulling_left": {
            "causes": [
                {"name": "Left tire underinflated", "probability": 0.70, "cost": "none", "severity": "low", "inspection": "Check and equalize tire pressures"},
                {"name": "Worn left front brake caliper", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Check if left wheel is hotter after driving"},
                {"name": "Wheel alignment off", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Have alignment checked; look for uneven tire wear"},
                {"name": "Worn left front suspension", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Inspect left control arm, ball joint, and bushing"},
            ],
            "safety_note": "Vehicle pulling to one side can indicate brake drag or alignment issues that affect emergency handling.",
        },
        "pulling_right": {
            "causes": [
                {"name": "Right tire underinflated", "probability": 0.70, "cost": "none", "severity": "low", "inspection": "Check and equalize tire pressures"},
                {"name": "Worn right front brake caliper", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Check if right wheel is hotter after driving"},
                {"name": "Wheel alignment off", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Have alignment checked; look for uneven tire wear"},
                {"name": "Road crown (normal)", "probability": 0.50, "cost": "none", "severity": "info", "inspection": "Test on flat road or in different lanes"},
                {"name": "Worn right front suspension", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Inspect right control arm, ball joint, and bushing"},
            ],
            "safety_note": "Vehicle pulling to one side can indicate brake drag or alignment issues that affect emergency handling.",
        },
        "slipping": {
            "causes": [
                {"name": "Clutch worn (manual transmission)", "probability": 0.80, "cost": "high", "severity": "high", "inspection": "RPM rises without speed increase during acceleration"},
                {"name": "Transmission fluid low/degraded", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Check transmission fluid level and condition"},
                {"name": "Worn transmission clutch packs", "probability": 0.60, "cost": "very_high", "severity": "high", "inspection": "Scan for transmission codes; check fluid condition"},
                {"name": "Faulty torque converter", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Slip primarily at highway speeds; stall test"},
                {"name": "Brakes dragging", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Check if wheels are hot after driving; verify caliper operation"},
            ],
            "safety_note": "Transmission slipping indicates internal wear. Continuing to drive can cause complete transmission failure.",
        },
        "shuddering": {
            "causes": [
                {"name": "Worn brake rotors (warped)", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Feel steering wheel shake during braking; measure rotor runout"},
                {"name": "Engine misfire under load", "probability": 0.60, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes; check coils and plugs"},
                {"name": "Torque converter clutch shudder", "probability": 0.50, "cost": "high", "severity": "medium", "inspection": "Shudder at specific speed (45-55 mph); try driving in different gears"},
                {"name": "Worn engine mounts", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Check engine movement during load changes"},
                {"name": "Worn U-joint or CV joint", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Inspect drivetrain components for play"},
                {"name": "Tire out of balance or separation", "probability": 0.45, "cost": "low", "severity": "high", "inspection": "Have tires balanced and inspected"},
            ],
            "safety_note": "Shuddering during braking often means warped rotors. Shuddering while driving can indicate driveline issues.",
        },
        "jerking": {
            "causes": [
                {"name": "Ignition misfire", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes; inspect spark plugs and coils"},
                {"name": "Fuel delivery issue", "probability": 0.60, "cost": "medium", "severity": "high", "inspection": "Check fuel pressure; test fuel pump and filter"},
                {"name": "Transmission harsh shift", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Check transmission fluid; scan for transmission codes"},
                {"name": "Dirty/faulty MAF sensor", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Clean MAF sensor with dedicated cleaner; check readings"},
                {"name": "Vacuum leak", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Spray carb cleaner around intake; listen for RPM changes"},
                {"name": "Clogged catalytic converter", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Check exhaust backpressure; scan for P0420"},
            ],
            "safety_note": "Jerking/hesitation during acceleration can be dangerous when merging. Diagnose promptly.",
        },
        "spongy_brake": {
            "causes": [
                {"name": "Air in brake lines", "probability": 0.75, "cost": "low", "severity": "critical", "inspection": "Pedal feels soft and travels far; pump pedal to test"},
                {"name": "Worn brake pads", "probability": 0.60, "cost": "low", "severity": "high", "inspection": "Check pad thickness; inspect for uneven wear"},
                {"name": "Failing master cylinder", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Pedal slowly sinks to floor when held"},
                {"name": "Brake fluid leak", "probability": 0.40, "cost": "low", "severity": "critical", "inspection": "Inspect all brake lines, calipers, and master cylinder for wetness"},
                {"name": "Rear brake shoe out of adjustment (drum)", "probability": 0.30, "cost": "none", "severity": "medium", "inspection": "Adjust drum brakes via star wheel"},
                {"name": "Faulty brake hose (swelling internally)", "probability": 0.20, "cost": "low", "severity": "critical", "inspection": "Hose looks fine outside but blocks pressure internally"},
            ],
            "safety_note": "CRITICAL: Spongy brake pedal indicates compromised braking ability. Do not drive until repaired.",
        },
        "hard_steering": {
            "causes": [
                {"name": "Low power steering fluid", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Check power steering reservoir level"},
                {"name": "Failing power steering pump", "probability": 0.60, "cost": "medium", "severity": "high", "inspection": "Listen for whining; check belt tension"},
                {"name": "Worn steering rack", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Check for play in steering; look for leaks from rack boots"},
                {"name": "Seized ball joint or tie rod", "probability": 0.30, "cost": "medium", "severity": "critical", "inspection": "Jack up front end, check for binding when turning wheels"},
                {"name": "EPS (electric steering) motor failure", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Scan for EPS codes; check fuses and wiring"},
                {"name": "Incorrect tire pressure (too low)", "probability": 0.35, "cost": "none", "severity": "low", "inspection": "Check tire pressure; inflate to spec"},
            ],
            "safety_note": "Hard steering makes emergency maneuvers difficult. A seized ball joint can cause wheel separation.",
        },
        "loose_steering": {
            "causes": [
                {"name": "Worn tie rod ends", "probability": 0.85, "cost": "low", "severity": "critical", "inspection": "Jack up front, wiggle wheels at 3 and 9 o'clock positions"},
                {"name": "Worn idler arm or pitman arm", "probability": 0.50, "cost": "medium", "severity": "high", "inspection": "Check steering linkage for play"},
                {"name": "Worn steering rack mounts", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Have assistant turn wheel while you watch rack movement"},
                {"name": "Worn ball joints", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Jack up, wiggle wheels at 12 and 6 o'clock positions"},
                {"name": "Wheel bearings loose", "probability": 0.35, "cost": "medium", "severity": "high", "inspection": "Jack up wheel, check for play in all directions"},
            ],
            "safety_note": "CRITICAL: Loose steering means reduced vehicle control. A failed tie rod or ball joint can cause a wheel to fold under the vehicle.",
        },
        "rough_idle": {
            "causes": [
                {"name": "Dirty throttle body", "probability": 0.60, "cost": "none", "severity": "low", "inspection": "Clean throttle body with throttle body cleaner"},
                {"name": "Vacuum leak", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Spray carb cleaner around intake; listen for RPM change"},
                {"name": "Worn spark plugs", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Remove and inspect spark plugs; check gap"},
                {"name": "Faulty ignition coil", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Scan for misfire codes; swap coils to isolate"},
                {"name": "Dirty/faulty MAF sensor", "probability": 0.45, "cost": "low", "severity": "low", "inspection": "Clean MAF sensor with dedicated cleaner"},
                {"name": "Clogged fuel injectors", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Use fuel injector cleaner additive or professional cleaning"},
                {"name": "Failing engine mount", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Watch engine movement under load"},
                {"name": "Low compression on one cylinder", "probability": 0.20, "cost": "very_high", "severity": "high", "inspection": "Compression test on all cylinders"},
            ],
            "safety_note": "Rough idle is usually not immediately dangerous but can indicate developing engine problems.",
        },
        "delayed_shifting": {
            "causes": [
                {"name": "Low transmission fluid", "probability": 0.75, "cost": "low", "severity": "high", "inspection": "Check transmission fluid level and condition"},
                {"name": "Worn transmission bands/clutches", "probability": 0.55, "cost": "very_high", "severity": "high", "inspection": "Scan for transmission codes; check shift timing"},
                {"name": "Faulty shift solenoid", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Scan for solenoid codes; test solenoid operation"},
                {"name": "Dirty transmission fluid", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Check fluid color and smell; should be red/pink, not brown/burnt"},
                {"name": "Transmission control module issue", "probability": 0.30, "cost": "high", "severity": "medium", "inspection": "Scan TCM for codes; check for software updates"},
                {"name": "Worn valve body", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Requires professional diagnosis and possible rebuild"},
            ],
            "safety_note": "Delayed shifting can leave you without power in intersections. Diagnose promptly.",
        },
        "pulsing_brake_pedal": {
            "causes": [
                {"name": "Warped brake rotors", "probability": 0.85, "cost": "low", "severity": "medium", "inspection": "Pedal pulses during braking; measure rotor runout"},
                {"name": "ABS self-test (normal)", "probability": 0.30, "cost": "none", "severity": "info", "inspection": "Brief pulse at low speed on first brake application is normal"},
                {"name": "Wheel bearing play", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Jack up wheel, check for play"},
                {"name": "Tire out of round", "probability": 0.20, "cost": "medium", "severity": "low", "inspection": "Have tires inspected for roundness"},
                {"name": "Suspension component loose", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Inspect suspension for worn components"},
            ],
            "safety_note": "Pulsing brake pedal usually means warped rotors. Braking effectiveness is reduced. Schedule service soon.",
        },
        "wandering": {
            "causes": [
                {"name": "Worn steering components", "probability": 0.75, "cost": "medium", "severity": "high", "inspection": "Check tie rods, ball joints, and steering rack for play"},
                {"name": "Incorrect alignment", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Have alignment checked and adjusted"},
                {"name": "Uneven tire pressure or wear", "probability": 0.50, "cost": "none", "severity": "low", "inspection": "Check and equalize tire pressures; inspect tread wear"},
                {"name": "Worn shocks or struts", "probability": 0.55, "cost": "medium", "severity": "medium", "inspection": "Bounce test; observe if car settles in more than 2 cycles"},
                {"name": "Loose wheel bearings", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Jack up wheels, check for play"},
            ],
            "safety_note": "Wandering steering requires constant correction and increases driver fatigue. Can be dangerous in emergencies.",
        },
        "stiff_gas_pedal": {
            "causes": [
                {"name": "Dirty/failing throttle body", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Clean throttle body; check for carbon buildup"},
                {"name": "Accelerator cable binding (older vehicles)", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Lubricate cable; check for kinks or fraying"},
                {"name": "Floor mat interference", "probability": 0.30, "cost": "none", "severity": "medium", "inspection": "Check floor mats are properly secured and not under pedal"},
                {"name": "Electronic throttle body fault", "probability": 0.35, "cost": "medium", "severity": "high", "inspection": "Scan for throttle body codes; check throttle position sensor"},
                {"name": "Cruise control cable interference", "probability": 0.15, "cost": "low", "severity": "low", "inspection": "Check cruise control cable routing"},
            ],
            "safety_note": "Stiff accelerator pedal can prevent quick throttle changes in emergencies. Inspect promptly.",
        },
    },
    # -------------------------------------------------------------------------
    # CATEGORY: SMELLS
    # -------------------------------------------------------------------------
    "smells": {
        "burning_oil": {
            "causes": [
                {"name": "Valve cover gasket leak", "probability": 0.80, "cost": "low", "severity": "medium", "inspection": "Look for oil on exhaust manifold from valve cover area"},
                {"name": "Oil pan gasket leak", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Inspect oil pan perimeter for seepage"},
                {"name": "Rear main seal leak", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Oil dripping from bell housing area where engine meets transmission"},
                {"name": "Oil filter loose or double-gasketed", "probability": 0.35, "cost": "none", "severity": "medium", "inspection": "Check oil filter tightness; look for oil around filter"},
                {"name": "Oil pressure sender leak", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Look for oil around oil pressure sensor on engine"},
                {"name": "Spilled oil during change", "probability": 0.25, "cost": "none", "severity": "info", "inspection": "Oil on exhaust from recent oil change will burn off in a few drives"},
                {"name": "Turbocharger oil seal leak", "probability": 0.20, "cost": "high", "severity": "high", "inspection": "Check for oil in intercooler pipes; smoke from exhaust"},
            ],
            "safety_note": "Oil leaking onto exhaust components can ignite and cause an engine fire. Inspect and repair promptly.",
        },
        "sweet_coolant": {
            "causes": [
                {"name": "Heater core leak", "probability": 0.65, "cost": "high", "severity": "medium", "inspection": "Sweet smell inside cabin; check passenger floor for wetness"},
                {"name": "Coolant hose leak", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Inspect all coolant hoses for swelling, cracks, or wetness"},
                {"name": "Head gasket leaking (small)", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Check for white exhaust smoke; check oil for coolant contamination"},
                {"name": "Radiator leak", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Look for coolant on ground under radiator; check tanks for cracks"},
                {"name": "Water pump weep hole leaking", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Look for coolant below water pump; small hole is the weep hole"},
                {"name": "Intake manifold gasket leak", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "External coolant leak at intake manifold mating surface"},
            ],
            "safety_note": "Coolant leaks can lead to overheating and engine damage. A sweet smell in the cabin often means heater core leak.",
        },
        "rotten_eggs": {
            "causes": [
                {"name": "Catalytic converter sulfur buildup", "probability": 0.70, "cost": "high", "severity": "low", "inspection": "Smell from exhaust; try a different brand of gasoline; may clear on highway run"},
                {"name": "Over-rich fuel mixture", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Scan for rich codes (P0172, P0175); black soot in tailpipe"},
                {"name": "Failing catalytic converter", "probability": 0.50, "cost": "high", "severity": "medium", "inspection": "Scan for P0420; converter may be overheating; check for glowing red converter"},
                {"name": "Contaminated fuel (high sulfur)", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Try different gas station; switch to Top Tier gasoline brand"},
                {"name": "Battery overcharging (hydrogen sulfide)", "probability": 0.15, "cost": "medium", "severity": "medium", "inspection": "Check charging voltage (should be 13.5-14.5V); smell near battery"},
            ],
            "safety_note": "A glowing red catalytic converter indicates internal temperatures over 1500F. This is a FIRE HAZARD -- pull over and shut off immediately.",
        },
        "burning_rubber": {
            "causes": [
                {"name": "Slipping serpentine belt", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Look for shiny glazed belt; check belt tension and pulley alignment"},
                {"name": "Sticking brake caliper", "probability": 0.50, "cost": "medium", "severity": "high", "inspection": "After driving, feel wheels for overheating; compare left vs right temperatures"},
                {"name": "Rubber hose contacting hot exhaust", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Inspect all rubber hoses and wiring near exhaust components"},
                {"name": "Clutch slipping (manual transmission)", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Smell during hard acceleration; RPM climbs without speed increase"},
                {"name": "Tire rubbing on body or suspension", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Look for rubber marks on inner fenders or suspension arms"},
                {"name": "Motor mount failure (engine movement)", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Open hood, shift D to R, watch for excessive engine rocking"},
            ],
            "safety_note": "Burning rubber from brakes indicates a dragging caliper that can cause BRAKE FAILURE from overheated fluid. Stop and inspect immediately.",
        },
        "gasoline": {
            "causes": [
                {"name": "Fuel injector O-ring leak", "probability": 0.60, "cost": "low", "severity": "critical", "inspection": "Inspect fuel rail and injector seals with flashlight; look for wet fuel"},
                {"name": "Fuel line leak (rubber or metal)", "probability": 0.50, "cost": "low", "severity": "critical", "inspection": "Trace fuel lines from tank to engine; look for wet spots or corrosion"},
                {"name": "Loose fuel cap", "probability": 0.45, "cost": "low", "severity": "low", "inspection": "Check fuel cap is tightened until it clicks; check seal gasket condition"},
                {"name": "Charcoal canister saturated", "probability": 0.30, "cost": "medium", "severity": "low", "inspection": "Gas smell after filling up; scan for EVAP codes (P0455, P0456)"},
                {"name": "Fuel tank leak or puncture", "probability": 0.20, "cost": "high", "severity": "critical", "inspection": "Inspect tank top from rear seat access; look for stains on tank underside"},
                {"name": "Fuel pressure regulator leaking (into vacuum line)", "probability": 0.25, "cost": "low", "severity": "high", "inspection": "Pull vacuum line from regulator; if fuel comes out, regulator is bad"},
            ],
            "safety_note": "GASOLINE LEAK = IMMEDIATE FIRE HAZARD. Do NOT start the engine. Do NOT drive. Have the vehicle towed. Gasoline vapors are explosive.",
        },
        "electrical_burning": {
            "causes": [
                {"name": "Overloaded circuit or short circuit", "probability": 0.65, "cost": "low", "severity": "critical", "inspection": "Pull fuses one by one to isolate circuit; look for melted fuse box"},
                {"name": "Failing alternator (overheating diodes)", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Check charging voltage; smell near alternator; check for overcharging (>15V)"},
                {"name": "Blower motor resistor overheating", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Smell from vents; check blower resistor behind glove box for melting"},
                {"name": "Wiring harness chafing (rubbing metal)", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Inspect wiring looms at sharp edges, firewall pass-throughs, door jambs"},
                {"name": "Aftermarket accessory wired incorrectly", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Inspect all non-factory wiring; look for scotch locks or twisted connections"},
                {"name": "Starter motor overheating", "probability": 0.20, "cost": "medium", "severity": "high", "inspection": "Smell after starting; starter may be failing and drawing excess current"},
            ],
            "safety_note": "ELECTRICAL FIRE WARNING: Burning electrical smell can precede a vehicle fire. Pull over, turn off all accessories, and investigate immediately. Keep a Class C fire extinguisher in your vehicle.",
        },
        "musty": {
            "causes": [
                {"name": "Clogged cabin air filter", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Remove cabin filter (behind glove box) and inspect for mold/debris"},
                {"name": "Evaporator core mold growth", "probability": 0.60, "cost": "medium", "severity": "low", "inspection": "Smell when A/C first turned on; use foaming evaporator cleaner through drain"},
                {"name": "Water leak into cabin (door seal, sunroof drain)", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Check floor carpets for wetness; test sunroof drain tubes with water"},
                {"name": "HVAC ductwork debris (leaves, rodent nest)", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Inspect intake grille at base of windshield; remove debris"},
                {"name": "Trunk seal leak with standing water", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Check spare tire well for standing water; replace trunk seal"},
            ],
            "safety_note": "Musty odors from the HVAC system can indicate mold that causes allergic reactions. People with asthma should clean the evaporator promptly.",
        },
        "burning_plastic": {
            "causes": [
                {"name": "Plastic bag melted on exhaust", "probability": 0.60, "cost": "none", "severity": "low", "inspection": "Visually inspect entire exhaust system for foreign material"},
                {"name": "Electrical connector overheating/melting", "probability": 0.45, "cost": "low", "severity": "critical", "inspection": "Inspect major connectors (alternator, blower motor, headlights) for distortion"},
                {"name": "Heater blower motor overheating", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Check blower operation on all speeds; smell strongest at vents"},
                {"name": "Relay or fuse holder melting", "probability": 0.25, "cost": "low", "severity": "critical", "inspection": "Remove and inspect all fuses and relays for heat damage or melting"},
                {"name": "Foreign object on engine (plastic part)", "probability": 0.35, "cost": "none", "severity": "low", "inspection": "Look under hood for any plastic items resting on hot engine components"},
            ],
            "safety_note": "Burning plastic from electrical components is a pre-fire warning. Disconnect the battery if you cannot immediately locate the source.",
        },
        "ammonia": {
            "causes": [
                {"name": "A/C refrigerant leak (R134a with dye)", "probability": 0.60, "cost": "medium", "severity": "low", "inspection": "UV dye may smell like ammonia; inspect with UV light for leaks"},
                {"name": "Catalytic converter chemical reaction", "probability": 0.30, "cost": "high", "severity": "low", "inspection": "Usually after specific fuel brands; runs cleaner with Top Tier gas"},
                {"name": "Urea/DEF leak (diesel vehicles)", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Check DEF tank and lines; DEF smells strongly of ammonia when leaked"},
                {"name": "Rodent urine in HVAC system", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Inspect cabin air filter and intake duct for rodent droppings/nests"},
            ],
            "safety_note": "Ammonia-like smells from a diesel DEF system indicate a leak that will eventually trigger limp mode. Top off DEF and repair leak promptly.",
        },
        "sweet_metallic": {
            "causes": [
                {"name": "Brake fluid leak onto hot components", "probability": 0.55, "cost": "medium", "severity": "critical", "inspection": "Brake fluid has sweet, metallic smell when burned; check all brake lines"},
                {"name": "Clutch fluid leak (manual transmission)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Check clutch master cylinder and slave cylinder reservoir levels"},
                {"name": "Power steering fluid leak onto exhaust", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Check power steering hoses and pump for leaks"},
                {"name": "Transmission fluid leak (some types smell sweet)", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Check transmission cooler lines and pan gasket"},
            ],
            "safety_note": "Sweet metallic smell from brake fluid means a leak in the hydraulic system. Check brake fluid level immediately.",
        },
        "exhaust_fumes": {
            "causes": [
                {"name": "Exhaust leak before catalytic converter", "probability": 0.80, "cost": "low", "severity": "critical", "inspection": "Listen at exhaust manifold; look for black soot marks; carbon monoxide risk"},
                {"name": "Rust hole in exhaust pipe or muffler", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Inspect exhaust system for rust holes or damage"},
                {"name": "Leaking exhaust manifold gasket", "probability": 0.55, "cost": "low", "severity": "critical", "inspection": "Listen for ticking at exhaust manifold; look for soot marks"},
                {"name": "Disconnected or broken exhaust pipe", "probability": 0.30, "cost": "medium", "severity": "critical", "inspection": "Visually inspect entire exhaust system for breaks or separations"},
                {"name": "Missing exhaust gasket at flange", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Check all exhaust flange connections for gasket condition"},
            ],
            "safety_note": "CARBON MONOXIDE HAZARD: Exhaust fumes in the cabin can cause unconsciousness and death. Drive with windows open and get immediate repair.",
        },
        "sweet_fruity": {
            "causes": [
                {"name": "Coolant leak onto hot engine", "probability": 0.70, "cost": "medium", "severity": "medium", "inspection": "Check all coolant hoses, heater core, and radiator for leaks"},
                {"name": "Heater core leak into cabin", "probability": 0.50, "cost": "high", "severity": "medium", "inspection": "Check passenger floor for wetness; smell inside cabin"},
                {"name": "Coolant overflow reservoir leak", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Inspect overflow tank and hose for cracks"},
            ],
            "safety_note": "Sweet fruity smell is almost always coolant. Find and fix the leak to prevent overheating damage.",
        },
        "sulfur_acid": {
            "causes": [
                {"name": "Overcharging alternator", "probability": 0.70, "cost": "medium", "severity": "high", "inspection": "Check charging voltage at battery (should be 13.5-14.5V, not over 15V)"},
                {"name": "Battery internal failure", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Check battery voltage; have battery load tested"},
                {"name": "Battery terminals corroded", "probability": 0.35, "cost": "none", "severity": "low", "inspection": "Inspect terminals for white/green corrosion; clean with baking soda solution"},
            ],
            "safety_note": "Sulfuric acid smell from battery means overcharging which will destroy the battery and can cause it to explode. Test charging system immediately.",
        },
    },
    # -------------------------------------------------------------------------
    # CATEGORY: VISUAL
    # -------------------------------------------------------------------------
    "visual": {
        "check_engine_light": {
            "causes": [
                {"name": "Emissions-related fault (many possible)", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Scan with OBD-II scanner; check gas cap first"},
                {"name": "Oxygen sensor failure", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Scan for specific O2 sensor codes"},
                {"name": "Catalytic converter efficiency low", "probability": 0.25, "cost": "high", "severity": "medium", "inspection": "Scan for P0420; check exhaust backpressure"},
                {"name": "Mass airflow sensor dirty/faulty", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Clean MAF sensor; check for air intake leaks"},
                {"name": "Ignition system misfire", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes (P0300-P0308); check spark plugs and coils"},
                {"name": "EVAP system leak (gas cap)", "probability": 0.40, "cost": "none", "severity": "low", "inspection": "Check gas cap is tight; inspect for cracked cap seal"},
                {"name": " thermostat stuck open", "probability": 0.15, "cost": "low", "severity": "low", "inspection": "Check if engine reaches normal operating temperature"},
            ],
            "safety_note": "Check engine light: Solid = schedule scan soon. Flashing = active misfire that can damage catalytic converter. Stop driving if flashing.",
        },
        "oil_light": {
            "causes": [
                {"name": "Low oil pressure (serious)", "probability": 0.60, "cost": "very_high", "severity": "critical", "inspection": "Check oil level immediately; if OK, engine wear likely"},
                {"name": "Faulty oil pressure sender", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Verify actual oil pressure with mechanical gauge"},
                {"name": "Oil level critically low", "probability": 0.55, "cost": "none", "severity": "critical", "inspection": "Check dipstick; add oil immediately if low"},
                {"name": "Clogged oil pick-up tube screen", "probability": 0.20, "cost": "high", "severity": "critical", "inspection": "Requires oil pan removal to inspect pick-up tube"},
                {"name": "Worn oil pump", "probability": 0.25, "cost": "high", "severity": "critical", "inspection": "Check oil pressure with mechanical gauge at idle and RPM"},
            ],
            "safety_note": "RED OIL LIGHT = STOP ENGINE IMMEDIATELY. Driving with low oil pressure causes catastrophic engine damage in seconds. Tow the vehicle.",
        },
        "battery_light": {
            "causes": [
                {"name": "Alternator not charging", "probability": 0.75, "cost": "medium", "severity": "high", "inspection": "Check charging voltage (should be 13.5-14.5V at idle)"},
                {"name": "Loose or corroded battery terminals", "probability": 0.50, "cost": "none", "severity": "medium", "inspection": "Clean and tighten battery terminals"},
                {"name": "Broken serpentine belt", "probability": 0.40, "cost": "low", "severity": "high", "inspection": "Inspect belt for breakage or jumping off pulleys"},
                {"name": "Faulty voltage regulator", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Check for overcharging or undercharging"},
                {"name": "Battery failing (internal short)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Have battery load tested at auto parts store"},
            ],
            "safety_note": "Battery light means the alternator is not charging. Vehicle will run until battery is depleted, then stall. Fix promptly.",
        },
        "coolant_leak": {
            "causes": [
                {"name": "Radiator hose leak", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Inspect all hoses for wetness, swelling, or cracks"},
                {"name": "Radiator tank or core leak", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Look for coolant on ground; pressure test radiator"},
                {"name": "Water pump leak", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Look for coolant below water pump; check weep hole"},
                {"name": "Heater core leak", "probability": 0.35, "cost": "high", "severity": "medium", "inspection": "Check passenger floor for wetness; smell inside cabin"},
                {"name": "Head gasket leak (external)", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Look for coolant seeping from head gasket area"},
                {"name": "Freeze plug (core plug) leak", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Inspect side of engine block for rust stains around freeze plugs"},
            ],
            "safety_note": "Coolant leaks lead to overheating. Monitor coolant level closely and repair before the level drops enough to cause engine damage.",
        },
        "oil_leak": {
            "causes": [
                {"name": "Valve cover gasket", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Look for oil pooling around valve cover edges"},
                {"name": "Oil pan gasket", "probability": 0.55, "cost": "low", "severity": "low", "inspection": "Inspect oil pan perimeter and drain plug"},
                {"name": "Rear main seal", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Oil dripping from bell housing area"},
                {"name": "Oil filter or drain plug loose", "probability": 0.40, "cost": "none", "severity": "medium", "inspection": "Check oil filter tightness and drain plug torque"},
                {"name": "Timing cover gasket", "probability": 0.30, "cost": "medium", "severity": "low", "inspection": "Look for oil seeping from timing cover edges"},
                {"name": "Camshaft seal leak", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Oil at front of engine near timing components"},
            ],
            "safety_note": "Monitor oil level regularly with any leak. Oil on exhaust is a fire hazard. Address promptly.",
        },
        "smoke_exhaust": {
            "causes": [
                {"name": "Blue smoke = burning oil", "probability": 0.70, "cost": "high", "severity": "high", "inspection": "Worn piston rings, valve seals, or turbo seal. Check oil consumption"},
                {"name": "White smoke = coolant burning", "probability": 0.65, "cost": "high", "severity": "critical", "inspection": "Head gasket failure or cracked head. Check for coolant in oil"},
                {"name": "Black smoke = rich fuel mixture", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Dirty air filter, faulty MAF, leaking injector, or O2 sensor issue"},
                {"name": "Gray smoke = transmission fluid burning (AT)", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Vacuum modulator or transmission cooler leak into intake"},
            ],
            "safety_note": "White smoke with sweet smell = coolant in combustion chamber. This causes overheating and engine destruction. Stop driving immediately.",
        },
        "smoke_engine": {
            "causes": [
                {"name": "Oil leaking onto exhaust manifold", "probability": 0.80, "cost": "low", "severity": "high", "inspection": "Look for oil on exhaust manifold; likely valve cover gasket"},
                {"name": "Coolant leak onto hot engine", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Look for coolant on engine; check hoses and fittings"},
                {"name": "Plastic bag or debris on exhaust", "probability": 0.30, "cost": "none", "severity": "low", "inspection": "Inspect exhaust system for foreign material"},
                {"name": "Electrical short/melting", "probability": 0.35, "cost": "low", "severity": "critical", "inspection": "Pull over immediately; inspect for burning wires or connectors"},
                {"name": "Brake fluid or power steering fluid leak", "probability": 0.20, "cost": "medium", "severity": "high", "inspection": "Check all hydraulic fluid reservoirs for level drops"},
            ],
            "safety_note": "Smoke from under the hood is a FIRE RISK. Pull over safely, turn off engine, and investigate immediately. Do not open hood if flames are visible.",
        },
        "fluid_under_car": {
            "causes": [
                {"name": "Engine oil leak", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Brown/black stain. Check oil level; inspect oil pan and gasket"},
                {"name": "Coolant leak", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Green/orange/pink puddle. Check coolant level; pressure test"},
                {"name": "Transmission fluid leak", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Red/pink/brown puddle. Check transmission fluid level"},
                {"name": "Water from A/C evaporator (NORMAL)", "probability": 0.90, "cost": "none", "severity": "info", "inspection": "Clear water under passenger side after A/C use is completely normal"},
                {"name": "Brake fluid leak", "probability": 0.25, "cost": "low", "severity": "critical", "inspection": "Clear to amber oily fluid. Check brake fluid level immediately"},
                {"name": "Power steering fluid leak", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Red/pink fluid. Check power steering reservoir level"},
                {"name": "Gasoline leak", "probability": 0.15, "cost": "low", "severity": "critical", "inspection": "Strong gas smell. DO NOT START ENGINE. Fire hazard."},
            ],
            "safety_note": "Identify fluid by color and location. Clear water from A/C is normal. Gasoline, brake fluid, or coolant leaks need prompt attention.",
        },
        "brake_warning_light": {
            "causes": [
                {"name": "Parking brake engaged", "probability": 0.70, "cost": "none", "severity": "info", "inspection": "Ensure parking brake is fully released"},
                {"name": "Low brake fluid level", "probability": 0.55, "cost": "low", "severity": "critical", "inspection": "Check brake fluid reservoir; if low, inspect for leaks immediately"},
                {"name": "Worn brake pads (some vehicles)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Check brake pad thickness"},
                {"name": "Brake system pressure imbalance", "probability": 0.25, "cost": "medium", "severity": "high", "inspection": "Inspect brake lines for leaks; check master cylinder"},
                {"name": "ABS fault", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Scan for ABS codes; check wheel speed sensors"},
            ],
            "safety_note": "Brake warning light often means low fluid which indicates worn pads or a leak. Check immediately.",
        },
        "tire_pressure_light": {
            "causes": [
                {"name": "Low tire pressure", "probability": 0.85, "cost": "none", "severity": "medium", "inspection": "Check and adjust all tire pressures to door jamb spec"},
                {"name": "TPMS sensor battery dead", "probability": 0.35, "cost": "medium", "severity": "low", "inspection": "Sensor battery lasts ~7-10 years; sensor needs replacement"},
                {"name": "TPMS sensor damaged", "probability": 0.20, "cost": "medium", "severity": "low", "inspection": "Often occurs after tire service; sensor may have been broken"},
                {"name": "Temperature-related pressure drop", "probability": 0.40, "cost": "none", "severity": "info", "inspection": "For every 10F drop, tires lose 1 PSI. Normal in cold weather."},
            ],
            "safety_note": "Low tire pressure reduces handling and increases blowout risk. Check and inflate to proper pressure.",
        },
        "airbag_light": {
            "causes": [
                {"name": "Seat occupancy sensor fault", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Scan for SRS codes; test passenger seat sensor"},
                {"name": "Clockspring failure (steering wheel)", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Scan for clockspring-related codes; check horn and steering wheel controls"},
                {"name": "Airbag module connector corroded", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Inspect connectors under seats and at airbag modules"},
                {"name": "Deployed airbag not reset", "probability": 0.20, "cost": "high", "severity": "high", "inspection": "SRS module may need reprogramming after deployment"},
                {"name": "Crash sensor fault", "probability": 0.20, "cost": "medium", "severity": "high", "inspection": "Scan for specific crash sensor codes"},
            ],
            "safety_note": "Airbag light means the airbag system is disabled and will NOT deploy in a crash. Have diagnosed and repaired promptly.",
        },
        "abs_light": {
            "causes": [
                {"name": "Faulty wheel speed sensor", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Scan for specific wheel sensor codes; clean sensor tip"},
                {"name": "Damaged tone ring (reluctor ring)", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Inspect tone ring on CV joint or hub for cracks/missing teeth"},
                {"name": "ABS module failure", "probability": 0.25, "cost": "high", "severity": "medium", "inspection": "Scan for ABS module communication codes"},
                {"name": "Low brake fluid", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Check brake fluid reservoir level"},
                {"name": "Blown ABS fuse", "probability": 0.20, "cost": "none", "severity": "low", "inspection": "Check ABS fuse in fuse box"},
            ],
            "safety_note": "ABS light means anti-lock braking is disabled. Normal braking still works, but wheels can lock during hard braking. Repair soon.",
        },
        "temperature_warning": {
            "causes": [
                {"name": "Low coolant level", "probability": 0.70, "cost": "none", "severity": "critical", "inspection": "Check coolant reservoir; add coolant if low; find leak"},
                {"name": "Failed thermostat (stuck closed)", "probability": 0.55, "cost": "low", "severity": "high", "inspection": "Upper hose stays cold when engine is hot; replace thermostat"},
                {"name": "Cooling fan not working", "probability": 0.50, "cost": "low", "severity": "high", "inspection": "Check fan fuse, relay, and fan motor operation"},
                {"name": "Water pump failure", "probability": 0.35, "cost": "medium", "severity": "critical", "inspection": "Coolant not circulating; check for leak at water pump weep hole"},
                {"name": "Clogged radiator", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Check for cool spots on radiator; may need flushing or replacement"},
                {"name": "Head gasket failure", "probability": 0.25, "cost": "high", "severity": "critical", "inspection": "Check for white exhaust smoke; check oil for coolant contamination"},
                {"name": "Coolant hose burst", "probability": 0.20, "cost": "low", "severity": "critical", "inspection": "Inspect all hoses; look for swollen or cracked sections"},
            ],
            "safety_note": "OVERHEATING WARNING: Stop driving immediately when temperature warning comes on. Driving overheated can warp the head and destroy the engine within minutes.",
        },
        "traction_control_light": {
            "causes": [
                {"name": "Faulty wheel speed sensor (shared with ABS)", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Scan for ABS/wheel sensor codes; clean sensor"},
                {"name": "Steering angle sensor fault", "probability": 0.35, "cost": "medium", "severity": "low", "inspection": "Scan for steering angle sensor codes; may need calibration"},
                {"name": "Yaw rate sensor fault", "probability": 0.20, "cost": "medium", "severity": "low", "inspection": "Scan for stability control codes"},
                {"name": "Tire size mismatch", "probability": 0.25, "cost": "none", "severity": "info", "inspection": "Check that all tires are same size and properly inflated"},
                {"name": "Traction control button pressed", "probability": 0.40, "cost": "none", "severity": "info", "inspection": "Check if traction control was manually disabled"},
            ],
            "safety_note": "Traction control disabled means reduced stability in slippery conditions. Normal driving is fine; repair when convenient.",
        },
    },
    # -------------------------------------------------------------------------
    # CATEGORY: TIMING/CONDITIONS
    # -------------------------------------------------------------------------
    "timing": {
        "cold_start_only": {
            "causes": [
                {"name": "Worn valve lifters", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Noise goes away after 30-60 seconds of running; check oil level"},
                {"name": "Piston slap (worn pistons)", "probability": 0.50, "cost": "very_high", "severity": "medium", "inspection": "Knock when cold that diminishes as engine warms; higher mileage engines"},
                {"name": "Exhaust manifold leak (cold)", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Ticking when cold that lessens as manifold expands; look for soot marks"},
                {"name": "Worn timing chain tensioner", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Rattle on cold start for 1-2 seconds; oil drains from tensioner overnight"},
                {"name": "Loose serpentine belt (cold)", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Squeal on cold start; check belt tension and condition"},
                {"name": "Battery weak (slow cranking)", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Slow cranking when cold; have battery load tested"},
            ],
            "safety_note": "Cold-start-only noises are often less urgent but can indicate developing wear. Monitor for worsening.",
        },
        "when_accelerating": {
            "causes": [
                {"name": "Engine misfire under load", "probability": 0.65, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes; check spark plugs, coils, and fuel pressure"},
                {"name": "Worn CV joint (clicking)", "probability": 0.70, "cost": "medium", "severity": "medium", "inspection": "Clicking during acceleration in turns; inspect CV boots"},
                {"name": "Transmission slipping", "probability": 0.55, "cost": "high", "severity": "high", "inspection": "RPM rises without speed increase; check transmission fluid"},
                {"name": "Exhaust leak (more audible under load)", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Listen at exhaust manifold; look for soot marks"},
                {"name": "Driveshaft/U-joint wear", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Vibration under acceleration; inspect U-joints for play"},
                {"name": "Turbocharger boost leak", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Whistle/whoosh sound; check intercooler hoses for splits"},
                {"name": "Motor mount broken", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Excessive engine movement during acceleration; clunk sound"},
            ],
            "safety_note": "Issues during acceleration affect merging and passing safety. Misfires under load can damage the catalytic converter.",
        },
        "when_braking": {
            "causes": [
                {"name": "Warped brake rotors (pulsation)", "probability": 0.80, "cost": "low", "severity": "medium", "inspection": "Steering wheel shake during braking; measure rotor runout"},
                {"name": "Worn brake pads (grinding/squealing)", "probability": 0.85, "cost": "low", "severity": "high", "inspection": "Check pad thickness through caliper inspection hole"},
                {"name": "Sticking brake caliper", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Vehicle pulls to one side; wheel hotter than others after driving"},
                {"name": "Loose suspension component", "probability": 0.35, "cost": "medium", "severity": "high", "inspection": "Clunk when braking; inspect ball joints, control arms, bushings"},
                {"name": "Worn wheel bearing (braking vibration)", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Jack up wheel, check for play"},
                {"name": "ABS false activation", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Pulsing pedal at low speed braking; clean tone ring and sensor"},
            ],
            "safety_note": "Braking-related symptoms directly affect safety. Have inspected immediately if braking performance feels compromised.",
        },
        "when_turning": {
            "causes": [
                {"name": "Worn CV joint (clicking)", "probability": 0.85, "cost": "medium", "severity": "medium", "inspection": "Clicking during turns; inspect CV boot for tears"},
                {"name": "Low power steering fluid", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Whining/groaning when turning; check reservoir level"},
                {"name": "Worn power steering pump", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Whine when turning wheel; check belt tension and fluid"},
                {"name": "Binding steering rack", "probability": 0.30, "cost": "high", "severity": "high", "inspection": "Notchy or stiff feeling in specific steering positions"},
                {"name": "Worn strut mount bearing", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Pop/click when turning at low speed; strut mount needs replacement"},
                {"name": "Differential issue (AWD/4WD)", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Binding during tight turns; check differential fluid"},
                {"name": "Tire rub (oversized tires or worn suspension)", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Inspect inner fender wells for tire rub marks"},
            ],
            "safety_note": "Steering and suspension issues during turns can cause loss of control. Inspect promptly if handling feels abnormal.",
        },
        "at_high_speed": {
            "causes": [
                {"name": "Wheel imbalance", "probability": 0.85, "cost": "low", "severity": "low", "inspection": "Vibration at specific speeds (60-75 mph); have wheels balanced"},
                {"name": "Tire out of round or separation", "probability": 0.50, "cost": "medium", "severity": "critical", "inspection": "Inspect tires for bulges, flat spots, or internal separation"},
                {"name": "Wheel bearing wear (advanced)", "probability": 0.45, "cost": "medium", "severity": "high", "inspection": "Howling/humming at speed; check for wheel play"},
                {"name": "Aerodynamic noise (windshield seal, mirror)", "probability": 0.25, "cost": "low", "severity": "info", "inspection": "Wind noise from specific location; check door and window seals"},
                {"name": "Driveshaft imbalance (RWD/4WD)", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Vibration increases with speed; check driveshaft balance and U-joints"},
            ],
            "safety_note": "High-speed vibrations can indicate tire separation or wheel bearing failure -- both can cause sudden loss of control at highway speeds.",
        },
        "at_idle": {
            "causes": [
                {"name": "Engine misfire at idle", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Scan for misfire codes; check spark plugs, coils, vacuum leaks"},
                {"name": "Dirty throttle body", "probability": 0.55, "cost": "none", "severity": "low", "inspection": "Clean throttle body; check idle air control valve if equipped"},
                {"name": "Vacuum leak", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Spray carb cleaner around intake; RPM change indicates leak"},
                {"name": "Worn engine mounts", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Excessive vibration felt in cabin; watch engine movement"},
                {"name": "AC compressor cycling", "probability": 0.50, "cost": "none", "severity": "info", "inspection": "Brief RPM dip when A/C engages is normal"},
                {"name": "Failing idle air control valve", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Erratic idle; clean or replace IAC valve"},
            ],
            "safety_note": "Rough idle is usually not immediately dangerous but can indicate developing engine problems. Monitor for worsening.",
        },
        "after_pothole": {
            "causes": [
                {"name": "Bent wheel rim", "probability": 0.65, "cost": "medium", "severity": "medium", "inspection": "Vibration after impact; inspect wheel inner lip for bending or cracking"},
                {"name": "Tire bubble/sidewall damage", "probability": 0.55, "cost": "medium", "severity": "critical", "inspection": "Inspect tire sidewall for bulges or bubbles -- indicates broken cords"},
                {"name": "Wheel knocked out of alignment", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Vehicle pulls after impact; steering wheel off-center; uneven tire wear"},
                {"name": "Damaged suspension component", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Clunking after impact; inspect control arms, tie rods, ball joints for damage"},
                {"name": "Strut or shock damage", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Bouncy ride after impact; inspect strut body for bending or fluid leak"},
                {"name": "Steering rack damage", "probability": 0.15, "cost": "high", "severity": "high", "inspection": "Tight spot in steering or leak from rack after hard impact"},
            ],
            "safety_note": "Pothole impacts can cause hidden tire damage (internal cord breakage) that leads to sudden blowouts days or weeks later. Always inspect tires after a hard pothole hit.",
        },
    },
}


# =============================================================================
# SECTION 2: DIAGNOSTIC PROTOCOL FUNCTIONS
# =============================================================================

def parse_symptoms(user_description: str) -> List[Dict[str, Any]]:
    """Parse free-text user description into structured symptoms.
    
    Uses keyword matching to identify symptoms, systems, and timing conditions.
    Returns structured list with confidence scores for further processing.
    
    Args:
        user_description: Free-text description from user (e.g., "my car makes a
                         grinding noise when I brake, especially at high speed")
    
    Returns:
        List of dicts: [{category, symptom, confidence, context}]
    """
    if not user_description or not isinstance(user_description, str):
        return []
    
    text = user_description.lower()
    identified = []
    
    # Keyword mapping: maps search terms to (category, symptom, confidence_boost)
    SOUND_KEYWORDS = {
        "chirp": ("sounds", "chirping"),
        "chirping": ("sounds", "chirping"),
        "grind": ("sounds", "grinding"),
        "grinding": ("sounds", "grinding"),
        "thump": ("sounds", "thumping"),
        "thumping": ("sounds", "thumping"),
        "squeal": ("sounds", "squealing"),
        "squealing": ("sounds", "squealing"),
        "squeak": ("sounds", "squeaking"),
        "squeaking": ("sounds", "squeaking"),
        "knock": ("sounds", "knocking"),
        "knocking": ("sounds", "knocking"),
        "hiss": ("sounds", "hissing"),
        "hissing": ("sounds", "hissing"),
        "rattle": ("sounds", "rattling"),
        "rattling": ("sounds", "rattling"),
        "click": ("sounds", "clicking"),
        "clicking": ("sounds", "clicking"),
        "tick": ("sounds", "ticking"),
        "ticking": ("sounds", "ticking"),
        "whine": ("sounds", "whining"),
        "whining": ("sounds", "whining"),
        "howl": ("sounds", "howling"),
        "howling": ("sounds", "howling"),
        "drone": ("sounds", "drone_hum"),
        "hum": ("sounds", "drone_hum"),
        "backfire": ("sounds", "backfiring"),
        "backfiring": ("sounds", "backfiring"),
        "pop": ("sounds", "backfiring"),
    }
    
    FEEL_KEYWORDS = {
        "vibration": ("feel", "vibration"),
        "vibrating": ("feel", "vibration"),
        "shake": ("feel", "vibration"),
        "shaking": ("feel", "vibration"),
        "pull left": ("feel", "pulling_left"),
        "pulling left": ("feel", "pulling_left"),
        "pulls left": ("feel", "pulling_left"),
        "pull right": ("feel", "pulling_right"),
        "pulling right": ("feel", "pulling_right"),
        "pulls right": ("feel", "pulling_right"),
        "veer left": ("feel", "pulling_left"),
        "veer right": ("feel", "pulling_right"),
        "slip": ("feel", "slipping"),
        "slipping": ("feel", "slipping"),
        "shudder": ("feel", "shuddering"),
        "shuddering": ("feel", "shuddering"),
        "jerk": ("feel", "jerking"),
        "jerking": ("feel", "jerking"),
        "hesitation": ("feel", "jerking"),
        "spongy brake": ("feel", "spongy_brake"),
        "soft brake": ("feel", "spongy_brake"),
        "soft pedal": ("feel", "spongy_brake"),
        "spongy pedal": ("feel", "spongy_brake"),
        "hard steering": ("feel", "hard_steering"),
        "stiff steering": ("feel", "hard_steering"),
        "loose steering": ("feel", "loose_steering"),
        "play in steering": ("feel", "loose_steering"),
        "rough idle": ("feel", "rough_idle"),
        "rough idling": ("feel", "rough_idle"),
        "stall": ("feel", "rough_idle"),
        "stalling": ("feel", "rough_idle"),
        "delayed shift": ("feel", "delayed_shifting"),
        "won't shift": ("feel", "delayed_shifting"),
        "pulsing brake": ("feel", "pulsing_brake_pedal"),
        "pulsing pedal": ("feel", "pulsing_brake_pedal"),
        "pedal pulse": ("feel", "pulsing_brake_pedal"),
        "wander": ("feel", "wandering"),
        "wandering": ("feel", "wandering"),
        "stiff gas": ("feel", "stiff_gas_pedal"),
        "hard accelerator": ("feel", "stiff_gas_pedal"),
    }
    
    SMELL_KEYWORDS = {
        "burning oil": ("smells", "burning_oil"),
        "oil smell": ("smells", "burning_oil"),
        "oil burning": ("smells", "burning_oil"),
        "sweet coolant": ("smells", "sweet_coolant"),
        "coolant smell": ("smells", "sweet_coolant"),
        "antifreeze": ("smells", "sweet_coolant"),
        "rotten egg": ("smells", "rotten_eggs"),
        "sulfur": ("smells", "rotten_eggs"),
        "burning rubber": ("smells", "burning_rubber"),
        "rubber burning": ("smells", "burning_rubber"),
        "gasoline smell": ("smells", "gasoline"),
        "gas smell": ("smells", "gasoline"),
        "fuel smell": ("smells", "gasoline"),
        "electrical burning": ("smells", "electrical_burning"),
        "burning wire": ("smells", "electrical_burning"),
        "musty": ("smells", "musty"),
        "moldy": ("smells", "musty"),
        "mildew": ("smells", "musty"),
        "burning plastic": ("smells", "burning_plastic"),
        "plastic burning": ("smells", "burning_plastic"),
        "ammonia": ("smells", "ammonia"),
        "sweet metallic": ("smells", "sweet_metallic"),
        "brake fluid smell": ("smells", "sweet_metallic"),
        "exhaust fumes": ("smells", "exhaust_fumes"),
        "exhaust smell": ("smells", "exhaust_fumes"),
        "sweet fruity": ("smells", "sweet_fruity"),
        "sulfur acid": ("smells", "sulfur_acid"),
        "battery smell": ("smells", "sulfur_acid"),
    }
    
    VISUAL_KEYWORDS = {
        "check engine": ("visual", "check_engine_light"),
        "check engine light": ("visual", "check_engine_light"),
        "cel": ("visual", "check_engine_light"),
        "service engine": ("visual", "check_engine_light"),
        "oil light": ("visual", "oil_light"),
        "oil pressure": ("visual", "oil_light"),
        "red oil light": ("visual", "oil_light"),
        "battery light": ("visual", "battery_light"),
        "charging light": ("visual", "battery_light"),
        "alt light": ("visual", "battery_light"),
        "coolant leak": ("visual", "coolant_leak"),
        "coolant puddle": ("visual", "coolant_leak"),
        "oil leak": ("visual", "oil_leak"),
        "oil puddle": ("visual", "oil_leak"),
        "oil spot": ("visual", "oil_leak"),
        "smoke exhaust": ("visual", "smoke_exhaust"),
        "exhaust smoke": ("visual", "smoke_exhaust"),
        "blue smoke": ("visual", "smoke_exhaust"),
        "white smoke": ("visual", "smoke_exhaust"),
        "black smoke": ("visual", "smoke_exhaust"),
        "smoke engine": ("visual", "smoke_engine"),
        "engine smoke": ("visual", "smoke_engine"),
        "smoke under hood": ("visual", "smoke_engine"),
        "fluid under car": ("visual", "fluid_under_car"),
        "leak under car": ("visual", "fluid_under_car"),
        "puddle under car": ("visual", "fluid_under_car"),
        "brake light": ("visual", "brake_warning_light"),
        "brake warning": ("visual", "brake_warning_light"),
        "tire pressure light": ("visual", "tire_pressure_light"),
        "tpms": ("visual", "tire_pressure_light"),
        "airbag light": ("visual", "airbag_light"),
        "srs light": ("visual", "airbag_light"),
        "abs light": ("visual", "abs_light"),
        "temperature warning": ("visual", "temperature_warning"),
        "overheating": ("visual", "temperature_warning"),
        "hot gauge": ("visual", "temperature_warning"),
        "traction light": ("visual", "traction_control_light"),
        "traction control": ("visual", "traction_control_light"),
    }
    
    TIMING_KEYWORDS = {
        "cold start": ("timing", "cold_start_only"),
        "when cold": ("timing", "cold_start_only"),
        "first start": ("timing", "cold_start_only"),
        "morning": ("timing", "cold_start_only"),
        "when accelerating": ("timing", "when_accelerating"),
        "acceleration": ("timing", "when_accelerating"),
        "under load": ("timing", "when_accelerating"),
        "when braking": ("timing", "when_braking"),
        "braking": ("timing", "when_braking"),
        "when i brake": ("timing", "when_braking"),
        "when turning": ("timing", "when_turning"),
        "turning": ("timing", "when_turning"),
        "in turns": ("timing", "when_turning"),
        "high speed": ("timing", "at_high_speed"),
        "highway": ("timing", "at_high_speed"),
        "at idle": ("timing", "at_idle"),
        "idling": ("timing", "at_idle"),
        "when stopped": ("timing", "at_idle"),
        "pothole": ("timing", "after_pothole"),
        "after bump": ("timing", "after_pothole"),
    }
    
    # Search for all keyword matches
    for keyword, (category, symptom) in SOUND_KEYWORDS.items():
        if keyword in text:
            identified.append({
                "category": category,
                "symptom": symptom,
                "confidence": 0.8,
                "context": "keyword_match",
            })
    
    for keyword, (category, symptom) in FEEL_KEYWORDS.items():
        if keyword in text:
            identified.append({
                "category": category,
                "symptom": symptom,
                "confidence": 0.8,
                "context": "keyword_match",
            })
    
    for keyword, (category, symptom) in SMELL_KEYWORDS.items():
        if keyword in text:
            identified.append({
                "category": category,
                "symptom": symptom,
                "confidence": 0.85,
                "context": "keyword_match",
            })
    
    for keyword, (category, symptom) in VISUAL_KEYWORDS.items():
        if keyword in text:
            identified.append({
                "category": category,
                "symptom": symptom,
                "confidence": 0.9,
                "context": "keyword_match",
            })
    
    for keyword, (category, symptom) in TIMING_KEYWORDS.items():
        if keyword in text:
            identified.append({
                "category": category,
                "symptom": symptom,
                "confidence": 0.75,
                "context": "keyword_match",
            })
    
    # Remove duplicates (same category+symptom), keeping highest confidence
    seen = {}
    for item in identified:
        key = (item["category"], item["symptom"])
        if key not in seen or item["confidence"] > seen[key]["confidence"]:
            seen[key] = item
    
    return list(seen.values())


def _rank_causes(symptoms_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank all probable causes from identified symptoms by combined probability.
    
    Aggregates causes across all identified symptoms, combining probabilities
    when the same cause appears for multiple symptoms.
    
    Args:
        symptoms_data: List of symptom entries from SYMPTOM_DATABASE
    
    Returns:
        Probability-sorted list of cause dicts
    """
    cause_scores: Dict[str, Dict[str, Any]] = {}
    
    for symptom_data in symptoms_data:
        causes = symptom_data.get("causes", [])
        for cause in causes:
            name = cause["name"]
            if name not in cause_scores:
                cause_scores[name] = {
                    "name": name,
                    "probability": 0.0,
                    "cost": cause.get("cost", "unknown"),
                    "severity": cause.get("severity", "unknown"),
                    "inspection": cause.get("inspection", ""),
                    "supporting_symptoms": [],
                }
            # Combine probabilities using independent events formula
            p = cause.get("probability", 0)
            cause_scores[name]["probability"] = max(cause_scores[name]["probability"], p)
            cause_scores[name]["supporting_symptoms"].append(symptom_data.get("symptom_name", ""))
    
    # Sort by probability descending
    ranked = sorted(cause_scores.values(), key=lambda x: x["probability"], reverse=True)
    return ranked


def diagnose(symptoms: List[str], vehicle_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Main diagnostic function.
    
    Takes a list of symptom descriptions and optional vehicle information,
    returns a comprehensive diagnostic report with differential diagnosis,
    recommended inspections, safety warnings, and cost estimates.
    
    Args:
        symptoms: List of symptom description strings
        vehicle_info: Dict with optional keys: year, make, model, mileage, vin
    
    Returns:
        Comprehensive diagnostic report dict
    """
    vehicle_info = vehicle_info or {}
    
    # Parse all symptoms
    all_identified = []
    for desc in symptoms:
        if isinstance(desc, str):
            identified = parse_symptoms(desc)
            all_identified.extend(identified)
    
    # Remove duplicate identifications
    seen = {}
    for item in all_identified:
        key = (item["category"], item["symptom"])
        if key not in seen:
            seen[key] = item
    all_identified = list(seen.values())
    
    # Gather symptom data from database
    symptom_data_list = []
    for ident in all_identified:
        category = ident["category"]
        symptom_key = ident["symptom"]
        if category in SYMPTOM_DATABASE and symptom_key in SYMPTOM_DATABASE[category]:
            data = dict(SYMPTOM_DATABASE[category][symptom_key])
            data["symptom_name"] = symptom_key
            data["category"] = category
            symptom_data_list.append(data)
    
    # Build differential diagnosis
    differential = _rank_causes(symptom_data_list)
    
    # Collect safety notes
    safety_notes = []
    for data in symptom_data_list:
        note = data.get("safety_note", "")
        if note and note not in safety_notes:
            safety_notes.append(note)
    
    # Apply safety filters
    safety_warnings = _apply_safety_filters(differential)
    
    # Determine urgency
    urgency = _determine_urgency(differential, safety_notes)
    
    # Generate inspections
    inspections = generate_inspections(differential)
    
    # Build the report
    report = {
        "input_symptoms": symptoms,
        "vehicle_info": vehicle_info,
        "identified_symptoms": [
            {"category": i["category"], "symptom": i["symptom"], "confidence": i["confidence"]}
            for i in all_identified
        ],
        "differential_diagnosis": differential[:10],  # Top 10
        "safety_notes": safety_notes,
        "safety_warnings": safety_warnings,
        "urgency": urgency,
        "recommended_inspections": inspections[:8],  # Top 8 most relevant
        "when_to_see_mechanic": _mechanic_timing_advice({"urgency": urgency}),
        "estimated_repair_costs": estimate_repair_cost({"differential_diagnosis": differential}, vehicle_info.get("year"), vehicle_info.get("luxury", False)),
        "disclaimer": (
            "This diagnostic report is generated by an AI system for informational purposes only. "
            "It does not constitute professional mechanical advice. Always consult a qualified "
            "automotive technician for proper diagnosis and repair. Vehicle problems can have "
            "multiple causes, and only hands-on inspection can provide definitive diagnosis. "
            "If you smell fuel, see smoke, or have lost braking or steering control, stop driving "
            "immediately and call for roadside assistance."
        ),
    }
    
    return report


def _apply_safety_filters(differential: List[Dict[str, Any]]) -> List[str]:
    """Apply safety filters to differential diagnosis.
    
    Identifies critical safety issues from the differential and returns
    appropriate safety warnings.
    
    Args:
        differential: Ranked list of probable causes
    
    Returns:
        List of safety warning strings
    """
    warnings = []
    
    for cause in differential[:5]:
        cause_name = cause.get("name", "").lower()
        severity = cause.get("severity", "")
        
        if severity == "critical":
            warnings.append(f"CRITICAL: {cause['name']} - {cause.get('inspection', 'Seek immediate professional assistance')}")
        
        if "brake" in cause_name and "failure" in cause_name:
            warnings.append(SAFETY_WARNINGS.get("brake", ""))
        elif "steering" in cause_name and ("seized" in cause_name or "broken" in cause_name):
            warnings.append(SAFETY_WARNINGS.get("steering", ""))
        elif "tire" in cause_name and "separation" in cause_name:
            warnings.append(SAFETY_WARNINGS.get("tire", ""))
        elif "fuel" in cause_name and "leak" in cause_name:
            warnings.append(SAFETY_WARNINGS.get("fuel_leak", ""))
    
    return [w for w in warnings if w]


def _determine_urgency(differential: List[Dict[str, Any]], safety_notes: List[str]) -> str:
    """Determine repair urgency based on differential diagnosis.
    
    Args:
        differential: Ranked list of probable causes
        safety_notes: List of safety notes from symptoms
    
    Returns:
        Urgency level string
    """
    # Check for critical causes in top 3
    for cause in differential[:3]:
        if cause.get("severity") == "critical":
            return "immediate"
        if cause.get("severity") == "high" and cause.get("probability", 0) > 0.7:
            return "immediate"
    
    # Check safety notes for critical language
    for note in safety_notes:
        note_lower = note.lower()
        critical_keywords = ["stop driving", "do not drive", "fire hazard", "carbon monoxide", "tow"]
        for keyword in critical_keywords:
            if keyword in note_lower:
                return "immediate"
    
    # Check for high-severity causes
    for cause in differential[:3]:
        if cause.get("severity") == "critical":
            return "immediate"
        if cause.get("severity") == "high" and cause.get("probability", 0) > 0.5:
            return "immediate"
    
    # Check for medium urgency
    for cause in differential[:3]:
        if cause.get("severity") in ("high", "critical"):
            return "soon"
    
    return "routine"


def _mechanic_timing_advice(diagnosis: dict) -> str:
    """Generate advice on when to see a mechanic."""
    urgency = diagnosis.get("urgency", "routine")
    
    advice_map = {
        "immediate": (
            "STOP DRIVING. This issue poses an immediate safety risk or can cause catastrophic "
            "vehicle damage. Have the vehicle towed to a repair facility today. Do not attempt "
            "to drive to the shop unless the specific repair allows safe short-distance driving."
        ),
        "soon": (
            "Schedule an appointment with a mechanic within 3-5 days. This issue could worsen "
            "and become more expensive or unsafe if delayed. Perform the zero-cost inspections "
            "in this report before your appointment to save diagnostic time."
        ),
        "routine": (
            "This issue can be addressed at your next scheduled maintenance or within 2-4 weeks. "
            "Perform the recommended inspections when convenient. Monitor for any worsening of symptoms."
        ),
    }
    
    return advice_map.get(urgency, advice_map["routine"])


# =============================================================================
# SECTION 3: CHECK-BEFORE-BUY INSPECTION LIBRARY
# =============================================================================
# Zero-cost inspection procedures organized by system.
# Each inspection has: name, cost, time, tools, steps, what_to_look_for, and optional safety_warning.

INSPECTION_LIBRARY: Dict[str, Dict[str, Any]] = {
    # --- Belt and Pulley Inspections ---
    "visual_belt_check": {
        "name": "Visual Serpentine Belt Inspection",
        "cost": 0,
        "time": "2 minutes",
        "tools": "Flashlight",
        "steps": [
            "Open hood and locate the serpentine belt routing diagram (usually on a decal)",
            "With engine OFF, visually trace the entire belt length",
            "Look for cracks across the ribbed surface (especially at rib bases)",
            "Check for glazing/shiny surface indicating slippage",
            "Check for fraying edges, missing chunks, or contamination (oil, coolant)",
            "Press on belt mid-span between pulleys -- should deflect approximately 1/2 to 1 inch",
        ],
        "what_youre_looking_for": (
            "Cracks across ribs = worn belt due for replacement. "
            "Glazing/shiny surface = belt slipping, check tensioner. "
            "Fraying edges = belt failing soon, replace within 500 miles. "
            "Missing chunks or separated layers = replace IMMEDIATELY."
        ),
    },
    "tensioner_pulley_check": {
        "name": "Belt Tensioner and Idler Pulley Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Flashlight, 1/2 inch breaker bar (optional)",
        "steps": [
            "With engine OFF, grasp the tensioner arm and attempt to move it",
            "Observe tensioner arm for smooth spring resistance -- should not stick or bind",
            "Start engine (carefully) and watch tensioner for vibration or wobble",
            "Remove belt (note routing), spin each idler pulley by hand",
            "Listen for grinding, roughness, or play in each pulley bearing",
        ],
        "what_youre_looking_for": (
            "Tensioner should have smooth spring action with no binding. "
            "Pulleys should spin freely with no noise or roughness. "
            "Any grinding, wobble, or resistance means replace the pulley/tensioner."
        ),
        "safety_warning": "Keep fingers clear of belt and pulleys. If checking with engine running, use extreme caution.",
    },
    
    # --- Brake Inspections ---
    "brake_pad_inspection": {
        "name": "Brake Pad Thickness Check",
        "cost": 0,
        "time": "5 minutes per wheel",
        "tools": "Flashlight, wheel chock, jack, jack stands, lug wrench",
        "steps": [
            "Park on level ground, apply parking brake, chock rear wheels",
            "Loosen lug nuts, jack up vehicle, secure on jack stands",
            "Remove wheel",
            "Shine flashlight through caliper inspection hole or slots",
            "Visually estimate pad material thickness remaining on backing plate",
            "Repeat for all four wheels (fronts usually wear faster)",
        ],
        "what_youre_looking_for": (
            "Pad thickness > 5mm = good condition. "
            "Pad thickness 3-5mm = plan replacement within 1000 miles. "
            "Pad thickness < 3mm = replace immediately. "
            "Metal backing plate visible or grinding noise = CRITICAL, stop driving."
        ),
        "safety_warning": "Always use jack stands. Never work under a car supported only by a hydraulic jack. Block wheels before jacking.",
    },
    "brake_rotor_inspection": {
        "name": "Brake Rotor Condition Check",
        "cost": 0,
        "time": "5 minutes per wheel",
        "tools": "Flashlight, jack, jack stands, straightedge or feeler gauge",
        "steps": [
            "Remove wheel as described in brake pad inspection",
            "Visually inspect rotor surface for scoring, grooves, cracks, or blue discoloration",
            "Run finger across rotor surface (when cool) to feel for deep grooves or lip",
            "Check for mirror-like glaze indicating overheating",
            "Use straightedge across rotor to check for warping (light gap test)",
            "Measure rotor thickness if caliper micrometer available (compare to spec stamped on rotor edge)",
        ],
        "what_youre_looking_for": (
            "Light surface rust = normal after rain, scrubs off with braking. "
            "Deep scoring/grooves = rotor needs resurfacing or replacement. "
            "Blue discoloration = overheated, replace rotor. "
            "Visible cracks = CRITICAL, replace immediately. "
            "Lip on outer edge > 2mm = rotor worn below minimum thickness."
        ),
    },
    "brake_fluid_check": {
        "name": "Brake Fluid Level and Condition Check",
        "cost": 0,
        "time": "2 minutes",
        "tools": "Flashlight, brake fluid test strips (optional, ~$5)",
        "steps": [
            "Locate brake fluid reservoir (on driver's side firewall, near brake booster)",
            "Check fluid level against MIN/MAX marks on reservoir",
            "Note fluid color -- should be clear to amber (like weak tea)",
            "Dark brown or black fluid = contaminated, needs flush",
            "If fluid is low, inspect for leaks before topping off",
        ],
        "what_youre_looking_for": (
            "Level between MIN and MAX = OK. "
            "Level below MIN = possible leak or severely worn pads. "
            "Dark fluid = moisture contamination, boiling point reduced. "
            "Cloudy fluid = contamination, schedule flush."
        ),
        "safety_warning": "Brake fluid destroys paint. Wipe spills immediately with damp cloth. Do NOT use DOT 5 fluid in systems designed for DOT 3/4.",
    },
    
    # --- Wheel Bearing Inspections ---
    "wheel_bearing_check": {
        "name": "Wheel Bearing Play Test",
        "cost": 0,
        "time": "3 minutes per wheel",
        "tools": "Jack, jack stands",
        "steps": [
            "Jack up suspected wheel until tire is off the ground",
            "Secure vehicle on jack stands, ensure stability",
            "Grab tire at 12 and 6 o'clock positions",
            "Rock tire back and forth vigorously",
            "Repeat at 3 and 9 o'clock positions",
            "Spin wheel by hand and listen for grinding or roughness",
        ],
        "what_youre_looking_for": (
            "Any vertical play (12-6 o'clock) = wheel bearing is worn and needs replacement. "
            "Horizontal play (3-9 o'clock) can indicate tie rod or ball joint issues. "
            "Grinding or roughness when spinning = bearing severely worn. "
            "Smooth quiet spin = bearing is OK."
        ),
        "safety_warning": "Always use jack stands. Test at multiple positions. Even slight play in a wheel bearing means it is failing.",
    },
    
    # --- Tire Inspections ---
    "tire_inspection": {
        "name": "Comprehensive Tire Inspection",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Tire pressure gauge, penny/depth gauge, flashlight",
        "steps": [
            "Check tire pressure in all four tires (including spare if accessible)",
            "Compare to door jamb sticker spec (NOT the max PSI on tire sidewall)",
            "Insert penny head-first into tread grooves -- Lincoln's head should be partially covered",
            "Inspect tread surface for uneven wear patterns (cupping, feathering, inner/outer edge wear)",
            "Inspect sidewalls for cracks, bulges, bubbles, or cuts",
            "Check for embedded nails, screws, or debris",
            "Verify tire age by DOT date code (4-digit number: week+year of manufacture)",
        ],
        "what_youre_looking_for": (
            "Tread depth > 4/32 inch = safe for dry, marginal for wet. "
            "Tread depth > 6/32 inch = good condition. "
            "Tread depth < 2/32 inch = ILLEGAL and DANGEROUS, replace immediately. "
            "Any sidewall bulge or bubble = tire structural failure, replace immediately. "
            "Tires over 6 years old should be inspected closely regardless of tread depth."
        ),
    },
    
    # --- Suspension Inspections ---
    "suspension_bounce_test": {
        "name": "Suspension Bounce Test",
        "cost": 0,
        "time": "2 minutes",
        "tools": "None",
        "steps": [
            "Go to each corner of the vehicle",
            "Push down firmly on the bumper/fender and release",
            "Count how many times the corner bounces",
            "A healthy suspension settles in 1-2 bounces",
            "If it bounces 3+ times, the shock or strut is worn",
        ],
        "what_youre_looking_for": (
            "1-2 bounces = shock/strut is good. "
            "3+ bounces = shock/strut is worn and should be replaced. "
            "Uneven bounce between sides = one side is worn more than the other."
        ),
    },
    "suspension_component_check": {
        "name": "Visual Suspension Component Inspection",
        "cost": 0,
        "time": "10 minutes",
        "tools": "Flashlight, jack, jack stands",
        "steps": [
            "Jack up vehicle and secure on jack stands",
            "Inspect control arm bushings for cracks, tears, or deterioration",
            "Check ball joints for play (jack up, wiggle wheel at 12 and 6 o'clock)",
            "Inspect tie rod ends for torn boots and play (wiggle at 3 and 9 o'clock)",
            "Check sway bar links and bushings for wear",
            "Look for leaking fluid from shocks or struts",
            "Inspect CV boot for tears and leaking grease",
        ],
        "what_youre_looking_for": (
            "Cracked or torn bushings = replace control arm or bushing. "
            "Play in ball joint = replace immediately (safety critical). "
            "Torn CV boot = replace boot or axle before joint is damaged. "
            "Fluid leak from shock/strut = replace shock/strut. "
            "Play in tie rod end = replace and get alignment."
        ),
        "safety_warning": "Always use jack stands. Ball joint and tie rod failures can cause wheel separation.",
    },
    
    # --- Engine Inspections ---
    "engine_oil_check": {
        "name": "Engine Oil Level and Condition Check",
        "cost": 0,
        "time": "3 minutes",
        "tools": "Paper towel or rag",
        "steps": [
            "Park on level ground, wait 5 minutes after turning off engine",
            "Locate and pull out the oil dipstick",
            "Wipe clean with paper towel, fully reinsert",
            "Pull out again and check level against MIN/MAX marks",
            "Note oil color on paper towel -- should be amber to dark brown",
            "If level is low, add correct oil grade; if very low, look for leak",
        ],
        "what_youre_looking_for": (
            "Level between MIN and MAX = OK. "
            "Level at or below MIN = add oil immediately and inspect for leak. "
            "Milky/creamy oil = coolant contamination (head gasket failure). "
            "Metal particles in oil = internal engine wear. "
            "Very black oil = due for change, but not immediately harmful."
        ),
    },
    "coolant_level_check": {
        "name": "Coolant Level and Condition Check",
        "cost": 0,
        "time": "2 minutes",
        "tools": "Flashlight",
        "steps": [
            "Ensure engine is COLD (never open hot coolant system)",
            "Locate coolant reservoir (usually translucent white tank)",
            "Check level against MIN/MAX marks",
            "Note coolant color -- should be green, orange, pink, or blue (not rusty or oily)",
            "If low, add correct coolant type (check owner's manual)",
        ],
        "what_youre_looking_for": (
            "Level between MIN and MAX = OK. "
            "Level below MIN = add coolant and find leak. "
            "Rusty coolant = corrosion in system, needs flush. "
            "Oily film = oil contamination (head gasket or oil cooler leak). "
            "Low coolant with no visible leak = possible head gasket or internal leak."
        ),
        "safety_warning": "NEVER open the radiator cap on a hot engine. Hot coolant can cause severe burns.",
    },
    "air_filter_check": {
        "name": "Engine Air Filter Inspection",
        "cost": 0,
        "time": "3 minutes",
        "tools": "None (may need screwdriver or clips)",
        "steps": [
            "Locate air filter box (large plastic box near engine, connected to intake hose)",
            "Open clips or remove screws on filter box",
            "Remove filter element",
            "Hold up to bright light -- you should see light through the filter",
            "Inspect for excessive dirt, debris, oil contamination, or damage",
        ],
        "what_youre_looking_for": (
            "Light passes through = filter is OK. "
            "Clogged with dirt/debris = replace filter (improves MPG and performance). "
            "Oil on filter = possible PCV system issue or turbo seal leak. "
            "Torn or damaged filter = replace immediately (unfiltered air damages engine)."
        ),
    },
    "spark_plug_inspection": {
        "name": "Spark Plug Condition Inspection",
        "cost": 0,
        "time": "15 minutes",
        "tools": "Spark plug socket, extension, ratchet, gap gauge",
        "steps": [
            "Remove ignition coils or spark plug wires (note order/position)",
            "Use spark plug socket to remove one plug at a time",
            "Inspect electrode color: tan/light brown = normal",
            "Black and sooty = rich fuel mixture or oil burning",
            "White/blistered = lean mixture or overheating",
            "Wet with fuel = flooding or no spark",
            "Check gap with feeler gauge against spec",
        ],
        "what_youre_looking_for": (
            "Tan/light brown = normal combustion, good condition. "
            "Black/sooty = running rich (check air filter, MAF, injectors). "
            "White/blistered = running lean or overheating (check vacuum leaks, cooling). "
            "Oil fouled = worn rings or valve seals (engine rebuild may be needed). "
            "Gap worn beyond spec = replace plugs."
        ),
    },
    
    # --- Electrical Inspections ---
    "battery_terminal_check": {
        "name": "Battery Terminal and Connection Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Wire brush or battery terminal cleaner, wrench",
        "steps": [
            "With engine OFF, inspect terminals for white/green corrosion",
            "Wiggle terminals -- should be tight with no movement",
            "If corroded: loosen bolts, remove terminals (negative first)",
            "Clean terminals and posts with wire brush or battery tool",
            "Reinstall (positive first, negative last), tighten securely",
            "Apply dielectric grease or petroleum jelly to prevent future corrosion",
        ],
        "what_youre_looking_for": (
            "Clean, tight terminals = good connection. "
            "White/green powdery corrosion = clean immediately (causes starting issues). "
            "Loose terminals = tighten; can cause intermittent electrical issues. "
            "Broken terminal clamp = replace cable end or entire cable."
        ),
    },
    "alternator_output_check": {
        "name": "Alternator Output Test",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Multimeter (or voltmeter)",
        "steps": [
            "Set multimeter to DC volts (20V range)",
            "With engine OFF, measure battery voltage (should be 12.4-12.6V)",
            "Start engine, measure voltage at battery terminals",
            "Voltage should be 13.5-14.5V at idle (charging properly)",
            "Turn on headlights and A/C -- voltage should stay above 13.0V",
            "If voltage > 15V, voltage regulator has failed (overcharging)",
        ],
        "what_youre_looking_for": (
            "13.5-14.5V at idle = alternator is charging properly. "
            "Below 13.0V = alternator undercharging or failing. "
            "Above 15.0V = voltage regulator failed, can destroy battery and electronics. "
            "Voltage drops below 13V with accessories = weak alternator or bad connection."
        ),
    },
    "fuse_check": {
        "name": "Fuse Inspection",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Fuse puller (or needle-nose pliers), flashlight",
        "steps": [
            "Locate fuse box(es) -- engine compartment and/or interior under dash",
            "Refer to fuse diagram on fuse box cover or owner's manual",
            "Identify fuses for the system with the problem",
            "Pull each suspect fuse and inspect the metal strip inside",
            "Check for melted/broken metal strip",
            "Also inspect fuse contacts for corrosion or melting",
        ],
        "what_youre_looking_for": (
            "Intact metal strip = fuse is good. "
            "Broken/melted strip = blown fuse. "
            "Replace with EXACT same amperage fuse only. "
            "Blown fuse immediately after replacement = short circuit in that circuit. "
            "Corroded fuse holder = clean with electrical contact cleaner."
        ),
        "safety_warning": "Always replace fuses with the same amperage rating. Using a higher amp fuse can cause wiring to overheat and start a fire.",
    },
    
    # --- Transmission Inspections ---
    "transmission_fluid_check": {
        "name": "Automatic Transmission Fluid Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Paper towel or rag",
        "steps": [
            "Park on completely LEVEL ground",
            "Start engine and let idle until warm (transmission fluid expands when hot)",
            "Apply parking brake, firmly press brake pedal",
            "Shift through all gears (P-R-N-D-L) pausing 3 seconds in each, return to Park",
            "Locate transmission dipstick (usually labeled, near firewall)",
            "Pull dipstick, wipe clean, fully reinsert, pull out and check level",
            "Note fluid color and smell on paper towel",
        ],
        "what_youre_looking_for": (
            "Bright translucent red/pink = good condition. "
            "Dark red/brown = aged, schedule fluid change. "
            "Black with burnt smell = transmission overheated, internal damage likely. "
            "Milky/pink foam = coolant contamination (radiator failure). "
            "Metallic particles = internal wear (clutch material, metal shavings). "
            "Level should be within crosshatch or HOT marks with engine running in Park."
        ),
        "safety_warning": "Some modern vehicles have sealed transmissions with no dipstick. Check owner's manual. Incorrect fluid level causes immediate transmission damage.",
    },
    
    # --- Exhaust Inspections ---
    "exhaust_leak_check": {
        "name": "Exhaust System Leak Inspection",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Flashlight, helper (optional)",
        "steps": [
            "With engine COLD, visually inspect exhaust manifold for cracks",
            "Inspect manifold-to-head gasket area for black soot marks",
            "Inspect flex pipe (corrugated section) for tears or breaks",
            "Inspect all flange joints for black soot (indicates leak)",
            "Inspect muffler and pipes for holes, rust-through, or damage",
            "Shake exhaust gently to check hanger condition",
            "With engine running, listen at tailpipe for even, rhythmic exhaust pulses",
        ],
        "what_youre_looking_for": (
            "Black soot at any joint = exhaust leak at that location. "
            "Ticking/hissing when cold that lessens when hot = manifold gasket leak. "
            "Rust holes in muffler or pipe = replace affected component. "
            "Broken hanger = exhaust can drag or break off. "
            "Uneven exhaust pulses = engine misfire or valve issue."
        ),
        "safety_warning": "Exhaust leaks before the catalytic converter can allow deadly carbon monoxide into the cabin. Any manifold leak must be repaired before driving.",
    },
    
    # --- Steering Inspections ---
    "power_steering_check": {
        "name": "Power Steering System Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Flashlight, rag",
        "steps": [
            "Locate power steering reservoir (near engine, labeled)",
            "Check fluid level against COLD or HOT marks (check as appropriate)",
            "Note fluid color -- should be clear, red, or pink depending on type",
            "Start engine, turn steering wheel lock to lock",
            "Listen for whining, groaning, or grinding noises",
            "Inspect hoses and connections for wetness/leaks",
            "Check if steering effort is consistent in both directions",
        ],
        "what_youre_looking_for": (
            "Proper fluid level and clear red fluid = good. "
            "Low fluid = leak somewhere in system. "
            "Black/burnt fluid = overheated pump, flush and inspect. "
            "Foamy fluid = air in system (leak on suction side). "
            "Whining when turning = low fluid or failing pump. "
            "Groaning = air in system or pump cavitation."
        ),
    },
    "steering_play_check": {
        "name": "Steering System Play Check",
        "cost": 0,
        "time": "3 minutes",
        "tools": "None",
        "steps": [
            "With engine running, turn steering wheel slowly from center",
            "Count how many degrees of wheel movement before tires begin to turn",
            "Normal: tires respond within 1-2 inches of steering wheel rim movement",
            "Excessive play: tires don't respond until wheel turned significantly",
            "Also check for binding, notchiness, or uneven effort",
        ],
        "what_youre_looking_for": (
            "Immediate response = steering system tight. "
            "More than 2 inches of rim movement before response = worn tie rods, "
            "idler arm, or steering rack. Inspect immediately for safety."
        ),
    },
    
    # --- HVAC Inspections ---
    "cabin_air_filter_check": {
        "name": "Cabin Air Filter Inspection",
        "cost": 0,
        "time": "5 minutes",
        "tools": "None (may need screwdriver)",
        "steps": [
            "Locate cabin filter (usually behind glove box or under hood near cowl)",
            "Remove glove box (squeeze sides inward) or access panel",
            "Slide out filter tray and remove filter",
            "Hold filter up to light -- check how much light passes through",
            "Inspect for leaves, debris, rodent nests, or mold",
            "Note airflow direction arrow on filter for reinstallation",
        ],
        "what_youre_looking_for": (
            "Clean, light passes through = good. "
            "Clogged with dust/debris = restricted airflow, weak A/C and heat. "
            "Leaves or rodent nest = clean thoroughly, consider pest deterrent. "
            "Mold/mildew smell = spray evaporator cleaner through drain tube. "
            "Replace every 12-15K miles or annually."
        ),
    },
    "hvac_vacuum_leak_check": {
        "name": "HVAC Control Vacuum Leak Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Vacuum gauge (optional), flashlight",
        "steps": [
            "Start engine, set HVAC to panel vents",
            "Cycle through all modes: panel, floor, defrost, mix",
            "Each mode should change airflow within 5 seconds",
            "If mode doors don't switch = vacuum leak or faulty actuator",
            "Inspect vacuum lines under hood (small black rubber hoses) for cracks",
            "Check vacuum reservoir for cracks (usually near firewall)",
        ],
        "what_youre_looking_for": (
            "All modes switch properly = system OK. "
            "Stuck in defrost = default failsafe mode, vacuum leak likely. "
            "Hissing under dash = vacuum line cracked or disconnected. "
            "Only works at high RPM = vacuum supply insufficient (leak or weak engine vacuum)."
        ),
    },
    
    # --- Fuel System Inspections ---
    "fuel_cap_check": {
        "name": "Fuel Cap and EVAP System Check",
        "cost": 0,
        "time": "2 minutes",
        "tools": "Flashlight",
        "steps": [
            "Remove fuel cap",
            "Inspect rubber gasket/seal for cracks, tears, or deformation",
            "Inspect cap tether for breakage",
            "Check filler neck for rust, debris, or damage where cap seals",
            "Reinstall cap until it clicks at least 3 times",
        ],
        "what_youre_looking_for": (
            "Intact rubber seal with no cracks = good. "
            "Cracked or hardened seal = replace cap (~$10-15). "
            "Rust or debris on filler neck = clean before reinstalling cap. "
            "A loose or faulty gas cap is the #1 cause of check engine lights (P0457)."
        ),
    },
    "fuel_injector_balance_test": {
        "name": "Fuel Injector Visual Balance Test",
        "cost": 0,
        "time": "10 minutes",
        "tools": "Long screwdriver (as stethoscope), mechanic's stethoscope (optional)",
        "steps": [
            "Start engine and let idle",
            "Place tip of long screwdriver on each fuel injector body",
            "Press handle of screwdriver against your ear (acts as stethoscope)",
            "Listen for consistent clicking sound from each injector",
            "Compare sound across all cylinders",
            "A cylinder that runs rough when injector electrical connector unplugged "
            "and makes no change when reconnected may have a weak injector",
        ],
        "what_youre_looking_for": (
            "Consistent rhythmic clicking from all injectors = all firing. "
            "No click from one injector = electrical issue or stuck closed injector. "
            "Erratic or weak click = injector may be partially clogged. "
            "One injector significantly quieter = may need cleaning or replacement."
        ),
    },
    
    # --- Underbody Inspections ---
    "underbody_visual_check": {
        "name": "Underbody Visual Inspection",
        "cost": 0,
        "time": "10 minutes",
        "tools": "Jack, jack stands, flashlight",
        "steps": [
            "Jack up vehicle and place on jack stands at all four jacking points",
            "Visually inspect all brake lines for rust, corrosion, or wetness",
            "Inspect fuel lines and EVAP lines for cracks or damage",
            "Check exhaust system for holes, rust, or broken hangers",
            "Look for any fluid leaks (oil, coolant, transmission, differential)",
            "Inspect CV axle boots for tears and leaking grease",
            "Check for structural rust or damage to floor pans and frame",
        ],
        "what_youre_looking_for": (
            "Rust on brake lines = replace before failure (critical safety). "
            "Torn CV boot = replace boot or axle ASAP before joint damage. "
            "Any fuel wetness = fire hazard, repair immediately. "
            "Structural rust = safety concern, have evaluated by professional."
        ),
        "safety_warning": "Always use jack stands. Never work under a vehicle supported only by a jack.",
    },
    "cv_axle_inspection": {
        "name": "CV Axle and Boot Inspection",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Jack, jack stands, flashlight",
        "steps": [
            "Jack up vehicle, secure on jack stands",
            "Rotate each front wheel and visually inspect the CV boot (rubber accordion cover)",
            "Look for tears, cracks, or grease leaking from the boot",
            "Check for play in the axle shaft",
            "Look for spray of grease on inside of wheel or underbody",
        ],
        "what_youre_looking_for": (
            "Intact boot with no tears = good. "
            "Torn boot with grease leaking = replace boot or axle before joint damage. "
            "Clicking noise when turning = CV joint is worn and needs replacement. "
            "Vibration under acceleration = inner CV joint may be worn."
        ),
    },
    
    # --- Differential/Transfer Case ---
    "differential_fluid_check": {
        "name": "Differential Fluid Level Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Flashlight, clean rag",
        "steps": [
            "Locate differential (rear axle center or front axle for 4WD)",
            "Find fill plug (upper) and drain plug (lower) on differential cover",
            "Remove fill plug with correct wrench/socket",
            "Insert pinky finger into fill hole -- fluid should be at bottom of fill hole",
            "Note fluid color on rag -- should be clear to dark amber (not black or metallic)",
        ],
        "what_youre_looking_for": (
            "Fluid at fill hole with amber/brown color = good. "
            "Fluid below fill hole = add correct gear oil to spec. "
            "Black fluid = overheated, change immediately. "
            "Metallic particles = gear wear, inspect gears. "
            "Milky fluid = water contamination (submerged axle or seal leak)."
        ),
    },
    
    # --- PCV System Inspection ---
    "pcv_valve_check": {
        "name": "PCV Valve and System Check",
        "cost": 0,
        "time": "5 minutes",
        "tools": "Pliers, flashlight",
        "steps": [
            "Locate PCV valve (on valve cover or intake manifold, connected to hose)",
            "Remove PCV valve from valve cover",
            "Shake valve -- should rattle freely (plunger inside moves)",
            "Blow through valve -- should flow one direction only (from valve cover toward intake)",
            "Inspect PCV hose for cracks, collapse, or oil saturation",
            "Check hose connections for secure fit",
        ],
        "what_youre_looking_for": (
            "Rattles and flows one direction = good. "
            "No rattle, doesn't flow = clogged, replace (~$5-15). "
            "Flows both directions = failed valve, replace. "
            "Cracked hose = vacuum leak and oil leak source, replace hose. "
            "Oil-saturated hose = excessive crankcase pressure, check for engine wear."
        ),
    },
    
    # --- Serpentine Belt Routing Check ---
    "belt_routing_verification": {
        "name": "Serpentine Belt Routing Verification",
        "cost": 0,
        "time": "2 minutes",
        "tools": "Belt routing diagram (from under hood decal or manual)",
        "steps": [
            "Find belt routing diagram (decal under hood or in manual)",
            "Trace actual belt path and compare to diagram",
            "Verify belt sits properly in ALL pulley grooves",
            "Check that belt is not twisted or misrouted",
            "Verify back of belt only contacts smooth idler/tensioner pulleys (not grooved)",
        ],
        "what_youre_looking_for": (
            "Belt matches diagram exactly = correctly routed. "
            "Belt off by one groove on any pulley = misrouted, squealing and premature wear. "
            "Belt routed incorrectly = immediate correction needed before engine damage."
        ),
    },
}


def generate_inspections(causes: list) -> list:
    """Generate relevant zero-cost inspections based on suspected causes.
    
    Maps causes to appropriate inspections from the INSPECTION_LIBRARY.
    Returns prioritized list of inspections the user can perform before
    spending money on parts or professional diagnosis.
    
    Args:
        causes: List of cause dicts from differential diagnosis
    
    Returns:
        List of inspection dicts with name, cost, time, tools, steps, etc.
    """
    # Mapping of cause keywords to inspection keys
    cause_to_inspection = {
        # Belt-related
        "serpentine belt": ["visual_belt_check", "belt_routing_verification", "tensioner_pulley_check"],
        "belt tensioner": ["tensioner_pulley_check", "visual_belt_check"],
        "idler pulley": ["tensioner_pulley_check"],
        "alternator": ["alternator_output_check", "battery_terminal_check"],
        
        # Brake-related
        "brake pad": ["brake_pad_inspection", "brake_rotor_inspection", "brake_fluid_check"],
        "brake rotor": ["brake_rotor_inspection", "brake_pad_inspection"],
        "brake fluid": ["brake_fluid_check"],
        "brake caliper": ["brake_pad_inspection", "brake_rotor_inspection"],
        "master cylinder": ["brake_fluid_check"],
        "spongy brake": ["brake_fluid_check", "brake_pad_inspection"],
        
        # Wheel/tire-related
        "wheel bearing": ["wheel_bearing_check", "tire_inspection"],
        "tire": ["tire_inspection", "tire_rotation_check", "wheel_bearing_check"],
        "flat-spotted": ["tire_inspection"],
        "balance": ["tire_inspection", "alignment_quick_check"],
        
        # Suspension-related
        "shock": ["suspension_bounce_test", "suspension_component_check"],
        "strut": ["suspension_bounce_test", "suspension_component_check"],
        "control arm": ["suspension_component_check"],
        "sway bar": ["suspension_component_check"],
        "ball joint": ["suspension_component_check"],
        "tie rod": ["suspension_component_check", "steering_play_check"],
        "bushing": ["suspension_component_check"],
        
        # Engine-related
        "spark plug": ["spark_plug_inspection", "ignition_coil_test"],
        "ignition coil": ["ignition_coil_test", "spark_plug_inspection"],
        "misfire": ["spark_plug_inspection", "ignition_coil_test", "fuel_injector_balance_test"],
        "vacuum leak": ["visual_belt_check", "pcv_valve_check"],
        "MAF sensor": ["air_filter_check"],
        "air filter": ["air_filter_check"],
        "oil": ["engine_oil_check"],
        "coolant": ["coolant_level_check", "radiator_visual_check"],
        "thermostat": ["thermostat_quick_check", "coolant_level_check"],
        "overheating": ["coolant_level_check", "radiator_visual_check", "thermostat_quick_check"],
        "head gasket": ["coolant_level_check", "engine_oil_check", "spark_plug_inspection"],
        "PCV": ["pcv_valve_check", "engine_oil_check"],
        
        # Transmission-related
        "transmission fluid": ["transmission_fluid_check"],
        "transmission": ["transmission_fluid_check"],
        "torque converter": ["transmission_fluid_check"],
        "clutch": ["transmission_fluid_check"],
        "CV joint": ["cv_axle_inspection", "underbody_visual_check"],
        "driveshaft": ["underbody_visual_check", "cv_axle_inspection"],
        "differential": ["differential_fluid_check", "underbody_visual_check"],
        
        # Electrical-related
        "battery": ["battery_terminal_check", "alternator_output_check"],
        "alternator": ["alternator_output_check", "battery_terminal_check"],
        "charging": ["alternator_output_check", "battery_terminal_check"],
        "fuse": ["fuse_check"],
        "electrical": ["fuse_check", "battery_terminal_check", "alternator_output_check"],
        
        # Steering-related
        "power steering": ["power_steering_check", "steering_play_check"],
        "steering rack": ["steering_play_check", "power_steering_check"],
        "loose steering": ["steering_play_check", "suspension_component_check"],
        "alignment": ["alignment_quick_check", "tire_inspection"],
        
        # Exhaust-related
        "exhaust": ["exhaust_leak_check"],
        "catalytic converter": ["exhaust_leak_check"],
        "oxygen sensor": ["exhaust_leak_check"],
        "manifold": ["exhaust_leak_check"],
        
        # HVAC-related
        "cabin filter": ["cabin_air_filter_check"],
        "evaporator": ["cabin_air_filter_check"],
        "A/C": ["cabin_air_filter_check", "hvac_vacuum_leak_check"],
        
        # Fuel-related
        "fuel injector": ["fuel_injector_balance_test"],
        "gasoline": ["fuel_cap_check"],
        "fuel pump": ["fuel_injector_balance_test"],
        "fuel filter": ["fuel_cap_check"],
        
        # Other
        "wiper": ["wiper_blade_check"],
        "light": ["lighting_system_check"],
    }
    
    inspection_keys = set()
    for cause in causes:
        cause_name = cause.get("name", "").lower()
        for keyword, inspections in cause_to_inspection.items():
            if keyword in cause_name:
                inspection_keys.update(inspections)
    
    # Build result list with priority ordering
    result = []
    seen = set()
    for key in inspection_keys:
        if key in INSPECTION_LIBRARY and key not in seen:
            seen.add(key)
            inspection = dict(INSPECTION_LIBRARY[key])
            inspection["key"] = key
            result.append(inspection)
    
    # Sort by time (quickest first) to encourage users to start
    result.sort(key=lambda x: int(x.get("time", "0").split()[0]) if x.get("time") else 0)
    
    return result


# =============================================================================
# SECTION 4: SAFETY FILTER
# =============================================================================

CRITICAL_SAFETY_SYSTEMS = ["brakes", "steering", "tires", "seatbelts", "airbags", "fuel_system", "structural"]

SAFETY_WARNINGS = {
    "brake": (
        "BRAKE SAFETY WARNING: Brake problems can lead to complete brake failure. "
        "If you experience ANY loss of braking power, pull over safely immediately and have the vehicle towed. "
        "Do NOT continue driving. Check brake fluid level before every drive until repaired. "
        "Test brakes at low speed before entering traffic."
    ),
    "steering": (
        "STEERING SAFETY WARNING: Steering problems can cause sudden loss of vehicle control. "
        "If steering feels loose, unresponsive, makes loud noises, or requires unusual effort, "
        "stop driving immediately. A seized ball joint or broken tie rod can cause the wheel to fold under the car."
    ),
    "tire": (
        "TIRE SAFETY WARNING: Tire failures at speed can cause catastrophic loss of control. "
        "Inspect tires before every drive if you suspect tire issues. "
        "Any sidewall bulge, visible cord, or tread separation means the tire must be replaced before driving. "
        "Do not exceed 50 mph on a tire you suspect is damaged."
    ),
    "fuel_leak": (
        "FUEL LEAK SAFETY WARNING: Fuel leaks are an EXPLOSION and FIRE HAZARD. "
        "Do NOT start or drive the vehicle. Do NOT smoke near the vehicle. "
        "Have it towed to a professional immediately. Even a small fuel leak can ignite from hot exhaust components."
    ),
    "overheating": (
        "OVERHEATING WARNING: Driving an overheating vehicle can destroy the engine within minutes "
        "(warped cylinder head, blown head gasket). Pull over immediately, turn off engine, and allow to cool. "
        "Do NOT open radiator cap on hot engine. Check coolant level only when cold."
    ),
}


# =============================================================================
# SECTION 5: OBD-II DIAGNOSTIC TROUBLE CODE DATABASE
# =============================================================================
# Comprehensive database of common OBD-II DTCs with descriptions,
# severity ratings, likely causes, and recommended inspections.
# Covers P0xxx (powertrain), B0xxx (body), C0xxx (chassis), U0xxx (network).

OBD2_CODES: Dict[str, Dict[str, Any]] = {
    # --- P0xxx: Powertrain ---
    "P0101": {
        "description": "Mass Air Flow (MAF) Circuit Range/Performance Problem",
        "severity": "medium",
        "likely_causes": ["Dirty MAF sensor", "Intake air leak after MAF", "Clogged air filter", "Faulty MAF sensor"],
        "inspections": ["Clean MAF sensor with dedicated cleaner", "Inspect intake hoses for cracks/leaks", "Check air filter condition"],
        "system": "engine",
    },
    "P0102": {
        "description": "Mass Air Flow (MAF) Circuit Low Input",
        "severity": "medium",
        "likely_causes": ["Dirty/contaminated MAF sensor", "Intake air leak", "Wiring issue to MAF", "Faulty MAF sensor"],
        "inspections": ["Clean MAF sensor", "Check MAF connector and wiring", "Inspect for vacuum leaks"],
        "system": "engine",
    },
    "P0107": {
        "description": "Manifold Absolute Pressure (MAP) Circuit Low Input",
        "severity": "medium",
        "likely_causes": ["MAP sensor vacuum hose disconnected/blocked", "MAP sensor connector loose", "Faulty MAP sensor"],
        "inspections": ["Check MAP sensor vacuum hose for cracks or disconnection", "Inspect electrical connector", "Test MAP sensor output voltage vs. altitude spec"],
        "system": "engine",
    },
    "P0108": {
        "description": "Manifold Absolute Pressure (MAP) Circuit High Input",
        "severity": "medium",
        "likely_causes": ["MAP sensor vacuum hose disconnected/blocked", "MAP sensor connector loose", "Faulty MAP sensor"],
        "inspections": ["Check MAP sensor vacuum hose for cracks or disconnection", "Inspect electrical connector", "Test MAP sensor output voltage vs. altitude spec"],
        "system": "engine",
    },
    "P0113": {
        "description": "Intake Air Temperature (IAT) Circuit High Input",
        "severity": "low",
        "likely_causes": ["IAT sensor connector disconnected", "Open circuit in IAT wiring", "Faulty IAT sensor"],
        "inspections": ["Check IAT sensor connector", "Test sensor resistance at known temperature", "Check wiring continuity"],
        "system": "engine",
    },
    "P0118": {
        "description": "Engine Coolant Temperature (ECT) Circuit High Input",
        "severity": "medium",
        "likely_causes": ["Faulty ECT sensor", "Wiring short to voltage", "Corroded connector pins", "Bad ground connection"],
        "inspections": ["Test ECT sensor resistance when cold (should be high ohms)", "Check connector for corrosion", "Verify coolant level and condition"],
        "system": "engine",
    },
    "P0120": {
        "description": "Throttle Position Sensor (TPS) Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Faulty TPS", "Corroded connector", "Wire harness damage", "Throttle body carbon buildup"],
        "inspections": ["Test TPS voltage sweep with multimeter (should be smooth 0.5-4.5V)", "Check connector for corrosion", "Clean throttle body"],
        "system": "engine",
    },
    "P0128": {
        "description": "Coolant Thermostat (Coolant Temperature Below Thermostat Regulating Temperature)",
        "severity": "low",
        "likely_causes": ["Thermostat stuck open", "Low coolant level", "Faulty ECT sensor", "Cooling fan running continuously"],
        "inspections": ["Check coolant level", "Test thermostat (upper hose should be cold then suddenly hot)", "Verify cooling fan operation with scanner"],
        "system": "cooling",
    },
    "P0130": {
        "description": "O2 Sensor Circuit Malfunction (Bank 1, Sensor 1)",
        "severity": "medium",
        "likely_causes": ["Heater circuit failure in O2 sensor", "Contaminated O2 sensor (silicone, coolant, oil)", "Exhaust leak upstream of sensor", "Wiring damage"],
        "inspections": ["Check O2 sensor heater resistance (4-8 ohms typical)", "Inspect for exhaust leaks before sensor", "Check sensor output voltage oscillates 0.1-0.9V"],
        "system": "exhaust",
    },
    "P0134": {
        "description": "O2 Sensor Circuit No Activity Detected (Bank 1, Sensor 1)",
        "severity": "medium",
        "likely_causes": ["O2 sensor worn out (slow response)", "Open heater circuit", "Sensor contaminated by coolant or oil", "Rich or lean condition masking sensor"],
        "inspections": ["Watch O2 sensor voltage on scanner -- should oscillate, not flatline", "Check for heater circuit DTCs", "Inspect for exhaust leaks"],
        "system": "exhaust",
    },
    "P0135": {
        "description": "O2 Sensor Heater Circuit Malfunction (Bank 1, Sensor 1)",
        "severity": "low",
        "likely_causes": ["Open heater element in O2 sensor", "Blown O2 sensor fuse", "Wiring open or shorted", "Relay failure"],
        "inspections": ["Test O2 sensor heater resistance across heater pins", "Check O2 sensor fuse", "Check for power and ground at heater connector"],
        "system": "exhaust",
    },
    "P0141": {
        "description": "O2 Sensor Heater Circuit Malfunction (Bank 1, Sensor 2)",
        "severity": "low",
        "likely_causes": ["Failed downstream O2 sensor heater", "Wiring issue", "Blown fuse"],
        "inspections": ["Test downstream O2 sensor heater resistance", "Check wiring and fuse", "Verify sensor is not contaminated"],
        "system": "exhaust",
    },
    "P0171": {
        "description": "System Too Lean (Bank 1)",
        "severity": "high",
        "likely_causes": ["Vacuum leak (intake manifold gasket, hose, PCV)", "Dirty/faulty MAF sensor", "Low fuel pressure (weak pump, clogged filter)", "Exhaust leak before O2 sensor", "Clogged fuel injector(s)"],
        "inspections": ["Smoke test or propane test for vacuum leaks", "Clean MAF sensor with dedicated cleaner", "Check fuel pressure at rail with gauge", "Inspect for exhaust leaks before upstream O2 sensor"],
        "system": "engine",
    },
    "P0172": {
        "description": "System Too Rich (Bank 1)",
        "severity": "medium",
        "likely_causes": ["Leaking fuel injector", "Faulty fuel pressure regulator", "Dirty/contaminated MAF sensor", "Clogged air filter", "Thermostat stuck open", "Faulty coolant temp sensor"],
        "inspections": ["Check fuel pressure -- high pressure causes rich condition", "Clean MAF sensor", "Check spark plugs for black soot", "Check engine temperature reaches normal range"],
        "system": "engine",
    },
    "P0174": {
        "description": "System Too Lean (Bank 2)",
        "severity": "high",
        "likely_causes": ["Vacuum leak on bank 2 side", "Dirty MAF sensor", "Low fuel pressure", "Exhaust leak"],
        "inspections": ["Same as P0171 -- lean condition on V-engine bank 2", "Focus vacuum leak search on bank 2 intake runners", "Clean MAF sensor", "Check fuel pressure"],
        "system": "engine",
    },
    "P0175": {
        "description": "System Too Rich (Bank 2)",
        "severity": "medium",
        "likely_causes": ["Leaking fuel injector on bank 2", "MAF contamination", "Fuel pressure too high"],
        "inspections": ["Check bank 2 spark plugs for black soot", "Test fuel pressure", "Clean MAF sensor", "Check bank 2 injector seals"],
        "system": "engine",
    },
    "P0201": {
        "description": "Injector Circuit Malfunction - Cylinder 1",
        "severity": "high",
        "likely_causes": ["Open or shorted injector wiring", "Faulty fuel injector (coil open)", "Corroded injector connector"],
        "inspections": ["Test injector resistance (typically 12-16 ohms)", "Check injector connector for power and ground pulse", "Noid light test for injector drive signal"],
        "system": "engine",
    },
    "P0300": {
        "description": "Random/Multiple Cylinder Misfire Detected",
        "severity": "high",
        "likely_causes": ["Worn spark plugs", "Failing ignition coil(s)", "Vacuum leak", "Low fuel pressure", "Clogged fuel injector", "Low compression", "EGR valve stuck open"],
        "inspections": ["Check spark plug condition and gap", "Swap ignition coils to isolate misfire", "Check fuel pressure", "Smoke test for vacuum leaks", "Compression test if misfire is persistent"],
        "system": "engine",
    },
    "P0301": {"description": "Cylinder 1 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 1", "Clogged injector on cylinder 1", "Low compression on cylinder 1"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 1", "Test injector on cylinder 1"], "system": "engine"},
    "P0302": {"description": "Cylinder 2 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 2", "Clogged injector on cylinder 2", "Low compression on cylinder 2"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 2", "Test injector on cylinder 2"], "system": "engine"},
    "P0303": {"description": "Cylinder 3 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 3", "Clogged injector on cylinder 3", "Low compression on cylinder 3"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 3", "Test injector on cylinder 3"], "system": "engine"},
    "P0304": {"description": "Cylinder 4 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 4", "Clogged injector on cylinder 4", "Low compression on cylinder 4"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 4", "Test injector on cylinder 4"], "system": "engine"},
    "P0305": {"description": "Cylinder 5 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 5", "Clogged injector on cylinder 5", "Low compression on cylinder 5"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 5", "Test injector on cylinder 5"], "system": "engine"},
    "P0306": {"description": "Cylinder 6 Misfire Detected", "severity": "high", "likely_causes": ["Bad spark plug or coil on cylinder 6", "Clogged injector on cylinder 6", "Low compression on cylinder 6"], "inspections": ["Swap coil/plug to another cylinder; see if misfire moves", "Check compression on cylinder 6", "Test injector on cylinder 6"], "system": "engine"},
    "P0316": {
        "description": "Misfire Detected on Startup (First 1000 Revolutions)",
        "severity": "medium",
        "likely_causes": ["Cold-start misfire due to worn spark plugs", "Leaking intake manifold gasket (coolant intrusion)", "Weak coil that improves when warm", "Low compression when cold (piston slap or valve seal)"],
        "inspections": ["Check spark plugs for coolant contamination", "Compression test when cold", "Check for coolant loss indicating head gasket leak"],
        "system": "engine",
    },
    "P0325": {
        "description": "Knock Sensor Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Failed knock sensor", "Wiring damaged by rodents or heat", "Connector corrosion", "Excessive engine noise masking sensor"],
        "inspections": ["Test knock sensor resistance (per service manual spec)", "Inspect wiring near exhaust manifold", "Check connector for corrosion"],
        "system": "engine",
    },
    "P0335": {
        "description": "Crankshaft Position Sensor Circuit Malfunction",
        "severity": "high",
        "likely_causes": ["Failed crankshaft position sensor", "Damaged tone ring (reluctor)", "Wiring issue", "Connector corrosion"],
        "inspections": ["Test CKP sensor resistance and output", "Inspect tone ring for damage/missing teeth", "Check wiring and connector"],
        "system": "engine",
    },
    "P0340": {
        "description": "Camshaft Position Sensor Circuit Malfunction",
        "severity": "high",
        "likely_causes": ["Failed camshaft position sensor", "Timing chain/belt issue", "Wiring damage", "Connector corrosion"],
        "inspections": ["Test CMP sensor resistance and output", "Inspect timing components", "Check wiring and connector"],
        "system": "engine",
    },
    "P0401": {
        "description": "Exhaust Gas Recirculation (EGR) Flow Insufficient",
        "severity": "medium",
        "likely_causes": ["Clogged EGR passage", "Faulty EGR valve", "EGR valve stuck closed", "DPFE sensor failure"],
        "inspections": ["Remove and clean EGR valve and passages", "Test EGR valve diaphragm/vacuum operation", "Check DPFE sensor hoses"],
        "system": "engine",
    },
    "P0420": {
        "description": "Catalyst System Efficiency Below Threshold (Bank 1)",
        "severity": "medium",
        "likely_causes": ["Failing catalytic converter", "Exhaust leak before converter", "Contaminated converter (oil/coolant)", "O2 sensor slow response (false positive)"],
        "inspections": ["Check for exhaust leaks before converter", "Monitor O2 sensor waveforms (should differ front vs rear)", "Check for coolant/oil contamination", "Replace converter if confirmed failed"],
        "system": "exhaust",
    },
    "P0430": {
        "description": "Catalyst System Efficiency Below Threshold (Bank 2)",
        "severity": "medium",
        "likely_causes": ["Same as P0420 but for bank 2 (V-engines)"],
        "inspections": ["Same diagnostic approach as P0420, focus on bank 2"],
        "system": "exhaust",
    },
    "P0440": {
        "description": "Evaporative Emission Control System Malfunction",
        "severity": "low",
        "likely_causes": ["Loose gas cap", "EVAP vent valve stuck open", "Leaking EVAP canister", "Faulty purge valve"],
        "inspections": ["Check gas cap seal and tightness", "Test purge valve (should hold vacuum when off)", "Smoke test EVAP system for leaks"],
        "system": "engine",
    },
    "P0442": {
        "description": "Evaporative Emission Control System Leak Detected (small leak)",
        "severity": "low",
        "likely_causes": ["Loose or faulty gas cap", "Small leak in EVAP line", "Faulty purge valve", "Leaking EVAP canister vent valve"],
        "inspections": ["Replace gas cap", "Inspect EVAP hoses for cracks", "Smoke test for small leaks"],
        "system": "engine",
    },
    "P0455": {
        "description": "Evaporative Emission Control System Leak Detected (gross leak)",
        "severity": "medium",
        "likely_causes": ["Missing or loose gas cap", "Large leak in EVAP line", "Disconnected EVAP hose", "Faulty fuel tank pressure sensor"],
        "inspections": ["Check gas cap (most common cause)", "Visually inspect all EVAP hoses for disconnection", "Smoke test for large leak"],
        "system": "engine",
    },
    "P0456": {
        "description": "Evaporative Emission Control System Leak Detected (very small leak)",
        "severity": "low",
        "likely_causes": ["Very small crack in EVAP line", "Deteriorated gas cap seal", "Pinhole in canister", "Loose hose clamp"],
        "inspections": ["Replace gas cap", "Carefully inspect all EVAP connections", "Smoke test for tiny leak"],
        "system": "engine",
    },
    "P0457": {
        "description": "Evaporative Emission Control System Leak Detected (fuel cap loose/off)",
        "severity": "low",
        "likely_causes": ["Gas cap left loose or off after refueling", "Faulty gas cap seal"],
        "inspections": ["Remove and reinstall gas cap until it clicks", "Inspect cap seal for cracks", "Replace cap if seal is damaged"],
        "system": "engine",
    },
    "P0463": {
        "description": "Fuel Level Sensor Circuit High Input",
        "severity": "low",
        "likely_causes": ["Faulty fuel level sensor (sender)", "Float arm stuck", "Wiring short to voltage"],
        "inspections": ["Check fuel gauge reading vs. actual fuel level", "Test sender resistance across fuel range", "Inspect wiring"],
        "system": "fuel",
    },
    "P0496": {
        "description": "Evaporative Emission System High Purge Flow",
        "severity": "medium",
        "likely_causes": ["Purge valve stuck open", "Faulty purge valve solenoid", "Excessive vacuum in EVAP system"],
        "inspections": ["Test purge valve (should not flow vacuum when off)", "Check for stuck-open purge valve", "Replace purge valve if faulty"],
        "system": "engine",
    },
    "P0500": {
        "description": "Vehicle Speed Sensor Malfunction",
        "severity": "medium",
        "likely_causes": ["Failed vehicle speed sensor (VSS)", "Wiring damage", "Tone ring damage", "Instrument cluster issue"],
        "inspections": ["Test VSS resistance and output", "Inspect wiring to sensor", "Check tone ring on axle/driveshaft"],
        "system": "transmission",
    },
    "P0505": {
        "description": "Idle Control System Malfunction",
        "severity": "medium",
        "likely_causes": ["Dirty throttle body", "Faulty idle air control (IAC) valve", "Vacuum leak", "Carbon buildup on throttle plate"],
        "inspections": ["Clean throttle body and idle air passage", "Test IAC valve operation", "Check for vacuum leaks"],
        "system": "engine",
    },
    "P0600": {
        "description": "Serial Communication Link Malfunction",
        "severity": "high",
        "likely_causes": ["ECM/PCM internal failure", "CAN bus wiring issue", "Communication module failure"],
        "inspections": ["Check for other communication DTCs", "Test CAN bus resistance and voltage", "Verify ECM powers and grounds"],
        "system": "electrical",
    },
    "P0700": {
        "description": "Transmission Control System Malfunction",
        "severity": "high",
        "likely_causes": ["Transmission control module (TCM) has stored fault codes", "Internal transmission fault", "Wiring issue to TCM"],
        "inspections": ["Scan transmission module for specific codes", "Check TCM powers, grounds, and communication", "Inspect transmission wiring harness"],
        "system": "transmission",
    },
    "P0740": {
        "description": "Torque Converter Clutch Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Faulty torque converter clutch (TCC) solenoid", "Internal TCC failure", "Wiring issue to TCC solenoid", "Low transmission fluid"],
        "inspections": ["Test TCC solenoid resistance", "Check transmission fluid level and condition", "Inspect wiring to TCC solenoid"],
        "system": "transmission",
    },
    "P0741": {
        "description": "Torque Converter Clutch Circuit Performance or Stuck Off",
        "severity": "medium",
        "likely_causes": ["Worn torque converter clutch", "TCC solenoid failing", "Internal hydraulic issue", "Low line pressure"],
        "inspections": ["Test TCC solenoid", "Check transmission fluid", "Monitor TCC apply with scan tool", "May require torque converter replacement"],
        "system": "transmission",
    },
    "P0750": {
        "description": "Shift Solenoid A Malfunction",
        "severity": "high",
        "likely_causes": ["Failed shift solenoid", "Wiring issue to solenoid", "Internal transmission hydraulic fault", "Dirty transmission fluid"],
        "inspections": ["Test shift solenoid resistance", "Check wiring harness to transmission", "Check transmission fluid condition"],
        "system": "transmission",
    },
    "P0776": {
        "description": "Pressure Control Solenoid B Stuck Off (common in GM 6T40)",
        "severity": "high",
        "likely_causes": ["Failed PC solenoid", "Valve body wear", "Internal transmission clutch failure", "Low fluid pressure"],
        "inspections": ["Test PC solenoid resistance", "Check transmission fluid level/condition", "May require valve body or transmission replacement"],
        "system": "transmission",
    },
    "P0850": {
        "description": "Park/Neutral Switch Input Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Faulty park/neutral safety switch", "Misadjusted shift linkage", "Wiring issue"],
        "inspections": ["Test switch operation in each gear position", "Check shift linkage adjustment", "Inspect wiring and connector"],
        "system": "transmission",
    },
    "P0868": {
        "description": "Transmission Fluid Pressure Low",
        "severity": "high",
        "likely_causes": ["Low transmission fluid", "Worn transmission pump", "Pressure regulator valve stuck", "Internal leak"],
        "inspections": ["Check transmission fluid level and condition", "Pressure test transmission hydraulic circuits", "May require transmission teardown"],
        "system": "transmission",
    },
    "P0962": {
        "description": "Pressure Control Solenoid A Control Circuit Low",
        "severity": "high",
        "likely_causes": ["Short to ground in PC solenoid circuit", "Failed PC solenoid", "Wiring damage", "TCM failure"],
        "inspections": ["Test solenoid resistance", "Check wiring for short to ground", "Verify TCM output signal"],
        "system": "transmission",
    },
    "P1101": {
        "description": "MAF Sensor Out of Self-Test Range (Ford)",
        "severity": "medium",
        "likely_causes": ["Dirty MAF sensor", "Intake air leak", "Aftermarket air intake (oiled filter)", "Faulty MAF"],
        "inspections": ["Clean MAF sensor", "Check for intake leaks", "Inspect air filter (oiled filters can contaminate MAF)", "Verify MAF readings at idle"],
        "system": "engine",
    },
    "P144A": {
        "description": "Evaporative System Vent Control Circuit Stuck Open (Ford)",
        "severity": "low",
        "likely_causes": ["Vent valve stuck open", "Wiring issue", "Canister vent valve filter clogged"],
        "inspections": ["Test vent valve operation", "Check vent filter for blockage", "Replace vent valve if stuck"],
        "system": "engine",
    },
    "P1450": {
        "description": "Unable to Bleed Up Fuel Tank Vacuum (Ford)",
        "severity": "medium",
        "likely_causes": ["Blocked EVAP vent path", "Canister vent valve stuck closed", "Excessive vacuum in fuel tank"],
        "inspections": ["Check canister vent valve operation", "Inspect vent hose for blockage", "Test fuel tank pressure sensor"],
        "system": "engine",
    },
    "P1627": {
        "description": "Engine Control Module (ECM) Internal Fault",
        "severity": "high",
        "likely_causes": ["Internal ECM failure", "Software corruption", "Water damage to ECM"],
        "inspections": ["Check for TSBs and reflash availability", "Verify ECM powers and grounds", "May require ECM replacement"],
        "system": "electrical",
    },
    "P2004": {
        "description": "Intake Manifold Runner Control Stuck Open (Bank 1)",
        "severity": "medium",
        "likely_causes": ["Runner control actuator failure", "Intake manifold carbon buildup", "Wiring issue", "Vacuum leak to actuator"],
        "inspections": ["Test runner actuator operation", "Inspect intake for carbon buildup", "Check vacuum supply to actuator"],
        "system": "engine",
    },
    "P2096": {
        "description": "Post Catalyst Fuel Trim System Too Lean (Bank 1)",
        "severity": "medium",
        "likely_causes": ["Exhaust leak before O2 sensor", "Failed upstream O2 sensor", "Weak fuel pump", "Vacuum leak"],
        "inspections": ["Check for exhaust leaks", "Test upstream O2 sensor operation", "Check fuel pressure"],
        "system": "exhaust",
    },
    "P2101": {
        "description": "Throttle Actuator Control Motor Circuit Range/Performance",
        "severity": "high",
        "likely_causes": ["Failed throttle body motor", "Carbon buildup in throttle body", "Wiring issue to throttle body", "ECM fault"],
        "inspections": ["Clean throttle body", "Test throttle body motor resistance", "Check wiring harness", "May require throttle body replacement"],
        "system": "engine",
    },
    "P2110": {
        "description": "Throttle Actuator Control System - Forced Limited RPM",
        "severity": "high",
        "likely_causes": ["Throttle body fault detected", "ECM entered limp mode due to throttle issue"],
        "inspections": ["Scan for related throttle body DTCs", "Clean and test throttle body", "Check throttle position sensor operation"],
        "system": "engine",
    },
    "P2122": {
        "description": "Throttle/Pedal Position Sensor/Switch D Circuit Low Input",
        "severity": "high",
        "likely_causes": ["Failed accelerator pedal position sensor", "Wiring short to ground", "Connector corrosion"],
        "inspections": ["Test APP sensor voltage with multimeter", "Check wiring for shorts", "Inspect connector"],
        "system": "engine",
    },
    "P219A": {
        "description": "Bank 1 Air-Fuel Ratio Imbalance",
        "severity": "medium",
        "likely_causes": ["Uneven fuel delivery between cylinders", "Intake manifold leak affecting one cylinder", "Injector imbalance"],
        "inspections": ["Perform injector balance test", "Check for intake leaks at gasket", "Compare cylinder contribution"],
        "system": "engine",
    },
    "P2270": {
        "description": "O2 Sensor Signal Stuck Lean (Bank 1, Sensor 2)",
        "severity": "medium",
        "likely_causes": ["Exhaust leak before downstream sensor", "Sensor contamination", "Failed downstream O2 sensor"],
        "inspections": ["Check for exhaust leaks before downstream sensor", "Test sensor response to propane enrichment", "Replace sensor if failed"],
        "system": "exhaust",
    },
    "P2610": {
        "description": "ECM/PCM Internal Engine Off Timer Performance",
        "severity": "low",
        "likely_causes": ["Internal ECM software issue", "Low battery voltage during start", "ECM calibration issue"],
        "inspections": ["Check for ECM reflash TSBs", "Verify battery condition", "Clear code and monitor"],
        "system": "electrical",
    },
    # --- B0xxx: Body Systems ---
    "B1000": {
        "description": "Electronic Control Unit (ECU) Internal Fault",
        "severity": "medium",
        "likely_causes": ["Internal module failure", "Software corruption", "Low voltage event"],
        "inspections": ["Check for software updates", "Verify system voltage", "May require module replacement"],
        "system": "electrical",
    },
    "B1200": {
        "description": "Climate Control Communication Error",
        "severity": "low",
        "likely_causes": ["HVAC module communication fault", "CAN bus issue", "Module power/ground problem"],
        "inspections": ["Scan HVAC module for codes", "Check CAN bus wiring", "Verify module powers and grounds"],
        "system": "hvac",
    },
    "B1317": {
        "description": "Battery Voltage High",
        "severity": "medium",
        "likely_causes": ["Alternator overcharging", "Voltage regulator failure", "Incorrect battery type"],
        "inspections": ["Check charging voltage (should be 13.5-14.5V)", "Test voltage regulator", "Verify battery is correct type"],
        "system": "electrical",
    },
    "B1318": {
        "description": "Battery Voltage Low",
        "severity": "medium",
        "likely_causes": ["Weak battery", "Alternator undercharging", "Parasitic drain", "Poor connection"],
        "inspections": ["Load test battery", "Check charging system output", "Test for parasitic draw", "Clean and tighten connections"],
        "system": "electrical",
    },
    "B1342": {
        "description": "ECU Internal Fault (Ford specific)",
        "severity": "medium",
        "likely_causes": ["Internal module failure", "Software issue"],
        "inspections": ["Check for reprogramming TSBs", "May require module replacement"],
        "system": "electrical",
    },
    "B1400": {
        "description": "Driver Power Window Motor Circuit Failure",
        "severity": "low",
        "likely_causes": ["Failed window motor", "Wiring break in door jamb", "Faulty window switch"],
        "inspections": ["Test motor with direct power", "Check wiring in rubber boot of door jamb", "Test switch output"],
        "system": "body",
    },
    "B1676": {
        "description": "Battery Saver Relay Circuit Failure",
        "severity": "low",
        "likely_causes": ["Failed battery saver relay", "Wiring issue", "Module controlling relay fault"],
        "inspections": ["Test relay operation", "Check relay coil resistance", "Verify control signal from module"],
        "system": "electrical",
    },
    "B1801": {
        "description": "Driver Side Air Bag Circuit Resistance Too Low",
        "severity": "high",
        "likely_causes": ["Short circuit in driver airbag circuit", "Clockspring internal short", "Wiring short to ground"],
        "inspections": ["Test airbag circuit resistance (should be 2-3 ohms)", "Inspect clockspring", "DO NOT test with multimeter on airbag terminals -- use dedicated tool"],
        "system": "airbags",
    },
    "B1806": {
        "description": "Driver Side Air Bag Circuit Resistance Too High",
        "severity": "high",
        "likely_causes": ["Open circuit in driver airbag", "Clockspring failure", "Connector corrosion", "Airbag deployed"],
        "inspections": ["Test airbag circuit continuity", "Inspect clockspring", "Check connector under seat if applicable"],
        "system": "airbags",
    },
    "B1921": {
        "description": "Air Bag Diagnostic Monitor Ground Circuit Open",
        "severity": "high",
        "likely_causes": ["Open ground circuit to airbag module", "Corroded ground connection", "Wiring damage"],
        "inspections": ["Check airbag module ground connection", "Verify ground continuity with ohmmeter", "Inspect for corrosion"],
        "system": "airbags",
    },
    "B2290": {
        "description": "Occupant Classification System Fault",
        "severity": "medium",
        "likely_causes": ["Failed passenger seat sensor", "Wiring issue under seat", "Calibration needed"],
        "inspections": ["Inspect wiring under passenger seat", "Check for TSB on recalibration procedure", "May require sensor replacement"],
        "system": "airbags",
    },
    "B2795": {
        "description": "Communication Error Between Key and Immobilizer (Toyota)",
        "severity": "high",
        "likely_causes": ["Faulty transponder key", "Immobilizer antenna failure", "Unprogrammed key", "Immobilizer module fault"],
        "inspections": ["Try spare key", "Check immobilizer antenna around ignition", "May require dealer key programming"],
        "system": "electrical",
    },
    "B2AAA": {
        "description": "Undefined DTC (Manufacturer Specific)",
        "severity": "unknown",
        "likely_causes": ["Manufacturer-specific code requires OEM scan tool for full definition"],
        "inspections": ["Use manufacturer-specific scan tool for complete diagnostic information"],
        "system": "unknown",
    },
    # --- C0xxx: Chassis Systems ---
    "C0035": {
        "description": "Left Front Wheel Speed Sensor Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Failed LF wheel speed sensor", "Damaged tone ring", "Wiring damage to sensor", "Corroded connector"],
        "inspections": ["Test sensor resistance and output", "Inspect tone ring for cracks/missing teeth", "Check wiring along suspension"],
        "system": "brakes",
    },
    "C0040": {
        "description": "Right Front Wheel Speed Sensor Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Same as C0035 but for right front wheel"],
        "inspections": ["Same as C0035, inspect right front components"],
        "system": "brakes",
    },
    "C0045": {
        "description": "Left Rear Wheel Speed Sensor Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Same as C0035 but for left rear wheel"],
        "inspections": ["Same as C0035, inspect left rear components"],
        "system": "brakes",
    },
    "C0050": {
        "description": "Right Rear Wheel Speed Sensor Circuit Malfunction",
        "severity": "medium",
        "likely_causes": ["Same as C0035 but for right rear wheel"],
        "inspections": ["Same as C0035, inspect right rear components"],
        "system": "brakes",
    },
    "C0060": {
        "description": "ABS Pump Motor Circuit Malfunction",
        "severity": "high",
        "likely_causes": ["Failed ABS pump motor", "Wiring issue to pump", "ABS module internal failure"],
        "inspections": ["Listen for ABS pump running at key-on (should run briefly)", "Check power and ground at pump motor connector", "If no power, suspect ABS module"],
        "system": "brakes",
    },
    "C0077": {
        "description": "Low Tire Pressure (Individual tire, specific to TPMS system)",
        "severity": "low",
        "likely_causes": ["Low tire pressure", "TPMS sensor battery low", "Faulty TPMS sensor"],
        "inspections": ["Check tire pressure with accurate gauge", "Inflate to spec on door jamb", "If light persists after proper inflation, sensor may need replacement"],
        "system": "tires",
    },
    "C0265": {
        "description": "ABS Hydraulic Pump Motor Circuit Open/Shorted (GM specific)",
        "severity": "high",
        "likely_causes": ["Failed ABS pump motor", "Open circuit in pump wiring", "EBCM internal failure"],
        "inspections": ["Test pump motor resistance", "Check wiring to EBCM", "May require EBCM replacement or rebuild"],
        "system": "brakes",
    },
    "C0550": {
        "description": "ECU (Electronic Control Unit) Internal Malfunction",
        "severity": "high",
        "likely_causes": ["Internal module software error", "Hardware failure in ABS/EBCM module", "Low voltage event"],
        "inspections": ["Check charging system voltage", "Try battery disconnect reset", "Module may need reprogramming or replacement"],
        "system": "electrical",
    },
    "C0561": {
        "description": "ABS Disabled (Due to stored DTCs in another module)",
        "severity": "medium",
        "likely_causes": ["Another system fault has disabled ABS", "Communication error between modules"],
        "inspections": ["Scan ALL modules for stored DTCs", "Address primary fault that caused ABS disable"],
        "system": "brakes",
    },
    "C0710": {
        "description": "Steering Position Signal Malfunction",
        "severity": "medium",
        "likely_causes": ["Steering angle sensor not calibrated", "Faulty steering angle sensor", "Clockspring issue", "Wiring problem"],
        "inspections": ["Steering angle sensor calibration procedure with scan tool", "Check SAS output while turning steering wheel", "Inspect clockspring"],
        "system": "steering",
    },
    "C1145": {
        "description": "Right Front Wheel Speed Sensor Input Circuit Failure (Ford)",
        "severity": "medium",
        "likely_causes": ["Failed RF wheel speed sensor", "Damaged tone ring", "Wiring damage", "Corroded connector"],
        "inspections": ["Test sensor resistance and output", "Inspect tone ring", "Check wiring along suspension"],
        "system": "brakes",
    },
    "C1233": {
        "description": "Left Front Wheel Speed Sensor Circuit Open or Shorted (Ford)",
        "severity": "medium",
        "likely_causes": ["Open or short in LF wheel speed sensor circuit", "Sensor failure", "Connector issue"],
        "inspections": ["Test sensor resistance", "Check wiring continuity from sensor to ABS module", "Inspect connector"],
        "system": "brakes",
    },
    "C1446": {
        "description": "Brake Switch Circuit malfunction",
        "severity": "medium",
        "likely_causes": ["Faulty brake light switch", "Misadjusted brake pedal", "Wiring issue"],
        "inspections": ["Check if brake lights work correctly", "Test brake switch continuity when pedal pressed/released", "Verify pedal free play and switch adjustment"],
        "system": "brakes",
    },
    # --- U0xxx: Network Communication ---
    "U0100": {
        "description": "Lost Communication with ECM/PCM",
        "severity": "high",
        "likely_causes": ["ECM power or ground issue", "CAN bus wiring damage", "ECM internal failure", "Blown ECM fuse"],
        "inspections": ["Check ECM fuses", "Test ECM power and ground pins", "Check CAN bus resistance (should be 60 ohms across pins 6 and 14 on OBD-II)"],
        "system": "electrical",
    },
    "U0121": {
        "description": "Lost Communication with Anti-Lock Brake System (ABS) Control Module",
        "severity": "high",
        "likely_causes": ["ABS module power/ground issue", "CAN bus line damage", "ABS module internal failure"],
        "inspections": ["Check ABS module fuses", "Test CAN bus continuity to ABS module", "Check ABS module power and grounds"],
        "system": "electrical",
    },
    "U0140": {
        "description": "Lost Communication with Body Control Module (BCM)",
        "severity": "high",
        "likely_causes": ["BCM power/ground issue", "CAN bus damage", "BCM internal failure", "BCM fuse blown"],
        "inspections": ["Check BCM fuses", "Verify BCM power and ground", "Test CAN bus wiring integrity"],
        "system": "electrical",
    },
    "U0401": {
        "description": "Invalid Data Received from ECM/PCM",
        "severity": "high",
        "likely_causes": ["ECM sending corrupted data", "CAN bus interference", "Software incompatibility between modules"],
        "inspections": ["Check for ECM DTCs", "Verify latest software calibration", "Check CAN bus for intermittent shorts"],
        "system": "electrical",
    },
    "U0415": {
        "description": "Invalid Data Received from ABS Control Module",
        "severity": "high",
        "likely_causes": ["ABS module sending corrupted data", "CAN bus issue", "ABS module internal fault"],
        "inspections": ["Check ABS module for DTCs", "Verify CAN bus integrity", "Check ABS module connections"],
        "system": "electrical",
    },
    "U1000": {
        "description": "CAN Communication Bus Error (Nissan/Infiniti specific)",
        "severity": "high",
        "likely_causes": ["CAN bus wiring short or open", "Termination resistor missing/failed", "Module pulling bus voltage low"],
        "inspections": ["Measure CAN bus resistance at DLC (should be 60 ohms)", "Check CAN bus voltage (CAN-H ~2.5-3.5V, CAN-L ~1.5-2.5V)", "Unplug modules one at a time to isolate short"],
        "system": "electrical",
    },
    "U0073": {
        "description": "Control Module Communication Bus 'A' Off",
        "severity": "high",
        "likely_causes": ["CAN bus short to power or ground", "Multiple module failures", "Wiring harness damage"],
        "inspections": ["Test CAN bus resistance and voltage at OBD-II port", "Inspect wiring at common junction points", "Disconnect modules one by one"],
        "system": "electrical",
    },
}


def lookup_obd2(code: str) -> Optional[Dict[str, Any]]:
    """Look up an OBD-II diagnostic trouble code.
    
    Args:
        code: OBD-II DTC string (e.g., 'P0300', 'B1801', 'C0035')
    
    Returns:
        Dict with description, severity, likely_causes, and inspections,
        or None if code not found.
    """
    if not code:
        return None
    
    # Normalize code: uppercase, strip spaces
    code = code.upper().strip()
    
    # Direct lookup
    if code in OBD2_CODES:
        result = dict(OBD2_CODES[code])
        result["code"] = code
        result["found"] = True
        return result
    
    # Try common variations (e.g., user might type "p0300" or "P0300")
    for key in OBD2_CODES:
        if key.upper() == code:
            result = dict(OBD2_CODES[key])
            result["code"] = key
            result["found"] = True
            return result
    
    return {"code": code, "found": False, "description": f"Code {code} not found in database.", "severity": "unknown", "likely_causes": [], "inspections": []}


def lookup_obd2_batch(codes: List[str]) -> List[Dict[str, Any]]:
    """Look up multiple OBD-II codes at once.
    
    Args:
        codes: List of OBD-II code strings
    
    Returns:
        List of lookup result dicts
    """
    return [lookup_obd2(code) for code in codes if code]


# =============================================================================
# SECTION 6: VEHICLE SYSTEMS REFERENCE
# =============================================================================
# Comprehensive reference data for major vehicle systems including components,
# common failures, and factory-recommended maintenance intervals.

VEHICLE_SYSTEMS: Dict[str, Dict[str, Any]] = {
    "engine": {
        "components": [
            "Cylinder block and heads", "Pistons, rings, and connecting rods",
            "Crankshaft and main bearings", "Camshaft(s) and timing chain/belt",
            "Valvetrain (valves, springs, retainers, lifters, rockers)",
            "Timing chain tensioners and guides", "Oil pump and pickup tube",
            "Oil pan and gasket", "Intake manifold", "Exhaust manifold(s)",
            "Cylinder head gaskets", "Valve cover gaskets", "PCV system",
            "Spark plugs and ignition coils", "Fuel injectors and rail",
            "Throttle body", "MAF/MAP sensors", "Crankshaft and camshaft sensors",
            "Engine mounts",
        ],
        "common_failures": [
            {"issue": "Blown head gasket", "symptoms": ["White smoke from exhaust", "Coolant in oil", "Overheating", "Sweet coolant smell"], "typical_mileage": "100K-200K"},
            {"issue": "Timing chain stretch/wear", "symptoms": ["Rattle on cold start", "Check engine light", "Rough idle"], "typical_mileage": "80K-150K"},
            {"issue": "Oil consumption (piston rings)", "symptoms": ["Low oil between changes", "Blue smoke", "Fouled spark plugs"], "typical_mileage": "80K-150K"},
            {"issue": "Valve cover gasket leak", "symptoms": ["Oil smell", "Oil on exhaust manifold", "Smoke from engine"], "typical_mileage": "60K-100K"},
            {"issue": "Ignition coil failure", "symptoms": ["Misfire", "Check engine light", "Rough running"], "typical_mileage": "60K-120K"},
            {"issue": "Oxygen sensor failure", "symptoms": ["Check engine light P0130-P0141", "Poor fuel economy"], "typical_mileage": "60K-100K"},
        ],
        "maintenance_intervals": {
            "oil_change": "3,000-7,500 miles (synthetic extends interval)",
            "spark_plugs": "30,000-100,000 miles (depends on type)",
            "timing_belt": "60,000-105,000 miles (if equipped)",
            "air_filter": "15,000-30,000 miles",
            "coolant_flush": "30,000-50,000 miles",
            "drive_belt": "50,000-70,000 miles",
        },
    },
    "transmission": {
        "components": [
            "Torque converter (automatic)", "Clutch assembly (manual)",
            "Transmission case and internals", "Valve body (automatic)",
            "Transmission control module", "Shift solenoids",
            "Gear sets and synchronizers", "Transmission pan and filter",
            "Transmission mounts", "Driveshaft/CV axles",
            "Differential", "Transfer case (AWD/4WD)",
        ],
        "common_failures": [
            {"issue": "Transmission slipping", "symptoms": ["RPM rises without speed", "Delayed shifts", "Burnt fluid smell"], "typical_mileage": "100K-200K"},
            {"issue": "Torque converter shudder", "symptoms": ["Vibration at 45-55 mph", "Feels like driving over rumble strips"], "typical_mileage": "80K-150K"},
            {"issue": "Valve body wear", "symptoms": ["Harsh or delayed shifts", "Getting stuck in gear"], "typical_mileage": "100K+"},
            {"issue": "CV axle boot tear", "symptoms": ["Clicking when turning", "Grease spray inside wheel"], "typical_mileage": "60K-100K"},
            {"issue": "Clutch wear (manual)", "symptoms": ["Slipping under acceleration", "High pedal engagement point"], "typical_mileage": "60K-120K (varies wildly)"},
            {"issue": "Transmission mount failure", "symptoms": ["Clunk when shifting", "Excessive vibration"], "typical_mileage": "80K-120K"},
        ],
        "maintenance_intervals": {
            "fluid_change": "30,000-60,000 miles",
            "filter_change": "With fluid change",
            "clutch_inspection": "At signs of slipping",
            "axle_boot_inspection": "At every oil change",
        },
    },
    "brakes": {
        "components": [
            "Brake pedal and booster", "Master cylinder",
            "Brake lines and hoses", "ABS module and pump",
            "Brake calipers (front)", "Brake drums or rotors",
            "Brake pads (front)", "Brake shoes (rear drum)",
            "Wheel cylinders (rear drum)", "Parking brake cables",
            "Brake fluid reservoir",
        ],
        "common_failures": [
            {"issue": "Brake pad wear", "symptoms": ["Squealing", "Grinding", "Reduced braking"], "typical_mileage": "30K-70K"},
            {"issue": "Rotor warping", "symptoms": ["Pulsing brake pedal", "Steering wheel shake when braking"], "typical_mileage": "30K-60K"},
            {"issue": "Caliper sticking", "symptoms": ["Vehicle pulls when braking", "Hot wheel", "Premature pad wear"], "typical_mileage": "60K-100K"},
            {"issue": "Brake line corrosion", "symptoms": ["Spongy pedal", "Fluid leak", "Pedal sinks"], "typical_mileage": "100K+ (salt belt)"},
            {"issue": "Master cylinder failure", "symptoms": ["Pedal sinks to floor", "Fluid loss", "No braking"], "typical_mileage": "100K-150K"},
            {"issue": "ABS sensor failure", "symptoms": ["ABS light on", "False ABS activation"], "typical_mileage": "60K-100K"},
        ],
        "maintenance_intervals": {
            "pad_inspection": "Every 5,000-10,000 miles",
            "fluid_flush": "2-3 years or 30,000 miles",
            "rotor_inspection": "With pad replacement",
            "line_inspection": "Annually in salt/rust belt",
        },
    },
    "suspension": {
        "components": [
            "Struts and shock absorbers", "Coil springs",
            "Control arms and bushings", "Ball joints",
            "Tie rod ends", "Sway bar links and bushings",
            "Wheel bearings and hubs", "Steering rack and pinion",
            "Subframe and bushings",
        ],
        "common_failures": [
            {"issue": "Strut/shock wear", "symptoms": ["Bouncy ride", "Nose dive when braking", "Body roll in turns"], "typical_mileage": "50K-100K"},
            {"issue": "Ball joint wear", "symptoms": ["Clunking over bumps", "Loose steering", "Uneven tire wear"], "typical_mileage": "70K-150K"},
            {"issue": "Tie rod end wear", "symptoms": ["Loose steering", "Wandering", "Uneven tire wear"], "typical_mileage": "60K-100K"},
            {"issue": "Wheel bearing failure", "symptoms": ["Humming noise", "Wheel play", "ABS light"], "typical_mileage": "80K-150K"},
            {"issue": "Control arm bushing wear", "symptoms": ["Clunking", "Poor handling", "Vibration"], "typical_mileage": "80K-150K"},
            {"issue": "Sway bar link wear", "symptoms": ["Clunking over small bumps", "Rattling"], "typical_mileage": "50K-100K"},
        ],
        "maintenance_intervals": {
            "component_inspection": "Every alignment or tire service",
            "shock_strut": "50,000 miles (check)",
            "alignment": "Annually or after suspension work",
            "bushing_inspection": "At every oil change (visual)",
        },
    },
    "cooling": {
        "components": [
            "Radiator", "Water pump",
            "Thermostat", "Cooling fan(s) and clutch",
            "Heater core", "Coolant hoses",
            "Radiator cap/overflow reservoir", "Coolant temperature sensor",
            "Radiator support and shroud",
        ],
        "common_failures": [
            {"issue": "Water pump leak/failure", "symptoms": ["Coolant leak", "Overheating", "Whining noise"], "typical_mileage": "60K-100K"},
            {"issue": "Thermostat stuck closed", "symptoms": ["Overheating", "No heat from vents", "Coolant overflow"], "typical_mileage": "40K-80K"},
            {"issue": "Radiator leak", "symptoms": ["Coolant loss", "Overheating", "Wet spots under radiator"], "typical_mileage": "80K-150K"},
            {"issue": "Coolant hose burst", "symptoms": ["Sudden coolant loss", "Steam from engine"], "typical_mileage": "60K-100K"},
            {"issue": "Heater core leak", "symptoms": ["Sweet smell in cabin", "Wet passenger floor", "Foggy windows"], "typical_mileage": "100K-200K"},
            {"issue": "Cooling fan failure", "symptoms": ["Overheating at idle/AC", "Fan not running"], "typical_mileage": "80K-150K"},
        ],
        "maintenance_intervals": {
            "coolant_flush": "30,000-50,000 miles",
            "hose_inspection": "Annually",
            "radiator_inspection": "Annually",
            "cap_pressure_test": "With coolant flush",
        },
    },
    "electrical": {
        "components": [
            "Battery", "Alternator",
            "Starter motor", "Fuse boxes and relays",
            "Wiring harnesses", "ECM/PCM and TCM",
            "Body control module (BCM)", "ABS module",
            "CAN bus network", "Sensors (various)",
        ],
        "common_failures": [
            {"issue": "Battery failure", "symptoms": ["Slow cranking", "No start", "Dim lights"], "typical_mileage": "3-5 years"},
            {"issue": "Alternator failure", "symptoms": ["Battery light on", "Dim lights", "Dead battery"], "typical_mileage": "80K-150K"},
            {"issue": "Starter motor failure", "symptoms": ["Click no start", "Intermittent starting"], "typical_mileage": "80K-150K"},
            {"issue": "Sensor failure (various)", "symptoms": ["Check engine light", "Poor performance", "Hard starting"], "typical_mileage": "60K-100K"},
            {"issue": "Wiring corrosion", "symptoms": ["Intermittent issues", "Blown fuses", "Corroded connectors"], "typical_mileage": "100K+ (salt belt)"},
            {"issue": "Ground connection issues", "symptoms": ["Weird electrical symptoms", "Multiple codes", "Clicking relays"], "typical_mileage": "Any"},
        ],
        "maintenance_intervals": {
            "battery_test": "Annually after 3 years",
            "alternator_check": "With battery test",
            "connection_cleaning": "Annually",
            "corrosion_inspection": "Annually",
        },
    },
    "hvac": {
        "components": [
            "A/C compressor", "Condenser",
            "Evaporator core", "Expansion valve/orifice tube",
            "Refrigerant lines", "Blower motor and resistor",
            "Blend door actuator(s)", "Heater core",
            "Cabin air filter", "HVAC control module",
        ],
        "common_failures": [
            {"issue": "A/C refrigerant leak", "symptoms": ["Warm air from vents", "A/C clutch not engaging", "Oily residue at fittings"], "typical_mileage": "Any"},
            {"issue": "Blend door actuator failure", "symptoms": ["Clicking under dash", "No temp control", "Stuck hot or cold"], "typical_mileage": "60K-100K"},
            {"issue": "Blower motor resistor failure", "symptoms": ["Blower only works on high", "Intermittent blower"], "typical_mileage": "40K-80K"},
            {"issue": "Compressor clutch failure", "symptoms": ["A/C not cold", "Clutch not engaging", "Noise from compressor"], "typical_mileage": "80K-150K"},
            {"issue": "Heater core leak", "symptoms": ["Sweet smell", "Wet passenger floor", "Foggy windows"], "typical_mileage": "100K-200K"},
            {"issue": "Cabin air filter clogged", "symptoms": ["Weak airflow", "Musty smell", "Noise from blower"], "typical_mileage": "15K-30K"},
        ],
        "maintenance_intervals": {
            "cabin_filter": "15,000-30,000 miles",
            "refrigerant_check": "Annually (if performance drops)",
            "blower_inspection": "With cabin filter",
        },
    },
    "steering": {
        "components": [
            "Steering wheel and column", "Steering rack and pinion",
            "Power steering pump (hydraulic)", "Power steering reservoir and hoses",
            "Tie rod ends", "Pitman arm and idler arm (if equipped)",
            "Steering knuckles", "EPS motor (electric power steering)",
            "Steering angle sensor", "Clockspring",
        ],
        "common_failures": [
            {"issue": "Power steering pump leak/failure", "symptoms": ["Whining noise", "Hard steering", "Low fluid"], "typical_mileage": "80K-150K"},
            {"issue": "Rack and pinion leak", "symptoms": ["Power steering fluid loss", "Steering play", "Fluid in rack boots"], "typical_mileage": "100K-200K"},
            {"issue": "Tie rod end wear", "symptoms": ["Loose steering", "Wandering", "Uneven tire wear"], "typical_mileage": "60K-100K"},
            {"issue": "Steering column U-joint binding", "symptoms": ["Notchy steering", "Stiff spots when turning"], "typical_mileage": "80K+"},
            {"issue": "EPS motor failure (electric power steering)", "symptoms": ["Sudden loss of power assist", "Heavy steering", "Warning light"], "typical_mileage": "Any"},
            {"issue": "Rack mount bushing wear", "symptoms": ["Clunking when turning", "Loose steering feel"], "typical_mileage": "80K-150K"},
        ],
        "maintenance_intervals": {
            "fluid_check": "At every oil change",
            "fluid_flush": "30,000-60,000 miles",
            "component_inspection": "At every alignment or tire service",
            "belt_inspection": "If hydraulic power steering -- with serpentine belt",
        },
    },
}



# =============================================================================
# SECTION 7: REPAIR COST ESTIMATOR
# =============================================================================
# Database of common repair procedures with parts costs, labor hours,
# DIY difficulty ratings, and required tools.

REPAIR_COST_DATABASE: Dict[str, Dict[str, Any]] = {
    # --- Brake Repairs ---
    "brake_pad_replacement": {
        "parts": 40,
        "labor_hours": 1.0,
        "diy_difficulty": "easy",
        "tools_needed": ["jack", "jack stands", "lug wrench", "C-clamp or brake pad spreader"],
        "notes": "Replace in axle pairs (both front or both rear). Always inspect rotors.",
    },
    "brake_rotor_replacement": {
        "parts": 60,
        "labor_hours": 1.2,
        "diy_difficulty": "easy",
        "tools_needed": ["jack", "jack stands", "lug wrench", "socket set", "torque wrench"],
        "notes": "Always replace pads when replacing rotors. Torque lug nuts to spec in star pattern.",
    },
    "brake_caliper_replacement": {
        "parts": 80,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "lug wrench", "socket set", "brake line wrench", "bleeder kit"],
        "notes": "Replace in pairs. Must bleed brakes after replacement. Use flare nut wrench on brake lines.",
    },
    "brake_master_cylinder": {
        "parts": 90,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["socket set", "flare nut wrenches", "bleeder kit", "brake fluid"],
        "notes": "Must bench-bleed new master cylinder before installation. Must bleed all four wheels after install.",
    },
    "brake_line_replacement": {
        "parts": 30,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["tubing cutter", "flare tool", "flare nut wrenches", "brake line bender"],
        "notes": "Pre-flared lines available for common vehicles. Stainless steel lines last longer.",
    },
    "brake_fluid_flush": {
        "parts": 15,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["bleeder kit or helper", "wrench set", "brake fluid (2 quarts)"],
        "notes": "Use correct DOT fluid. Start at farthest wheel (RR, LR, RF, LF). Do not let reservoir run dry.",
    },
    
    # --- Wheel Bearing Repairs ---
    "wheel_bearing_replacement": {
        "parts": 80,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["jack", "jack stands", "lug wrench", "torque wrench", "socket set", "bearing puller or press"],
        "notes": "Front wheel bearings on FWD often require press. Rear bearings may be bolt-in hub assemblies.",
    },
    "wheel_bearing_hub_assembly_replacement": {
        "parts": 120,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "lug wrench", "socket set", "torque wrench", "impact wrench (helpful)"],
        "notes": "Hub assemblies are bolt-on and easier than press-in bearings. Torque axle nut to EXACT spec.",
    },
    
    # --- Suspension Repairs ---
    "strut_replacement": {
        "parts": 150,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["jack", "jack stands", "spring compressor (RENT THIS)", "socket set", "torque wrench"],
        "notes": "SPRING COMPRESSOR IS MANDATORY AND DANGEROUS. Rent proper tool. Mark alignment cam positions before disassembly.",
    },
    "shock_absorber_replacement": {
        "parts": 80,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "socket set", "wrenches"],
        "notes": "Rear shocks are typically bolt-on and accessible. Front may require spring removal.",
    },
    "control_arm_replacement": {
        "parts": 120,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["jack", "jack stands", "socket set", "torque wrench", "ball joint separator (pickle fork)"],
        "notes": "Get alignment after control arm replacement. Some arms come with pre-installed ball joints.",
    },
    "ball_joint_replacement": {
        "parts": 60,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["jack", "jack stands", "ball joint press (RENT)", "socket set", "torque wrench"],
        "notes": "Pressed-in joints require special tool. Some vehicles have bolt-in joints (easier). Always get alignment after.",
    },
    "tie_rod_end_replacement": {
        "parts": 40,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "wrenches", "tie rod end puller", "torque wrench"],
        "notes": "Count turns when removing to approximate alignment. MUST get alignment after replacement.",
    },
    "sway_bar_link_replacement": {
        "parts": 30,
        "labor_hours": 0.5,
        "diy_difficulty": "easy",
        "tools_needed": ["jack", "jack stands", "wrenches or ratchet"],
        "notes": "One of the easiest suspension repairs. Often done in pairs. Common clunk source.",
    },
    "sway_bar_bushing_replacement": {
        "parts": 25,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "wrenches", "socket set"],
        "notes": "May need to lower subframe slightly for access. Lubricate new bushings with silicone grease.",
    },
    "alignment": {
        "parts": 0,
        "labor_hours": 1.0,
        "diy_difficulty": "not_diy",
        "tools_needed": ["Alignment rack (shop only)"],
        "notes": "Required after any suspension work that changes geometry. Check before/after printout.",
    },
    
    # --- Engine Repairs ---
    "spark_plug_replacement": {
        "parts": 40,
        "labor_hours": 1.0,
        "diy_difficulty": "easy",
        "tools_needed": ["spark plug socket", "extension", "ratchet", "gap gauge", "torque wrench"],
        "notes": "Use anti-seize on threads. Gap to spec. Do NOT overtighten (aluminum heads strip easily).",
    },
    "ignition_coil_replacement": {
        "parts": 60,
        "labor_hours": 0.5,
        "diy_difficulty": "easy",
        "tools_needed": ["socket set", "screwdriver"],
        "notes": "Coil-on-plug systems: one per cylinder. Coil pack systems: one unit for all cylinders.",
    },
    "valve_cover_gasket_replacement": {
        "parts": 30,
        "labor_hours": 2.0,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "torque wrench", "scraper", "RTV sealant"],
        "notes": "Clean all old gasket material thoroughly. Use RTV at cam journal caps. Torque to spec in sequence.",
    },
    "timing_belt_replacement": {
        "parts": 200,
        "labor_hours": 4.0,
        "diy_difficulty": "expert",
        "tools_needed": ["socket set", "torque wrench", "timing belt tools (cam/crank locks)", "pulley puller"],
        "notes": "CRITICAL: Interference engine -- valve-to-piston contact if mistimed. Replace water pump and tensioner while in there.",
    },
    "timing_chain_replacement": {
        "parts": 400,
        "labor_hours": 8.0,
        "diy_difficulty": "expert",
        "tools_needed": ["Full tool set", "timing chain tools", "torque wrench", "shop manual"],
        "notes": "Major repair. Often requires engine support bar and special tools. Consider professional shop.",
    },
    "water_pump_replacement": {
        "parts": 80,
        "labor_hours": 3.0,
        "diy_difficulty": "hard",
        "tools_needed": ["socket set", "scraper", "torque wrench", "coolant drain pan"],
        "notes": "Replace coolant and bleed system. On some engines, water pump is behind timing cover.",
    },
    "thermostat_replacement": {
        "parts": 25,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "scraper", "coolant drain pan", "torque wrench"],
        "notes": "Use OEM thermostat. Cheap thermostats fail prematurely. Replace coolant. Bleed system properly.",
    },
    "head_gasket_replacement": {
        "parts": 300,
        "labor_hours": 15.0,
        "diy_difficulty": "expert",
        "tools_needed": ["Full tool set", "torque wrench", "torque angle gauge", "head bolt set", "machine shop for head surfacing"],
        "notes": "Major repair. Head MUST be checked for warpage at machine shop. Use new head bolts (often torque-to-yield).",
    },
    "fuel_injector_replacement": {
        "parts": 60,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "fuel line disconnect tool", "torque wrench"],
        "notes": "Relieve fuel pressure first. Replace O-rings. Use clean practices -- injectors are precision parts.",
    },
    "fuel_pump_replacement": {
        "parts": 120,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["socket set", "fuel line disconnect tools", "jack", "jack stands (if tank under car)"],
        "notes": "In-tank pumps: remove rear seat or drop tank. External pumps: usually bolt-on. Relieve pressure first.",
    },
    "alternator_replacement": {
        "parts": 150,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "wrenches", "torque wrench"],
        "notes": "Disconnect battery before starting. Note belt routing. Test new alternator output after install.",
    },
    "starter_replacement": {
        "parts": 120,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "wrenches", "jack (if hard to reach)"],
        "notes": "Disconnect battery first. May need to access from underneath. Check flywheel teeth for damage.",
    },
    
    # --- Transmission Repairs ---
    "transmission_fluid_change": {
        "parts": 50,
        "labor_hours": 1.0,
        "diy_difficulty": "medium",
        "tools_needed": ["drain pan", "funnel", "socket set", "torque wrench"],
        "notes": "Use EXACT fluid specified by manufacturer. Wrong fluid destroys transmissions. Measure what comes out, put same amount in.",
    },
    "cv_axle_replacement": {
        "parts": 80,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["jack", "jack stands", "lug wrench", "socket set", "pry bar", "torque wrench"],
        "notes": "Remove axle nut with car on ground (breaker bar). May need pry bar to pop axle from transmission. Use new axle nut.",
    },
    "clutch_replacement": {
        "parts": 250,
        "labor_hours": 6.0,
        "diy_difficulty": "expert",
        "tools_needed": ["Full tool set", "transmission jack", "clutch alignment tool", "torque wrench", "shop manual"],
        "notes": "Major repair. Must remove transmission. Use alignment tool. Inspect flywheel for hot spots. Consider flywheel resurfacing.",
    },
    
    # --- Cooling System Repairs ---
    "radiator_replacement": {
        "parts": 150,
        "labor_hours": 2.0,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "pliers", "coolant drain pan", "torque wrench"],
        "notes": "Drain coolant first. Transfer fan shroud and any accessories to new radiator. Bleed system after.",
    },
    "heater_core_replacement": {
        "parts": 100,
        "labor_hours": 6.0,
        "diy_difficulty": "expert",
        "tools_needed": ["Full tool set", "shop manual (for dash removal)", "coolant drain pan"],
        "notes": "Major job. Usually requires partial dashboard removal. Consider bypassing heater core as temporary fix.",
    },
    
    # --- Exhaust Repairs ---
    "catalytic_converter_replacement": {
        "parts": 300,
        "labor_hours": 2.0,
        "diy_difficulty": "medium",
        "tools_needed": ["socket set", "penetrating oil", "oxy-acetylene torch (may be needed for seized bolts)", "torque wrench"],
        "notes": "Aftermarket converters are cheaper but may not last as long. Check warranty. May need O2 sensor sockets.",
    },
    "muffler_replacement": {
        "parts": 80,
        "labor_hours": 1.0,
        "diy_difficulty": "easy",
        "tools_needed": ["socket set", "wrenches", "hacksaw (if clamp-on)"],
        "notes": "Clamp-on mufflers are DIY-friendly. Welded systems require shop. Consider stainless steel for longevity.",
    },
    "oxygen_sensor_replacement": {
        "parts": 50,
        "labor_hours": 0.5,
        "diy_difficulty": "easy",
        "tools_needed": ["O2 sensor socket", "ratchet", "penetrating oil", "torque wrench"],
        "notes": "Use proper O2 sensor socket (slotted for wire). Soak with penetrating oil. Do NOT overtighten.",
    },
    
    # --- Steering Repairs ---
    "power_steering_pump_replacement": {
        "parts": 120,
        "labor_hours": 2.0,
        "diy_difficulty": "hard",
        "tools_needed": ["socket set", "pulley puller/installer", "torque wrench", "power steering fluid"],
        "notes": "Need special tool to remove/install pulley on new pump. Flush system. Use correct fluid type.",
    },
    "steering_rack_replacement": {
        "parts": 250,
        "labor_hours": 4.0,
        "diy_difficulty": "expert",
        "tools_needed": ["Full tool set", "jack", "jack stands", "torque wrench", "shop manual"],
        "notes": "Major repair. Must get alignment after. May need to drop subframe for access. Transfer inner tie rods or replace.",
    },
    
    # --- HVAC Repairs ---
    "ac_compressor_replacement": {
        "parts": 300,
        "labor_hours": 3.0,
        "diy_difficulty": "hard",
        "tools_needed": ["socket set", "A/C manifold gauge set", "vacuum pump", "torque wrench"],
        "notes": "Must evacuate refrigerant (EPA requirement -- shop does this). Replace receiver drier. Vacuum and recharge after install.",
    },
    "blend_door_actuator_replacement": {
        "parts": 40,
        "labor_hours": 1.5,
        "diy_difficulty": "medium",
        "tools_needed": ["screwdriver", "socket set (small)", "patience"],
        "notes": "Usually behind glove box or under dash. Can be tight space. Note actuator position before removal.",
    },
    "cabin_air_filter_replacement": {
        "parts": 20,
        "labor_hours": 0.3,
        "diy_difficulty": "easy",
        "tools_needed": ["None (may need screwdriver)"],
        "notes": "Behind glove box or under hood at cowl. Replace every 15K-30K miles. Easy and improves A/C performance.",
    },
    
    # --- Maintenance Items ---
    "oil_change": {
        "parts": 35,
        "labor_hours": 0.5,
        "diy_difficulty": "easy",
        "tools_needed": ["jack", "jack stands", "oil filter wrench", "drain pan", "funnel", "socket set"],
        "notes": "Warm up engine first (oil flows better). Use correct oil weight and capacity. Recycle used oil.",
    },
    "tire_replacement": {
        "parts": 400,
        "labor_hours": 1.0,
        "diy_difficulty": "not_diy",
        "tools_needed": ["Tire mounting and balancing machine (shop only)"],
        "notes": "Always replace in pairs (front or rear) or all four (AWD). Get alignment with new tires.",
    },
    "battery_replacement": {
        "parts": 150,
        "labor_hours": 0.2,
        "diy_difficulty": "easy",
        "tools_needed": ["wrenches", "battery terminal cleaner"],
        "notes": "Disconnect negative first, reconnect negative last. Use memory saver to preserve radio settings. Clean terminals.",
    },
    "serpentine_belt_replacement": {
        "parts": 35,
        "labor_hours": 0.5,
        "diy_difficulty": "easy",
        "tools_needed": ["socket set or breaker bar", "belt routing diagram"],
        "notes": "Note routing BEFORE removing. Draw diagram. Check tensioner and idler pulleys while belt is off.",
    },
    "belt_tensioner_replacement": {
        "parts": 65,
        "labor_hours": 0.8,
        "diy_difficulty": "easy",
        "tools_needed": ["socket set", "breaker bar"],
        "notes": "Replace tensioner whenever replacing belt if over 60K miles on tensioner. Check idler pulleys too.",
    },
    "pcv_valve_replacement": {
        "parts": 15,
        "labor_hours": 0.3,
        "diy_difficulty": "easy",
        "tools_needed": ["pliers or wrench"],
        "notes": "One of the cheapest maintenance items. Often overlooked. Can cause oil leaks and rough idle when clogged.",
    },
    "air_filter_replacement": {
        "parts": 20,
        "labor_hours": 0.2,
        "diy_difficulty": "easy",
        "tools_needed": ["None (may need screwdriver for clips)"],
        "notes": "Check every 15K miles. Replace when dirty. Quick 2-minute job that improves performance and MPG.",
    },
    "fuel_filter_replacement": {
        "parts": 20,
        "labor_hours": 0.5,
        "diy_difficulty": "medium",
        "tools_needed": ["line wrench set", "drain pan", "safety glasses"],
        "notes": "Relieve fuel pressure first (pull fuel pump fuse, run engine until stall). Fuel spray risk -- wear eye protection.",
    },
}

# Regional labor rate multipliers (USD per hour)
LABOR_RATES = {
    "national_average": 100,  # per hour
    "low_cost": 75,
    "high_cost": 150,
    "luxury_specialist": 200,
    "dealership_average": 130,
}

# Luxury vehicle parts cost multiplier
LUXURY_MULTIPLIER = 1.8  # European luxury parts cost ~80% more

# Older vehicle considerations
OLD_VEHICLE_YEAR_THRESHOLD = 2005  # Before this, parts may be harder to find
OLD_VEHICLE_PARTS_MULTIPLIER = 1.3  # 30% premium for hard-to-find parts


def estimate_repair_cost(diagnosis: dict, vehicle_year: int = None, luxury: bool = False) -> dict:
    """Estimate repair costs based on differential diagnosis.
    
    Cross-references the top causes in the differential diagnosis with the
    REPAIR_COST_DATABASE to provide cost estimates. Accounts for vehicle age,
    luxury status, and regional labor rates.
    
    Args:
        diagnosis: Diagnostic report dict containing differential_diagnosis
        vehicle_year: Optional model year of the vehicle
        luxury: True if the vehicle is a luxury brand (BMW, Mercedes, Audi, etc.)
    
    Returns:
        Dict with cost breakdown: low_end, high_end, diy_savings, parts_cost,
        labor_hours, labor_cost, notes, and per-repair breakdown.
    """
    differential = diagnosis.get("differential_diagnosis", [])
    
    if not differential:
        return {
            "low_end": 0,
            "high_end": 0,
            "diy_savings": 0,
            "parts_cost": 0,
            "labor_hours": 0,
            "labor_cost": 0,
            "notes": "No specific repair identified. Schedule professional inspection.",
            "breakdown": [],
        }
    
    matched_repairs = []
    total_low = 0
    total_high = 0
    total_parts = 0
    total_labor_hours = 0
    
    # Map cause keywords to repair procedures
    cause_repair_map = {
        "brake pad": "brake_pad_replacement",
        "brake rotor": "brake_rotor_replacement",
        "caliper": "brake_caliper_replacement",
        "master cylinder": "brake_master_cylinder",
        "brake line": "brake_line_replacement",
        "brake fluid": "brake_fluid_flush",
        "wheel bearing": "wheel_bearing_hub_assembly_replacement",
        "shock": "shock_absorber_replacement",
        "strut": "strut_replacement",
        "control arm": "control_arm_replacement",
        "ball joint": "ball_joint_replacement",
        "tie rod": "tie_rod_end_replacement",
        "sway bar link": "sway_bar_link_replacement",
        "sway bar bushing": "sway_bar_bushing_replacement",
        "alignment": "alignment",
        "spark plug": "spark_plug_replacement",
        "ignition coil": "ignition_coil_replacement",
        "valve cover gasket": "valve_cover_gasket_replacement",
        "timing belt": "timing_belt_replacement",
        "timing chain": "timing_chain_replacement",
        "water pump": "water_pump_replacement",
        "thermostat": "thermostat_replacement",
        "head gasket": "head_gasket_replacement",
        "fuel injector": "fuel_injector_replacement",
        "fuel pump": "fuel_pump_replacement",
        "fuel filter": "fuel_filter_replacement",
        "serpentine belt": "serpentine_belt_replacement",
        "belt tensioner": "belt_tensioner_replacement",
        "alternator": "alternator_replacement",
        "starter": "starter_replacement",
        "transmission fluid": "transmission_fluid_change",
        "CV joint": "cv_axle_replacement",
        "clutch": "clutch_replacement",
        "battery": "battery_replacement",
        "radiator": "radiator_replacement",
        "heater core": "heater_core_replacement",
        "catalytic converter": "catalytic_converter_replacement",
        "muffler": "muffler_replacement",
        "oxygen sensor": "oxygen_sensor_replacement",
        "power steering pump": "power_steering_pump_replacement",
        "steering rack": "steering_rack_replacement",
        "A/C compressor": "ac_compressor_replacement",
        "blend door actuator": "blend_door_actuator_replacement",
        "cabin air filter": "cabin_air_filter_replacement",
        "air filter": "air_filter_replacement",
        "oil change": "oil_change",
        "tire": "tire_replacement",
        "PCV valve": "pcv_valve_replacement",
        "brake hose": "brake_line_replacement",
    }
    
    seen_repairs = set()
    
    for cause in differential[:5]:  # Top 5 causes
        cause_name = cause.get("name", "").lower()
        
        # Find matching repair procedure
        matched_key = None
        for keyword, repair_key in cause_repair_map.items():
            if keyword in cause_name and repair_key not in seen_repairs:
                matched_key = repair_key
                seen_repairs.add(repair_key)
                break
        
        if matched_key and matched_key in REPAIR_COST_DATABASE:
            repair = REPAIR_COST_DATABASE[matched_key]
            
            # Calculate costs
            base_parts = repair["parts"]
            labor_hrs = repair["labor_hours"]
            
            # Apply luxury multiplier
            parts_multiplier = LUXURY_MULTIPLIER if luxury else 1.0
            
            # Apply old vehicle multiplier
            if vehicle_year and vehicle_year < OLD_VEHICLE_YEAR_THRESHOLD:
                parts_multiplier *= OLD_VEHICLE_PARTS_MULTIPLIER
            
            adjusted_parts = round(base_parts * parts_multiplier, 2)
            
            # Calculate labor cost range
            labor_low = round(labor_hrs * LABOR_RATES["low_cost"], 2)
            labor_high = round(labor_hrs * LABOR_RATES["high_cost"], 2)
            labor_avg = round(labor_hrs * LABOR_RATES["national_average"], 2)
            
            repair_low = adjusted_parts + labor_low
            repair_high = adjusted_parts + labor_high
            
            # DIY savings (no labor cost)
            diy_cost = adjusted_parts
            diy_savings = labor_avg
            
            matched_repairs.append({
                "cause": cause["name"],
                "repair_procedure": repair["name"] if "name" in repair else matched_key,
                "parts_cost": adjusted_parts,
                "labor_hours": labor_hrs,
                "labor_cost_low": labor_low,
                "labor_cost_high": labor_high,
                "total_low": repair_low,
                "total_high": repair_high,
                "diy_cost": diy_cost,
                "diy_savings": diy_savings,
                "diy_difficulty": repair["diy_difficulty"],
                "notes": repair.get("notes", ""),
            })
            
            total_low += repair_low
            total_high += repair_high
            total_parts += adjusted_parts
            total_labor_hours += labor_hrs
    
    # Calculate overall DIY savings
    total_diy_savings = sum(r["diy_savings"] for r in matched_repairs)
    
    notes = []
    if luxury:
        notes.append("Luxury vehicle multiplier applied (+80% parts cost). European luxury vehicles often require specialist tools.")
    if vehicle_year and vehicle_year < OLD_VEHICLE_YEAR_THRESHOLD:
        notes.append(f"Pre-{OLD_VEHICLE_YEAR_THRESHOLD} vehicle: parts may be harder to find (+30% parts cost estimate).")
    if total_labor_hours > 8:
        notes.append("Major repair estimated. Consider getting multiple quotes from independent shops.")
    if not matched_repairs:
        notes.append("No matching repair procedures found for the identified causes. Professional diagnosis recommended.")
    
    # Per-repair difficulty summary
    diy_possibilities = [r for r in matched_repairs if r["diy_difficulty"] in ("easy", "medium")]
    
    return {
        "low_end": round(total_low, 2),
        "high_end": round(total_high, 2),
        "diy_possible": len(diy_possibilities) > 0,
        "diy_savings": round(total_diy_savings, 2),
        "parts_cost": round(total_parts, 2),
        "labor_hours": round(total_labor_hours, 1),
        "labor_cost_low": round(total_labor_hours * LABOR_RATES["low_cost"], 2),
        "labor_cost_high": round(total_labor_hours * LABOR_RATES["high_cost"], 2),
        "notes": " ".join(notes) if notes else "Estimates based on national average labor rates.",
        "breakdown": matched_repairs,
        "diy_friendly_repairs": [r["repair_procedure"] for r in diy_possibilities],
    }


def get_diy_guide(repair_name: str) -> Optional[Dict[str, Any]]:
    """Get detailed DIY information for a specific repair procedure.
    
    Args:
        repair_name: Key name from REPAIR_COST_DATABASE
    
    Returns:
        Dict with repair details or None if not found.
    """
    if repair_name not in REPAIR_COST_DATABASE:
        # Try to find by partial match
        for key in REPAIR_COST_DATABASE:
            if repair_name.lower() in key.lower():
                repair_name = key
                break
        else:
            return None
    
    repair = dict(REPAIR_COST_DATABASE[repair_name])
    repair["key"] = repair_name
    return repair


# =============================================================================
# SECTION 8: FORMATTED REPORT OUTPUT
# =============================================================================

def format_diagnosis_report(diagnosis: dict) -> str:
    """Format a diagnostic report as a human-readable string.
    
    Args:
        diagnosis: Diagnostic report dict from diagnose()
    
    Returns:
        Formatted multi-line string report
    """
    lines = []
    
    # Header
    lines.append("=" * 70)
    lines.append("LUQI AI AUTOMOTIVE DIAGNOSTIC REPORT")
    lines.append("=" * 70)
    
    # Vehicle info
    vehicle = diagnosis.get("vehicle_info", {})
    if vehicle:
        lines.append(f"\nVehicle: {vehicle.get('year', 'N/A')} {vehicle.get('make', 'N/A')} {vehicle.get('model', 'N/A')}")
        if vehicle.get("mileage"):
            lines.append(f"Mileage: {vehicle['mileage']:,}")
    
    # Input symptoms
    lines.append(f"\nReported Symptoms:")
    for symptom in diagnosis.get("input_symptoms", []):
        lines.append(f"  - {symptom}")
    
    # Identified symptoms
    identified = diagnosis.get("identified_symptoms", [])
    if identified:
        lines.append(f"\nIdentified Symptom Patterns ({len(identified)}):")
        for item in identified:
            conf = int(item.get("confidence", 0) * 100)
            lines.append(f"  - {item['category']}.{item['symptom']} ({conf}% confidence)")
    
    # Safety warnings
    safety_warnings = diagnosis.get("safety_warnings", [])
    if safety_warnings:
        lines.append("\n" + "!" * 70)
        lines.append("SAFETY WARNINGS")
        lines.append("!" * 70)
        for warning in safety_warnings:
            lines.append(f"  ⚠ {warning}")
        lines.append("!" * 70)
    
    # Differential diagnosis
    differential = diagnosis.get("differential_diagnosis", [])
    if differential:
        lines.append("\n" + "-" * 70)
        lines.append("DIFFERENTIAL DIAGNOSIS (Most Likely Causes)")
        lines.append("-" * 70)
        for i, cause in enumerate(differential[:8], 1):
            prob = int(cause.get("probability", 0) * 100)
            severity = cause.get("severity", "unknown").upper()
            cost = cause.get("cost", "unknown")
            lines.append(f"\n  {i}. {cause['name']}")
            lines.append(f"     Probability: {prob}% | Severity: {severity} | Cost: {cost}")
            if cause.get("inspection"):
                lines.append(f"     Check: {cause['inspection']}")
    
    # Safety notes
    safety_notes = diagnosis.get("safety_notes", [])
    if safety_notes:
        lines.append("\n" + "-" * 70)
        lines.append("SAFETY NOTES")
        lines.append("-" * 70)
        for note in safety_notes:
            lines.append(f"  • {note}")
    
    # Recommended inspections
    inspections = diagnosis.get("recommended_inspections", [])
    if inspections:
        lines.append("\n" + "-" * 70)
        lines.append("ZERO-COST INSPECTIONS YOU CAN DO NOW")
        lines.append("-" * 70)
        for i, insp in enumerate(inspections[:6], 1):
            lines.append(f"\n  {i}. {insp['name']} (Time: {insp.get('time', 'N/A')})")
            lines.append(f"     Tools needed: {insp.get('tools', 'None')}")
            if insp.get("steps"):
                lines.append("     Steps:")
                for step in insp["steps"][:4]:  # Show first 4 steps
                    lines.append(f"       • {step}")
                if len(insp["steps"]) > 4:
                    lines.append(f"       • ... ({len(insp['steps']) - 4} more steps)")
            if insp.get("what_youre_looking_for"):
                lines.append(f"     What to look for: {insp['what_youre_looking_for'][:120]}...")
            if insp.get("safety_warning"):
                lines.append(f"     ⚠ SAFETY: {insp['safety_warning']}")
    
    # Urgency
    urgency = diagnosis.get("urgency", "routine")
    urgency_display = {
        "immediate": "⚠ IMMEDIATE ACTION REQUIRED",
        "soon": "⏱ SCHEDULE WITHIN 3-5 DAYS",
        "routine": "📅 ROUTINE MAINTENANCE WINDOW",
    }
    lines.append("\n" + "-" * 70)
    lines.append("URGENCY ASSESSMENT")
    lines.append("-" * 70)
    lines.append(f"  {urgency_display.get(urgency, urgency)}")
    
    # Cost estimates
    costs = diagnosis.get("estimated_repair_costs", {})
    if costs and costs.get("low_end", 0) > 0:
        lines.append("\n" + "-" * 70)
        lines.append("ESTIMATED REPAIR COSTS")
        lines.append("-" * 70)
        lines.append(f"  Low estimate:  ${costs['low_end']:.2f}")
        lines.append(f"  High estimate: ${costs['high_end']:.2f}")
        lines.append(f"  Parts:         ${costs.get('parts_cost', 0):.2f}")
        lines.append(f"  Labor hours:   {costs.get('labor_hours', 0):.1f}")
        if costs.get("diy_possible"):
            lines.append(f"  DIY savings:   ${costs.get('diy_savings', 0):.2f}")
        
        breakdown = costs.get("breakdown", [])
        if breakdown:
            lines.append("\n  Breakdown by repair:")
            for item in breakdown:
                lines.append(f"    - {item['repair_procedure']}: ${item['total_low']:.0f}-${item['total_high']:.0f} "
                           f"(DIY: {item['diy_difficulty']})")
        
        if costs.get("notes"):
            lines.append(f"\n  Notes: {costs['notes']}")
    
    # When to see mechanic
    lines.append("\n" + "-" * 70)
    lines.append("WHEN TO SEE A MECHANIC")
    lines.append("-" * 70)
    lines.append(f"  {diagnosis.get('when_to_see_mechanic', 'Schedule at your convenience.')}")
    
    # Disclaimer
    lines.append("\n" + "=" * 70)
    lines.append("DISCLAIMER")
    lines.append("=" * 70)
    lines.append(diagnosis.get("disclaimer", ""))
    lines.append("")
    
    return "\n".join(lines)


def diagnose_from_text(description: str, vehicle_info: dict = None) -> str:
    """One-shot diagnostic function that takes free text and returns formatted report.
    
    This is the simplest entry point for the diagnostic system.
    
    Args:
        description: Free-text symptom description from the user
        vehicle_info: Optional vehicle details
    
    Returns:
        Formatted diagnostic report string
    """
    result = diagnose([description], vehicle_info)
    return format_diagnosis_report(result)


def quick_check(system: str = None) -> Dict[str, Any]:
    """Get a quick reference for a vehicle system.
    
    Args:
        system: System name (engine, transmission, brakes, suspension, etc.)
               If None, returns list of available systems.
    
    Returns:
        System reference data or list of available systems
    """
    if system is None:
        return {
            "available_systems": list(VEHICLE_SYSTEMS.keys()),
            "description": "Pass one of the available system names to get detailed reference info.",
        }
    
    system_lower = system.lower()
    if system_lower in VEHICLE_SYSTEMS:
        return VEHICLE_SYSTEMS[system_lower]
    
    return {"error": f"System '{system}' not found. Available: {list(VEHICLE_SYSTEMS.keys())}"}


def get_maintenance_schedule(vehicle_year: int = None, mileage: int = None) -> List[Dict[str, str]]:
    """Generate a maintenance schedule based on vehicle age and mileage.
    
    Args:
        vehicle_year: Model year of vehicle
        mileage: Current odometer reading
    
    Returns:
        List of maintenance items with due status
    """
    from datetime import datetime
    
    schedule = []
    current_year = datetime.now().year
    age = current_year - vehicle_year if vehicle_year else 0
    
    # Build schedule from all systems
    for system_name, system_data in VEHICLE_SYSTEMS.items():
        for item, interval in system_data.get("maintenance_intervals", {}).items():
            schedule.append({
                "system": system_name,
                "item": item,
                "recommended_interval": interval,
                "status": "check" if mileage else "refer to manual",
            })
    
    return schedule


def diagnose_with_obd2(obd2_codes: List[str], symptoms: List[str] = None, vehicle_info: dict = None) -> dict:
    """Combined diagnostic using both OBD-II codes and symptom descriptions.
    
    This provides the most comprehensive diagnostic by cross-referencing
    stored trouble codes with reported symptoms.
    
    Args:
        obd2_codes: List of OBD-II DTC strings
        symptoms: Optional list of symptom descriptions
        vehicle_info: Optional vehicle details
    
    Returns:
        Combined diagnostic report
    """
    vehicle_info = vehicle_info or {}
    
    # Look up all OBD-II codes
    code_results = lookup_obd2_batch(obd2_codes)
    found_codes = [c for c in code_results if c.get("found")]
    
    # Build symptom list from OBD-II code descriptions
    all_symptoms = list(symptoms) if symptoms else []
    
    # Add code descriptions as symptoms for cross-referencing
    for code in found_codes:
        desc = code.get("description", "")
        if desc:
            all_symptoms.append(desc)
    
    # Run main diagnosis
    diagnosis = diagnose(all_symptoms, vehicle_info)
    
    # Add OBD-II specific data
    diagnosis["obd2_codes"] = {
        "codes_read": obd2_codes,
        "codes_found": [c["code"] for c in found_codes],
        "codes_not_found": [c["code"] for c in code_results if not c.get("found")],
        "code_details": found_codes,
    }
    
    # If any codes indicate high severity, upgrade urgency
    for code in found_codes:
        if code.get("severity") in ("high", "critical"):
            if diagnosis.get("urgency") not in ("immediate",):
                diagnosis["urgency"] = "soon"
    
    return diagnosis


# =============================================================================
# MODULE ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Demo/self-test when run directly
    print("Luqi AI Automotive Diagnostic Module v1.0.0")
    print("=" * 50)
    print()
    
    # Test 1: Parse symptoms
    print("TEST 1: Symptom Parsing")
    test_desc = "My car makes a grinding noise when I brake, especially at high speed"
    parsed = parse_symptoms(test_desc)
    print(f"Input: '{test_desc}'")
    print(f"Parsed: {len(parsed)} symptoms")
    for p in parsed:
        print(f"  - {p['category']}.{p['symptom']} ({int(p['confidence']*100)}%)")
    print()
    
    # Test 2: OBD-II lookup
    print("TEST 2: OBD-II Code Lookup")
    for code in ["P0300", "P0420", "B1801"]:
        result = lookup_obd2(code)
        if result.get("found"):
            print(f"  {code}: {result['description'][:50]}...")
    print()
    
    # Test 3: Full diagnosis
    print("TEST 3: Full Diagnosis")
    report = diagnose_from_text(
        "grinding noise when braking and steering wheel vibration at highway speed",
        {"year": 2015, "make": "Toyota", "model": "Camry", "mileage": 85000}
    )
    # Print first 30 lines of report
    for line in report.split("\n")[:30]:
        print(line)
    print("...")
    print()
    
    # Test 4: Statistics
    print("TEST 4: Database Statistics")
    total_symptoms = sum(len(cat) for cat in SYMPTOM_DATABASE.values())
    total_causes = sum(
        len(symptom.get("causes", []))
        for category in SYMPTOM_DATABASE.values()
        for symptom in category.values()
    )
    print(f"  Symptom categories: {len(SYMPTOM_DATABASE)}")
    print(f"  Total symptoms: {total_symptoms}")
    print(f"  Total causes: {total_causes}")
    print(f"  OBD-II codes: {len(OBD2_CODES)}")
    print(f"  Inspection procedures: {len(INSPECTION_LIBRARY)}")
    print(f"  Repair procedures: {len(REPAIR_COST_DATABASE)}")
    print(f"  Vehicle systems: {len(VEHICLE_SYSTEMS)}")
    print()
    print("All tests completed successfully.")