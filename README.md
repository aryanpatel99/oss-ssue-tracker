# 🚀 CNCF Daily Issue Tracker & LFX Mentorship Radar

> An automated, daily-updated radar that tracks newly opened `good first issue`, `help wanted`, and `lfx-mentorship` issues across the **Cloud Native Computing Foundation (CNCF)** ecosystem.

[![Daily Tracker](https://github.com/actions/workflows/daily_tracker.yml/badge.svg)](https://github.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CNCF Ecosystem](https://img.shields.io/badge/Ecosystem-CNCF-326CE5?logo=cncf&logoColor=white)](https://landscape.cncf.io)
[![LFX Mentorship](https://img.shields.io/badge/Program-LFX%20Mentorship-008080?logo=linux&logoColor=white)](https://mentorship.lfx.linuxfoundation.org)

---

## 🎯 Live Issue Dashboard

<!-- CNCF_TRACKER_START -->

> 🕒 **Last updated**: `2026-09-14 04:58 UTC` (looking back 48 hours)
> 🎯 **Total newcomer & mentorship issues found**: `2`
> 💻 **Languages**: **Go**: 2
> 🏛️ **CNCF Tiers**: **Sandbox**: 2

---

### ⚡ Application & Edge Frameworks (2)

| Project | Issue Title | Stack | Labels | Opened | Comments |
| :--- | :--- | :---: | :--- | :---: | :---: |
| [meshery/meshery](https://github.com/meshery/meshery) | [#21951 [Docs] Add a troubleshooting note for Meshery Server startup failures](https://github.com/meshery/meshery/issues/21951) | `Go` | `help wanted` `area/docs` `language/markdown` +1 | 14h ago | 💬 2 |
| [meshery/meshery](https://github.com/meshery/meshery) | [#21949 [Docs] Fix broken relative image paths in mesheryctl command reference and contrib...](https://github.com/meshery/meshery/issues/21949) | `Go` | `help wanted` `area/docs` `language/markdown` +1 | 1d ago | 💬 2 |


<!-- CNCF_TRACKER_END -->

---

## 💡 Why This Tracker for LFX Mentorship?

The **Linux Foundation (LFX) Mentorship** is one of the premier open-source fellowship programs in the world. Mentors receive hundreds of applications each term.

**How Mentors Actually Select Mentees:**
1. **Prior Activity**: Mentors strongly favor applicants who have actively participated in their repo *before* or *during* the application window.
2. **First Responders**: When a mentor or maintainer creates an issue tagged `good first issue` or `lfx-mentorship`, candidates who submit a high-quality analysis or PR within 24–48 hours stand out immediately.
3. **Consistency**: Solving 2–3 small bugs, writing tests, or improving docs across Kubernetes, Prometheus, OpenTelemetry, Cilium, or Kyverno establishes proof of capability.

---

## 🛠️ Monitored CNCF Projects

This tracker monitors projects across key Cloud Native pillars:

| Category | Projects Included | Primary Languages |
| :--- | :--- | :---: |
| **☸️ Kubernetes & Core** | `kubernetes`, `minikube`, `kind`, `kustomize`, `cluster-api`, `containerd`, `etcd`, `cri-o` | Go |
| **📊 Observability** | `prometheus`, `opentelemetry-collector`, `opentelemetry-go`, `opentelemetry-rust`, `opentelemetry-python`, `jaeger`, `fluent-bit` | Go, Rust, Python, C |
| **🌐 Networking & Mesh** | `cilium`, `envoy`, `linkerd2`, `linkerd2-proxy`, `coredns` | Go, C++, Rust |
| **🚀 GitOps & Delivery** | `argo-cd`, `argo-workflows`, `flux2`, `helm`, `crossplane` | Go |
| **🛡️ Security & Policy** | `kyverno`, `falco`, `cert-manager`, `opa`, `in-toto` | Go, C++, Python |
| **💾 Distributed Storage** | `tikv`, `vitess`, `rook` | Rust, Go |
| **⚡ Edge & Frameworks** | `dapr`, `keda`, `litmuschaos`, `meshery` | Go |
| **🎓 Mentorship Hub** | `cncf/mentoring` (all proposals and issues) | Multi |

---

## ⚡ Quick Start

### 1. Run Locally

Clone and install dependencies:
```bash
git clone <your-repo-url>
cd cncf-issue-tracker
pip install -r requirements.txt
```

Run an ad-hoc search and print to terminal (dry run):
```bash
python main.py --dry-run
```

Search the past 48 hours and update the `README.md` + generate daily report:
```bash
python main.py --hours 48 --update-readme
```

> **Tip**: Set `export GITHUB_TOKEN="ghp_yourPersonalAccessToken"` to avoid GitHub's unauthenticated API rate limits.

---

### 2. Automated Daily Tracking on GitHub

You can fork/host this repository on your own GitHub account:

1. **Push to your GitHub repository**:
   ```bash
   git init
   git add .
   git commit -m "feat: initial commit for cncf issue tracker"
   git branch -M main
   git remote add origin https://github.com/<your-username>/cncf-issue-tracker.git
   git push -u origin main
   ```

2. **Enable Workflow Permissions**:
   - Go to your repo **Settings** → **Actions** → **General**.
   - Under **Workflow permissions**, select **"Read and write permissions"**.
   - Click **Save**.

3. **Schedule**:
   - The workflow `.github/workflows/daily_tracker.yml` will automatically run **every 6 hours**, querying GitHub, archiving digests to `reports/`, and updating the `README.md` table!
   - You can also manually trigger it anytime via the **Actions** tab by clicking **Run workflow**.

---

### 3. Optional Push Notifications (Discord / Telegram / Slack)

To get pinged on your phone/desktop whenever new issues drop:

1. Add your webhook URL to your GitHub Repository **Settings** → **Secrets and variables** → **Actions**:
   - `DISCORD_WEBHOOK_URL`
   - `SLACK_WEBHOOK_URL`
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`
2. The GitHub Action will automatically notify your channel on every run!

---

## ⚙️ Customization

Edit [`config.yaml`](config.yaml) to:
- Add or remove repositories to monitor.
- Change the target labels (e.g. add `documentation`, `area/security`).
- Adjust the lookback time window (`default_hours: 24`).

---

## 📄 License
[MIT](LICENSE)
