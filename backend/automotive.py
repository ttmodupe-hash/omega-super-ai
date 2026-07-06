"""
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
            "safety_note": "Hissing from the exhaust manifold area can allow deadly carbon monoxide into the cabin. Never drive with windows closed if exhaust leak is suspected.",
        },
        "rattling": {
            "causes": [
                {"name": "Loose exhaust heat shield", "probability": 0.85, "cost": "low", "severity": "low", "inspection": "Tap exhaust components with rubber mallet to isolate rattle"},
                {"name": "Worn catalytic converter internals", "probability": 0.50, "cost": "high", "severity": "medium", "inspection": "Shake catalytic converter by hand -- ceramic substrate rattling confirms failure"},
                {"name": "Loose suspension components", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Jack up vehicle, wiggle control arms, sway bar links, and tie rods"},
                {"name": "Timing chain tensioner worn", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Rattle on cold start that goes away; check oil quality and level"},
                {"name": "Loose interior trim or bodywork", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Press on interior panels and exterior trim to locate source"},
                {"name": "Bad water pump bearing", "probability": 0.25, "cost": "medium", "severity": "high", "inspection": "Wiggle water pump pulley; check for coolant weep hole leakage"},
                {"name": "Loose brake caliper bolts", "probability": 0.15, "cost": "low", "severity": "critical", "inspection": "Immediately check all brake caliper mounting bolts for proper torque"},
            ],
            "safety_note": "Rattling from suspension or brakes must be inspected before highway driving. Loose brake caliper bolts are an IMMEDIATE safety hazard.",
        },
        "clicking": {
            "causes": [
                {"name": "Failing CV joint (outer)", "probability": 0.80, "cost": "medium", "severity": "medium", "inspection": "Clicking during turns indicates outer CV joint; inspect boots"},
                {"name": "Failing CV joint (inner)", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Clicking during acceleration/deceleration; inspect boots"},
                {"name": "Loud fuel injector ticking", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Use mechanic's stethoscope to confirm noise at injector rail"},
                {"name": "Valve train tick (lifter/rocker)", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Check oil level and condition; low oil causes valve tick"},
                {"name": "Loose spark plug", "probability": 0.20, "cost": "low", "severity": "high", "inspection": "Remove and re-torque spark plugs to spec with feeler gauge"},
                {"name": "Relay or solenoid cycling", "probability": 0.15, "cost": "low", "severity": "low", "inspection": "Listen under dash and hood to isolate electrical clicking"},
                {"name": "Wheel bearing with debris in race", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Rotate wheel by hand and feel for rough spots or clicks"},
            ],
            "safety_note": "CV joint clicking during turns means the joint is near failure. A broken CV joint causes sudden loss of power to the wheel.",
        },
        "whining": {
            "causes": [
                {"name": "Low power steering fluid", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Check power steering reservoir level and color"},
                {"name": "Worn power steering pump", "probability": 0.60, "cost": "medium", "severity": "medium", "inspection": "Whine increases when turning steering wheel; check pump pulley"},
                {"name": "Alternator bearing failing", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Remove belt, spin alternator pulley by hand for roughness"},
                {"name": "Transmission pump whine (low fluid)", "probability": 0.50, "cost": "low", "severity": "high", "inspection": "Check transmission fluid level with engine running in Park"},
                {"name": "Differential pinion bearing wear", "probability": 0.25, "cost": "high", "severity": "medium", "inspection": "Whine changes with vehicle speed, not engine speed"},
                {"name": "Worn timing belt/chain idler", "probability": 0.20, "cost": "high", "severity": "high", "inspection": "Remove timing cover and inspect belt/chain tensioners"},
                {"name": "Fuel pump failing", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Whine from rear of vehicle under back seat or fuel tank area"},
            ],
            "safety_note": "Transmission or power steering whining often indicates low fluid. Continuing to drive can destroy the pump or transmission.",
        },
        "drone_hum": {
            "causes": [
                {"name": "Worn wheel bearing", "probability": 0.85, "cost": "medium", "severity": "medium", "inspection": "Drone changes with vehicle speed; swerve left/right to load/unload bearings"},
                {"name": "Tire cupping/feathering", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Run hand across tire tread in both directions for uneven wear"},
                {"name": "Differential carrier bearing wear", "probability": 0.30, "cost": "high", "severity": "medium", "inspection": "Drone at highway speeds; check differential fluid"},
                {"name": "Wheel alignment issue (toe out)", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Inspect tire inner/outer edges for feathered wear pattern"},
                {"name": "Propeller shaft/U-joint wear", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Check driveshaft U-joints for play by twisting shaft by hand"},
                {"name": "Road noise from aggressive tread tires", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Check if noise changes dramatically on different road surfaces"},
            ],
            "safety_note": "Wheel bearing drones tend to get suddenly louder before total failure. Plan replacement within 200 miles of noticing.",
        },
        "backfiring": {
            "causes": [
                {"name": "Ignition timing too advanced", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Check timing with timing light; scan for P0011/P0014 codes"},
                {"name": "Lean air/fuel mixture", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Check for vacuum leaks, dirty MAF sensor, clogged fuel filter"},
                {"name": "Exhaust leak near engine", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Visual inspection of exhaust manifold gasket and flange bolts"},
                {"name": "Cracked exhaust valve", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Compression test; low compression on one cylinder indicates valve issue"},
                {"name": "Faulty ignition coil (intermittent)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Swap coils between cylinders; see if misfire follows the coil"},
            ],
            "safety_note": "Backfires through the intake can damage MAF sensors and air intake components. Avoid hard acceleration until diagnosed.",
        },
        "ticking": {
            "causes": [
                {"name": "Exhaust manifold leak (cracked manifold or gasket)", "probability": 0.70, "cost": "medium", "severity": "medium", "inspection": "Look for black soot at manifold-to-head joint; listen with stethoscope"},
                {"name": "Lifter tick (low oil or worn lifters)", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Check oil level first; add oil if low. Use engine flush if sludged"},
                {"name": "Fuel injector normal operation", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Stethoscope at fuel rail -- even, rhythmic ticking is normal"},
                {"name": "Worn rocker arm or lash adjuster", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Remove valve cover, inspect rocker arms for wear or looseness"},
                {"name": "Spark plug arcing (bad wire/boot)", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Spray soapy water on plug wires in dark -- look for blue arcing"},
                {"name": "Alternator diode failure", "probability": 0.15, "cost": "medium", "severity": "medium", "inspection": "Ticking from alternator area; check charging voltage (should be 13.5-14.5V)"},
            ],
            "safety_note": "Persistent loud ticking accompanied by low oil pressure gauge reading indicates serious engine damage. Stop driving immediately.",
        },
        "squeaking": {
            "causes": [
                {"name": "Worn sway bar bushings", "probability": 0.75, "cost": "low", "severity": "low", "inspection": "Spray rubber bushing with silicone lubricant; noise should temporarily stop"},
                {"name": "Dry ball joint or tie rod end", "probability": 0.60, "cost": "medium", "severity": "medium", "inspection": "Inspect rubber boots for tears; check for grease leakage"},
                {"name": "Worn control arm bushings", "probability": 0.50, "cost": "medium", "severity": "low", "inspection": "Have assistant bounce car while you watch control arm movement"},
                {"name": "Dry door/trunk/hood hinge or seal", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Apply silicone spray to rubber seals and white lithium grease to hinges"},
                {"name": "Worn suspension spring isolators", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Remove spring and inspect upper/lower isolator pads for wear"},
            ],
            "safety_note": "Squeaking suspension components are usually not immediately dangerous but indicate wear that will progress. Inspect within 2 weeks.",
        },
        "howling": {
            "causes": [
                {"name": "Severely worn wheel bearing", "probability": 0.80, "cost": "medium", "severity": "high", "inspection": "Jack up wheel, rotate by hand -- grinding or roughness confirms failure"},
                {"name": "Differential gear wear", "probability": 0.40, "cost": "high", "severity": "high", "inspection": "Howl under acceleration or deceleration; check differential fluid level/color"},
                {"name": "Transmission bearing failure", "probability": 0.30, "cost": "high", "severity": "high", "inspection": "Howl in specific gear or all gears; check transmission fluid"},
                {"name": "Wind noise (door seal or mirror)", "probability": 0.55, "cost": "low", "severity": "low", "inspection": "Tape suspected areas with masking tape and test drive to isolate"},
            ],
            "safety_note": "Howling wheel bearings can seize without warning at highway speeds. This is a CRITICAL safety issue -- replace immediately.",
        },
    },

    # -------------------------------------------------------------------------
    # CATEGORY: FEEL / DRIVING DYNAMICS
    # -------------------------------------------------------------------------
    "feel": {
        "vibration": {
            "causes": [
                {"name": "Unbalanced tire (lost wheel weight)", "probability": 0.80, "cost": "low", "severity": "low", "inspection": "Check wheel for missing balance weight; vibration at specific speed"},
                {"name": "Bent wheel rim", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Jack up car, spin wheel slowly and watch for wobble"},
                {"name": "Worn engine mount", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Vibration in drive but not in neutral; watch engine movement under load"},
                {"name": "Warped brake rotor", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Vibration only when braking; measure rotor runout with dial indicator"},
                {"name": "Driveshaft out of balance", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Vibration increases with speed; inspect driveshaft weights"},
                {"name": "Misfire under load", "probability": 0.35, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes; check spark plugs and coils"},
                {"name": "Failing constant velocity joint", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Vibration during acceleration; check CV boots for tears"},
            ],
            "safety_note": "Severe vibration at highway speeds can cause loss of control. Reduce speed until cause is identified.",
        },
        "pulling_left": {
            "causes": [
                {"name": "Low left front tire pressure", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Check and compare all four tire pressures with gauge"},
                {"name": "Worn left front brake caliper (dragging)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "After driving, check if left wheel is hotter than right (dragging brake)"},
                {"name": "Wheel alignment (excessive negative camber on left)", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Visual check of tire wear on inner vs outer edge; get alignment check"},
                {"name": "Broken left front spring (sagging)", "probability": 0.15, "cost": "medium", "severity": "high", "inspection": "Measure ride height left vs right; look for cracked or broken coil spring"},
                {"name": "Worn steering rack mount (bushing)", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Have assistant turn wheel while you watch rack movement under car"},
            ],
            "safety_note": "A vehicle that pulls sharply to one side can dart unexpectedly on crowned roads or during emergency maneuvers. Correct before highway driving.",
        },
        "pulling_right": {
            "causes": [
                {"name": "Low right front tire pressure", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Check and compare all four tire pressures with gauge"},
                {"name": "Worn right front brake caliper (dragging)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "After driving, check if right wheel is hotter than left (dragging brake)"},
                {"name": "Wheel alignment (excessive negative camber on right)", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Visual check of tire wear inner vs outer edge; get alignment check"},
                {"name": "Road crown effect (normal on flat roads)", "probability": 0.40, "cost": "none", "severity": "low", "inspection": "Test on perfectly flat road or parking lot; slight pull may be normal"},
                {"name": "Broken right front spring (sagging)", "probability": 0.15, "cost": "medium", "severity": "high", "inspection": "Measure ride height left vs right; look for cracked or broken coil spring"},
            ],
            "safety_note": "Same safety concerns as pulling left. Always verify tire pressures first before assuming alignment issues.",
        },
        "slipping": {
            "causes": [
                {"name": "Worn clutch (manual transmission)", "probability": 0.80, "cost": "high", "severity": "high", "inspection": "Engine revs increase but car does not accelerate; test in high gear at low speed"},
                {"name": "Low automatic transmission fluid", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Check transmission fluid level with engine running in Park, on level ground"},
                {"name": "Worn automatic transmission clutches", "probability": 0.55, "cost": "very_high", "severity": "high", "inspection": "Slips in specific gear or between shifts; fluid may be dark/burnt"},
                {"name": "Faulty torque converter", "probability": 0.30, "cost": "high", "severity": "high", "inspection": "High RPM at highway speed with poor acceleration; may set P0741 code"},
                {"name": "Worn differential clutch packs (AWD/4WD)", "probability": 0.20, "cost": "high", "severity": "medium", "inspection": "Slipping sensation on turns or under hard acceleration in AWD vehicles"},
            ],
            "safety_note": "TRANSMISSION SLIPPING: Slipping transmission can fail completely without warning. Avoid highway driving and steep hills until repaired.",
        },
        "shuddering": {
            "causes": [
                {"name": "Warped brake rotors", "probability": 0.75, "cost": "low", "severity": "medium", "inspection": "Shudder ONLY when braking; feel through brake pedal and steering wheel"},
                {"name": "Worn engine/transmission mounts", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Shudder at idle in drive; watch engine movement when shifting P-R-N-D"},
                {"name": "Failing torque converter clutch (TCC)", "probability": 0.40, "cost": "high", "severity": "medium", "inspection": "Shudder at highway speed 45-55mph; feels like driving over rumble strips"},
                {"name": "Bent wheel or tire out of round", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Shudder at specific speed; swap wheels front to rear to test"},
                {"name": "Driveshaft/U-joint worn", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Shudder under acceleration; check U-joints for play"},
            ],
            "safety_note": "Torque converter clutch shudder can damage the transmission if driven for extended periods. Have diagnosed within 500 miles.",
        },
        "jerking": {
            "causes": [
                {"name": "Engine misfire (ignition or fuel)", "probability": 0.75, "cost": "low", "severity": "high", "inspection": "Scan for misfire codes (P030x); check spark plugs, coils, injectors"},
                {"name": "Dirty/failing MAF sensor", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Clean MAF with dedicated cleaner; check for P0101 code"},
                {"name": "Clogged fuel filter", "probability": 0.35, "cost": "low", "severity": "high", "inspection": "Check fuel pressure at rail; jerking under load indicates fuel starvation"},
                {"name": "Faulty throttle position sensor (TPS)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Scan for P0120-P0124; test TPS voltage sweep with multimeter"},
                {"name": "Dirty throttle body", "probability": 0.45, "cost": "low", "severity": "low", "inspection": "Remove intake hose, inspect throttle plate for carbon buildup"},
                {"name": "Failing ignition coil", "probability": 0.40, "cost": "low", "severity": "high", "inspection": "Swap coils between cylinders; see if misfire follows the swapped coil"},
            ],
            "safety_note": "Jerking/misfiring during highway merging or passing is a SAFETY HAZARD. Complete loss of power in traffic can cause a collision.",
        },
        "spongy_brake": {
            "causes": [
                {"name": "Air in brake lines", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Pedal feels soft, travels to floor; brake fluid may be low (leak)"},
                {"name": "Brake fluid leak", "probability": 0.55, "cost": "medium", "severity": "critical", "inspection": "Inspect brake lines, calipers, wheel cylinders, master cylinder for wet spots"},
                {"name": "Worn brake master cylinder", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Pedal slowly sinks to floor when held; internal seal failure"},
                {"name": "Rear brake shoe out of adjustment (drums)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Remove drum, check shoe adjustment and wheel cylinder for leaks"},
                {"name": "Flexible brake hose ballooning", "probability": 0.20, "cost": "low", "severity": "high", "inspection": "Inspect rubber brake hoses for swelling or soft spots"},
                {"name": "Contaminated brake fluid (water absorption)", "probability": 0.25, "cost": "low", "severity": "high", "inspection": "Test brake fluid with moisture tester; dark color indicates contamination"},
            ],
            "safety_note": "CRITICAL BRAKE WARNING: A spongy brake pedal can indicate an impending total brake failure. Do NOT drive the vehicle. Have it towed to a repair facility.",
        },
        "hard_steering": {
            "causes": [
                {"name": "Low power steering fluid", "probability": 0.80, "cost": "low", "severity": "medium", "inspection": "Check power steering reservoir level and condition"},
                {"name": "Failing power steering pump", "probability": 0.55, "cost": "medium", "severity": "medium", "inspection": "Listen for whining; check belt tension; test pump pressure"},
                {"name": "Damaged steering rack", "probability": 0.35, "cost": "high", "severity": "high", "inspection": "Hard steering in both directions; check rack boots for leaks"},
                {"name": "Seized tie rod end or ball joint", "probability": 0.30, "cost": "medium", "severity": "critical", "inspection": "Jack up front wheels, disconnect tie rods, test each joint for binding"},
                {"name": "Incorrect tire pressure (severely low)", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Check all tire pressures with gauge"},
                {"name": "Binding steering column U-joint", "probability": 0.15, "cost": "low", "severity": "medium", "inspection": "Feel for notchiness or binding when turning steering wheel with engine off"},
            ],
            "safety_note": "Hard steering makes emergency evasive maneuvers extremely difficult. A seized ball joint can cause sudden loss of steering control.",
        },
        "loose_steering": {
            "causes": [
                {"name": "Worn tie rod ends", "probability": 0.85, "cost": "low", "severity": "high", "inspection": "Jack up front wheels, wiggle tire at 3 and 9 o'clock positions"},
                {"name": "Worn steering rack mount bushings", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Have assistant turn wheel; watch rack housing for excessive movement"},
                {"name": "Worn idler arm or pitman arm", "probability": 0.40, "cost": "low", "severity": "high", "inspection": "Wiggle center link at idler/pitman arm connections"},
                {"name": "Worn upper or lower ball joints", "probability": 0.45, "cost": "medium", "severity": "critical", "inspection": "Jack up wheels, wiggle tire at 12 and 6 o'clock positions"},
                {"name": "Excessive toe alignment", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Vehicle wanders on straight road; steering feels disconnected"},
            ],
            "safety_note": "Loose steering from worn tie rods or ball joints can cause the wheel to fold under during a turn, resulting in complete loss of control. Inspect IMMEDIATELY.",
        },
        "rough_idle": {
            "causes": [
                {"name": "Dirty/faulty idle air control (IAC) valve", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Remove IAC valve, clean carbon buildup with throttle body cleaner"},
                {"name": "Vacuum leak", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Spray carb cleaner around intake manifold -- RPM change indicates leak"},
                {"name": "Worn spark plugs", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Remove and inspect plugs for wear, gap, fouling, or oil contamination"},
                {"name": "Dirty MAF sensor", "probability": 0.45, "cost": "low", "severity": "low", "inspection": "Clean MAF sensor element with dedicated MAF cleaner spray"},
                {"name": "Clogged fuel injector", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Pour fuel injector cleaner in tank; swap injectors to isolate"},
                {"name": "Low compression on one cylinder", "probability": 0.25, "cost": "high", "severity": "high", "inspection": "Perform compression test on all cylinders; compare readings"},
                {"name": "Failing ignition coil", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Scan for misfire codes; swap coils between cylinders"},
                {"name": "Dirty throttle body", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Remove intake hose, clean throttle plate and bore with cleaner"},
            ],
            "safety_note": "Rough idle caused by vacuum leaks can cause stalling at intersections. This is a safety concern in traffic.",
        },
        "delayed_shifting": {
            "causes": [
                {"name": "Low transmission fluid", "probability": 0.75, "cost": "low", "severity": "high", "inspection": "Check fluid level hot, engine running in Park on level ground"},
                {"name": "Worn transmission solenoids", "probability": 0.50, "cost": "medium", "severity": "medium", "inspection": "Scan for transmission-related codes; check shift solenoid operation"},
                {"name": "Dirty/contaminated transmission fluid", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Check fluid color -- bright red is good, brown/black is bad, burnt smell = bad"},
                {"name": "Failing transmission control module", "probability": 0.20, "cost": "high", "severity": "medium", "inspection": "Scan for communication or TCM fault codes"},
                {"name": "Worn clutch packs (internal)", "probability": 0.35, "cost": "very_high", "severity": "high", "inspection": "Delayed engagement in Drive or Reverse after sitting; transmission rebuild needed"},
            ],
            "safety_note": "Delayed engagement when shifting into Drive or Reverse can cause unexpected vehicle movement. Always apply brake firmly when shifting automatic transmissions.",
        },
        "pulsing_brake_pedal": {
            "causes": [
                {"name": "Warped brake rotors", "probability": 0.90, "cost": "low", "severity": "medium", "inspection": "Pedal pulses/vibrates during braking; most common cause"},
                {"name": "ABS false activation", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Pulsing at low speed on dry pavement; scan for ABS codes"},
                {"name": "Uneven brake pad deposit on rotor", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Rotors have blue discoloration spots; perform bed-in procedure"},
                {"name": "Rear drum brake out of round", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Pulsing felt in brake pedal but not steering wheel; check rear drums"},
                {"name": "Loose wheel bearings causing rotor wobble", "probability": 0.15, "cost": "medium", "severity": "high", "inspection": "Check wheel bearings for play with wheel off ground"},
            ],
            "safety_note": "Severely warped rotors reduce braking effectiveness and increase stopping distance. Replace before emergency braking is needed.",
        },
        "wandering": {
            "causes": [
                {"name": "Worn steering components (tie rods, idler arm)", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Jack up front, check all steering linkage for play"},
                {"name": "Worn suspension bushings", "probability": 0.55, "cost": "medium", "severity": "medium", "inspection": "Inspect control arm bushings for cracking, tearing, or excessive movement"},
                {"name": "Incorrect toe alignment", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Vehicle does not track straight on level road; tires may show feathering"},
                {"name": "Worn struts or shocks", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Bounce test; vehicle continues to oscillate beyond 2 cycles = worn"},
                {"name": "Uneven tire pressures", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Check all four tire pressures with accurate gauge"},
            ],
            "safety_note": "Wandering steering requires constant correction and increases driver fatigue. In an emergency, delayed reaction time can cause an accident.",
        },
        "stiff_gas_pedal": {
            "causes": [
                {"name": "Dirty throttle body/throttle plate", "probability": 0.65, "cost": "low", "severity": "low", "inspection": "Remove intake hose, inspect throttle plate for carbon buildup restricting movement"},
                {"name": "Binding throttle cable", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Disconnect cable at throttle body, test pedal feel; lubricate cable housing"},
                {"name": "Accelerator pedal sensor fault", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Scan for P2120-P2123 (APP sensor codes); test sensor voltage"},
                {"name": "Cruise control cable interference", "probability": 0.15, "cost": "low", "severity": "low", "inspection": "Inspect cruise control cable routing and connector at throttle body"},
                {"name": "Floor mat interference", "probability": 0.25, "cost": "none", "severity": "high", "inspection": "Check floor mat position; Toyota recall issue -- mats can trap pedal"},
            ],
            "safety_note": "FLOOR MAT HAZARD: Ensure floor mats are properly secured with retention clips. A trapped accelerator pedal is a severe safety risk.",
        },
    },

    # -------------------------------------------------------------------------
    # CATEGORY: SMELLS
    # -------------------------------------------------------------------------
    "smells": {
        "burning_oil": {
            "causes": [
                {"name": "Oil leaking onto exhaust manifold", "probability": 0.85, "cost": "low", "severity": "medium", "inspection": "Look for smoke from under hood; oil on exhaust manifold or pipe will smoke"},
                {"name": "Valve cover gasket leak", "probability": 0.75, "cost": "low", "severity": "low", "inspection": "Inspect valve cover perimeter for oil seepage onto exhaust"},
                {"name": "Oil filler cap or dipstick loose/missing", "probability": 0.30, "cost": "low", "severity": "low", "inspection": "Check oil cap is tight; check dipstick is fully seated"},
                {"name": "Rear main seal leak", "probability": 0.25, "cost": "high", "severity": "medium", "inspection": "Oil accumulating between engine and transmission; requires transmission removal"},
                {"name": "Turbocharger oil seal failure", "probability": 0.20, "cost": "high", "severity": "medium", "inspection": "Blue smoke from exhaust; oil in intercooler piping; check shaft play"},
                {"name": "PCV system clogged (forcing oil out seals)", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Remove PCV valve and shake; should rattle freely. Check breather hose"},
            ],
            "safety_note": "Oil leaking onto a hot exhaust manifold is a FIRE HAZARD. Keep a fire extinguisher rated for Class B fires in your vehicle if you smell burning oil.",
        },
        "sweet_coolant": {
            "causes": [
                {"name": "Coolant leak (heater core)", "probability": 0.70, "cost": "medium", "severity": "medium", "inspection": "Sweet smell inside cabin; wet passenger floorboard; foggy windows with oily film"},
                {"name": "Coolant leak (radiator hose)", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Inspect upper/lower radiator hoses, heater hoses for swelling or wetness"},
                {"name": "Head gasket leak (internal)", "probability": 0.40, "cost": "high", "severity": "critical", "inspection": "White smoke from exhaust; coolant reservoir bubbling; milky oil on dipstick"},
                {"name": "Radiator cap not sealing", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Check cap gasket condition; pressure test cooling system"},
                {"name": "Intake manifold gasket leak", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "External coolant leak at manifold-to-head joint; scan for lean codes"},
                {"name": "Water pump weep hole leaking", "probability": 0.45, "cost": "medium", "severity": "high", "inspection": "Look for coolant stain/trail below water pump weep hole"},
            ],
            "safety_note": "A strong coolant smell inside the cabin with foggy windows indicates a leaking heater core. Coolant vapor is TOXIC -- do not drive with these symptoms.",
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
                {"name": "Power steering fluid leak onto exhaust", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Check power steering lines and rack boots for leaks"},
                {"name": "Transmission fluid leak onto exhaust", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Inspect transmission cooler lines and pan gasket"},
            ],
            "safety_note": "A sweet metallic smell combined with any brake fluid loss is CRITICAL. Brake fluid leaks can cause sudden brake failure.",
        },
        "exhaust_fumes": {
            "causes": [
                {"name": "Exhaust leak before catalytic converter", "probability": 0.80, "cost": "medium", "severity": "critical", "inspection": "Look for black soot at manifold flanges, flex pipe, or gasket joints"},
                {"name": "Missing or damaged exhaust manifold gasket", "probability": 0.60, "cost": "low", "severity": "critical", "inspection": "Listen for ticking/hissing; look for soot marks at manifold-to-head joint"},
                {"name": "Hole in floorboard or trunk seal", "probability": 0.30, "cost": "medium", "severity": "critical", "inspection": "Inspect floor pans from underneath for rust holes; check all rubber plugs"},
                {"name": "Rear hatch/trunk seal leaking (station wagons/SUVs)", "probability": 0.20, "cost": "low", "severity": "high", "inspection": "Exhaust enters through rear when idling; check tailpipe extension length"},
                {"name": "Window or door seal leak (convertibles)", "probability": 0.25, "cost": "low", "severity": "critical", "inspection": "Fumes enter at stops; check soft top seals and window alignment"},
            ],
            "safety_note": "CARBON MONOXIDE POISONING HAZARD: Exhaust fumes in the cabin can be FATAL. Do NOT drive the vehicle. Carbon monoxide is odorless -- by the time you smell exhaust, CO levels are already dangerous. Have towed immediately.",
        },
        "sweet_fruity": {
            "causes": [
                {"name": "Ethylene glycol coolant leak (heater core)", "probability": 0.75, "cost": "medium", "severity": "high", "inspection": "Fruity smell in cabin indicates heater core leak; check passenger floor"},
                {"name": "Coolant overflow reservoir cap leak", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Inspect reservoir cap seal; pressure test to verify system holds pressure"},
                {"name": "Windshield washer fluid leak (methanol smell)", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Some washer fluids have sweet smell; check washer reservoir and lines"},
                {"name": "Coolant leak at hose clamp", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Check all hose clamps for tightness; look for white coolant residue"},
            ],
            "safety_note": "Coolant (ethylene glycol) is HIGHLY TOXIC if inhaled as vapor. Do not drive with a suspected heater core leak -- the cabin vapor concentration can cause poisoning.",
        },
        "sulfur_acid": {
            "causes": [
                {"name": "Overcharged battery (boiling electrolyte)", "probability": 0.65, "cost": "medium", "severity": "high", "inspection": "Check charging voltage -- over 15.5V indicates voltage regulator failure"},
                {"name": "Failing alternator/voltage regulator", "probability": 0.55, "cost": "medium", "severity": "high", "inspection": "Measure voltage at battery with engine running; should be 13.5-14.5V"},
                {"name": "Shorted battery cell", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Battery feels hot after driving; hydrometer shows one cell different"},
                {"name": "Battery terminal corrosion", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "White/green powder on terminals; clean with baking soda and water"},
            ],
            "safety_note": "A boiling battery produces explosive hydrogen gas and sulfuric acid vapor. Do not smoke or create sparks near a boiling battery. Replace immediately.",
        },
    },

    # -------------------------------------------------------------------------
    # CATEGORY: VISUAL / DASHBOARD INDICATORS
    # -------------------------------------------------------------------------
    "visual": {
        "check_engine_light": {
            "causes": [
                {"name": "Loose or missing gas cap", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Tighten gas cap until it clicks; check for cracked cap seal"},
                {"name": "Oxygen sensor failure", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Scan for O2 sensor codes (P0130-P0167); check sensor response with scanner"},
                {"name": "Catalytic converter efficiency low", "probability": 0.30, "cost": "high", "severity": "medium", "inspection": "Scan for P0420/P0430; check O2 sensor waveforms"},
                {"name": "Mass airflow (MAF) sensor dirty", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Clean MAF sensor with dedicated cleaner; check for P0101"},
                {"name": "Ignition system misfire", "probability": 0.40, "cost": "low", "severity": "high", "inspection": "Scan for P030x codes; check spark plugs, coils, and injectors"},
                {"name": "EVAP system leak", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Scan for P0455/P0456; check gas cap, purge valve, and EVAP lines"},
                {"name": "Thermostat stuck open", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Engine takes too long to reach operating temperature; scan for P0128"},
            ],
            "safety_note": "A flashing check engine light indicates an active misfire that will damage the catalytic converter. Drive minimally and avoid hard acceleration.",
        },
        "oil_light": {
            "causes": [
                {"name": "Low engine oil level", "probability": 0.85, "cost": "low", "severity": "critical", "inspection": "Check oil level immediately on dipstick; add oil if low"},
                {"name": "Faulty oil pressure sensor", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Install mechanical oil pressure gauge to verify actual pressure"},
                {"name": "Worn engine bearings (low oil pressure)", "probability": 0.30, "cost": "very_high", "severity": "critical", "inspection": "Mechanical oil pressure test; low hot idle pressure = worn bearings"},
                {"name": "Clogged oil pickup tube screen", "probability": 0.20, "cost": "medium", "severity": "critical", "inspection": "Low oil pressure at idle; may be sludge from infrequent oil changes"},
                {"name": "Oil pump failure", "probability": 0.15, "cost": "high", "severity": "critical", "inspection": "No oil pressure even with correct level; engine noise accompanies"},
                {"name": "Oil viscosity too thin (wrong oil)", "probability": 0.15, "cost": "low", "severity": "medium", "inspection": "Verify correct oil viscosity for climate; check if oil was recently changed"},
            ],
            "safety_note": "OIL LIGHT = STOP IMMEDIATELY. Driving with the oil light on will destroy your engine within minutes. The oil light indicates pressure loss, not just low level. TOW THE VEHICLE.",
        },
        "battery_light": {
            "causes": [
                {"name": "Failing alternator (not charging)", "probability": 0.70, "cost": "medium", "severity": "high", "inspection": "Check voltage at battery with engine running (should be 13.5-14.5V)"},
                {"name": "Loose or corroded battery terminals", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Wiggle terminals; clean white/green corrosion with baking soda solution"},
                {"name": "Broken alternator belt", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Open hood, verify serpentine belt is present and tensioned"},
                {"name": "Failing battery (won't hold charge)", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Load test battery at auto parts store; should hold >9.6V under load"},
                {"name": "Voltage regulator failure", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Voltage over 15V or under 13V indicates regulator issue"},
                {"name": "Parasitic electrical drain", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Measure current draw with all systems off; should be <50mA"},
            ],
            "safety_note": "With the battery light on, you have 15-45 minutes of driving before the battery dies and the engine stalls. Headlights and power steering will fail. Drive only to nearest safe location.",
        },
        "coolant_leak": {
            "causes": [
                {"name": "Radiator hose leak (upper/lower)", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Inspect all hoses for swelling, cracks, or wetness at connections"},
                {"name": "Radiator leak (core or tank)", "probability": 0.50, "cost": "medium", "severity": "high", "inspection": "Look for coolant between radiator fins; pressure test radiator"},
                {"name": "Water pump leak (weep hole)", "probability": 0.60, "cost": "medium", "severity": "high", "inspection": "Look for coolant stain below water pump weep hole on timing cover"},
                {"name": "Heater core leak", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Wet passenger floorboard; sweet smell in cabin; foggy windows"},
                {"name": "Head gasket external leak", "probability": 0.30, "cost": "high", "severity": "critical", "inspection": "Coolant at head/block mating surface; may have white exhaust smoke"},
                {"name": "Expansion tank/reservoir crack", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Inspect plastic reservoir for cracks, especially at hose connections"},
                {"name": "Freeze plug (core plug) leak", "probability": 0.15, "cost": "medium", "severity": "high", "inspection": "Rust-colored coolant weeping from side of engine block"},
            ],
            "safety_note": "ANY coolant leak can lead to overheating and catastrophic engine damage (warped head, blown head gasket, seized engine). Monitor temperature gauge closely and carry coolant/water.",
        },
        "oil_leak": {
            "causes": [
                {"name": "Valve cover gasket leak", "probability": 0.80, "cost": "low", "severity": "low", "inspection": "Oil seeping from valve cover perimeter; common on high-mileage engines"},
                {"name": "Oil pan gasket leak", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Oil on bottom of oil pan; may require removal for proper resealing"},
                {"name": "Rear main seal leak", "probability": 0.45, "cost": "high", "severity": "medium", "inspection": "Oil between engine and transmission; requires transmission removal"},
                {"name": "Oil filter loose or double-gasketed", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Check filter tightness by hand; look for oil around filter base"},
                {"name": "Oil pressure sender leak", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Small leak from sensor on side of engine block; replace sender"},
                {"name": "Camshaft seal leak", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Oil from behind cam gear/timing cover; inspect timing cover area"},
                {"name": "Drain plug leak (washer/gasket)", "probability": 0.20, "cost": "low", "severity": "low", "inspection": "Oil around drain plug; replace crush washer or gasket"},
            ],
            "safety_note": "Even small oil leaks can reach the exhaust manifold and cause a fire. Also, chronic oil leaks lead to low oil levels and engine damage. Check oil level weekly until repaired.",
        },
        "smoke_exhaust": {
            "causes": [
                {"name": "Burning oil (blue smoke)", "probability": 0.70, "cost": "high", "severity": "medium", "inspection": "Blue smoke indicates oil burning; check PCV valve, valve seals, or rings"},
                {"name": "Coolant burning (white smoke)", "probability": 0.65, "cost": "high", "severity": "critical", "inspection": "Sweet-smelling white smoke = head gasket; check for coolant in oil"},
                {"name": "Rich fuel mixture (black smoke)", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Black sooty smoke; scan for rich codes, check MAF sensor and fuel pressure"},
                {"name": "Turbocharger oil seal failure", "probability": 0.30, "cost": "high", "severity": "medium", "inspection": "Blue smoke after idle (turbo drains oil into exhaust); check shaft play"},
                {"name": "Leaking fuel injector (black smoke)", "probability": 0.25, "cost": "low", "severity": "high", "inspection": "Black smoke at idle; remove spark plugs -- black wet plug = leaking injector"},
                {"name": "Cracked cylinder head or block", "probability": 0.10, "cost": "very_high", "severity": "critical", "inspection": "Continuous white smoke with coolant loss; compression test and leak-down test"},
            ],
            "safety_note": "White smoke with sweet smell = BLOWN HEAD GASKET. Stop driving immediately. Coolant in the oil will destroy engine bearings within hours of operation.",
        },
        "smoke_engine": {
            "causes": [
                {"name": "Oil leaking onto exhaust manifold", "probability": 0.85, "cost": "low", "severity": "high", "inspection": "Look for smoke from under hood at front of engine; check valve cover gasket"},
                {"name": "Coolant leaking onto exhaust", "probability": 0.40, "cost": "medium", "severity": "high", "inspection": "Sweet-smelling white smoke from engine bay; check intake manifold gasket"},
                {"name": "Power steering fluid leak onto exhaust", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Smoke during steering; check power steering hose routing near exhaust"},
                {"name": "Brake fluid leak onto exhaust", "probability": 0.15, "cost": "medium", "severity": "critical", "inspection": "Sweet chemical smell; check brake lines near exhaust components"},
                {"name": "Plastic debris on hot engine", "probability": 0.30, "cost": "none", "severity": "low", "inspection": "Look for shopping bags, leaves, or plastic parts resting on exhaust manifold"},
                {"name": "Electrical short/overheating wire", "probability": 0.20, "cost": "low", "severity": "critical", "inspection": "Acrid electrical smell; inspect wiring near hot components"},
            ],
            "safety_note": "SMOKE FROM THE ENGINE COMPARTMENT IS A FIRE RISK. Pull over immediately, turn off the engine, and pop the hood (do NOT open fully if flames visible). Use a fire extinguisher if needed. Call emergency services.",
        },
        "fluid_under_car": {
            "causes": [
                {"name": "Engine oil leak", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Brown/black, oily texture; check oil level; inspect pan, valve cover, seals"},
                {"name": "Coolant leak", "probability": 0.55, "cost": "low", "severity": "high", "inspection": "Green, orange, or pink; sweet smell; slimy texture; check reservoir level"},
                {"name": "Transmission fluid leak", "probability": 0.45, "cost": "medium", "severity": "high", "inspection": "Red or brown, oily; check transmission dipstick; inspect pan gasket and lines"},
                {"name": "Condensation from A/C (normal water)", "probability": 0.80, "cost": "none", "severity": "low", "inspection": "Clear water, no smell, only with A/C running -- this is NORMAL"},
                {"name": "Brake fluid leak", "probability": 0.20, "cost": "medium", "severity": "critical", "inspection": "Clear to amber, oily, distinct smell; check master cylinder reservoir level"},
                {"name": "Power steering fluid leak", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Red or clear, oily; check PS reservoir; inspect lines and rack boots"},
                {"name": "Gasoline leak", "probability": 0.10, "cost": "low", "severity": "critical", "inspection": "Clear, strong gasoline smell, evaporates quickly; DO NOT START ENGINE"},
                {"name": "Differential/transfer case leak", "probability": 0.15, "cost": "low", "severity": "medium", "inspection": "Thick, brown/black gear oil; check differential cover and pinion seal"},
            ],
            "safety_note": "GASOLINE: Do not start engine, do not drive. BRAKE FLUID: Check reservoir level before driving; if low, do not drive. All other leaks: identify fluid type and monitor levels before driving.",
        },
        "brake_warning_light": {
            "causes": [
                {"name": "Low brake fluid level", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Check brake fluid reservoir; low level indicates worn pads or leak"},
                {"name": "Worn brake pads (low pad sensor)", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Some vehicles have pad wear sensors; inspect pad thickness"},
                {"name": "Parking brake partially engaged", "probability": 0.40, "cost": "none", "severity": "low", "inspection": "Ensure parking brake is fully released; pull and release again"},
                {"name": "Brake fluid leak in system", "probability": 0.25, "cost": "medium", "severity": "critical", "inspection": "Inspect all brake lines, calipers, and wheel cylinders for wetness"},
                {"name": "ABS system fault", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Scan for ABS codes; check wheel speed sensors for debris"},
            ],
            "safety_note": "The brake warning light indicates a hydraulic or fluid level issue. Test brakes at low speed before continuing. If pedal feels soft, tow the vehicle.",
        },
        "tire_pressure_light": {
            "causes": [
                {"name": "Low tire pressure (one or more tires)", "probability": 0.85, "cost": "none", "severity": "medium", "inspection": "Check all four tire pressures with accurate gauge; inflate to door jamb spec"},
                {"name": "Tire puncture (slow leak)", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Spray soapy water on tire tread and sidewall; look for bubbles"},
                {"name": "Faulty TPMS sensor", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Light flashes then stays solid = sensor battery dead or sensor failed"},
                {"name": "Temperature change (seasonal pressure drop)", "probability": 0.50, "cost": "none", "severity": "low", "inspection": "For every 10F temperature drop, tires lose 1 PSI -- re-inflate"},
                {"name": "Spare tire low (some vehicles monitor spare)", "probability": 0.10, "cost": "none", "severity": "low", "inspection": "Check spare tire pressure; often overlooked cause of TPMS light"},
            ],
            "safety_note": "Driving on underinflated tires causes overheating and can lead to sudden tire failure (blowout). For every 1 PSI underinflated, fuel economy drops 0.2%.",
        },
        "airbag_light": {
            "causes": [
                {"name": "Faulty clockspring (steering wheel)", "probability": 0.50, "cost": "medium", "severity": "high", "inspection": "Scan for B1801 or similar; horn and cruise may also not work"},
                {"name": "Disconnected seat connector (under seat)", "probability": 0.40, "cost": "none", "severity": "high", "inspection": "Check yellow connector under front seats is fully clicked in"},
                {"name": "Bad occupant sensor (passenger seat)", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Scan for passenger occupant classification system codes"},
                {"name": "Deployed airbag not reset", "probability": 0.15, "cost": "high", "severity": "high", "inspection": "History of accident; airbag module may need programming after replacement"},
                {"name": "Corrosion in airbag harness connector", "probability": 0.20, "cost": "low", "severity": "high", "inspection": "Inspect all yellow airbag harness connectors for green corrosion"},
            ],
            "safety_note": "The airbag light means the airbag WILL NOT deploy in a crash. This is a critical safety system. In many jurisdictions, an illuminated airbag light is an inspection failure.",
        },
        "abs_light": {
            "causes": [
                {"name": "Faulty wheel speed sensor", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Scan for specific wheel sensor code; inspect sensor tip for metal debris/rust"},
                {"name": "Broken tone ring (reluctor ring)", "probability": 0.35, "cost": "medium", "severity": "medium", "inspection": "Inspect tone ring on CV joint or axle hub for cracks or missing teeth"},
                {"name": "Low brake fluid triggering ABS fault", "probability": 0.30, "cost": "low", "severity": "high", "inspection": "Check brake fluid level; low fluid can trigger both brake and ABS lights"},
                {"name": "ABS module failure", "probability": 0.15, "cost": "high", "severity": "medium", "inspection": "Communication error with ABS module; module may need rebuild or replace"},
                {"name": "Wiring harness damage to wheel sensor", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Follow sensor wire from hub to body; look for chafing at suspension joints"},
            ],
            "safety_note": "With the ABS light on, your anti-lock brakes are disabled. In a panic stop on slippery surfaces, wheels WILL lock up. Increase following distance and brake earlier.",
        },
        "temperature_warning": {
            "causes": [
                {"name": "Low coolant level", "probability": 0.75, "cost": "low", "severity": "critical", "inspection": "Check coolant reservoir when engine is COLD; add 50/50 coolant/water mix"},
                {"name": "Faulty thermostat (stuck closed)", "probability": 0.50, "cost": "low", "severity": "high", "inspection": "Overheats at highway speed; upper radiator hose stays cold = stuck closed"},
                {"name": "Failed water pump", "probability": 0.35, "cost": "medium", "severity": "critical", "inspection": "No coolant circulation; belt-driven -- check belt; electric -- check fuse"},
                {"name": "Clogged radiator (internal or external)", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "External: clean bugs/debris from fins; Internal: flush, check for cold spots"},
                {"name": "Faulty cooling fan", "probability": 0.40, "cost": "low", "severity": "high", "inspection": "Overheats at idle/stop; check fan spins freely when engine hot; check fuse/relay"},
                {"name": "Blown head gasket (combustion gases in coolant)", "probability": 0.25, "cost": "high", "severity": "critical", "inspection": "Coolant bubbling in reservoir; white exhaust; milky oil; combustion leak test"},
                {"name": "Faulty temperature sensor", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Gauge reads high but engine not actually hot; verify with infrared thermometer"},
            ],
            "safety_note": "OVERHEATING: Pull over IMMEDIATELY when temperature gauge enters red. Driving even 1 more mile can warp the cylinder head ($2000+ repair). Wait 30+ minutes before opening radiator cap.",
        },
        "traction_control_light": {
            "causes": [
                {"name": "Faulty wheel speed sensor (shared with ABS)", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Usually accompanies ABS light; scan for wheel speed sensor codes"},
                {"name": "Mismatched tire sizes (different rolling diameter)", "probability": 0.30, "cost": "medium", "severity": "low", "inspection": "Check all four tires are same size; even small differences trigger traction control"},
                {"name": "Steering angle sensor needs calibration", "probability": 0.25, "cost": "low", "severity": "low", "inspection": "Scan tool calibration procedure; may occur after alignment or battery disconnect"},
                {"name": "Lateral acceleration sensor fault", "probability": 0.15, "cost": "medium", "severity": "low", "inspection": "Scan for yaw rate or lateral acceleration sensor codes"},
                {"name": "Traction control button accidentally pressed", "probability": 0.35, "cost": "none", "severity": "low", "inspection": "Look for TC OFF button on dash or center console; press to re-enable"},
            ],
            "safety_note": "With traction control disabled, wheelspin on wet/slippery surfaces is more likely. Drive more cautiously in adverse weather conditions.",
        },
    },

    # -------------------------------------------------------------------------
    # CATEGORY: TIMING / CONDITIONS
    # -------------------------------------------------------------------------
    "timing": {
        "cold_start_only": {
            "causes": [
                {"name": "Piston slap (normal on some engines)", "probability": 0.50, "cost": "low", "severity": "low", "inspection": "Knock when cold that disappears within 2-3 minutes; common on certain engines"},
                {"name": "Worn valve lifters (hydraulic lash adjuster bleed-down)", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Ticking when cold that lessens as oil warms and circulates"},
                {"name": "Loose accessory belt (cold contraction)", "probability": 0.45, "cost": "low", "severity": "low", "inspection": "Squeal on cold start only; belt contracts in cold weather, reduces tension"},
                {"name": "Exhaust leak at manifold gasket", "probability": 0.55, "cost": "low", "severity": "medium", "inspection": "Ticking/hissing when cold; metal contracts, opens gap in gasket"},
                {"name": "Weak battery (slow cranking when cold)", "probability": 0.40, "cost": "medium", "severity": "medium", "inspection": "Cranks slowly when cold; test battery CCA rating and load test"},
                {"name": "Glow plug failure (diesel engines)", "probability": 0.65, "cost": "low", "severity": "medium", "inspection": "Hard cold start; scan for glow plug codes; test each glow plug resistance"},
            ],
            "safety_note": "Cold-start-only noises that go away are usually not critical. However, if the noise gets progressively louder or lasts longer, schedule inspection.",
        },
        "when_accelerating": {
            "causes": [
                {"name": "Engine misfire under load", "probability": 0.65, "cost": "low", "severity": "high", "inspection": "Hesitation/jerking under hard acceleration; scan for misfire codes"},
                {"name": "Failing CV joint (inner)", "probability": 0.55, "cost": "medium", "severity": "medium", "inspection": "Vibration or clicking during acceleration; check CV boots"},
                {"name": "Worn engine mount (torque-induced movement)", "probability": 0.40, "cost": "low", "severity": "medium", "inspection": "Clunk when shifting from P to D or on hard acceleration; watch engine movement"},
                {"name": "Exhaust leak (flex pipe or gasket)", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Raspy noise under load; look for black soot at flex pipe or flanges"},
                {"name": "Knock sensor detecting pre-detonation", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Pinging/rattling under load; try higher octane fuel; check for carbon buildup"},
                {"name": "Turbocharger boost leak", "probability": 0.25, "cost": "low", "severity": "medium", "inspection": "Whistling + lack of power under boost; smoke-test intake pipes and intercooler"},
                {"name": "Fuel delivery insufficient for demand", "probability": 0.30, "cost": "medium", "severity": "high", "inspection": "Fuel pump weak or filter clogged; check fuel pressure under load"},
            ],
            "safety_note": "Misfiring during highway merging or passing reduces power when you need it most. This is a safety issue in heavy traffic.",
        },
        "when_braking": {
            "causes": [
                {"name": "Warped brake rotors", "probability": 0.80, "cost": "low", "severity": "medium", "inspection": "Steering wheel shake during braking; measure rotor runout with dial indicator"},
                {"name": "Worn brake pads (metal-on-metal)", "probability": 0.70, "cost": "low", "severity": "high", "inspection": "Grinding noise when braking; inspect pad thickness through caliper window"},
                {"name": "Loose wheel bearings (rotor wobble)", "probability": 0.35, "cost": "medium", "severity": "high", "inspection": "Shake in wheel during braking; check wheel bearing play"},
                {"name": "Worn suspension bushings (brake dive causes movement)", "probability": 0.30, "cost": "medium", "severity": "medium", "inspection": "Clunk when braking; inspect control arm and radius rod bushings"},
                {"name": "ABS false activation", "probability": 0.25, "cost": "medium", "severity": "medium", "inspection": "Pulsing pedal at low speed on dry pavement; scan for ABS codes"},
                {"name": "Rear brake bias issue (drums out of round)", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Pulsing felt in pedal not steering wheel; rear drum brake issue"},
                {"name": "Tire defect (tread separation causing wobble)", "probability": 0.15, "cost": "medium", "severity": "critical", "inspection": "Inspect tire tread for bulges, bubbles, or separation"},
            ],
            "safety_note": "Any symptom that occurs ONLY during braking is BRAKE-SYSTEM RELATED. Do not ignore -- your ability to stop in an emergency depends on these components.",
        },
        "when_turning": {
            "causes": [
                {"name": "Failing outer CV joint", "probability": 0.85, "cost": "medium", "severity": "medium", "inspection": "Clicking when turning in one direction; inspect CV boot on outer joint"},
                {"name": "Low power steering fluid", "probability": 0.60, "cost": "low", "severity": "medium", "inspection": "Whining or groaning when turning; check power steering reservoir"},
                {"name": "Binding upper strut mount bearing", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Squeaking or popping when turning steering wheel while stationary"},
                {"name": "Worn power steering rack", "probability": 0.30, "cost": "high", "severity": "medium", "inspection": "Stiffness or notchiness when turning; check rack boots for leaks"},
                {"name": "Differential binding (AWD/4WD)", "probability": 0.20, "cost": "high", "severity": "high", "inspection": "Tight feeling in turns; incorrect tire sizes can cause AWD differential binding"},
                {"name": "Low speed pre-ignition (LSPI) in turbo engines", "probability": 0.15, "cost": "medium", "severity": "high", "inspection": "Knocking/rattle at low RPM under load in turn; use API SN Plus oil"},
            ],
            "safety_note": "CV joint clicking means the joint is near catastrophic failure. A broken CV joint on a highway on-ramp causes sudden loss of power and control.",
        },
        "at_high_speed": {
            "causes": [
                {"name": "Wheel balance lost (threw a weight)", "probability": 0.70, "cost": "low", "severity": "low", "inspection": "Vibration at specific speed (usually 55-70mph); rebalance wheels"},
                {"name": "Tire out of round or separated", "probability": 0.50, "cost": "medium", "severity": "critical", "inspection": "Vibration increases with speed; inspect tires for bulges or uneven wear"},
                {"name": "Worn wheel bearing", "probability": 0.45, "cost": "medium", "severity": "medium", "inspection": "Humming/droning at highway speed; swerve to load/unload bearings"},
                {"name": "Aerodynamic noise (roof rack, mirror, window seal)", "probability": 0.35, "cost": "low", "severity": "low", "inspection": "Wind noise at speed; check roof rack tightness and window seal alignment"},
                {"name": "Driveshaft out of balance", "probability": 0.20, "cost": "medium", "severity": "medium", "inspection": "Vibration increases with speed; inspect driveshaft for missing balance weights"},
                {"name": "Steering shimmy (caster or toe misalignment)", "probability": 0.30, "cost": "low", "severity": "medium", "inspection": "Steering wheel shakes at speed; check alignment and tire wear patterns"},
            ],
            "safety_note": "High-speed vibrations can cause sudden tire failure or wheel bearing seizure. Do not exceed the speed where symptoms appear until repaired.",
        },
        "at_idle": {
            "causes": [
                {"name": "Vacuum leak", "probability": 0.70, "cost": "low", "severity": "medium", "inspection": "Rough idle, may stall; spray carb cleaner around intake to find leak"},
                {"name": "Dirty throttle body", "probability": 0.60, "cost": "low", "severity": "low", "inspection": "Low/rough idle especially with A/C on; clean throttle plate"},
                {"name": "Worn engine mounts", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Excessive vibration in drive at idle; watch engine movement when shifting P-R-N-D"},
                {"name": "Failing idle air control valve", "probability": 0.40, "cost": "low", "severity": "low", "inspection": "Erratic idle speed; may stall when coming to a stop; clean or replace IAC"},
                {"name": "Fuel injector clog (one cylinder)", "probability": 0.35, "cost": "low", "severity": "medium", "inspection": "Misfire at idle smooths out at higher RPM; swap injectors to isolate"},
                {"name": "Weak spark (worn plugs or coils)", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Rough idle; scan for misfire codes; inspect spark plug condition"},
                {"name": "A/C compressor loading engine excessively", "probability": 0.25, "cost": "medium", "severity": "low", "inspection": "Idle drops significantly when A/C engages; check compressor amp draw"},
                {"name": "EGR valve stuck open", "probability": 0.20, "cost": "low", "severity": "medium", "inspection": "Rough idle, possible stalling; scan for EGR codes; test valve operation"},
            ],
            "safety_note": "A stalling engine at intersections is a safety hazard. If your engine stalls and you lose power steering and brakes, use emergency brake to stop.",
        },
        "intermittent": {
            "causes": [
                {"name": "Failing ignition coil (heat-sensitive)", "probability": 0.55, "cost": "low", "severity": "high", "inspection": "Misfire when hot, clears when cold; swap coils to isolate failing unit"},
                {"name": "Intermittent sensor failure (CKP, CMP, O2)", "probability": 0.50, "cost": "low", "severity": "medium", "inspection": "Scan for pending codes; watch sensor data with scanner during symptom"},
                {"name": "Loose wiring harness connection", "probability": 0.45, "cost": "low", "severity": "medium", "inspection": "Wiggle test: manipulate wiring looms while engine runs to isolate"},
                {"name": "Failing fuel pump (intermittent pressure drop)", "probability": 0.35, "cost": "medium", "severity": "high", "inspection": "Install fuel pressure gauge and tape to windshield; monitor during symptom"},
                {"name": "Failing crankshaft position sensor", "probability": 0.40, "cost": "low", "severity": "critical", "inspection": "Stalling when hot, starts back after cooling; scan for P0335"},
# ===CHUNK2===
