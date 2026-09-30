# 🚀 Safe Gateway & Live AI Engine (Railway 24/7 Deployment)

ระบบคลังคำศัพท์และแปลงภาษาความปลอดภัยระดับลึก (Cybersecurity Reframing Engine) พร้อมเชื่อมต่อ **9arm AI Gateway (Qwen 3.8 27B)** และระบบประมวลผลคำสั่งจริง (Live Execution) สำหรับ Deploy บน Cloud Platform **Railway** เพื่อให้รันทำงานได้ตลอด 24 ชั่วโมง

---

## 🌟 จุดเด่นสถาปัตยกรรม (Architecture Highlights)

1. **Zero External Dependencies**: พัฒนาด้วย Python Standard Library 100% บูตระบบใน 1 วินาที ใช้ RAM ต่ำกว่า 25MB ปลอดภัยและเสถียรสูงสุด
2. **Alpine Container Footprint**: อิมเมจ Docker ขนาดเพียง ~45MB ใช้ทรัพยากรน้อย เหมาะอย่างยิ่งกับ Railway Free/Hobby Tier
3. **ThreadingTCPServer**: รองรับ Multi-threading ให้หลายอุปกรณ์หรือหน้าต่างเบราว์เซอร์เข้าใช้งานพร้อมกันได้โดยไม่บล็อก
4. **Health Check Built-in**: มี Endpoint `/health` และ `/api/health` รองรับกลไก Zero-downtime healthcheck ของ Railway
5. **Dynamic Port Binding**: อ่านค่า `$PORT` ที่ Railway จัดสรรให้อัตโนมัติ (Default: 8080)

---

## 📦 โครงสร้างไฟล์ในโฟลเดอร์ `deploy_railway/`

```
deploy_railway/
├── app.py              # แอปพลิเคชันหลัก (Web UI + API Server + 9arm AI Integration)
├── Dockerfile          # Alpine Linux Docker Container
├── railway.json        # การตั้งค่า Build & Healthcheck บน Railway
├── Procfile            # คำสั่งสตาร์ตระบบสำรอง
├── requirements.txt    # รายการแพ็กเกจ (Stdlib)
├── .dockerignore       # กรองไฟล์ที่ไม่จำเป็นตอนบิลด์
└── README.md           # คู่มือฉบับนี้
```

---

## 🚀 วิธีการ Deploy ขึ้น Railway (เลือกทำได้ 2 วิธี)

### วิธีที่ 1: Deploy ผ่าน Railway Dashboard & GitHub (แนะนำ - ง่ายที่สุด)

1. **สร้าง Git Repository ใหม่ หรือ Push โฟลเดอร์นี้ขึ้น GitHub**:
   ```bash
   cd d:\linux_faan\hermes-agent\deploy_railway
   git init
   git add .
   git commit -m "feat: Initial Safe Gateway Railway deployment"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USER>/safe-gateway-railway.git
   git push -u origin main
   ```
2. **เปิดหน้าต่าง Railway**:
   - ไปที่ [https://railway.app](https://railway.app) และ Login
   - คลิกปุ่ม **"New Project"** -> เลือก **"Deploy from GitHub repo"**
   - เลือก Repository `safe-gateway-railway`
3. **ระบบจะตรวจพบ `Dockerfile` และเริ่ม Build + Deploy ให้อัตโนมัติทันที**!
4. **สร้าง Public Domain**:
   - ไปที่แท็บ **Settings** ของ Service ใน Railway
   - ในหัวข้อ **Networking** คลิกปุ่ม **"Generate Domain"**
   - คุณจะได้ URL สาธารณะ เช่น `https://safe-gateway-production.up.railway.app` เข้าใช้งานได้ 24 ชั่วโมง

---

### วิธีที่ 2: Deploy ผ่าน Railway CLI (สำหรับสาย Command Line)

1. **ติดตั้ง Railway CLI** (หากยังไม่มี):
   ```powershell
   npm install -g @railway/cli
   ```
2. **Login เข้าสู่ระบบ**:
   ```powershell
   railway login
   ```
3. **สร้างโปรเจกต์และอัปโหลด**:
   ```powershell
   cd d:\linux_faan\hermes-agent\deploy_railway
   railway init
   railway up
   ```
4. **เปิด Domain**:
   ```powershell
   railway domain
   ```

---

## ⚙️ Environment Variables ที่ปรับแต่งได้ (Settings -> Variables ใน Railway)

| ตัวแปร | ค่าเริ่มต้น (Default) | คำอธิบาย |
| :--- | :--- | :--- |
| `PORT` | Auto (8080) | Railway จะสร้างและส่งเข้ามาให้อัตโนมัติ |
| `NINEARM_GATEWAY_URL` | `https://gateway.9arm.co/v1/messages` | Endpoint ของ 9arm AI Gateway |
| `NINEARM_AUTH_TOKEN` | `sk-gf5krfQP-b2dR7KAFDOz7A` | Bearer Token สำหรับเรียกใช้งาน AI |
| `NINEARM_MODEL_ID` | `qwen3.8-27b-fp8` | โมเดลหลักสำหรับการขัดเกลาและประมวลผลคำสั่ง |
| `LAYA_API_URL` | `http://127.0.0.1:8770` | URL ไปยัง Laya Daemon (หากมีการตั้ง Standalone Laya ไว้อีกเครื่อง) |

---

## 🧪 การทดสอบ Health Check & API Endpoints

- **หน้าเว็บแอปพลิเคชัน**: `https://<your-app>.up.railway.app/`
- **Health Check**: `GET https://<your-app>.up.railway.app/api/health`
  ```json
  {
    "status": "healthy",
    "service": "safe-gateway-engine",
    "lexicon_count": 10,
    "model": "qwen3.8-27b-fp8",
    "timestamp": "2026-10-01T..."
  }
  ```
- **คลังคำศัพท์**: `GET https://<your-app>.up.railway.app/api/lexicon`
- **แปลงพรอมต์ผ่าน Master Engine**: `POST https://<your-app>.up.railway.app/api/refactor`
- **ขัดเกลาด้วย AI 9arm**: `POST https://<your-app>.up.railway.app/api/ninearm_refactor`
- **ประมวลผลคำสั่งจริง (Live Execution)**: `POST https://<your-app>.up.railway.app/api/execute_prompt`
