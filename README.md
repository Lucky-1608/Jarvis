<div align="center">

# 🌊 Jarvis OS

**A self-hosted autonomous AI assistant that runs 24/7 — and proves what it did.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-WebSocket-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Kotlin](https://img.shields.io/badge/Android-Kotlin-3DDC84?style=flat-square&logo=android&logoColor=white)](https://kotlinlang.org)
[![Postgres](https://img.shields.io/badge/Database-PostgreSQL-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![pgvector](https://img.shields.io/badge/Vector_DB-pgvector-FF6F00?style=flat-square)](https://github.com/pgvector/pgvector)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

<samp>

**$0 inference spend** · **~2s typical reply** · **5-provider failover** · **solo build**

</samp>

*Not a chatbot. A 24/7 assistant that schedules real actions, executes on remote devices,*
*protects you from fraud — and verifies its own claims against ground truth.*

</div>

---

## Why this exists

Every AI assistant you can rent is **request–response**: it helps for three minutes when prompted,
then stops existing. Its memory of you belongs to the vendor. It has no hands. And you cannot audit
whether it actually did what it said.

Jarvis OS is the opposite of all four. It owns its data, runs on hardware you control, holds intentions
across days, acts through real devices — and every consequential action leaves a ground-truth record
that can be diffed against what it claimed.

Language models lie about their own actions — not maliciously, but because pattern-matching a plausible confirmation is easier than doing the work. Mine once reported *"Task scheduled successfully"* with no row in the database. Everything below is downstream of taking that seriously.

---

## Architecture

```
                            ┌──────────────────────────────────┐
                            │           CLOUD BRAIN            │
                            │    FastAPI · WebSocket :8000     │
                            │                                  │
   WhatsApp  ◄──Baileys───► │  router ───► 5-provider cascade  │ ◄──WS──► React UI /
   (loop-proof              │      │         opencode →        │          Dashboard
    secretary)              │      │         gemini →          │        
                            │      │         ollama →          │
   Gmail  ◄────poll───────► │      │         grok → nvidia     │
   (+ Guardian scan)        │      │                           │ ◄──WS──► Device nodes
                            │      │                           │      laptop ✓  phone ✓
   Calendar ◄──OAuth──────► │  memory tree      scheduler      │      (AccessibilityService)
                            │  (episodic →                     │
                            │   summary)                       │
                            │                                  │
                            │  pgvector      [TOOL RESULTS]    │
                            │  semantic       truth seals      │
                            │  recall         (the lie detector│
                            └──────────────────────────────────┘
```

**One brain, multiple entry points**. A single `/ws` WebSocket carries chat, status, streamed UI state, and device-node registration.

---

## Capabilities

| Capability | How it works |
|---|---|
| **Messaging secretary** | Native WhatsApp (Baileys): rate limiting, 5s debounce. Echo-loop-proof by design — she runs on my own number, so every reply echoes back as `is_self` and is ignored. |
| **Verified missions** | A goal is decomposed into steps, each with an *objectively checkable* verification. A step is not done because she says so — it's done because evidence proved it. |
| **Device hands** | Lightweight agents connect *outbound* from laptop and phone and register capabilities. The Android client drives arbitrary apps via a native Kotlin `AccessibilityService` (tap-by-text, scroll) — the only way to act autonomously. |
| **Guardian fraud shield** | Rule-first scam detection on inbound mail and messages: OTP/KYC urgency, shortened links. Warn-only — never auto-deletes, auto-replies, or clicks. |
| **Truth seals** | Every side-effecting tool call generates a cryptographic `seal_id`. Claims are auditable against seals; when words and seals disagree, **seals win**. |
| **Vector memory** | Deep semantic recall on every message via `pgvector` hosted on Supabase, allowing meaning-based retrieval across thousands of past interactions. |
| **GraphRAG** | Uses Graphify to understand codebase architecture and concept relationships contextually, not just textually. |
