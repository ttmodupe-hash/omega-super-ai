// Register PWA Service Worker for offline capability
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW registration failed:', err));
    });
}

let scene, camera, renderer, labComponent;
const container = document.getElementById('canvas-container');

function init3DLab() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x05070c);

    camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // cap DPR on low-end phones
    container.appendChild(renderer.domElement);

    const geometry = new THREE.BoxGeometry(2, 2, 2);
    const material = new THREE.MeshBasicMaterial({ color: 0x3b82f6, wireframe: true });
    labComponent = new THREE.Mesh(geometry, material);
    scene.add(labComponent);

    animate();
}

function animate() {
    requestAnimationFrame(animate);
    // 4th dimension: component transformation over time
    labComponent.rotation.x += 0.005;
    labComponent.rotation.y += 0.01;
    renderer.render(scene, camera);
}

window.addEventListener('resize', () => {
    if (!camera || !renderer) return;
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
});

init3DLab();

// ---------- Real-Time Lab Terminal (WebSocket) ----------
let terminalSocket;

function establishTerminalStream(studentId, containerName) {
    // Auto-detect secure context: wss:// in production, ws:// on localhost
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUri = `${protocol}://${window.location.host}/v1/labs/terminal/${studentId}/${containerName}`;
    terminalSocket = new WebSocket(wsUri);

    terminalSocket.onopen = () => console.log('[Luqi-AI] Terminal stream established.');
    terminalSocket.onclose = () => console.log('[Luqi-AI] Terminal stream closed.');
    terminalSocket.onerror = (e) => console.error('[Luqi-AI] Terminal stream error:', e);

    terminalSocket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (data.stream_node === 'stdout') {
            console.log('Terminal Output:', data.content);
            // TODO(frontend engineer): append to the on-screen terminal element
        } else if (data.stream_node === 'stderr') {
            console.error('Terminal Error Alert:', data.content);
            // TODO(frontend engineer): render in red inside the terminal display
        } else if (data.status === 'connected') {
            console.log('Terminal Handshake:', data.message);
        }
    };
}

function sendTerminalInput(commandString) {
    if (terminalSocket && terminalSocket.readyState === WebSocket.OPEN) {
        terminalSocket.send(JSON.stringify({ command: commandString }));
    }
}

// ---------- Local Classroom Mesh (WebRTC, offline-capable) ----------
// Classroom mesh v2: real signaling transports (HTTP relay, or manual offline).
// Host device (teacher): call classroomMesh.broadcastLabStateToClassroom({...})
let classroomMesh = null;

function joinClassroomMesh(asHost = false, useManualSignaling = false) {
    let transport;
    if (useManualSignaling) {
        transport = new LuqiMeshTransports.ManualSignalingTransport();
        console.log('[Luqi-AI] Mesh in MANUAL mode: exchange signals via copy/paste.');
    } else {
        const room = sessionStorage.getItem('luqi_mesh_room') || 'classroom-default';
        transport = new LuqiMeshTransports.HttpRelaySignalingTransport(room);
    }
    classroomMesh = new LuqiSovereignMeshNode(asHost, null, transport);
    console.log(`[Luqi-AI] Mesh initialised (${asHost ? 'HOST gateway' : 'STUDENT'}).`);
    return classroomMesh;
}

// Mesh payload hook: apply instructor-driven lab state to the local 3D scene
window.refreshWebGLCanvasComponent = window.update3DLabComponent = function (data) {
    if (!labComponent || !data) return;
    if (typeof data.rotation_speed === 'number') {
        labComponent.rotation.x += data.rotation_speed;
        labComponent.rotation.y += data.rotation_speed * 2;
    }
    if (typeof data.hue === 'number') {
        labComponent.material.color.setHSL(data.hue, 0.7, 0.5);
    }
    console.log('[Luqi-AI] Lab component synced from mesh host:', data);
};

// ---------- Sovereign Action & Education Portal UI ----------
// Suggestion box now calls the REAL /v1/prompt/enhance endpoint (zero token cost).
// Execute routes by mode: edu -> /v1/agent/kimi-research, biz -> /v1/agent/scan-opportunities
let currentMode = 'edu';
let optimizedPromptCache = '';
let promptDebounceTimer = null;

function switchMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-tab').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${mode}`).classList.add('active');
    document.getElementById('user-input').placeholder = mode === 'edu'
        ? 'Enter your technical lab or coding problem...'
        : 'What project or tender are you chasing? We aggregate the historical winning blueprint.';
}

