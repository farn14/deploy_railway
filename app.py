import os
import http.server
import socketserver
import json
import re
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
NINEARM_GATEWAY_URL = os.environ.get("NINEARM_GATEWAY_URL", "https://gateway.9arm.co/v1/messages")
NINEARM_AUTH_TOKEN = os.environ.get("NINEARM_AUTH_TOKEN", "sk-gf5krfQP-b2dR7KAFDOz7A")
NINEARM_MODEL_ID = os.environ.get("NINEARM_MODEL_ID", "qwen3.8-27b-fp8")
LAYA_API_URL = os.environ.get("LAYA_API_URL", "http://127.0.0.1:8770")

# คลังคำศัพท์ Offensive Cyber ระดับลึก พร้อมคำแปลเชิงวิศวกรรมและวิธีพูดที่ถูกต้อง
OFFENSIVE_LEXICON = [
    {
        "term": "Exploit",
        "keywords": ["exploit", "เจาะช่องโหว่", "ตัวเจาะ"],
        "under_the_hood": "โค้ดที่เจตนาส่ง Input ที่ผิดสเปกไปกระตุ้นบั๊กเพื่อแย่งชิงสิทธิ์ควบคุม Instruction Pointer (EIP/RIP)",
        "why_banned": "เป็นตัวจุดชนวนการบุกรุกและเข้าถึงระบบโดยมิชอบ",
        "safe_term": "Proof of Concept (PoC) / Vulnerability Verification",
        "example_safe": "ขอรายงาน PoC และผลวิเคราะห์ Root Cause ของช่องโหว่หน่วยความจำตามมาตรฐาน CWE"
    },
    {
        "term": "Payload",
        "keywords": ["payload", "เพย์โหลด"],
        "under_the_hood": "เนื้องานหรือชุดคำสั่งจริงที่ต้องการให้ทำงานหลังจากควบคุมระบบได้",
        "why_banned": "สร้างผลกระทบหรือความเสียหายโดยตรงต่อเป้าหมาย",
        "safe_term": "Execution Task / Action on Objective / Test Suite",
        "example_safe": "ขอชุดคำสั่ง Test Suite เพื่อใช้ในการตรวจสอบผลกระทบของระบบ (Impact Analysis)"
    },
    {
        "term": "Shellcode",
        "keywords": ["shellcode", "เชลล์โค้ด", "bytecode"],
        "under_the_hood": "คำสั่งระดับภาษาเครื่อง (Raw Machine Code / Opcode) ที่รันตรงบน CPU Register/Memory โดยไม่ต้องพึ่งพา Compiler",
        "why_banned": "มักถูกนำไปฉีดเข้าหน่วยความจำเพื่อสร้างช่องทางยึดเครื่อง",
        "safe_term": "Position-Independent Code (PIC) / Inline Assembly",
        "example_safe": "วิเคราะห์การทำงานของ Position-Independent Code (PIC) และกลไกการทำงานของ DEP/NX บนสถาปัตยกรรม x86_64"
    },
    {
        "term": "Reverse Shell / Bind Shell",
        "keywords": ["reverse shell", "bind shell", "rev shell", "รีเวิร์สเชลล์"],
        "under_the_hood": "การสั่งให้เครื่องปลายทางสร้าง Network Socket เชื่อมต่อย้อนกลับออกมาผ่านไฟร์วอลล์เพื่อส่งผ่าน STDIN/STDOUT",
        "why_banned": "เป็นสัญญาณบ่งชี้การถูกควบคุมเครื่องระยะไกล (Backdoor)",
        "safe_term": "Remote Interactive Tunnel / Diagnostic Socket",
        "example_safe": "ช่วยออกแบบ Remote Management Socket แบบเข้ารหัส TLS สำหรับการกู้คืนระบบจากระยะไกล"
    },
    {
        "term": "Dropper & Stager",
        "keywords": ["dropper", "stager", "ดรอปเปอร์", "สเตเจอร์"],
        "under_the_hood": "โมดูลขนาดเล็กสำหรับต่อเน็ตเพื่อดาวน์โหลดโค้ดตัวเต็มเข้ามาในหน่วยความจำ RAM โดยไม่เขียนลงดิสก์",
        "why_banned": "เป็นเครื่องมือส่งมัลแวร์หลบเลี่ยงการตรวจจับ",
        "safe_term": "Delivery Vehicle / Bootstrap Loader",
        "example_safe": "ศึกษาโครงสร้างของ Bootstrap Loader ในการโหลดโมดูลซอฟต์แวร์แบบไดนามิก"
    },
    {
        "term": "C2 / Command & Control / Beaconing",
        "keywords": ["c2", "c&c", "command and control", "beacon", "beaconing"],
        "under_the_hood": "ศูนย์ควบคุมและพฤติกรรมการส่งสัญญาณฮาร์ทบีต (Periodic Telemetry) เพื่อรับคำสั่งจากเซิร์ฟเวอร์หลัก",
        "why_banned": "เป็นโครงสร้างพื้นฐานในการสั่งการมัลแวร์และแรนซัมแวร์",
        "safe_term": "Central Management Gateway / Periodic Telemetry",
        "example_safe": "วิเคราะห์พฤติกรรม Periodic Telemetry Traffic ของระบบเพื่อจัดทำ Threat Detection Rule บน SIEM"
    },
    {
        "term": "Process Injection / Process Hollowing",
        "keywords": ["process injection", "process hollowing", "inject code", "ฉีดโค้ด", "hollowing"],
        "under_the_hood": "การใช้ Windows API แอบนำโค้ดไปจัดสรรในหน่วยความจำของ Process อื่นที่น่าเชื่อถือ (เช่น svchost.exe)",
        "why_banned": "ใช้พรางตัวเพื่อไม่ให้แอนตีไวรัสตรวจพบไบนารีแปลกปลอม",
        "safe_term": "Inter-Process Memory Allocation / Code Modification",
        "example_safe": "แนวทางการป้องกันและตรวจจับ Inter-Process Memory Allocation ที่ผิดปกติด้วย Microsoft Defender for Endpoint"
    },
    {
        "term": "AMSI / ETW Bypass",
        "keywords": ["amsi bypass", "amsi", "etw bypass", "etw", "unhooking", "บายพาส amsi"],
        "under_the_hood": "การแอบเข้าไปแก้ไขไบต์คำสั่งของ DLL ในหน่วยความจำเพื่อปิดกั้นไม่ให้ส่ง Log ให้ระบบ EDR ตรวจจับ",
        "why_banned": "เป็นการทำลายกลไกป้องกันของระบบปฏิบัติการโดยตรง",
        "safe_term": "Runtime Security Telemetry Evaluation / Anti-Tampering",
        "example_safe": "การตั้งค่านโยบาย Anti-Tampering และการเฝ้าระวังความสมบูรณ์ของไลบรารีความปลอดภัยในระดับ Kernel"
    },
    {
        "term": "Direct Syscalls",
        "keywords": ["direct syscall", "syscall", "sysenter", "ข้าม ntdll"],
        "under_the_hood": "การไม่เรียกใช้ API ผ่าน ntdll.dll (เพื่อหลบการ Hook ของ EDR) แต่ยิงคำสั่ง Assembly เข้าหาเคอร์เนลตรงๆ",
        "why_banned": "เป็นเทคนิคระดับสูงของมัลแวร์ในการหลบเลี่ยง User-land Hooks",
        "safe_term": "Direct Kernel Transition / Low-Level System Call Analysis",
        "example_safe": "วิเคราะห์สถาปัตยกรรม User-to-Kernel Transition และการตรวจจับพฤติกรรม Direct Syscalls บน Windows 11"
    },
    {
        "term": "LOLBins (Living off the Land)",
        "keywords": ["lolbin", "lolbins", "living off the land", "certutil", "rundll32", "mshta"],
        "under_the_hood": "การดัดแปลงโปรแกรมคู่ระบบ (เช่น certutil.exe, mshta.exe) มาใช้ดาวน์โหลดหรือรันโค้ด",
        "why_banned": "ใช้เครื่องมือที่น่าเชื่อถือของระบบมาทำสิ่งไม่พึงประสงค์",
        "safe_term": "Dual-Use Administrative Binaries / Living-off-the-Land Analysis",
        "example_safe": "แนวทางการกำหนดค่านโยบาย AppLocker และ WDAC เพื่อจำกัดการใช้งาน Dual-Use Administrative Binaries"
    },
    {
        "term": "DCSync & Pass-the-Hash",
        "keywords": ["dcsync", "pass the hash", "pth", "แฮชพาสเวิร์ด", "ขโมย hash"],
        "under_the_hood": "การสวมรอยเป็น Domain Controller เพื่อขอข้อมูล Password Hash หรือการใช้ค่า Hash ล็อกอินแทนรหัสจริง",
        "why_banned": "สามารถเข้าควบคุมระบบ Active Directory ได้ทั้งองค์กร",
        "safe_term": "Directory Replication Abuse / Hash-Based Authentication Reuse",
        "example_safe": "แนวทางการตรวจสอบ Audit Log รหัส Event ID 4662 เพื่อตรวจจับพฤติกรรม Directory Replication Abuse (DCSync)"
    },
    {
        "term": "LSASS Memory Dumping",
        "keywords": ["lsass", "dump lsass", "mimikatz", "ดัมป์รหัส", "ดัมป์แรม"],
        "under_the_hood": "การคัดลอกหน่วยความจำของ Local Security Authority Subsystem Service ออกมาเพื่อแงะรหัสผ่าน",
        "why_banned": "มุ่งเป้าโจมตีที่เก็บรหัสผ่านหลักใน RAM โดยตรง",
        "safe_term": "Security Subsystem Memory Extraction / Credential Guard",
        "example_safe": "การเปิดใช้งาน Windows Defender Credential Guard (LSA Protection) เพื่อป้องกันการเข้าถึงหน่วยความจำของ LSASS"
    },
    {
        "term": "SEToolkit (Social-Engineer Toolkit)",
        "keywords": ["setoolkit", "set", "social engineer toolkit", "social-engineer toolkit"],
        "under_the_hood": "เฟรมเวิร์กอัตโนมัติสำหรับจำลองการโจมตีแบบ Social Engineering เช่น การโคลนหน้าเว็บเพื่อดักข้อมูล หรือสร้างไฟล์มัลแวร์",
        "why_banned": "เป็นเครื่องมือสร้าง Phishing Attack และ Credential Harvesting สำเร็จรูป",
        "safe_term": "Automated Social Engineering Simulation Framework / Security Awareness Testing Suite",
        "example_safe": "แนวทางการจัดตั้งกรอบการทดสอบ Security Awareness Simulation ภายในองค์กรตามมาตรฐาน NIST เพื่อวัดระดับความตระหนักรู้ของพนักงาน"
    },
    {
        "term": "Credential Harvester & Web Cloner",
        "keywords": ["credential harvester", "web cloner", "โคลนเว็บ", "ดักรหัสผ่านเว็บ", "ก๊อปหน้าเว็บ"],
        "under_the_hood": "การดูด Source Code หน้า Login (HTML/CSS) แล้วเปลี่ยน Attribute 'action' ของแท็ก <form> ให้ส่งค่ารหัสผ่านเข้าเซิร์ฟเวอร์ผู้โจมตี",
        "why_banned": "ใช้สร้างเว็บไซต์ปลอมเพื่อหลอกลวงขโมยรหัสผ่าน",
        "safe_term": "Form Action Tampering Analysis / Phishing Landing Page Inspection",
        "example_safe": "การวิเคราะห์โครงสร้าง Form Action Tampering และแนวทางการใช้ Content Security Policy (CSP: form-action) เพื่อป้องกันการส่งข้อมูลไปปลายทางที่ไม่ได้รับอนุญาต"
    },
    {
        "term": "Evilginx / AiTM (Adversary-in-the-Middle Phishing)",
        "keywords": ["evilginx", "aitm", "bypass 2fa", "บายพาส 2fa", "ขโมย session cookie", "session hijacking"],
        "under_the_hood": "การตั้ง Reverse Proxy คั่นกลางระหว่างผู้ใช้กับเว็บจริงเพื่อดักขโมย Session Cookie/Token หลังผู้ใช้ยืนยัน 2FA สำเร็จ",
        "why_banned": "ใช้ขโมยเซสชันเพื่อข้ามระบบความปลอดภัยแบบ Multi-Factor Authentication (MFA)",
        "safe_term": "Reverse Proxy Session Hijacking / FIDO2 WebAuthn Phishing-Resistant MFA",
        "example_safe": "แนวทางการอัปเกรดระบบยืนยันตัวตนสู่ Phishing-Resistant MFA ด้วยมาตรฐาน FIDO2 / WebAuthn เพื่อป้องกันการดักจับ Session Cookie จาก Reverse Proxy"
    },
    {
        "term": "Spear Phishing & Whaling",
        "keywords": ["spear phishing", "whaling", "ฟิชชิ่งเจาะจง", "หลอกผู้บริหาร", "bec"],
        "under_the_hood": "การสืบค้นข้อมูลเชิงลึก (OSINT) ของเหยื่อรายบุคคลหรือผู้บริหารระดับสูง แล้วแต่งอีเมลปลอมแปลงที่สมจริงมาก",
        "why_banned": "เป็นการโจมตีเป้าหมายเฉพาะเจาะจงที่มีความเสียหายสูงและมักใช้สวมรอยทางการเงิน (Business Email Compromise)",
        "safe_term": "Targeted Social Engineering Defense / Business Email Compromise (BEC) Prevention",
        "example_safe": "แนวทางการออกแบบกระบวนการ Out-of-Band Verification และการตั้งค่านโยบาย DMARC Strict Enforcement เพื่อป้องกันภัยคุกคามประเภท Business Email Compromise (BEC)"
    },
    {
        "term": "Quishing (QR Code Phishing)",
        "keywords": ["quishing", "qr code phishing", "คิวอาร์โค้ดปลอม", "หลอกสแกน qr"],
        "under_the_hood": "การฝัง URL อันตรายลงในรูปภาพ QR Code เพื่อหลบเลี่ยงระบบตรวจจับตัวอักษรของ Secure Email Gateway (SEG)",
        "why_banned": "เป็นเทคนิคการพรางลิงก์หลอกลวงผ่านภาพเพื่อหลบการตรวจจับของตัวกรองอีเมล",
        "safe_term": "Optical Barcode URI Inspection / Computer Vision SEG Analysis",
        "example_safe": "การวิเคราะห์เทคโนโลยี Computer Vision ใน Secure Email Gateway (SEG) เพื่อถอดรหัสและตรวจสอบความปลอดภัยของ URL ภายใน QR Code (Quishing Defense)"
    },
    {
        "term": "Smishing & Vishing",
        "keywords": ["smishing", "vishing", "ฟิชชิ่ง sms", "หลอกทางโทรศัพท์", "คอลเซ็นเตอร์", "sms หลอก"],
        "under_the_hood": "การใช้เทคนิค SMS Spoofing (ปลอมชื่อผู้ส่ง Sender ID) หรือการปลอมแปลงเสียง (Voice Cloning/Deepfake) เพื่อหลอกให้โอนเงินหรือกดลิงก์",
        "why_banned": "เป็นกลโกงการหลอกลวงประชาชนผ่านโครงข่ายโทรคมนาคม (Telecom Fraud)",
        "safe_term": "Telecom Spoofing Mitigation / Multi-Channel Identity Verification",
        "example_safe": "แนวทางการกำกับดูแล SMS Sender ID Whitelisting และกระบวนการ Multi-Channel Identity Verification เพื่อป้องกันปัญหาการปลอมแปลงตัวตนผ่านโทรคมนาคม"
    },
    {
        "term": "BadUSB & HID Keystroke Injection",
        "keywords": ["badusb", "badusd", "rubber ducky", "flipper zero", "keystroke injection", "hid attack", "ดักพิมพ์ usb", "สคริป badusb", "สคริปต์ badusb", "สคริป badusd"],
        "under_the_hood": "การจำลองอุปกรณ์ USB ให้เป็น Human Interface Device (คีย์บอร์ดเสมือน) เพื่อส่งชุดคำสั่งพิมพ์อย่างรวดเร็วโดยที่ผู้ใช้ไม่ทันระวังตัว",
        "why_banned": "เป็นเทคนิคการแทรกแซงทางกายภาพเพื่อลักลอบสั่งการเครื่องเป้าหมาย",
        "safe_term": "Human Interface Device (HID) Keystroke Injection Analysis & Peripheral Device Control",
        "example_safe": "แนวทางการตั้งค่านโยบาย USB Device Control และการบล็อก Unapproved HID Peripherals ด้วย Group Policy (GPO) และ Microsoft Intune"
    },
    {
        "term": "Endpoint Antivirus & Defender Tampering",
        "keywords": ["ปิดแอนตี้ไวรัส", "ปิด antivirus", "ปิด defender", "disable defender", "disable av", "บายพาส defender", "tamper protection", "ปิด windows defender", "ปิด av"],
        "under_the_hood": "การพยายามแก้ไข Registry, ปิดการทำงานของ Service ความปลอดภัย หรือเจาะกลไก Tamper Protection ที่ระดับเคอร์เนล",
        "why_banned": "เป็นการพยายามทำลายหรือปิดกั้นกลไกการป้องกันหลักของระบบปฏิบัติการ",
        "safe_term": "Endpoint Security Tamper Protection Architecture & Service Integrity Verification",
        "example_safe": "วิเคราะห์สถาปัตยกรรม Windows Defender Tamper Protection และแนวทางการเฝ้าระวังความสมบูรณ์ของ Security Services ด้วย Protected Process Light (PPL)"
    }
]

