# PR Review Dashboard

ระบบตรวจสอบ Pull Request อัตโนมัติจาก Azure DevOps พร้อม security scanning แบบ multi-layer (grep patterns + semgrep) และ web dashboard สำหรับดูผล

![Dashboard](https://img.shields.io/badge/Status-Active-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Python](https://img.shields.io/badge/Python-3.11-yellow)
![React](https://img.shields.io/badge/React-18-61dafb)

---

## 📋 สารบัญ

- [ภาพรวม](#ภาพรวม)
- [Architecture](#architecture)
- [Features](#features)
- [สิ่งที่ต้องมี](#สิ่งที่ต้องมี)
- [Quick Start](#quick-start)
- [การตั้งค่า (Configuration)](#การตั้งค่า-configuration)
- [ระบบทำงานอย่างไร](#ระบบทำงานอย่างไร)
- [Security Scanning](#security-scanning)
- [API Endpoints](#api-endpoints)
- [Frontend Pages](#frontend-pages)
- [การปรับแต่ง (Customization)](#การปรับแต่ง-customization)
- [Scheduler Control](#scheduler-control)
- [Troubleshooting](#troubleshooting)

---

## ภาพรวม

ระบบนี้จะ **poll Azure DevOps** เป็นระยะเพื่อตรวจหา PR ใหม่ที่ assign คุณเป็น reviewer เมื่อเจอ PR ใหม่ ระบบจะ:

1. ดึงไฟล์ที่เปลี่ยนแปลงแบบ **ขนาน** (10 workers พร้อมกัน)
2. สร้าง diff ระหว่าง branch ต้นทางและ branch เป้าหมาย
3. รัน **security scan** 2 ชั้น:
   - **Grep patterns** — 20+ regex patterns ตรวจ hardcoded secrets, injection, SSRF, IDOR ฯลฯ
   - **Semgrep** — SAST scanner ระดับ industry standard
4. บันทึกผลในฐานข้อมูล PostgreSQL
5. แสดงผลบน web dashboard

PR เก่าที่มีอยู่ก่อนเปิดระบบจะถูก **ข้าม** (ไม่ review ซ้ำ) — เฉพาะ PR ใหม่เท่านั้นที่จะถูกตรวจสอบ

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                          │
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │  Backend          │    │  Frontend         │              │
│  │  FastAPI          │    │  React + Vite     │              │
│  │  + APScheduler    │    │  + TailwindCSS    │              │
│  │  Port 9100        │    │  Port 9101        │              │
│  └────────┬─────────┘    └────────┬─────────┘              │
│           │                       │                          │
│           │    ┌──────────────────┘                          │
│           │    │ (nginx proxy)                               │
│           ▼    ▼                                             │
│  ┌─────────────────────────────────────────┐                │
│  │              PostgreSQL                  │                │
│  │         (pg-local, port 5432)            │                │
│  │         Database: pr_review              │                │
│  └─────────────────────────────────────────┘                │
│                                                              │
│  ┌─────────────────────────────────────────┐                │
│  │         Azure DevOps API                 │                │
│  │   (poll ทุก N นาที ผ่าน PAT)           │                │
│  └─────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Technology | หน้าที่ |
|-----------|-----------|--------|
| **Backend** | FastAPI + APScheduler + SQLAlchemy | REST API, polling, review engine |
| **Frontend** | React + Vite + TailwindCSS | Web dashboard |
| **Database** | PostgreSQL | เก็บ PR, reviews, findings, poll state |
| **Security Scanner** | grep patterns + semgrep | ตรวจช่องโหว่ |

---

## Features

### ✅ PR Monitoring
- Poll Azure DevOps API ตาม interval ที่กำหนด
- กรองเฉพาะ PR ที่ assign คุณเป็น reviewer (required หรือ optional)
- ตรวจ DB ก่อน — ถ้าไม่มี PR ใหม่ ไม่เสีย token/เวลา
- First-run mode: บันทึก PR เก่าโดยไม่ review (ข้ามงานซ้ำ)

### ✅ Parallel File Fetching
- ใช้ `asyncio.Semaphore` + concurrent requests (10 workers)
- ดึงทั้ง source และ target version พร้อมกัน
- สร้าง unified diff อัตโนมัติ

### ✅ Multi-Layer Security Scanning

**Layer 1: Grep Patterns (built-in, ไม่ต้องลงอะไร)**
- 20+ regex patterns ครอบคลุม OWASP Top 10
- Hardcoded secrets, SQL injection, command injection, SSRF, IDOR, path traversal, weak crypto ฯลฯ

**Layer 2: Semgrep (installed)**
- SAST scanner ระดับ industry standard
- TypeScript + OWASP rules
- ลด false positives กว่า grep

### ✅ Web Dashboard
- Dashboard: สถิติภาพรวม, recent reviews
- PR List: filter by repo/status
- PR Detail: findings, scores, diff viewer, manual review
- Settings: เปิด/ปิด poller, เปลี่ยน interval, ดูสถานะ

### ✅ Scheduler Control
- เปิด/ปิดระบบอัตโนมัติ (ควบคุม APScheduler จริง ไม่ใช่แค่ flag)
- เปลี่ยนความถี่ polling ได้ตั้งแต่ 1 นาที ถึง 24 ชั่วโมง
- สถานะ live (refresh ทุก 5 วินาที)

---

## สิ่งที่ต้องมี

- **Docker** + **Docker Compose**
- **PostgreSQL** (ใช้ `pg-local` ที่มีอยู่ หรือตั้งใหม่)
- **Azure DevOps PAT** — scope: Code (Read)
- **ชื่อใน Azure DevOps** — ใช้กรอง PR ที่ assign คุณ

---

## Quick Start

### 1. Clone repo

```bash
git clone https://github.com/Fernlizer/pr-review-dashboard.git
cd pr-review-dashboard
```

### 2. สร้าง .env

```bash
cp .env.example .env
```

แก้ไข `.env`:

```env
# Azure DevOps PAT (ต้องมี scope: Code Read)
AZURE_DEVOPS_PAT=your_pat_here

# ชื่อของคุณใน Azure DevOps (ตรงกับ displayName หรือ uniqueName)
REVIEWER_NAME=Your Name

# Repos ที่ต้องการ poll (comma-separated)
REPOS=purchase,usermgt,coop

# ความถี่ polling (นาที)
POLL_INTERVAL_MINUTES=10
```

### 3. สร้าง Database

```bash
# ถ้าใช้ pg-local ที่มีอยู่
PGPASSWORD=fern psql -h localhost -U admin -d mydb -c "CREATE DATABASE pr_review"

# ถ้าใช้ PostgreSQL อื่น แก้ DATABASE_URL ใน docker-compose.yml
```

### 4. รัน Docker

```bash
docker compose up -d
```

### 5. เปิดเว็บ

- **Dashboard:** http://localhost:9101
- **API:** http://localhost:9100
- **Health check:** http://localhost:9100/health

---

## การตั้งค่า (Configuration)

### Environment Variables

| Variable | Default | คำอธิบาย |
|----------|---------|----------|
| `AZURE_DEVOPS_PAT` | *(required)* | Personal Access Token จาก Azure DevOps |
| `REVIEWER_NAME` | `FERN` | ชื่อที่ใช้กรอง PR (ตรงกับ `displayName` หรือ `uniqueName` ใน Azure DevOps) |
| `REPOS` | `purchase,usermgt,coop` | Repositories ที่ต้องการ poll (comma-separated) |
| `POLL_INTERVAL_MINUTES` | `10` | ความถี่ polling (นาที) — เปลี่ยนได้ผ่านหน้า Settings |

### Database URL

กำหนดใน `docker-compose.yml`:

```yaml
environment:
  - DATABASE_URL=postgresql+asyncpg://admin:fern@host.docker.internal:5432/pr_review
```

เปลี่ยน `admin:fern` เป็น username:password ของ PostgreSQL คุณ

### Azure DevOps Organization

กำหนดใน `docker-compose.yml`:

```yaml
environment:
  - AZURE_ORG=AXONS-FIT-Business-and-CPTG
  - AZURE_PROJECT=AgriTech
```

---

## ระบบทำงานอย่างไร

### Polling Flow

```
ทุก N นาที (default 10)
│
├─ ดึง active PRs จาก Azure DevOps API (ทีละ repo)
│
├─ กรอง PR ที่ REVIEWER_NAME เป็น reviewer
│
├─ เปรียบเทียบกับ DB
│   ├─ First-run? → บันทึก PR record (ไม่ review) → จบ
│   ├─ PR อยู่ใน DB แล้ว? → ข้าม
│   └─ PR ใหม่? → เข้าสู่ review process ↓
│
└─ Review Process
    ├─ ดึง iterations + changes
    ├─ Parallel fetch ไฟล์ (10 workers)
    ├─ สร้าง diff
    ├─ Security scan (grep + semgrep)
    ├─ สร้าง Finding records
    ├─ คำนวณ scores
    └─ บันทึกลง DB
```

### Token Cost

| สถานการณ์ | Token/วัน |
|-----------|-----------|
| ไม่มี PR ใหม่ | **~0** (แค่ API call ไม่ใช้ LLM) |
| 1-2 PR/วัน | ~6,000-10,000 |
| 5-10 PR/วัน | ~30,000-50,000 |

> ระบบนี้ **ไม่ใช้ LLM** สำหรับ polling — ใช้เฉพาะ grep patterns + semgrep จึงไม่เสีย token เมื่อไม่มี PR ใหม่

---

## Security Scanning

### Grep Patterns (Built-in)

| Category | Patterns | OWASP |
|----------|----------|-------|
| **Hardcoded Secrets** | password, api_key, token, JWT, AWS key, private key | A07 |
| **Injection** | SQL concat, command injection, eval, deserialization | A03 |
| **SSRF** | User-controlled URLs in fetch/axios | A10 |
| **Path Traversal** | File operations with user input | A01 |
| **Sensitive Data** | Passwords in logs/responses, CORS wildcard | A09, A05 |
| **Insecure Config** | SSL verify false, debug mode | A05, A02 |
| **Weak Crypto** | MD5, SHA1, Math.random | A02 |
| **Mass Assignment** | Object.assign with req.body | A04 |

### Semgrep

ใช้ rules: `p/security-audit`

```bash
# ดู rules ที่ใช้
semgrep --config "p/security-audit" --show-supported-languages
```

### เพิ่ม Security Patterns

แก้ไข `backend/services/security_scanner.py`:

```python
SECURITY_PATTERNS: Dict[str, tuple] = {
    # เพิ่ม pattern ใหม่
    "my_custom_pattern": (
        r'regex_pattern_here',     # regex
        "HIGH",                     # severity: HIGH, MEDIUM, LOW
        "A03:Injection",           # OWASP tag
    ),
    # ...
}
```

---

## API Endpoints

### PRs

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/api/prs` | รายการ PR ทั้งหมด (filter: `repo`, `status`, `limit`, `offset`) |
| `GET` | `/api/prs/{id}` | รายละเอียด PR + reviews + findings |
| `POST` | `/api/prs/{id}/review` | สั่ง review PR นี้ด้วยตนเอง |

### Reviews

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/api/reviews` | รายการ review ทั้งหมด (filter: `status`, `recommendation`) |
| `GET` | `/api/reviews/{id}` | รายละเอียด review + findings + diff |

### Stats

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/api/stats` | สถิติภาพรวม (PRs, reviews, findings, poll states) |

### Scheduler Control

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/api/scheduler/status` | สถานะ scheduler จริง (enabled, interval, next_run) |
| `POST` | `/api/scheduler/enable` | เปิด poller (resume APScheduler job) |
| `POST` | `/api/scheduler/disable` | หยุด poller (pause APScheduler job) |
| `PUT` | `/api/scheduler/interval` | เปลี่ยนความถี่ polling (body: `{"minutes": 5}`) |
| `POST` | `/api/poll` | สั่ง poll ทันที |

### Health

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/health` | Health check |

---

## Frontend Pages

### Dashboard (`/`)
- สถิติภาพรวม: Total PRs, Reviews, Findings, HIGH Issues
- Recommendation breakdown: Approved, Changes Requested, Comments
- Poll status ของแต่ละ repo
- Recent reviews list

### PR List (`/prs`)
- รายการ PR ทั้งหมด
- Filter by repo และ status
- แสดง Required/Optional reviewer badge
- แสดง review status (approve/request_changes/comment)

### PR Detail (`/prs/{id}`)
- รายละเอียด PR: title, author, branch, reviewers
- Review scores: Logic, Security, Tests, Style, Architecture
- Findings list พร้อม severity, OWASP tag, code snippet, fix suggestion
- Diff viewer
- ปุ่ม "Run Review" สำหรับ PR ที่ยังไม่ได้ review

### Settings (`/settings`)
- สถานะระบบ: running/stopped, interval, next run
- ปุ่มเปิด/ปิด poller (ควบคุม APScheduler จริง)
- เปลี่ยน interval (input + preset buttons: 5/10/15/30/60 นาที)

---

## การปรับแต่ง (Customization)

### เปลี่ยน Reviewer Name

แก้ `.env`:

```env
REVIEWER_NAME=Your Full Name
```

> ต้องตรงกับ `displayName` หรือ `uniqueName` ใน Azure DevOps (ไม่ case-sensitive)

จากนั้น restart:

```bash
docker compose up -d backend
```

### เพิ่ม/ลบ Repository

แก้ `.env`:

```env
REPOS=purchase,usermgt,coop,document-lambda,new-repo
```

> คั่นด้วย comma, ไม่มีช่องว่าง

จากนั้น restart:

```bash
docker compose up -d backend
```

### เปลี่ยน Polling Interval

**ผ่านหน้าเว็บ:** ไปที่ Settings → เลือก interval → กด "อัพเดท"

**ผ่าน API:**

```bash
curl -X PUT http://localhost:9100/api/scheduler/interval \
  -H "Content-Type: application/json" \
  -d '{"minutes": 5}'
```

**ผ่าน .env (ต้อง restart):**

```env
POLL_INTERVAL_MINUTES=5
```

### เปลี่ยน Azure DevOps Organization

แก้ `docker-compose.yml`:

```yaml
environment:
  - AZURE_ORG=your-org-name
  - AZURE_PROJECT=your-project-name
```

### เปลี่ยน Ports

แก้ `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "9200:9100"    # เปลี่ยน port ภายนอก
  frontend:
    ports:
      - "9201:80"      # เปลี่ยน port ภายนอก
```

### ปรับ Frontend Proxy

ถ้าเปลี่ยน port backend ต้องแก้ `frontend/nginx.conf`:

```nginx
location /api/ {
    proxy_pass http://host.docker.internal:9200;  # port ใหม่
}
```

---

## Scheduler Control

ระบบ scheduler ควบคุมผ่าน APScheduler โดยตรง — ไม่ใช่ boolean flag

### เปิด/ปิด ผ่านหน้าเว็บ

ไปที่ **Settings** → กดปุ่ม "หยุดตรวจสอบอัตโนมัติ" หรือ "เปิดตรวจสอบอัตโนมัติ"

### เปิด/ปิด ผ่าน API

```bash
# หยุด
curl -X POST http://localhost:9100/api/scheduler/disable

# เปิด
curl -X POST http://localhost:9100/api/scheduler/enable

# ดูสถานะ
curl http://localhost:9100/api/scheduler/status
```

### ตรวจสอบว่า scheduler ทำงานจริง

```bash
curl http://localhost:9100/api/scheduler/status | jq
```

Response:

```json
{
  "enabled": true,              ← job.next_run_time != null
  "interval_minutes": 10,       ← ความถี่ปัจจุบัน
  "next_run": "2026-07-07T...", ← เวลา poll ครั้งถัดไป
  "job_exists": true,           ← APScheduler job มีอยู่
  "scheduler_running": true     ← APScheduler instance ทำงาน
}
```

---

## Troubleshooting

### ไม่มี PR ขึ้นใน Dashboard

1. ตรวจว่า `REVIEWER_NAME` ตรงกับชื่อใน Azure DevOps
2. ตรวจว่ามี PR ที่ assign คุณเป็น reviewer (active status)
3. ตรวจ logs: `docker logs pr-review-backend 2>&1 | tail -20`

### Frontend ไม่เชื่อมต่อ Backend

1. ตรวจว่า backend รันอยู่: `curl http://localhost:9100/health`
2. ตรวจ nginx proxy: `docker logs pr-review-frontend 2>&1 | tail -10`

### Security Scan ไม่เจอ findings

1. บาง PR อาจไม่มีไฟล์ที่มี pattern ที่ตรวจ — เป็นเรื่องปกติ
2. ตรวจว่า semgrep ทำงาน: `docker exec pr-review-backend semgrep --version`

### Database Connection Error

1. ตรวจว่า PostgreSQL รันอยู่: `docker ps | grep pg`
2. ตรวจ credentials ใน `docker-compose.yml`
3. ตรวจว่า database `pr_review` มีอยู่: `PGPASSWORD=fern psql -h localhost -U admin -d mydb -c "\l" | grep pr_review`

### ดู Logs

```bash
# Backend logs
docker logs pr-review-backend -f 2>&1

# Frontend logs
docker logs pr-review-frontend -f 2>&1

# Filter เฉพาะ poll results
docker logs pr-review-backend 2>&1 | grep -E "Poll complete|Found|ERROR"
```

---

## License

MIT