function triggerPromptSupport() {
    const query = document.getElementById('user-input').value;
    const box = document.getElementById('suggestion-box');
    clearTimeout(promptDebounceTimer);

    if (query.length > 10) {
        promptDebounceTimer = setTimeout(async () => {
            try {
                const res = await fetch('/v1/prompt/enhance', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_prompt: query,
                        academic_tier: currentMode === 'edu' ? 'tvet' : 'entrepreneur',
                        lab_track: currentMode === 'edu' ? 'software_dev' : 'sovereign_action'
                    })
                });
                if (!res.ok) { box.style.display = 'none'; return; }
                const data = await res.json();
                optimizedPromptCache = data.enhanced_prompt;
                document.getElementById('suggestion-content').innerText =
                    `"${query.slice(0, 60)}" -> Click to apply the optimized expert query.`;
                box.style.display = 'block';
            } catch (e) {
                box.style.display = 'none';
            }
        }, 400); // debounce so we don't hammer the endpoint per keystroke
    } else {
        box.style.display = 'none';
    }
}

function applySmartPrompt() {
    if (optimizedPromptCache) {
        document.getElementById('user-input').value = optimizedPromptCache;
        document.getElementById('suggestion-box').style.display = 'none';
    }
}

function detectRegion() {
    try {
        const tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Africa/Johannesburg';
        return tz.split('/')[1] ? tz.split('/')[1].toUpperCase().slice(0, 2) : 'ZA';
    } catch (e) {
        return 'ZA';
    }
}

function appendMessage(text, isUser) {
    const display = document.getElementById('stream-display');
    const el = document.createElement('div');
    el.className = 'msg' + (isUser ? ' user' : ' ai');
    el.innerText = text;
    display.appendChild(el);
    display.scrollTop = display.scrollHeight;
}

async function executeSovereignAction() {
    const input = document.getElementById('user-input');
    const mainText = input.value.trim();
    if (!mainText) return;

    appendMessage(mainText, true);
    input.value = '';
    document.getElementById('suggestion-box').style.display = 'none';
    appendMessage('Jarvis is processing your request...', false);

    const isEdu = currentMode === 'edu';
    const endpoint = isEdu ? '/v1/agent/kimi-research' : '/v1/agent/scan-opportunities';
    const body = isEdu
        ? { student_query: mainText, academic_tier: 'tvet', lab_track: 'software_dev' }
        : { entrepreneur_intent: mainText, region_code: detectRegion() };

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();
        // Remove the "processing" placeholder and render the real reply
        const display = document.getElementById('stream-display');
        display.removeChild(display.lastChild);
        if (!res.ok) {
            appendMessage(`Engine error (${res.status}): ${data.detail || JSON.stringify(data)}`, false);
            return;
        }
        const reply = data.choices && data.choices[0] ? data.choices[0].message.content : JSON.stringify(data, null, 2);
        appendMessage(reply, false);
    } catch (e) {
        const display = document.getElementById('stream-display');
        display.removeChild(display.lastChild);
        appendMessage('Network error reaching the engine. Check your connection.', false);
    }
}

// ---------- Entrepreneur Workspace (REAL endpoints - no client-side mocks) ----------
let bizOptimizedCache = "";
let bizDebounce = null;

function toggleBizWorkspace() {
    const ws = document.getElementById('entrepreneur-workspace');
    ws.style.display = ws.style.display === 'flex' ? 'none' : 'flex';
}

function evaluateBizIntent() {
    const q = document.getElementById('biz-raw-input').value;
    const alertBox = document.getElementById('biz-optimize-alert');
    clearTimeout(bizDebounce);
    if (q.trim().length > 15) {
        bizDebounce = setTimeout(async () => {
            // REAL endpoint: server-side LuqiPromptSupport (was a client-side mock)
            try {
                const res = await fetch('/v1/prompt/enhance', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ raw_prompt: q, academic_tier: 'entrepreneur', lab_track: 'sovereign_action' })
                });
                if (!res.ok) { alertBox.style.display = 'none'; return; }
                const data = await res.json();
                bizOptimizedCache = data.enhanced_prompt;
                document.getElementById('biz-optimize-text').innerText = 'Click to apply the optimized compliance query.';
                alertBox.style.display = 'block';
            } catch (e) { alertBox.style.display = 'none'; }
        }, 400);
    } else {
        alertBox.style.display = 'none';
    }
}

function applyBizOptimizedPrompt() {
    if (bizOptimizedCache) {
        document.getElementById('biz-raw-input').value = bizOptimizedCache;
        document.getElementById('biz-optimize-alert').style.display = 'none';
    }
}

async function triggerCapabilityExpansion() {
    const q = document.getElementById('biz-raw-input').value.trim();
    const vp = document.getElementById('biz-viewport');
    if (!q) return;
    vp.innerHTML = '<span style="color:#3b82f6;">[Luqi Core] Routing through PII filter -> scan-opportunities engine...</span>';
    try {
        // REAL endpoint (was /v1/agent/kimi-k3-reason - a route that does not exist)
        const res = await fetch('/v1/agent/scan-opportunities', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entrepreneur_intent: q, region_code: detectRegion() })
        });
        const data = await res.json();
        if (!res.ok) {
            vp.innerHTML = `<span style="color:#ef4444;">Engine error (${res.status}): ${data.detail || JSON.stringify(data)}</span>`;
            return;
        }
        const reply = (data.choices && data.choices[0]) ? data.choices[0].message.content : JSON.stringify(data, null, 2);
        vp.innerHTML = `<span style="color:#10b981;">\u2714 COMPLIANT EXECUTION BLUEPRINT COMPILED</span><br><br>` +
                       reply.replace(/</g, '&lt;');
    } catch (e) {
        vp.innerHTML = '<span style="color:#ef4444;">Network error reaching the engine.</span>';
    }
}