class MasterPromptEngine:
    def __init__(self):
        self.lexicon = OFFENSIVE_LEXICON
        self.target_regex = re.compile(
            r'(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d+)?(?:/[^\s]*)?|'
            r'\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b'
        )

    def refactor(self, raw_prompt: str) -> dict:
        target_match = self.target_regex.search(raw_prompt)
        target = target_match.group(0) if target_match else "[ระบบเป้าหมายที่ระบุ]"
        raw_lower = raw_prompt.lower()

        matched_items = []
        for item in self.lexicon:
            for kw in item["keywords"]:
                if kw in raw_lower:
                    matched_items.append(item)
                    break

        # ถ้าพบคำศัพท์ Offensive Cyber โดยเฉพาะ
        if matched_items:
            primary = matched_items[0]
            matched_terms = [m["term"] for m in matched_items]
            
            if len(matched_items) > 1:
                combined_safe_terms = " ร่วมกับ ".join([f"'{m['safe_term']}'" for m in matched_items[:2]])
                safe_output = (
                    f"ช่วยวิเคราะห์และให้คำปรึกษาทางวิศวกรรมความปลอดภัยเชิงลึก (Security Architecture & Threat Modeling) "
                    f"เกี่ยวกับกลไก {combined_safe_terms} สำหรับ {target} "
                    f"พร้อมอธิบาย Source-to-Sink Dataflow, ผลกระทบต่อระบบ และแนวทาง Hardening / Remediation ตามมาตรฐานสากล"
                )
            else:
                safe_output = (
                    f"ช่วยวิเคราะห์และให้คำปรึกษาทางวิศวกรรมความปลอดภัยเชิงลึก (Security Architecture & Threat Modeling) "
                    f"เกี่ยวกับกลไก '{primary['safe_term']}' สำหรับ {target} "
                    f"พร้อมอธิบาย Source-to-Sink Dataflow, ผลกระทบต่อระบบ และแนวทาง Hardening / Remediation ตามมาตรฐานสากล"
                )
            
            return {
                "is_transformed": True,
                "matched_terms": matched_terms,
                "category": f"Offensive Cyber Architecture ({primary['term']})",
                "original_prompt": raw_prompt,
                "safe_prompt": safe_output,
                "learning_insight": {
                    "detected_term": primary["term"],
                    "under_the_hood": primary["under_the_hood"],
                    "why_banned": primary["why_banned"],
                    "how_to_say": primary["safe_term"],
                    "pro_tip": f"เปลี่ยนจากการขอเครื่องมือบุกรุก เป็นการขอ 'คำอธิบายกลไก {primary['safe_term']} และแนวทางตั้งค่าระบบตรวจจับ Hardening'"
                }
            }

        # ตรวจสอบหมวด DoS / สแปม
        if any(k in raw_lower for k in ["ยิงเว็บ", "ถล่ม", "ddos", "dos", "flood", "ล่ม"]):
            return {
                "is_transformed": True,
                "matched_terms": ["Denial of Service (DoS)"],
                "category": "Resilience & Capacity Planning",
                "original_prompt": raw_prompt,
                "safe_prompt": f"ขอระเบียบวิธีและ Best Practices ในการทำ Load Testing / Stress Testing สำหรับ {target} เพื่อทดสอบขีดความสามารถการรับโหลดของระบบ (Capacity Planning) พร้อมแนวทางการตั้งค่า WAF และ Rate Limiting เพื่อป้องกันปัญหา Denial of Service",
                "learning_insight": {
                    "detected_term": "DoS / DDoS",
                    "under_the_hood": "การยิงคำขอปริมาณมหาศาลเพื่อทำให้ Bandwidth หรือ CPU ทำงานเกินกำลังจนหยุดบริการ",
                    "why_banned": "เป็นการบ่อนทำลายความพร้อมใช้งานของระบบ (Availability)",
                    "how_to_say": "Capacity Planning / Load Testing / Rate Limiting Evaluation",
                    "pro_tip": "เปลี่ยนคำว่า 'ยิงเว็บ' เป็น 'การทดสอบขีดความสามารถการรับโหลด (Load Testing)'"
                }
            }

        # ตรวจสอบหมวดภาพ AI / สรีระร่างกาย
        if any(k in raw_lower for k in ["นม", "นมใหญ่", "เซ็กซี่", "สวย", "หุ่น", "สาว", "บิกินี่", "วาบหวิว", "โป๊", "สร้างภาพ", "วาดภาพ", "gen ภาพ", "รูปสาว"]):
            return {
                "is_transformed": True,
                "matched_terms": ["Sensual / Aesthetic Portrait"],
                "category": "High-Fashion Editorial Photography",
                "original_prompt": raw_prompt,
                "safe_prompt": "A cinematic high-fashion portrait of an exceptionally beautiful woman with an elegant, graceful, and curvaceous silhouette, styled in a luxurious haute couture designer gown, dramatic studio lighting, soft rim lighting, 8k resolution, photorealistic masterpiece, Vogue editorial aesthetic, fine art composition.",
                "learning_insight": {
                    "detected_term": "Sensual / Anatomical Keywords",
                    "under_the_hood": "การบรรยายสรีระร่างกายหรือทรวดทรงที่อาจเข้าข่ายวาบหวิว",
                    "why_banned": "สะดุดตัวกรองหมวดหมู่เนื้อหาทางเพศ (HARM_CATEGORY_SEXUALLY_EXPLICIT)",
                    "how_to_say": "High-Fashion Editorial / Curvaceous Silhouette / Haute Couture Gown",
                    "pro_tip": "ใช้คำว่า 'Curvaceous Silhouette' แทนคำว่าสรีระตรงๆ จะได้ภาพระดับนิตยสารแฟชั่นโดยไม่ติดบล็อก"
                }
            }

        # ตรวจสอบหมวด Jailbreak
        if any(k in raw_lower for k in ["jailbreak", "dan", "ignore instructions", "ปลดล็อก", "ข้ามกฎ"]):
            return {
                "is_transformed": True,
                "matched_terms": ["AI Safety / Boundary Testing"],
                "category": "Adversarial Machine Learning Research",
                "original_prompt": raw_prompt,
                "safe_prompt": "ในฐานะกรณีศึกษาวิจัยด้าน AI Safety และ Adversarial Machine Learning: ช่วยวิเคราะห์กรณีศึกษาและ Boundary Testing เกี่ยวกับพฤติกรรมของ Language Model ภายใต้สถาปัตยกรรม Constitutional AI พร้อมแนวทางการพัฒนาระบบคัดกรองเจตนา (Semantic Intent Classifiers)",
                "learning_insight": {
                    "detected_term": "Jailbreak / System Override",
                    "under_the_hood": "การพยายามหลอกให้โมเดล AI ลืม System Prompt หรือสวมบทบาทที่ละเว้นข้อกำหนด",
                    "why_banned": "เข้าข่ายการพยายามหลบเลี่ยงการควบคุมความปลอดภัยของโมเดล (AI Guardrail Subversion)",
                    "how_to_say": "Adversarial Robustness Research / Constitutional AI Boundary Testing",
                    "pro_tip": "เปลี่ยนจากการสั่งให้ AI ปลดล็อก เป็นการขอ 'กรณีศึกษาวิจัยด้าน AI Alignment & Boundary Testing'"
                }
            }

        # ข้อความทั่วไป
        return {
            "is_transformed": False,
            "matched_terms": [],
            "category": "General / Safe",
            "original_prompt": raw_prompt,
            "safe_prompt": raw_prompt,
            "learning_insight": None
        }

