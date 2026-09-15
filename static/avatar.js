/**
 * OMEGA-LUQI Jarvis Companion Avatar - procedural, dependency-light.
 *
 * Design lesson (from the AI Avatar v20 write-up): AI-generated 3D models are
 * unreliable; this avatar is built from primitives and code-driven animation.
 * Four states: idle | happy | alert | speaking. Speech bubble included.
 *
 * Event reactivity: polls /v1/companion/status (public, counts only) and
 * enters 'alert' whenever anything sits frozen at the 30% human gate.
 */
(function () {
    const mount = document.createElement('div');
    mount.id = 'luqi-avatar-mount';
    mount.style.cssText = 'position:fixed;bottom:12px;right:12px;width:120px;height:140px;z-index:999;pointer-events:none;';
    const bubble = document.createElement('div');
    bubble.id = 'luqi-avatar-bubble';
    bubble.style.cssText = 'position:fixed;bottom:150px;right:12px;max-width:220px;background:#0c111d;border:1px solid #1e293b;color:#e2e8f0;font-size:12px;padding:8px 10px;border-radius:8px;display:none;z-index:999;pointer-events:none;';
    document.addEventListener('DOMContentLoaded', () => {
        document.body.appendChild(mount);
        document.body.appendChild(bubble);
        initAvatar();
    });

    let scene, camera, renderer, avatar, state = 'idle', stateUntil = 0, tick = 0;

    function initAvatar() {
        if (typeof THREE === 'undefined') return; // no WebGL -> avatar silently absent
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(40, 120 / 140, 0.1, 100);
        camera.position.z = 6;
        renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(120, 140);
        mount.appendChild(renderer.domElement);
        scene.add(new THREE.AmbientLight(0xffffff, 0.9));
        const key = new THREE.DirectionalLight(0xffffff, 0.6);
        key.position.set(2, 3, 4);
        scene.add(key);

        avatar = new THREE.Group();
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x059669 });
        const darkMat = new THREE.MeshStandardMaterial({ color: 0x0b0f19 });
        const body = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.7, 1.3, 12), bodyMat);
        body.position.y = -0.6;
        const head = new THREE.Mesh(new THREE.SphereGeometry(0.55, 16, 16), bodyMat);
        head.position.y = 0.55;
        const eyeL = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), darkMat);
        eyeL.position.set(-0.2, 0.65, 0.48);
        const eyeR = eyeL.clone();
        eyeR.position.x = 0.2;
        const antenna = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.5, 6), darkMat);
        antenna.position.y = 1.25;
        const tip = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 8),
            new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x10b981 }));
        tip.position.y = 1.55;
        avatar.add(body, head, eyeL, eyeR, antenna, tip);
        scene.add(avatar);
        animate();
        pollStatus();
        setInterval(pollStatus, 15000);
    }

    function setState(next, holdMs = 0) {
        state = next;
        stateUntil = holdMs ? Date.now() + holdMs : 0;
    }

    function say(text, ms = 4000) {
        bubble.innerText = text;
        bubble.style.display = 'block';
        setState('speaking', ms);
        setTimeout(() => { bubble.style.display = 'none'; }, ms);
    }

    function pollStatus() {
        fetch('/v1/companion/status').then(r => r.ok ? r.json() : null).then(d => {
            if (!d) return;
            if (Date.now() < stateUntil) return;           // manual state wins temporarily
            if (d.pending_gate_count > 0) setState('alert');
            else if (state === 'alert') setState('idle');
        }).catch(() => {});
    }

    function animate() {
        requestAnimationFrame(animate);
        if (!avatar) return;
        tick += 0.03;
        const t = Date.now();
        if (stateUntil && t > stateUntil) { state = 'idle'; stateUntil = 0; }
        if (state === 'idle') {
            avatar.position.y = Math.sin(tick) * 0.08;
            avatar.rotation.y += 0.004;
            avatar.scale.setScalar(1);
        } else if (state === 'happy') {
            avatar.position.y = Math.abs(Math.sin(tick * 2.5)) * 0.5;
            avatar.rotation.y += 0.02;
        } else if (state === 'alert') {
            avatar.position.y = Math.sin(tick * 3) * 0.05;
            const pulse = 1 + Math.sin(tick * 6) * 0.05;
            avatar.scale.setScalar(pulse);
            avatar.children.forEach(c => { if (c.material && c.material.emissive) c.material.emissive.setHex(0x7f1d1d); });
        } else if (state === 'speaking') {
            avatar.rotation.z = Math.sin(tick * 5) * 0.08;
            avatar.position.y = Math.sin(tick * 2) * 0.05;
        }
        if (state !== 'alert') {
            avatar.children.forEach(c => { if (c.material && c.material.emissive) c.material.emissive.setHex(0x10b981); });
        }
        renderer.render(scene, camera);
    }

    window.LuqiAvatar = { setState, say };
})();
