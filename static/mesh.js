/**
 * OMEGA-LUQI Advanced Peer-to-Peer Classroom Mesh Engine
 *
 * Sovereign Mesh Gateway pattern: the instructor's phone (host) loads the PWA
 * once, then broadcasts lab state to student phones over a local hotspot -
 * zero internet data.
 *
 * SIGNALING (the piece previous blueprints always omitted - two real options):
 *   1. HttpRelaySignalingTransport  - relays SDP via the Luqi backend
 *      (/v1/mesh/signal/{room}). Works with any connectivity or LAN-hosted node.
 *   2. ManualSignalingTransport     - base64 copy/paste exchange. Zero
 *      infrastructure; the honest option for fully offline classrooms.
 */
class LuqiSovereignMeshNode {
    constructor(isHostNode = false, localNodeIdentity = null, signalingTransport = null) {
        this.isHost = isHostNode;
        this.nodeId = localNodeIdentity || `node-${Math.random().toString(36).slice(2, 11)}`;
        this.signaling = signalingTransport;
        this.activePeerConnections = new Map();
        this.activeDataChannels = new Map();

        if (this.signaling) {
            this.signaling.onSignal = (signal) => this.handleIncomingSignal(signal);
        }

        // STUN endpoint in valid syntax (prior blueprints shipped a malformed URL).
        // STUN is only needed if the hotspot has no LAN route; harmless otherwise.
        this.iceConfiguration = {
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
            iceTransportPolicy: 'all'
        };
    }

    async initiateLocalConnectionBridge(targetPeerId) {
        if (this.activePeerConnections.has(targetPeerId)) {
            return this.activePeerConnections.get(targetPeerId);
        }
        const pc = new RTCPeerConnection(this.iceConfiguration);
        this.activePeerConnections.set(targetPeerId, pc);

        pc.onicecandidate = (event) => {
            if (event.candidate && this.signaling) {
                this.signaling.send({
                    type: 'ice_candidate', sender: this.nodeId,
                    target: targetPeerId, candidate: event.candidate
                });
            }
        };
        pc.onconnectionstatechange = () => {
            if (['failed', 'closed', 'disconnected'].includes(pc.connectionState)) {
                this.activeDataChannels.delete(targetPeerId);
                this.activePeerConnections.delete(targetPeerId);
            }
        };

        if (this.isHost) {
            const dc = pc.createDataChannel("LuqiMeshDataStream", { ordered: true });
            this.bindDataChannelEventHandlers(dc, targetPeerId);
            this.activeDataChannels.set(targetPeerId, dc);

            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            this.signaling && this.signaling.send({
                type: 'mesh_offer', sender: this.nodeId, target: targetPeerId, sdp: offer
            });
        } else {
            pc.ondatachannel = (event) => {
                this.bindDataChannelEventHandlers(event.channel, targetPeerId);
                this.activeDataChannels.set(targetPeerId, event.channel);
            };
        }
        return pc;
    }

    /** COMPLETED HANDSHAKE (was missing: students never answered offers). */
    async handleIncomingSignal(signal) {
        if (signal.target && signal.target !== this.nodeId) return;
        let pc = this.activePeerConnections.get(signal.sender);
        if (!pc) pc = await this.initiateLocalConnectionBridge(signal.sender);

        if (signal.type === 'mesh_offer') {
            await pc.setRemoteDescription(signal.sdp);
            const answer = await pc.createAnswer();
            await pc.setLocalDescription(answer);
            this.signaling && this.signaling.send({
                type: 'mesh_answer', sender: this.nodeId, target: signal.sender, sdp: answer
            });
        } else if (signal.type === 'mesh_answer') {
            await pc.setRemoteDescription(signal.sdp);
        } else if (signal.type === 'ice_candidate') {
            try { await pc.addIceCandidate(signal.candidate); } catch (e) { /* stale candidate */ }
        }
    }

    bindDataChannelEventHandlers(channel, peerId) {
        channel.onopen = () => console.log(`[Luqi Mesh] P2P tunnel established: ${peerId}`);
        channel.onclose = () => {
            this.activeDataChannels.delete(peerId);
            this.activePeerConnections.delete(peerId);
        };
        channel.onmessage = (event) => {
            try { this.routeIncomingMeshPayload(JSON.parse(event.data)); }
            catch (err) { console.error("[Luqi Mesh] Corrupted packet dropped:", err); }
        };
    }

    broadcastLabStateToClassroom(laboratoryStateData) {
        if (!this.isHost) return;
        const envelope = JSON.stringify({ sender_node: this.nodeId, timestamp: Date.now(), payload: laboratoryStateData });
        this.activeDataChannels.forEach((ch) => { if (ch.readyState === "open") ch.send(envelope); });
    }

    routeIncomingMeshPayload(envelope) {
        if (envelope.payload && typeof window.refreshWebGLCanvasComponent === "function") {
            window.refreshWebGLCanvasComponent(envelope.payload);
        }
    }
}

/** Transport 1: relay via the Luqi backend (needs any connectivity). */
class HttpRelaySignalingTransport {
    constructor(roomId, baseUrl = '/v1/mesh/signal') {
        this.room = roomId;
        this.base = baseUrl;
        this.onSignal = null;
        this._timer = null;
        this._poll();
    }
    async send(signal) {
        try {
            await fetch(`${this.base}/${this.room}`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(signal)
            });
        } catch (e) { /* relay unreachable - retry next poll */ }
    }
    async _poll() {
        try {
            const r = await fetch(`${this.base}/${this.room}`);
            if (r.ok) {
                const signal = await r.json();
                if (signal && this.onSignal) await this.onSignal(signal);
            }
        } catch (e) { /* offline - keep polling */ }
        this._timer = setTimeout(() => this._poll(), 1500);
    }
}

/** Transport 2: manual base64 copy/paste - true offline, zero infrastructure. */
class ManualSignalingTransport {
    constructor(onSendPrompt) {
        this.onSignal = null;
        this._prompt = onSendPrompt || ((label, value) => window.prompt(label, value));
    }
    async send(signal) {
        const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(signal))));
        this._prompt("Copy this mesh signal and hand it to the other device:", encoded);
    }
    async receive() {
        const pasted = this._prompt("Paste the mesh signal from the other device:", "");
        if (!pasted) return;
        try {
            const signal = JSON.parse(decodeURIComponent(escape(atob(pasted.trim()))));
            if (this.onSignal) await this.onSignal(signal);
        } catch (e) { alert("Invalid mesh signal - check the copied text."); }
    }
}

window.LuqiSovereignMeshNode = LuqiSovereignMeshNode;
window.LuqiMeshTransports = { HttpRelaySignalingTransport, ManualSignalingTransport };
