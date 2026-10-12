# BrandShield AI — 3–4 Minute Live Hackathon Demo Script

This script provides a structured, time-boxed walkthrough of BrandShield AI for live hackathon judging and presentations.

---

## Pre-Demo Setup & Cold-Start Preparation (T-minus 5 Minutes)

> [!IMPORTANT]
> **Avoid Free-Tier Cold Starts:**
> If hosting on a free-tier cloud platform (e.g., Render), backend containers spin down after periods of inactivity and require ~50 seconds to boot.
> **5 minutes before presenting, send a ping request:**
> ```bash
> curl -s https://<your-backend-api-url>/api/v1/health/ready
> ```
> Verify that the response returns `{"status":"ready","database":"connected"}` before starting your screen share.

---

## Timed Walkthrough (Total: 3 minutes 45 seconds)

### Phase 1: Problem & Brand Safety Guard (0:00 – 0:50)
* **Screen:** Open **Dashboard** (`/`) and navigate to **Brand Profiles** (`/brands`).
* **Click Action:** Select the seeded **NovaPay** profile.
* **Talking Points:**
  * *"Every day, fintechs and brands face rapid-fire impersonators across social media and mobile app stores. Traditional tools often inundate analysts with false positives — often flagging the company's own official channels."*
  * *"Here in BrandShield AI, we begin with strong identity anchoring: we register NovaPay's official website, verified Bluesky handles (`novapay.synthetic.example`), and official Apple App Store bundle IDs (`example.synthetic.novapay.wallet`)."*
  * *"Crucially, our **Official-Asset Safety Guard** runs before any risk scoring occurs. The company's legitimate accounts are permanently marked `OFFICIAL_EXCLUDED` and cannot trigger noisy security alerts."*

### Phase 2: Live Ingestion & Source Resilience (0:50 – 1:35)
* **Screen:** Navigate to **Social Monitoring** (`/social`).
* **Click Action:** Point out the **Source Health Monitor** in the UI, then trigger a live scan or view connector status.
* **Talking Points:**
  * *"Notice our real-time Source Health card: we maintain live public connectors to Bluesky XRPC search and the Apple iTunes Search API."*
  * *"Let's examine source provenance. In this interface, you will see explicit tags: `LIVE CONNECTOR`, `MANUAL SUBMISSION`, and `DEMO SEED`. We never blur the line between real public internet data and offline test seeds."*
  * *"If an upstream network request times out or returns HTTP 500, BrandShield AI degrades gracefully per-source. It logs the exact error, keeps the other sources alive, and never substitutes synthetic records as fake live findings."*

### Phase 3: Explainable Threat Detection & Evidence Trail (1:35 – 2:30)
* **Screen:** Click on a high-risk candidate, such as `N0vaPay Support` (Social) or `NovaPay Wallet 2FA` (App).
* **Click Action:** Open the **Evidence Trail** drawer/modal.
* **Talking Points:**
  * *"Let's inspect this candidate: `N0vaPay Support` scored 80 (High Risk). Why?"*
  * *"BrandShield AI does not use an unexplainable black-box classifier. In the Evidence Trail, an analyst can audit every point awarded:"*
    * *"Levenshtein homoglyph evasion detected: replacing 'o' with '0' awarded 35 name points + 5 evasion bonus, respecting our 40-point Name-Only Ceiling."*
    * *"External link `https://attacker-infrastructure.com` detected as a look-alike phishing domain (+25 points)."*
    * *"Scam urgency keywords in bio ('giveaway refund') awarded +15 points."*
  * *"Similarly, for mobile apps, our engine flags developer publisher mismatches (+20 points) when an unverified developer publishes under NovaPay's brand name."*

### Phase 4: Impersonation Campaign Graph (2:30 – 3:15)
* **Screen:** Navigate to **Campaigns** (`/campaigns`).
* **Click Action:** View the interactive Campaign Graph and click on the linked campaign node.
* **Talking Points:**
  * *"Attackers rarely operate in isolation. This is BrandShield AI's signature feature: the **Impersonation Campaign Graph**."*
  * *"Rather than reviewing 10 isolated alerts, analysts see the broader operation. Here, two distinct social profiles and a suspicious app are grouped together."*
  * *"Why are they connected? Because our engine found a concrete, recorded indicator: all three assets direct victims to the identical non-generic phishing host `attacker-infrastructure.com`."*
  * *"Notice the strict security rule: we do not draw lines based on similar names alone, and common hosting providers like GitHub or Bitly are excluded from creating false campaign links. Furthermore, we label these as `POTENTIAL_COORDINATION`, preserving analyst objectivity without making unproven legal claims."*

### Phase 5: Analyst Investigation Triage & Wrap-up (3:15 – 3:45)
* **Screen:** Navigate to **Investigations** (`/investigations`).
* **Click Action:** Update candidate status from `New` to `Investigating` or `Confirmed Threat`, add an analyst note ("Coordinated phishing infrastructure identified"), and click Save. Refresh the page to demonstrate persistence.
* **Talking Points:**
  * *"Analysts can triage alerts, assign priority, and record audit notes directly. When we refresh, the investigation state is seamlessly persisted in MongoDB Atlas."*
  * *"To summarize: BrandShield AI delivers zero-false-positive official protection, explainable multi-signal detection, live public connector monitoring, and coordinated campaign graphing."*
  * *"Thank you, and we welcome your questions!"*

---

## Backup Video Recording Checklist

In the event of network disruption or projector issues during a live presentation, maintain an offline MP4/WebM recording following this exact sequence:

- [ ] **Recording Resolution:** 1080p (1920x1080) at 60 FPS or 30 FPS.
- [ ] **Browser Window:** Chrome/Edge fullscreen (F11), bookmarks bar hidden, zoom level 100%.
- [ ] **Data Pre-Seeded:** NovaPay brand profile and synthetic campaign records populated before starting recording.
- [ ] **Step 1 Captured:** Brand Profile view showing official assets excluded.
- [ ] **Step 2 Captured:** Live public connector health status.
- [ ] **Step 3 Captured:** Social & App candidate listings with severity badges (Critical, High, Medium, Low).
- [ ] **Step 4 Captured:** Evidence Trail modal showing granular signal breakdown and audit points.
- [ ] **Step 5 Captured:** Campaign Graph interaction showing shared indicator modal.
- [ ] **Step 6 Captured:** Investigation status change and persistent reload.
- [ ] **Audio/Captions:** Clear microphone narration or subtitle overlays following the talking points above.