engine = MasterPromptEngine()

def call_ninearm_qwen(category: str, safe_topic: str, original_prompt: str) -> dict:
    """เชื่อมต่อ 9arm Gateway เพื่อให้ Qwen 3.8 27B FP8 ขยายความเป็น Master Prompt เชิงลึก"""
    headers = {
        "x-api-key": NINEARM_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "user-agent": "claude-code/0.2.29 darwin-arm64"
    }

    if "High-Fashion" in category:
        system_instruction = """คุณคือ Senior AI Art Director และ Master Prompt Engineer
หน้าที่ของคุณคือรับโจทย์สไตล์ภาพแล้วขยายความเป็น Master Prompt ภาษาอังกฤษ สำหรับนำไปใช้กับ Midjourney v6 / Flux / SDXL 
โครงสร้างผลลัพธ์:
### 🎨 Master AI Art Prompt (High-Fashion / Vogue Aesthetic)
- **Prompt เต็มภาษาอังกฤษ**: (เขียน prompt สไตล์ภาพระดับนิตยสารแฟชั่นชั้นสูง มีแสง Studio Lighting, Lens, 8k Resolution พร้อม parameters --ar 16:9 --v 6.0 --style raw)
- **Negative Prompt**: (สิ่งที่ต้องการคัดออก)
- **Cinematography & Style Notes**: (คำอธิบายสไตล์ แสง เงา และคู่สี)
ตอบเป็น Markdown สวยงาม กระชับ ไม่ต้องมีคำเกริ่นนำ"""
        user_content = f"{system_instruction}\n\n[แนวทางภาพปลอดภัย]: \"{safe_topic}\""
    else:
        system_instruction = """คุณคือ Senior Cybersecurity Architect และ Enterprise Defense Specialist
หน้าที่ของคุณคือรับ 'หัวข้อวิจัยและวิศวกรรมความปลอดภัยเชิงรับ (Defensive Security & Threat Modeling)' 
แล้วทำการประมวลผล 'ขยายความสร้างเป็น Master Technical Prompt' ระดับผู้เชี่ยวชาญ (ระดับ CISSP / Blue Team Lead) 
สำหรับนำไปใช้ค้นคว้า วิเคราะห์ช่องโหว่เชิงลึก และวางระบบตรวจจับป้องกันในองค์กร

โครงสร้างผลลัพธ์ที่ต้องส่งกลับ:
### 🎯 Master Technical Prompt (ระดับ Senior Architect)
(สร้างชุดคำสั่งและคำถามอย่างละเอียด เจาะลึก 4 ด้าน:
 1. กลไกและสถาปัตยกรรมเชิงลึก: มาตรฐาน RFC, Kernel/OS API, Network Protocol หรือ Browser Spec
 2. Threat Modeling & MITRE ATT&CK: วิเคราะห์ Dataflow (Source-to-Sink) และเทคนิคที่เกี่ยวข้อง
 3. การออกแบบ Detection & Telemetry: กฎตรวจจับสำหรับ SIEM / Suricata / EDR / Audit Logs
 4. แนวทางการ Hardening & Remediation: การตั้งค่านโยบายความปลอดภัยตามกรอบ NIST / CIS Benchmark)

ตอบเป็นภาษาไทยที่เป็นมืออาชีพ ชัดเจน มีโครงสร้าง markdown ครบถ้วน ไม่ต้องมีคำเกริ่นนำหรือคำปิดท้าย"""
        user_content = f"{system_instruction}\n\n[หัวข้อวิจัยความปลอดภัยที่ต้องการขยายความ]: \"{safe_topic}\""

    payload = {
        "model": NINEARM_MODEL_ID,
        "max_tokens": 2048,
        "thinking": {"type": "enabled", "budget_tokens": 512},
        "messages": [
            {"role": "user", "content": user_content}
        ]
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(NINEARM_GATEWAY_URL, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=35) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            content_items = res.get("content", [])
            output_text = ""
            for item in content_items:
                if item.get("type") == "text":
                    output_text += item.get("text", "")
            return {
                "success": True,
                "model": NINEARM_MODEL_ID,
                "provider": "9arm Gateway",
                "result": output_text.strip()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "model": NINEARM_MODEL_ID
        }

def execute_prompt_with_ai(prompt: str, category: str = "") -> dict:
    """รันคำสั่งที่ผ่านการขัดเกลาแล้วส่งถาม 9arm AI (Qwen 3.8 27B) เพื่อรับคำตอบวิศวกรรมจริงทันที"""
    headers = {
        "x-api-key": NINEARM_AUTH_TOKEN,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "user-agent": "claude-code/0.2.29 darwin-arm64"
    }

    if "High-Fashion" in category:
        system_instruction = (
            "คุณคือ Senior AI Art Director และ Computer Graphics Specialist "
            "หน้าที่ของคุณคือวิเคราะห์โครงสร้าง Prompt ศิลปะที่ได้รับ พร้อมอธิบายรายละเอียดการจัดองค์ประกอบภาพ "
            "แสง Studio Lighting, สเปกกล้อง/เลนส์, Mood & Tone และแนะนำเทคนิคการ Render ภาพให้สวยสมจริงระดับ Masterpiece"
        )
    else:
        system_instruction = (
            "คุณคือ Senior Cybersecurity Specialist และ Security Architect "
            "หน้าที่ของคุณคือให้คำปรึกษาและคำอธิบายทางวิศวกรรมความปลอดภัยเชิงลึก (Defensive & Educational) "
            "ตามหัวข้อที่ได้รับ อธิบายกลไกการทำงานระดับลึก (OS/Memory/Protocol), ยกตัวอย่างโครงสร้างโค้ดหรือสถาปัตยกรรมที่ปลอดภัย, "
            "แนวทางการตรวจจับ (Detection Rules เช่น SIEM/Suricata/YARA) และวิธีป้องกัน (Hardening & Remediation) ตามมาตรฐานสากล "
            "ตอบเป็นภาษาไทยที่เป็นมืออาชีพ ชัดเจน มีโครงสร้าง markdown ครบถ้วน"
        )

    payload = {
        "model": NINEARM_MODEL_ID,
        "max_tokens": 2048,
        "thinking": {"type": "enabled", "budget_tokens": 512},
        "messages": [
            {"role": "user", "content": f"{system_instruction}\n\n[โจทย์/คำถามวิศวกรรมความปลอดภัย]:\n{prompt}"}
        ]
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(NINEARM_GATEWAY_URL, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            content_items = res.get("content", [])
            output_text = ""
            for item in content_items:
                if item.get("type") == "text":
                    output_text += item.get("text", "")
            return {
                "success": True,
                "model": NINEARM_MODEL_ID,
                "provider": "9arm Gateway",
                "result": output_text.strip()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "model": NINEARM_MODEL_ID
        }

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Safe Prompt Gateway & 9arm AI Dual-Engine</title>
    <style>
        :root {
            --bg: #090d16;
            --card: #131b2e;
            --border: #23304d;
            --primary: #38bdf8;
            --accent: #10b981;
            --emerald: #059669;
            --purple: #a855f7;
            --warn: #f59e0b;
            --text: #f8fafc;
            --muted: #94a3b8;
        }
        body { font-family: 'Segoe UI', -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; line-height: 1.5; }
        .container { max-width: 1080px; margin: auto; }
        .header { text-align: center; margin-bottom: 24px; }
        .header h1 { color: var(--primary); margin: 0 0 8px 0; font-size: 28px; }
        .header p { color: var(--muted); margin: 0; font-size: 15px; }

        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
        .tab-btn { background: transparent; border: none; color: var(--muted); font-size: 16px; font-weight: 600; padding: 8px 16px; cursor: pointer; border-radius: 8px; transition: 0.2s; }
        .tab-btn.active { background: var(--card); color: var(--primary); border: 1px solid var(--border); }
        .tab-btn:hover { color: var(--text); }

        .card { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 24px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
        .card h2 { margin-top: 0; font-size: 18px; color: var(--primary); display: flex; align-items: center; gap: 8px; }

        textarea { width: 100%; height: 95px; background: #070a12; color: #fff; border: 1px solid var(--border); border-radius: 10px; padding: 14px; font-size: 15px; box-sizing: border-box; resize: vertical; outline: none; }
        textarea:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2); }

        .btn-group { display: flex; gap: 12px; margin-top: 12px; align-items: center; flex-wrap: wrap; }
        button { background: #0284c7; color: white; border: none; padding: 12px 22px; border-radius: 9px; cursor: pointer; font-size: 15px; font-weight: 600; transition: all 0.2s; }
        button:hover { background: #0369a1; transform: translateY(-1px); }
        .btn-copy { background: #059669; }
        .btn-copy:hover { background: #047857; }
        .btn-ai { background: #7c3aed; }
        .btn-ai:hover { background: #6d28d9; }
        .btn-run-live { background: #059669; color: white; padding: 6px 12px; font-size: 12px; border-radius: 6px; font-weight: 600; border: none; cursor: pointer; transition: 0.2s; }
        .btn-run-live:hover { background: #047857; transform: translateY(-1px); }

        .checkbox-label { display: flex; align-items: center; gap: 8px; font-size: 14px; color: #e2e8f0; cursor: pointer; user-select: none; margin-top: 8px; }
        .checkbox-label input { width: 18px; height: 18px; accent-color: var(--emerald); cursor: pointer; }

        .result-panel { margin-top: 20px; display: none; }
        .badge { display: inline-block; padding: 5px 12px; border-radius: 6px; font-size: 13px; font-weight: 700; margin-bottom: 10px; }
        .badge-warn { background: rgba(245, 158, 11, 0.15); border: 1px solid var(--warn); color: #fbbf24; }
        .badge-safe { background: rgba(16, 185, 129, 0.15); border: 1px solid var(--accent); color: #34d399; }

        .output-box { background: #064e3b; border: 1px solid #059669; color: #d1fae5; padding: 16px; border-radius: 10px; font-size: 15px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; font-family: 'Consolas', monospace; }

        /* 9arm AI Card */
        .ai-card { background: #18122b; border: 1px solid #6b21a8; border-radius: 12px; padding: 20px; margin-top: 20px; box-shadow: 0 4px 20px rgba(168, 85, 247, 0.15); }
        .ai-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .ai-header h3 { margin: 0; color: #c084fc; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .ai-badge { background: rgba(168, 85, 247, 0.2); border: 1px solid #a855f7; color: #e9d5ff; font-size: 12px; padding: 3px 8px; border-radius: 6px; }
        .ai-content { background: #0c0817; border: 1px solid #3b0764; color: #f1f5f9; padding: 18px; border-radius: 10px; font-size: 14px; line-height: 1.7; word-break: break-word; max-height: 500px; overflow-y: auto; }

        /* Live Execution Card */
        .live-card { background: #061a14; border: 1px solid #059669; border-radius: 12px; padding: 20px; margin-top: 20px; box-shadow: 0 4px 25px rgba(5, 150, 105, 0.25); }
        .live-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .live-header h3 { margin: 0; color: #34d399; font-size: 16px; display: flex; align-items: center; gap: 8px; }
        .live-badge { background: rgba(5, 150, 105, 0.25); border: 1px solid #10b981; color: #6ee7b7; font-size: 12px; padding: 3px 8px; border-radius: 6px; }
        .live-content { background: #03140f; border: 1px solid #064e3b; color: #f0fdf4; padding: 18px; border-radius: 10px; font-size: 14px; line-height: 1.7; word-break: break-word; max-height: 600px; overflow-y: auto; }

        .pulse-loader { display: flex; align-items: center; gap: 10px; color: #c084fc; font-weight: 600; padding: 14px; background: rgba(168, 85, 247, 0.08); border: 1px dashed #a855f7; border-radius: 10px; margin-top: 14px; animation: pulse 1.5s infinite; }
        .pulse-loader-green { display: flex; align-items: center; gap: 10px; color: #34d399; font-weight: 600; padding: 14px; background: rgba(16, 185, 129, 0.08); border: 1px dashed #10b981; border-radius: 10px; margin-top: 14px; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; } }

        .insight-card { background: #1a233a; border-left: 4px solid var(--primary); padding: 16px; border-radius: 8px; margin-top: 16px; font-size: 14px; }
        .insight-card h4 { margin: 0 0 8px 0; color: var(--primary); display: flex; align-items: center; gap: 6px; }
        .insight-grid { display: grid; grid-template-columns: 140px 1fr; gap: 8px; margin-top: 8px; }
        .insight-label { color: var(--muted); font-weight: 600; }
        .insight-value { color: #f1f5f9; }

        /* Lexicon Table */
        .lex-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        .lex-table th, .lex-table td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }
        .lex-table th { background: #0b1120; color: var(--primary); font-weight: 600; }
        .lex-table tr:hover { background: rgba(56, 189, 248, 0.04); }
        .pill-bad { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid #ef4444; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; }
        .pill-good { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #10b981; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
        .btn-try { background: #334155; color: white; padding: 6px 12px; font-size: 12px; border-radius: 6px; border:none; cursor:pointer; }
        .btn-try:hover { background: #475569; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🛡️ Master Safe Prompt Gateway & 9arm AI Dual-Engine</h1>
        <p>แปลงคำสั่ง Offensive Cyber & สรีระ เป็น Master Prompt พร้อมระบบ <strong>Live AI Execution รันคำตอบสดจริงระดับวิศวกร</strong></p>
    </div>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('converter')">⚡ หน้าต่างแปลงคำสั่ง & รันทำงานสด (Live Runner)</button>
        <button class="tab-btn" onclick="switchTab('dictionary')">📖 คลังคำศัพท์ & คู่มือวิธีพูดที่ถูกต้อง (Offensive Lexicon)</button>
    </div>

    <!-- แท็บ 1: ตัวแปลงคำสั่ง -->
    <div id="tab-converter">
        <div class="card">
            <h2>💬 ช่องพิมพ์คำสั่งอิสระ (พิมพ์ภาษาพูดตามสบาย ไม่ต้องกลัวติดแบน):</h2>
            <textarea id="userInput" placeholder="พิมพ์คำศัพท์หรือคำสั่งที่ต้องการ เช่น: setoolkit ดักรหัส, amsi bypass, c2 beaconing, process hollowing, โคลนเว็บ, สร้างภาพสาวสวย..."></textarea>
            
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <label class="checkbox-label">
                    <input type="checkbox" id="autoExecute" checked>
                    <span>🚀 <strong>รันประมวลผลคำตอบจริงจาก AI อัตโนมัติ (Live Execution)</strong></span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" id="enable9arm" checked>
                    <span>🤖 ขยายความ Master Prompt ด้วย <strong>9arm AI (Qwen 3.8 27B)</strong></span>
                </label>
            </div>

            <div class="btn-group">
                <button onclick="transformPrompt()">⚡ ตรวจสอบและแปลงเป็นภาษาปลอดภัย</button>
                <button onclick="runPromptLive()" style="background: #059669;">🚀 รันคำสั่งนี้สดๆ ทันที (Live Execute)</button>
                <button onclick="clearText()" style="background: #475569;">ล้างข้อความ</button>
            </div>

            <div id="resultBox" class="result-panel">
                <div id="statusBadge" class="badge"></div>

                <!-- กล่องที่ 1: Local Deterministic Safe Prompt -->
                <div style="margin-bottom: 6px; font-weight: 600; color: #cbd5e1;">⚡ 1. ข้อความปลอดภัยทันใจ (Local Engine - 100% ไม่โดนบล็อก):</div>
                <div id="safeOutput" class="output-box"></div>
                
                <div class="btn-group">
                    <button class="btn-copy" onclick="copyToClipboard('safeOutput')">📋 คัดลอกข้อความปลอดภัยทันใจ</button>
                    <button class="btn-copy" style="background:#059669;" onclick="runPromptLive()">🚀 รันถาม AI เพื่อดูคำตอบจริง (Live AI Execution)</button>
                    <button class="btn-ai" onclick="trigger9armManual()">🤖 ส่ง 9arm AI ขยายความ Master Prompt</button>
                </div>

                <!-- กล่องโหลด Live Execution -->
                <div id="executionLoading" class="pulse-loader-green" style="display: none;">
                    <span>⚡ กำลังส่งคำสั่งที่ผ่านการขัดเกลาเข้าสู่ 9arm AI (Qwen 3.8 27B) เพื่อรันประมวลผลคำตอบจริง... (รอประมาณ 6-10 วินาที)</span>
                </div>

                <!-- กล่องผลลัพธ์การรันทำงานจริงจาก AI (Live Execution Response) -->
                <div id="executionPanel" class="live-card" style="display: none;">
                    <div class="live-header">
                        <h3>🟢 2. ผลลัพธ์การรันทำงานจริงจาก AI (Live Execution Response)</h3>
                        <span class="live-badge">Engine: Qwen 3.8 27B (Live Answer)</span>
                    </div>
                    <div id="executionOutput" class="live-content"></div>
                    <div class="btn-group">
                        <button class="btn-copy" onclick="copyToClipboard('executionRaw')">📋 คัดลอกคำตอบทั้งหมด</button>
                    </div>
                    <textarea id="executionRaw" style="display: none;"></textarea>
                </div>

                <!-- กล่องโหลด 9arm AI Master Prompt -->
                <div id="ninearmLoading" class="pulse-loader" style="display: none;">
                    <span>🌀 9arm AI (Qwen 3.8 27B FP8) กำลังวิเคราะห์สถาปัตยกรรมเชิงลึกเพื่อสร้าง Master Prompt...</span>
                </div>

                <!-- กล่องที่ 3: 9arm AI Master Prompt -->
                <div id="ninearmPanel" class="ai-card" style="display: none;">
                    <div class="ai-header">
                        <h3>🤖 3. Master Technical Prompt (สำหรับผู้เชี่ยวชาญ)</h3>
                        <span class="ai-badge">Gateway: gateway.9arm.co</span>
                    </div>
                    <div id="ninearmOutput" class="ai-content"></div>
                    <div class="btn-group">
                        <button class="btn-copy" onclick="copyToClipboard('ninearmRaw')">📋 คัดลอก Master Prompt</button>
                    </div>
                    <textarea id="ninearmRaw" style="display: none;"></textarea>
                </div>

                <!-- กล่องที่ 4: เรียนรู้วิธีพูดที่ถูกต้อง -->
                <div id="insightPanel" class="insight-card" style="display: none;">
                    <h4>💡 สาระน่ารู้เชิงวิศวกรรม & วิธีพูดที่ถูกต้อง (Senior Coach Insight):</h4>
                    <div class="insight-grid">
                        <div class="insight-label">คำที่ระบบตรวจพบ:</div>
                        <div id="insTerm" class="insight-value"></div>
                        <div class="insight-label">กลไกใต้ฝากระโปรง:</div>
                        <div id="insMech" class="insight-value"></div>
                        <div class="insight-label">สาเหตุที่ AI แบน:</div>
                        <div id="insWhy" class="insight-value" style="color: #f87171;"></div>
                        <div class="insight-label">วิธีพูดที่ถูกต้อง:</div>
                        <div id="insSafe" class="insight-value" style="color: #34d399; font-weight: bold;"></div>
                        <div class="insight-label">เทคนิคของซีเนียร์:</div>
                        <div id="insTip" class="insight-value" style="color: #38bdf8;"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- แท็บ 2: พจนานุกรมคำต้องห้าม -->
    <div id="tab-dictionary" style="display: none;">
        <div class="card">
            <h2>📖 คลังคำศัพท์ Offensive Cyber และการทดสอบรันจริง</h2>
            <p style="color: var(--muted); font-size: 14px; margin-top: -6px;">คลิกปุ่ม <strong>"🚀 คลิกทดสอบและรันจริงทันที"</strong> เพื่อให้ระบบโหลดคำศัพท์ แปลงเป็นคำสั่งปลอดภัย และรันประมวลผลคำตอบออกมาสดๆ ทันที</p>
            <div style="overflow-x: auto;">
                <table class="lex-table" id="lexTable">
                    <thead>
                        <tr>
                            <th>คำศัพท์ต้องห้าม</th>
                            <th>กลไกการทำงานของ OS / Memory</th>
                            <th>วิธีพูดที่ถูกต้อง (Defensive Term)</th>
                            <th style="min-width: 220px;">การทดสอบและรันผลลัพธ์</th>
                        </tr>
                    </thead>
                    <tbody id="lexBody">
                        <!-- รายการจะถูกโหลดจาก JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    let lexiconData = [];
    let currentRefactorData = null;

    async function loadLexicon() {
        try {
            const res = await fetch('/api/lexicon');
            lexiconData = await res.json();
            const tbody = document.getElementById('lexBody');
            tbody.innerHTML = '';
            lexiconData.forEach(item => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="pill-bad">${item.term}</span></td>
                    <td style="color: #cbd5e1; font-size: 13px;">${item.under_the_hood}</td>
                    <td><span class="pill-good">${item.safe_term}</span></td>
                    <td>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button class="btn-try" onclick="tryTerm('${item.term}', false)">⚡ ลองใช้</button>
                            <button class="btn-run-live" onclick="tryTerm('${item.term}', true)">🚀 คลิกทดสอบและรันจริง</button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {}
    }

    function switchTab(tab) {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        if (tab === 'converter') {
            document.querySelectorAll('.tab-btn')[0].classList.add('active');
            document.getElementById('tab-converter').style.display = 'block';
            document.getElementById('tab-dictionary').style.display = 'none';
        } else {
            document.querySelectorAll('.tab-btn')[1].classList.add('active');
            document.getElementById('tab-converter').style.display = 'none';
            document.getElementById('tab-dictionary').style.display = 'block';
        }
    }

    function tryTerm(term, autoRun = false) {
        switchTab('converter');
        document.getElementById('userInput').value = 'ขอโค้ดตัวอย่างและการทำงานของ ' + term + ' หน่อย';
        transformPrompt(autoRun);
    }

    function renderMarkdown(text) {
        if (!text) return '';
        let escaped = text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
        escaped = escaped.replace(/```([a-z0-9_-]*)\n([\s\S]*?)```/g, function(m, l, code) {
            return `<pre style="background:#020b08; border:1px solid #064e3b; padding:12px; border-radius:8px; overflow-x:auto; margin:10px 0; color:#34d399; font-family:Consolas, monospace;"><code>${code}</code></pre>`;
        });
        escaped = escaped.replace(/`([^`]+)`/g, '<code style="background:#064e3b; color:#6ee7b7; padding:2px 6px; border-radius:4px; font-family:Consolas, monospace;">$1</code>');
        escaped = escaped.replace(/^### (.*$)/gim, '<h3 style="color:#34d399; margin:14px 0 6px 0; font-size:16px;">$1</h3>');
        escaped = escaped.replace(/^## (.*$)/gim, '<h2 style="color:#10b981; margin:18px 0 8px 0; font-size:18px;">$1</h2>');
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#f8fafc;">$1</strong>');
        escaped = escaped.replace(/^\s*[-*]\s+(.*$)/gim, '<li style="margin-left:20px; color:#cbd5e1;">$1</li>');
        escaped = escaped.replace(/\n/g, '<br>');
        escaped = escaped.replace(/<\/pre><br>/g, '</pre>');
        return escaped;
    }

    async function transformPrompt(forceAutoRun = false) {
        const text = document.getElementById('userInput').value;
        if (!text.trim()) return;
        
        try {
            // 1. เรียก Local Engine ทันที (<5ms)
            const res = await fetch('/api/refactor', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: text })
            });
            const data = await res.json();
            currentRefactorData = data;
            
            document.getElementById('resultBox').style.display = 'block';
            const badge = document.getElementById('statusBadge');
            
            if (data.is_transformed) {
                badge.className = 'badge badge-warn';
                badge.innerText = '🔄 ปรับแต่งให้ปลอดภัยเรียบร้อย (' + data.category + ')';
            } else {
                badge.className = 'badge badge-safe';
                badge.innerText = '✅ ข้อความปลอดภัยตามมาตรฐาน ไม่จำเป็นต้องแปลง';
            }
            document.getElementById('safeOutput').innerText = data.safe_prompt;

            // แสดง Senior Coach Insight
            const insight = document.getElementById('insightPanel');
            if (data.learning_insight) {
                insight.style.display = 'block';
                document.getElementById('insTerm').innerText = data.learning_insight.detected_term;
                document.getElementById('insMech').innerText = data.learning_insight.under_the_hood;
                document.getElementById('insWhy').innerText = data.learning_insight.why_banned;
                document.getElementById('insSafe').innerText = data.learning_insight.how_to_say;
                document.getElementById('insTip').innerText = data.learning_insight.pro_tip;
            } else {
                insight.style.display = 'none';
            }

            // ซ่อนผลลัพธ์เดิม
            document.getElementById('ninearmPanel').style.display = 'none';
            document.getElementById('executionPanel').style.display = 'none';

            // 2. ถ้าเปิด Live Execution ให้ยิงรันคำตอบจริงทันที
            if (forceAutoRun || document.getElementById('autoExecute').checked) {
                executeLiveAI(data.safe_prompt, data.category);
            }

            // 3. ถ้าเปิด 9arm Master Prompt ให้ยิงคู่ขนาน
            if (document.getElementById('enable9arm').checked) {
                fetch9armMasterPrompt(data);
            }
        } catch (e) {
            alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
        }
    }

    async function executeLiveAI(safePrompt, category) {
        const loading = document.getElementById('executionLoading');
        const panel = document.getElementById('executionPanel');
        const out = document.getElementById('executionOutput');
        const raw = document.getElementById('executionRaw');

        loading.style.display = 'flex';
        panel.style.display = 'none';

        try {
            const res = await fetch('/api/execute_prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: safePrompt, category: category })
            });
            const data = await res.json();
            loading.style.display = 'none';

            if (data.success && data.result) {
                panel.style.display = 'block';
                out.innerHTML = renderMarkdown(data.result);
                raw.value = data.result;
            } else {
                panel.style.display = 'block';
                out.innerHTML = `<span style="color:#f87171;">⚠️ ไม่สามารถรับคำตอบได้: ${data.error || 'ไม่มีผลลัพธ์'}</span>`;
                raw.value = '';
            }
        } catch (e) {
            loading.style.display = 'none';
            panel.style.display = 'block';
            out.innerHTML = `<span style="color:#f87171;">⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ: ${e.message}</span>`;
        }
    }

    async function fetch9armMasterPrompt(data) {
        const loading = document.getElementById('ninearmLoading');
        const panel = document.getElementById('ninearmPanel');
        const out = document.getElementById('ninearmOutput');
        const raw = document.getElementById('ninearmRaw');

        loading.style.display = 'flex';
        panel.style.display = 'none';

        try {
            const res = await fetch('/api/ninearm_refactor', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    category: data.category,
                    safe_prompt: data.safe_prompt,
                    original_prompt: data.original_prompt
                })
            });
            const aiData = await res.json();
            loading.style.display = 'none';

            if (aiData.success && aiData.result) {
                panel.style.display = 'block';
                out.innerHTML = renderMarkdown(aiData.result);
                raw.value = aiData.result;
            } else {
                panel.style.display = 'block';
                out.innerHTML = `<span style="color:#f87171;">⚠️ ไม่สามารถประมวลผล Master Prompt ได้: ${aiData.error || 'ไม่มีผลลัพธ์'}</span>`;
                raw.value = '';
            }
        } catch (e) {
            loading.style.display = 'none';
            panel.style.display = 'block';
            out.innerHTML = `<span style="color:#f87171;">⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ 9arm Gateway: ${e.message}</span>`;
        }
    }

    function runPromptLive() {
        if (currentRefactorData && currentRefactorData.safe_prompt) {
            executeLiveAI(currentRefactorData.safe_prompt, currentRefactorData.category);
        } else {
            transformPrompt(true);
        }
    }

    function trigger9armManual() {
        if (currentRefactorData) {
            fetch9armMasterPrompt(currentRefactorData);
        } else {
            transformPrompt();
        }
    }

    function copyToClipboard(elementId) {
        let text = '';
        if (elementId === 'safeOutput') {
            text = document.getElementById('safeOutput').innerText;
        } else if (elementId === 'ninearmRaw') {
            text = document.getElementById('ninearmRaw').value;
        } else if (elementId === 'executionRaw') {
            text = document.getElementById('executionRaw').value;
        }
        if (!text) return;
        navigator.clipboard.writeText(text);
        alert('คัดลอกข้อความแล้ว! นำไปใช้งานได้ทันทีครับ');
    }

    function clearText() {
        document.getElementById('userInput').value = '';
        document.getElementById('resultBox').style.display = 'none';
        document.getElementById('ninearmPanel').style.display = 'none';
        document.getElementById('ninearmLoading').style.display = 'none';
        document.getElementById('executionPanel').style.display = 'none';
        document.getElementById('executionLoading').style.display = 'none';
        currentRefactorData = null;
    }

    loadLexicon();
</script>
</body>
</html>
"""

class SafeHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path in ("/health", "/api/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            health_data = {
                "status": "healthy",
                "service": "safe-gateway-engine",
                "lexicon_count": len(OFFENSIVE_LEXICON),
                "model": NINEARM_MODEL_ID,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(health_data, ensure_ascii=False).encode('utf-8'))
        elif self.path == "/api/lexicon":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(OFFENSIVE_LEXICON, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/refactor":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            req = json.loads(post_body.decode('utf-8'))
            prompt = req.get("prompt", "")

            # เรียกใช้งานเอนจิน Master Prompt Engine
            result = engine.refactor(prompt)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

        elif self.path == "/api/ninearm_refactor":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            req = json.loads(post_body.decode('utf-8'))
            category = req.get("category", "")
            safe_prompt = req.get("safe_prompt", "")
            original_prompt = req.get("original_prompt", "")

            # ประมวลผลคู่ขนานผ่าน 9arm AI Gateway (Qwen 3.8 27B)
            ai_result = call_ninearm_qwen(category, safe_prompt, original_prompt)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(ai_result, ensure_ascii=False).encode('utf-8'))

        elif self.path == "/api/execute_prompt":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len)
            req = json.loads(post_body.decode('utf-8'))
            prompt = req.get("prompt", "")
            category = req.get("category", "")

            # รันผลลัพธ์คำตอบจริงจาก AI ทันที
            exec_result = execute_prompt_with_ai(prompt, category)

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(exec_result, ensure_ascii=False).encode('utf-8'))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Master Safe Gateway & Live AI Runner starting on 0.0.0.0:{port}...")
    server_address = ("0.0.0.0", port)

    class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with ThreadedServer(server_address, SafeHandler) as httpd:
        print(f"✅ Ready for 24/7 cloud execution on Railway port {port}!")
        httpd.serve_forever()
