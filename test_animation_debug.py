#!/usr/bin/env python3
"""Debug script to test animation endpoint loading."""

import sys
import traceback

print("=" * 60)
print("Animation Endpoint Debug Test")
print("=" * 60)

# Test 1: Can we import animation_engine?
print("\n[1] Importing animation_engine...")
try:
    from backend import animation_engine
    print("  OK - animation_engine imported")
    print(f"  AnimationEngine class: {animation_engine.AnimationEngine}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# Test 2: Can we import visual_learning?
print("\n[2] Importing visual_learning...")
try:
    from backend import visual_learning
    print("  OK - visual_learning imported")
    print(f"  VisualLearningEngine class: {visual_learning.VisualLearningEngine}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# Test 3: Can we import v25_animation_endpoints?
print("\n[3] Importing v25_animation_endpoints...")
try:
    from backend import v25_animation_endpoints
    print("  OK - v25_animation_endpoints imported")
    print(f"  Animation available: {v25_animation_endpoints._ANIMATION_AVAILABLE}")
    print(f"  Visual available: {v25_animation_endpoints._VISUAL_AVAILABLE}")
    print(f"  App available: {v25_animation_endpoints._APP_AVAILABLE}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

# Test 4: List all registered routes
print("\n[4] Checking registered routes...")
try:
    from backend.router import app
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    anim_routes = [r for r in routes if 'animation' in r or 'visual' in r or 'training' in r]
    print(f"  Total routes: {len(routes)}")
    print(f"  Animation/Visual/Training routes: {len(anim_routes)}")
    for r in anim_routes:
        print(f"    - {r}")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()

print("\n" + "=" * 60)