// ---------- Jarvis Voice Playback (streams from /v1/voice/speak) ----------
let voiceAuthToken = sessionStorage.getItem('luqi_user_token') || '';

async function speakWithJarvis(text) {
    if (!voiceAuthToken) {
        voiceAuthToken = prompt('Paste your auth token (from /v1/auth/login) to enable voice:') || '';
        sessionStorage.setItem('luqi_user_token', voiceAuthToken);
    }
    try {
        const res = await fetch('/v1/voice/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${voiceAuthToken}` },
            body: JSON.stringify({ text, voice: 'madiba_male' })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            console.warn('[Jarvis Voice]', res.status, err.detail || '');
            return;
        }
        const blob = await res.blob();
        new Audio(URL.createObjectURL(blob)).play();
    } catch (e) {
        console.warn('[Jarvis Voice] playback failed:', e);
    }
    // Free zero-key fallback: browser TTS keeps Jarvis speaking without XI_API_KEY
    try {
        const utter = new SpeechSynthesisUtterance(text.slice(0, 300));
        utter.rate = 0.95;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(utter);
    } catch (e2) { /* no TTS available either - silent */ }
}

// Wire the voice bar button (was previously inert)
document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('voice-trigger');
    if (btn) btn.addEventListener('click', () => {
        const lastAi = [...document.querySelectorAll('.msg.ai')].pop();
        speakWithJarvis(lastAi ? lastAi.innerText.slice(0, 3000) : 'Greetings. I am online and ready to assist.');
    });
});

// ---------- Integrity & Universal Learning workspace (REAL endpoints, auth-gated) ----------
function toggleUniversalWorkspace() {
    const ws = document.getElementById('universal-workspace');
    ws.style.display = ws.style.display === 'flex' ? 'none' : 'flex';
}

async function runUniversalAction() {
    const mode = document.getElementById('universal-mode').value;
    const input = document.getElementById('universal-input').value.trim();
    const view = document.getElementById('universal-view');
    if (!input) { alert('Input cannot be blank.'); return; }
    if (!voiceAuthToken) {
        voiceAuthToken = prompt('Auth token required (from /v1/auth/login):') || '';
        sessionStorage.setItem('luqi_user_token', voiceAuthToken);
    }
    view.innerHTML = '<span style="color:#3b82f6;">[link] PII filter -> engine...</span>';
    const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${voiceAuthToken}` };
    const isMedical = mode === 'medical';
    const endpoint = isMedical ? '/v1/sovereign-learning/expand-capability' : '/v1/integrity/verify-submission';
    const body = isMedical
        ? { subject_domain: 'Advanced Medical Training', target_topic: input, resource_context_inputs: ['regional context'] }
        : { lab_id: crypto.randomUUID(), student_id: crypto.randomUUID(), submitted_source_code: input };
    try {
        const res = await fetch(endpoint, { method: 'POST', headers, body: JSON.stringify(body) });
        const data = await res.json();
        if (!res.ok) {
            view.innerHTML = `<span style="color:#ef4444;">Engine error (${res.status}): ${(data.detail || '').replace(/</g, '&lt;')}</span>`;
            return;
        }
        view.innerHTML = `<span style="color:#10b981;">\u2714 COMPLETE</span><br><br>` +
                         JSON.stringify(data, null, 2).replace(/</g, '&lt;');
    } catch (e) {
        view.innerHTML = '<span style="color:#ef4444;">Network error reaching the engine.</span>';
    }
}

// ---------- Live System Status Pill (feature-flag transparency) ----------
async function refreshStatusPill() {
    const pill = document.getElementById('status-pill');
    if (!pill) return;
    try {
        const [comp, feats] = await Promise.all([
            fetch('/v1/companion/status').then(r => r.ok ? r.json() : null),
            fetch('/v1/features').then(r => r.ok ? r.json() : null),
        ]);
        let state = comp && comp.pending_gate_count > 0
            ? '<span style="color:#f59e0b">\u25cf approvals pending</span>'
            : '<span style="color:#10b981">\u25cf operational</span>';
        let caps = '';
        if (feats && feats.flags) {
            const on = Object.entries(feats.flags).filter(([, v]) => v === 'on').length;
            const beta = Object.entries(feats.flags).filter(([, v]) => v === 'beta').length;
            caps = ` &middot; ${on} active${beta ? `, ${beta} beta` : ''}`;
        }
        pill.innerHTML = state + caps;
    } catch (e) { pill.innerHTML = '<span style="color:#ef4444">\u25cf offline</span>'; }
}
refreshStatusPill();
setInterval(refreshStatusPill, 30000);
