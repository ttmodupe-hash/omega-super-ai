/**
 * OMEGA-LUQI Skill Engine Client (vanilla JS, JWT auth).
 * The pasted apiClient.js had no authentication at all - ours sends the JWT
 * the engine requires. Token persisted in localStorage like their design.
 */
class LuqiSkillClient {
    constructor(baseURL = "") {
        this.baseURL = baseURL;
    }
    _token() { return localStorage.getItem('luqi_user_token') || ""; }
    _headers() {
        return { "Content-Type": "application/json",
                 "Authorization": `Bearer ${this._token()}` };
    }
    async _req(method, path, body) {
        const res = await fetch(`${this.baseURL}${path}`, {
            method, headers: this._headers(),
            body: body ? JSON.stringify(body) : undefined,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `${res.status}`);
        return data;
    }
    registerTrade(trade)          { return this._req("POST", "/v1/skills/register", { trade }); }
    gapAnalysis(trade)            { return this._req("GET", `/v1/skills/gap-analysis?trade=${encodeURIComponent(trade)}`); }
    verifySubmission(skill, text) { return this._req("POST", "/v1/skills/verify", { skill, submission: text }); }
    profile()                     { return this._req("GET", "/v1/skills/profile"); }
    issueCertificate(trade)       { return this._req("POST", "/v1/skills/certificate/issue", { trade }); }
    // verifyCertificate is PUBLIC - no token needed (employer check)
    static async verifyCertificate(certId, baseURL = "") {
        const res = await fetch(`${baseURL}/v1/skills/certificate/${certId}`);
        if (!res.ok) throw new Error(`certificate invalid: ${res.status}`);
        return res.json();
    }
}
window.LuqiSkillClient = LuqiSkillClient;
