"""RiceGuard analysis payload consumed by doc13/doc15/doc19.

Covers all five top-level URLs the user listed on riceguard.nttagid.com:
  /amcp/       → admin.riceguard.ai (riceguard-admin, Next.js + Apollo)
  /aiops/      → aiops.riceguard.ai (riceguard-aiops, Next.js + Apollo)
  /analytics/  → analytics.riceguard.ai (riceguard-analytics, Vite+React)
  /user/       → riceguard-sentinel-poc mobile PWA (SvelteKit + LINE LIFF)
  /admin/      → riceguard-sentinel-poc admin demo (SvelteKit + LINE LIFF)

Each app expands into multiple sub-routes; 30 modules are documented below.
"""

analysis = {
    "description": {
        "en": "RiceGuard is a multi-frontend agricultural IoT platform for smart rice farming in Thailand. A single GraphQL backend (Rice-Guard-API, built on Bun + Elysia) powers four web dashboards — Admin/AMCP for device management, AI-Ops for ML model operations, Analytics for regional insights, and a LINE LIFF Sentinel PoC — plus a farmer-facing Mobile PWA. IoT sensors in the field publish telemetry via an MQTT bridge, which the backend persists to MySQL, caches on Redis, routes through RabbitMQ, and feeds into pest/drought/yield AI models. All frontends share a unified GraphQL schema, JWT+LINE authentication, and the same user/farm/crop/sensor domains.",
        "th": "RiceGuard คือแพลตฟอร์มเกษตร IoT แบบหลายส่วนหน้า สำหรับการปลูกข้าวอัจฉริยะในประเทศไทย  ระบบหลังบ้าน GraphQL เดียว (Rice-Guard-API สร้างด้วย Bun + Elysia) รองรับแดชบอร์ด 4 ตัว ได้แก่ Admin/AMCP สำหรับจัดการอุปกรณ์ AI-Ops สำหรับบริหารโมเดล ML, Analytics สำหรับวิเคราะห์ระดับภูมิภาค และ LINE LIFF Sentinel PoC พร้อม Mobile PWA สำหรับเกษตรกร  เซ็นเซอร์ IoT ในแปลงนาส่งข้อมูลผ่าน MQTT Bridge เข้าสู่ระบบซึ่งเก็บใน MySQL แคชด้วย Redis กระจายงานผ่าน RabbitMQ และส่งให้โมเดล AI พยากรณ์ศัตรูพืช ภัยแล้ง และผลผลิต  ทุกส่วนหน้าใช้ schema GraphQL เดียว ใช้การยืนยันตัวตน JWT + LINE ร่วมกัน และอ้างอิงโดเมนข้อมูลเดียวกันของผู้ใช้ ฟาร์ม พืชผล และเซ็นเซอร์"
    },
    "frontend_intro": {
        "en": "RiceGuard exposes five top-level URLs under riceguard.nttagid.com which, after redirects, resolve to four production web apps and a LINE LIFF demo. Each URL is documented below as one or more modules with live screenshots, route, and feature list.",
        "th": "RiceGuard มี URL หลัก 5 เส้นทางภายใต้ riceguard.nttagid.com ซึ่งเมื่อเปลี่ยนเส้นทางจะไปยังแอปเว็บโปรดักชันสี่ตัวและ LINE LIFF หนึ่งตัว  ด้านล่างนี้คือโมดูลของแต่ละ URL พร้อมภาพหน้าจอ เส้นทาง และรายการคุณสมบัติ"
    },
    "tech_stack": [
        ("Frontend", "Admin dashboard (/amcp/)", "Next.js 14 App Router + Apollo Client + Radix UI + Tailwind", "14.x"),
        ("Frontend", "AI-Ops console (/aiops/)", "Next.js 14 + Apollo Client + Radix UI + Tailwind", "14.x"),
        ("Frontend", "Analytics dashboard (/analytics/)", "Vite + React + TanStack Query + Radix UI + Google Maps JS", "18.x"),
        ("Frontend", "Sentinel PoC (/user/, /admin/)", "SvelteKit + Tailwind + LINE LIFF SDK", "2.x"),
        ("Frontend", "Farmer mobile app", "React Native (Android) — riceguard-farmer-app", "0.74"),
        ("Backend", "GraphQL API", "Bun + Elysia + @elysiajs/graphql-yoga + @graphql-tools/schema", "Bun 1.x"),
        ("Backend", "ORM", "Drizzle ORM with drizzle-kit migrations", "0.30"),
        ("Backend", "Auth", "@elysiajs/jwt + bcrypt + LINE OAuth (LIFF)", "—"),
        ("Backend", "Queue + scheduler", "amqplib (RabbitMQ) + node-cron", "—"),
        ("Backend", "Cache / pub-sub", "ioredis (Redis 7)", "7.x"),
        ("Backend", "Object storage", "@aws-sdk/client-s3 + presigned URLs", "v3"),
        ("Backend", "Push + email", "firebase-admin + @sendgrid/mail + nodemailer", "—"),
        ("ML", "Pest detection", "CV classifier (images → pest class)", "—"),
        ("ML", "Growth stage", "CV regression / classifier", "—"),
        ("ML", "Yield prediction", "Tabular model on sensor + weather features", "—"),
        ("ML", "Pest escalation risk", "Time-series + weather → escalation probability", "—"),
        ("Infra", "Compute", "AWS EC2 (ap-southeast-7) — ec2-43-208-206-33", "—"),
        ("Infra", "Database", "MySQL 8 (Drizzle schema)", "8.0"),
        ("Infra", "IoT bridge", "riceguard-mqtt-bridge (Node.js)", "—"),
        ("Infra", "Reverse proxy + LIFF host", "Nginx fronting riceguard.nttagid.com", "—"),
    ],
    "api_services": [
        ("API-001", "GraphQL endpoint", "/graphql (port 8080)", "Single entrypoint: auth, device, farm, crop, sensor, alert, report, analytics, AI queries/mutations via resolvers per-domain"),
        ("API-002", "Auth / login", "mutation login(email, password)", "JWT bearer token issued; also callback endpoint for LINE OAuth code exchange"),
        ("API-003", "IoT telemetry", "MQTT → riceguard-mqtt-bridge → internal REST", "Ingests sensor readings and forwards to the telemetry consumer"),
        ("API-004", "Firebase push", "firebase-admin messaging", "Sends pest / drought / harvest alerts to farmer devices"),
        ("API-005", "Image upload", "GraphQL multipart (graphql-upload-minimal) + S3", "Images for pest reports, farm photos, evidence"),
        ("API-006", "Sentinel PoC admin", "/admin/trigger, /admin/state, /admin/reset (Elysia)", "Investor-demo triggers: deploy, healthy, drought, pest, harvest"),
        ("API-007", "Sentinel PoC SSE", "/events (Server-Sent Events)", "Streams state changes from API to mobile PWA in real time"),
        ("API-008", "LINE LIFF", "LIFF SDK + LINE Login", "Auth gate for /user/ and /admin/ Sentinel routes on riceguard.nttagid.com"),
    ],
    "db_tables": [
        ("users", "Platform accounts (admin, analyst, farmer, aiops)", "id, email, password_hash, role, line_user_id, created_at"),
        ("farmer_profiles", "Extended farmer data + cooperative link", "user_id, citizen_id, phone, cooperative_id, address_*"),
        ("cooperatives", "Registered cooperatives / groups", "id, name, province_code, officer_user_id"),
        ("farms", "Physical farm boundaries + owner", "id, farmer_id, name, geom, area_rai, province_code"),
        ("fields", "Sub-plots inside a farm", "id, farm_id, name, geom, current_crop_id"),
        ("crops", "Crop definitions (rice variety, planting cycle)", "id, name_en, name_th, variety_code, cycle_days"),
        ("seasons", "Per-field growing season record", "id, field_id, crop_id, planted_at, harvested_at, yield_kg"),
        ("iot_devices", "Deployed field devices", "id, serial, farm_id, firmware_version, last_seen_at"),
        ("sensors", "Sensors attached to a device", "id, device_id, type (ph, moisture, temp, humidity), unit, healthy"),
        ("telemetry_readings", "Time-series sensor values", "id, sensor_id, ts, value, quality_flag"),
        ("alerts", "Pest / drought / harvest / device alerts", "id, farm_id, type, severity, payload_json, acknowledged_at"),
        ("pest_reports", "Farmer-submitted pest sightings (image + location)", "id, farmer_id, field_id, image_s3_key, pest_code, confidence"),
        ("weather_snapshots", "Cached weather per province / field", "id, province_code, ts, temp_c, humidity, rainfall_mm"),
        ("audit_events", "Append-only audit log", "id, actor_user_id, action, target_type, target_id, at"),
    ],
    "infrastructure": [
        ("API server", "Bun + Elysia", "Single Node-compatible process, GraphQL Yoga + REST side-endpoints", "EC2 ap-southeast-7"),
        ("Database", "MySQL 8", "All domain tables, Drizzle-managed migrations", "Managed MySQL"),
        ("Cache / pub-sub", "Redis 7 (ioredis)", "GraphQL caching, SSE fan-out, DataLoader keying", "Managed Redis"),
        ("Queue", "RabbitMQ (amqplib)", "Async jobs: image processing, AI inference, push fan-out", "Managed RabbitMQ"),
        ("Object storage", "Amazon S3", "Pest photos, farm photos, harvest evidence, exports", "Presigned URLs"),
        ("Push", "Firebase Cloud Messaging (firebase-admin)", "Farmer alerts + sentinel updates", "Google Cloud"),
        ("Email", "SendGrid + SMTP (nodemailer)", "Transactional email (invitations, password reset, reports)", "SendGrid"),
        ("IoT bridge", "riceguard-mqtt-bridge", "Subscribes to MQTT broker and forwards readings to API", "Node.js"),
        ("Reverse proxy", "Nginx", "Fronts admin.riceguard.ai, aiops.riceguard.ai, analytics.riceguard.ai and riceguard.nttagid.com LIFF", "Shared Nginx host"),
    ],
    "external_services": [
        ("LINE Platform", "LINE Messaging + LIFF + Login", "User auth on Sentinel PoC and notification channel for farmers", "OAuth 2.0 + LIFF SDK"),
        ("Firebase Cloud Messaging", "Google Cloud", "Push notifications to farmer app", "firebase-admin server SDK"),
        ("Amazon S3", "AWS", "Image + evidence + exports storage", "SigV4 presigned URLs"),
        ("Amazon RDS / MySQL", "AWS", "Primary relational database", "Credentialed, VPC private"),
        ("Amazon EC2", "AWS (ap-southeast-7)", "Bun/Elysia API host", "SSH key (rice_guard.pem)"),
        ("Google Maps JS + Marker Clusterer", "Google Cloud", "Map view in Analytics dashboard", "JavaScript API key"),
        ("SendGrid", "Twilio SendGrid", "Transactional email", "API key"),
        ("Weather provider", "Third-party API (cached in weather_snapshots)", "Daily weather per province / field", "HTTP + API key"),
    ],
    "security": [
        ("Network", "HTTPS + Nginx edge", "All traffic to *.riceguard.ai and riceguard.nttagid.com is TLS 1.2+ via Let's Encrypt"),
        ("Authentication", "Email+password JWT + LINE OAuth", "JWT issued by @elysiajs/jwt; bcrypt password hashing; LINE Login gates LIFF routes"),
        ("Authorization", "Role-based at GraphQL resolver", "Roles: admin, aiops, analyst, farmer — enforced via context/RBAC module"),
        ("Secrets", ".env + server-side only", "DB/Redis/S3/Firebase credentials never shipped to clients; firebase-admin key server-side only"),
        ("Input validation", "Zod schemas + GraphQL typed inputs", "All mutations validated before hitting Drizzle"),
        ("Upload safety", "graphql-upload-minimal + S3 virus-scan policy", "Images routed to S3 only after MIME + size checks"),
        ("Audit", "audit_events table", "Sensitive admin + verifier actions are append-only logged"),
        ("Rate limiting", "Elysia middleware + LINE rate limits", "Login + push endpoints rate-limited per IP / per user"),
    ],
    "test_coverage": {
        "en": "Quality assurance across the RiceGuard platform is organized into four layers: (1) manual smoke test — every documented URL in this report is loaded after each release and the core widgets (map, charts, tables, alert banners) are verified to render with live staging data; (2) backend integration tests (bun test) — Drizzle + Elysia unit/integration suites under Rice-Guard-API/tests cover auth, iot-device, alert and analytics domains; (3) IoT/Sentinel demo replay — the sentinel PoC trigger endpoints (/admin/trigger) are replayed for Day 1 → Drought → Pest → Harvest flow and the mobile PWA is verified to receive SSE updates within 1 s; (4) AI model sanity — AI-Ops dashboard metrics (model accuracy, drift, inference latency) are tracked against a known baseline, with alerts firing when drift > 5 %.",
        "th": "การประกันคุณภาพของ RiceGuard แบ่งเป็นสี่ชั้น ได้แก่ (1) Smoke test ด้วยมือ — ทุก URL ที่มีอยู่ในรายงานนี้จะถูกเปิดหลังทุกการปล่อยรุ่น และตรวจสอบ widget หลัก (แผนที่ กราฟ ตาราง แบนเนอร์แจ้งเตือน) ว่าแสดงข้อมูลจาก staging ได้ (2) การทดสอบ integration ของฝั่ง backend (bun test) — ชุดทดสอบ Drizzle + Elysia ภายใต้ Rice-Guard-API/tests ครอบคลุม auth, iot-device, alert และ analytics (3) การเล่นสคริปต์สาธิต IoT/Sentinel — เรียก endpoint /admin/trigger เพื่อสร้างสถานการณ์ Day 1 → ภัยแล้ง → ศัตรูพืช → เก็บเกี่ยว และตรวจสอบว่า Mobile PWA รับ SSE ภายใน 1 วินาที (4) ความน่าเชื่อถือของโมเดล AI — แดชบอร์ด AI-Ops ตรวจสอบ accuracy, drift, inference latency ของโมเดลเทียบกับ baseline และแจ้งเตือนเมื่อ drift เกิน 5 %"
    },
    "frontend_modules": [
        {
            "id": "amcp-dashboard",
            "title": {"en": "AMCP — Dashboard Overview", "th": "AMCP — ภาพรวมแดชบอร์ด"},
            "route": "/amcp/dashboard",
            "description": {
                "en": "Landing page of the Agricultural Management Control Platform. Shows total farms, active IoT devices, open alerts, and today's sensor readings aggregated from the GraphQL API.",
                "th": "หน้าแรกของ Agricultural Management Control Platform แสดงจำนวนฟาร์มทั้งหมด อุปกรณ์ IoT ที่ใช้งาน การแจ้งเตือนที่ยังไม่ถูกปิด และค่าเซ็นเซอร์วันนี้ รวบรวมจาก GraphQL API"
            },
            "features": {
                "en": ["Summary KPI cards", "Recent alerts feed", "Fleet health widget", "Apollo cached queries"],
                "th": ["การ์ด KPI สรุป", "ฟีดการแจ้งเตือนล่าสุด", "วิดเจ็ตสุขภาพอุปกรณ์", "Query แคชด้วย Apollo"]
            },
            "screenshot": "amcp-dashboard.png"
        },
        {
            "id": "amcp-alerts",
            "title": {"en": "AMCP — Alerts Triage", "th": "AMCP — คัดกรองการแจ้งเตือน"},
            "route": "/amcp/dashboard/alerts",
            "description": {
                "en": "Centralised triage queue of pest, drought, device-offline, and harvest-ready alerts. Staff can filter by severity, acknowledge, and drill into the originating farm/sensor.",
                "th": "คิวกลางสำหรับคัดกรองการแจ้งเตือนเรื่องศัตรูพืช ภัยแล้ง อุปกรณ์ออฟไลน์ และพร้อมเก็บเกี่ยว เจ้าหน้าที่สามารถกรองตามความรุนแรง ยืนยันรับทราบ และเจาะลึกไปยังฟาร์ม/เซ็นเซอร์ต้นทาง"
            },
            "features": {
                "en": ["Severity filter + search", "Acknowledge / assign", "Deep-link to farm + sensor", "Resolved/pending counts"],
                "th": ["กรองตามความรุนแรงและค้นหา", "รับทราบ/มอบหมาย", "ลิงก์ไปยังฟาร์มและเซ็นเซอร์", "สถานะปิด/รอดำเนินการ"]
            },
            "screenshot": "amcp-alerts.png"
        },
        {
            "id": "amcp-cooperatives",
            "title": {"en": "AMCP — Cooperatives", "th": "AMCP — สหกรณ์"},
            "route": "/amcp/dashboard/cooperatives",
            "description": {
                "en": "Registry of agricultural cooperatives and government extension groups. Each row links to member farmers and aggregate farm metrics.",
                "th": "ทะเบียนสหกรณ์การเกษตรและกลุ่มส่งเสริมของรัฐ แต่ละรายการเชื่อมไปยังเกษตรกรสมาชิกและข้อมูลรวมของฟาร์ม"
            },
            "features": {
                "en": ["Cooperative CRUD", "Member count + region breakdown", "Officer assignment"],
                "th": ["จัดการข้อมูลสหกรณ์ (CRUD)", "จำนวนสมาชิกและกระจายตามภูมิภาค", "มอบหมายเจ้าหน้าที่"]
            },
            "screenshot": "amcp-cooperatives.png"
        },
        {
            "id": "amcp-crops",
            "title": {"en": "AMCP — Crops Catalog", "th": "AMCP — บัญชีพืชผล"},
            "route": "/amcp/dashboard/crops",
            "description": {
                "en": "Catalog of rice varieties and other crops the platform supports, including planting cycle, typical yield, and AI-model coverage.",
                "th": "บัญชีพันธุ์ข้าวและพืชอื่น ๆ ที่ระบบรองรับ ครอบคลุมรอบการปลูก ผลผลิตทั่วไป และโมเดล AI ที่รองรับ"
            },
            "features": {
                "en": ["Per-variety cycle configuration", "AI-model mapping", "Thai/English names"],
                "th": ["ตั้งค่ารอบปลูกต่อพันธุ์", "แมปโมเดล AI ต่อพันธุ์", "ชื่อไทย/อังกฤษ"]
            },
            "screenshot": "amcp-crops.png"
        },
        {
            "id": "amcp-farms",
            "title": {"en": "AMCP — Farms", "th": "AMCP — ฟาร์ม"},
            "route": "/amcp/dashboard/farms",
            "description": {
                "en": "All farms in the system with owner, area, province, and number of deployed devices. Admins can approve, flag, or merge duplicate records.",
                "th": "รายการฟาร์มทั้งหมด พร้อมเจ้าของ พื้นที่ จังหวัด และจำนวนอุปกรณ์ที่ติดตั้ง ผู้ดูแลสามารถอนุมัติ ตั้งธง หรือรวมระเบียนซ้ำได้"
            },
            "features": {
                "en": ["Search + province filter", "Device count per farm", "Bulk approve / merge"],
                "th": ["ค้นหาและกรองตามจังหวัด", "จำนวนอุปกรณ์ต่อฟาร์ม", "อนุมัติ/รวมข้อมูลเป็นกลุ่ม"]
            },
            "screenshot": "amcp-farms.png"
        },
        {
            "id": "amcp-iot-devices",
            "title": {"en": "AMCP — IoT Devices", "th": "AMCP — อุปกรณ์ IoT"},
            "route": "/amcp/dashboard/iot-devices",
            "description": {
                "en": "Fleet view of deployed sensor gateways: firmware version, last-seen timestamp, battery, and connectivity health. Pairs to the MQTT bridge ingestion layer.",
                "th": "ภาพรวม fleet ของเกตเวย์เซ็นเซอร์: รุ่นเฟิร์มแวร์ เวลาพบล่าสุด แบตเตอรี่ และสุขภาพการเชื่อมต่อ เชื่อมกับ MQTT bridge"
            },
            "features": {
                "en": ["Online/offline indicator", "Firmware drift report", "Remote reboot trigger (via API)"],
                "th": ["สถานะออนไลน์/ออฟไลน์", "รายงานเฟิร์มแวร์ไม่ตรง", "สั่งรีบูตระยะไกล (ผ่าน API)"]
            },
            "screenshot": "amcp-iot-devices.png"
        },
        {
            "id": "amcp-readings",
            "title": {"en": "AMCP — Sensor Readings", "th": "AMCP — ค่าเซ็นเซอร์"},
            "route": "/amcp/dashboard/readings",
            "description": {
                "en": "Raw time-series viewer — admins can pick a sensor and date range to inspect individual readings, useful for debugging anomalies reported by farmers.",
                "th": "หน้า inspector อนุกรมเวลาแบบดิบ — ผู้ดูแลสามารถเลือกเซ็นเซอร์และช่วงวันที่เพื่อดูค่าแต่ละจุด มีประโยชน์เมื่อ debug เหตุการณ์ผิดปกติที่เกษตรกรแจ้ง"
            },
            "features": {
                "en": ["Sensor picker + date range", "Chart + CSV export", "Quality flag filter"],
                "th": ["เลือกเซ็นเซอร์และช่วงวันที่", "กราฟและ export CSV", "กรองตาม quality flag"]
            },
            "screenshot": "amcp-readings.png"
        },
        {
            "id": "amcp-sensors",
            "title": {"en": "AMCP — Sensors", "th": "AMCP — เซ็นเซอร์"},
            "route": "/amcp/dashboard/sensors",
            "description": {
                "en": "All individual sensors (soil pH, moisture, temperature, humidity) across every device. Supports per-sensor calibration metadata and health flag.",
                "th": "รายการเซ็นเซอร์ทั้งหมด (pH ดิน ความชื้น อุณหภูมิ ความชื้นอากาศ) ทุกอุปกรณ์ รองรับ metadata การสอบเทียบและสถานะสุขภาพต่อเซ็นเซอร์"
            },
            "features": {
                "en": ["Group by device / farm", "Calibration metadata", "Healthy/unhealthy flag"],
                "th": ["จัดกลุ่มตามอุปกรณ์/ฟาร์ม", "ข้อมูลสอบเทียบ", "ธงสถานะสุขภาพ"]
            },
            "screenshot": "amcp-sensors.png"
        },
        {
            "id": "amcp-settings",
            "title": {"en": "AMCP — Platform Settings", "th": "AMCP — การตั้งค่าแพลตฟอร์ม"},
            "route": "/amcp/dashboard/settings",
            "description": {
                "en": "System-wide configuration: alert thresholds, notification channels, language defaults, and feature flags for the RiceGuard platform.",
                "th": "การตั้งค่าระดับระบบ: เกณฑ์การแจ้งเตือน ช่องทางแจ้งเตือน ภาษาเริ่มต้น และ feature flag ของ RiceGuard"
            },
            "features": {
                "en": ["Alert threshold editor", "Notification channels", "Feature flags", "Default language"],
                "th": ["ตัวแก้ไขเกณฑ์แจ้งเตือน", "ช่องทางแจ้งเตือน", "Feature flag", "ภาษาเริ่มต้น"]
            },
            "screenshot": "amcp-settings.png"
        },
        {
            "id": "amcp-users",
            "title": {"en": "AMCP — Users & Roles", "th": "AMCP — ผู้ใช้และบทบาท"},
            "route": "/amcp/dashboard/users",
            "description": {
                "en": "Platform user list with role assignment (admin, analyst, aiops, farmer). Supports invitation, role change, and suspension.",
                "th": "รายชื่อผู้ใช้ในระบบพร้อมกำหนดบทบาท (admin, analyst, aiops, farmer) รองรับการเชิญ เปลี่ยนบทบาท และระงับผู้ใช้"
            },
            "features": {
                "en": ["Invite by email", "Role change with audit", "Suspend / reactivate"],
                "th": ["เชิญด้วยอีเมล", "เปลี่ยนบทบาทพร้อมบันทึก audit", "ระงับ/เปิดใช้งาน"]
            },
            "screenshot": "amcp-users.png"
        },
        {
            "id": "aiops-dashboard",
            "title": {"en": "AI-Ops — Console Overview", "th": "AI-Ops — ภาพรวมคอนโซล"},
            "route": "/aiops/dashboard",
            "description": {
                "en": "ML operations console. Summarizes active models, recent training runs, live inference traffic, and any anomaly alerts across all RiceGuard models.",
                "th": "คอนโซลปฏิบัติการ ML สรุปโมเดลที่ใช้งาน การฝึกล่าสุด traffic inference สด และการแจ้งเตือน anomaly ของทุกโมเดลของ RiceGuard"
            },
            "features": {
                "en": ["Models online / offline", "Training-job feed", "Anomaly alerts", "Drift overview"],
                "th": ["โมเดลที่ออนไลน์/ออฟไลน์", "ฟีดงานฝึกโมเดล", "แจ้งเตือน anomaly", "ภาพรวม drift"]
            },
            "screenshot": "aiops-dashboard.png"
        },
        {
            "id": "aiops-models",
            "title": {"en": "AI-Ops — Models Registry", "th": "AI-Ops — ทะเบียนโมเดล"},
            "route": "/aiops/models",
            "description": {
                "en": "Registry of RiceGuard AI models (pest detection, growth stage, yield, pest escalation, weather). Shows version, training data, accuracy, and deployed environment.",
                "th": "ทะเบียนโมเดล AI ของ RiceGuard (ตรวจศัตรูพืช ระยะเจริญเติบโต ผลผลิต ความเสี่ยงระบาดศัตรูพืช อากาศ) พร้อมเวอร์ชัน ข้อมูลฝึก ความแม่นยำ และสภาพแวดล้อมที่ใช้งาน"
            },
            "features": {
                "en": ["Version history", "Accuracy / F1 metrics", "Deployed environment tag"],
                "th": ["ประวัติเวอร์ชัน", "เมตริก accuracy / F1", "ป้ายกำกับสภาพแวดล้อมใช้งาน"]
            },
            "screenshot": "aiops-models.png"
        },
        {
            "id": "aiops-monitoring",
            "title": {"en": "AI-Ops — Live Monitoring", "th": "AI-Ops — การตรวจสอบสด"},
            "route": "/aiops/monitoring",
            "description": {
                "en": "Live inference metrics: p50/p95 latency, error rate, requests-per-minute per model, plus data-drift and concept-drift indicators.",
                "th": "เมตริก inference สด: latency p50/p95 อัตราข้อผิดพลาด คำร้องต่อนาทีต่อโมเดล และตัวชี้วัด data-drift กับ concept-drift"
            },
            "features": {
                "en": ["Latency + throughput charts", "Drift indicators", "Per-model filter", "Alerts on threshold breach"],
                "th": ["กราฟ latency และ throughput", "ตัวชี้วัด drift", "กรองรายโมเดล", "แจ้งเตือนเมื่อเกินเกณฑ์"]
            },
            "screenshot": "aiops-monitoring.png"
        },
        {
            "id": "aiops-deployments",
            "title": {"en": "AI-Ops — Deployments", "th": "AI-Ops — การดีพลอย"},
            "route": "/aiops/deployments",
            "description": {
                "en": "History and status of model deployments per environment (staging, production). Supports rollback, promotion, and canary weight adjustment.",
                "th": "ประวัติและสถานะการดีพลอยโมเดลต่อสภาพแวดล้อม (staging, production) รองรับการย้อนเวอร์ชัน การโปรโมต และการปรับน้ำหนัก canary"
            },
            "features": {
                "en": ["Rollback to previous", "Canary weight slider", "Promotion staging → production", "Activity log"],
                "th": ["ย้อนกลับเวอร์ชันก่อนหน้า", "ปรับน้ำหนัก canary", "โปรโมต staging → production", "บันทึกกิจกรรม"]
            },
            "screenshot": "aiops-deployments.png"
        },
        {
            "id": "aiops-training",
            "title": {"en": "AI-Ops — Training Jobs", "th": "AI-Ops — งานฝึกโมเดล"},
            "route": "/aiops/training",
            "description": {
                "en": "Queue and history of training jobs — dataset used, hyperparameters, resulting metrics, and a link to the produced model version.",
                "th": "คิวและประวัติงานฝึกโมเดล — ชุดข้อมูลที่ใช้ ไฮเปอร์พารามิเตอร์ เมตริกผลลัพธ์ และลิงก์ไปยังเวอร์ชันโมเดลที่ได้"
            },
            "features": {
                "en": ["Queue pending / running / done", "Dataset + hyperparam log", "Result metrics", "One-click promote"],
                "th": ["คิว รอ/กำลังรัน/เสร็จ", "log ชุดข้อมูลและไฮเปอร์พารามิเตอร์", "เมตริกผลลัพธ์", "โปรโมตคลิกเดียว"]
            },
            "screenshot": "aiops-training.png"
        },
        {
            "id": "analytics-landing",
            "title": {"en": "Analytics — Landing", "th": "Analytics — หน้าแรก"},
            "route": "/analytics/",
            "description": {
                "en": "Entry screen of the analytics dashboard after login. Summarises regional rice-farming KPIs and quick links to the individual reports.",
                "th": "หน้าแรกของแดชบอร์ด analytics หลังเข้าสู่ระบบ สรุป KPI การปลูกข้าวระดับภูมิภาคและทางลัดไปยังรายงานแต่ละหมวด"
            },
            "features": {
                "en": ["Region-level KPI cards", "Quick links to reports", "Scheduled reports"],
                "th": ["การ์ด KPI ระดับภูมิภาค", "ทางลัดไปยังรายงาน", "รายงานตามกำหนดการ"]
            },
            "screenshot": "analytics-landing.png"
        },
        {
            "id": "analytics-map",
            "title": {"en": "Analytics — Farm Map", "th": "Analytics — แผนที่ฟาร์ม"},
            "route": "/analytics/map",
            "description": {
                "en": "Geographic map of registered farms powered by Google Maps + marker clusterer. Layers toggle between pest hotspots, drought risk, and weather stations.",
                "th": "แผนที่ภูมิศาสตร์ของฟาร์มที่ลงทะเบียน ใช้ Google Maps + marker clusterer สลับเลเยอร์ได้ระหว่าง hotspot ศัตรูพืช ความเสี่ยงภัยแล้ง และสถานีอากาศ"
            },
            "features": {
                "en": ["Google Maps + marker clusterer", "Pest / drought / weather layers", "Click-through to farm detail"],
                "th": ["Google Maps + marker clusterer", "เลเยอร์ศัตรูพืช ภัยแล้ง อากาศ", "คลิกทะลุไปยังรายละเอียดฟาร์ม"]
            },
            "screenshot": "analytics-map.png"
        },
        {
            "id": "analytics-growth",
            "title": {"en": "Analytics — Growth Stages", "th": "Analytics — ระยะการเติบโต"},
            "route": "/analytics/growth",
            "description": {
                "en": "Distribution of rice growth stages across farms, derived from the growth-ai model. Useful for forecasting harvest windows per province.",
                "th": "การกระจายตัวของระยะการเติบโตของข้าวในฟาร์มต่าง ๆ ซึ่งได้จากโมเดล growth-ai ใช้พยากรณ์ช่วงเก็บเกี่ยวต่อจังหวัด"
            },
            "features": {
                "en": ["Province filter", "Stage histogram", "Trend over time"],
                "th": ["กรองตามจังหวัด", "histogram ระยะเติบโต", "แนวโน้มตามเวลา"]
            },
            "screenshot": "analytics-growth.png"
        },
        {
            "id": "analytics-pest",
            "title": {"en": "Analytics — Pest Tracking", "th": "Analytics — ติดตามศัตรูพืช"},
            "route": "/analytics/pest",
            "description": {
                "en": "Pest incidence analysis — counts by pest type, severity, and farm. Feeds escalation-risk decisions for regional coordinators.",
                "th": "การวิเคราะห์การระบาดศัตรูพืช — นับตามชนิด ความรุนแรง และฟาร์ม ใช้ประกอบการตัดสินใจเรื่องการยกระดับเหตุของผู้ประสานงานระดับภูมิภาค"
            },
            "features": {
                "en": ["Pest-type breakdown", "Severity heatmap", "Date range filter"],
                "th": ["แจกแจงตามชนิดศัตรูพืช", "heatmap ความรุนแรง", "กรองช่วงวันที่"]
            },
            "screenshot": "analytics-pest.png"
        },
        {
            "id": "analytics-pest-escalation",
            "title": {"en": "Analytics — Pest Escalation Risk", "th": "Analytics — ความเสี่ยงระบาดศัตรูพืช"},
            "route": "/analytics/pest-escalation",
            "description": {
                "en": "Probability view of a pest incident escalating into a regional outbreak within N days. Driven by the pest-escalation-risk AI model and weather data.",
                "th": "มุมมองความน่าจะเป็นที่การระบาดของศัตรูพืชจะลุกลามเป็นระดับภูมิภาคภายใน N วัน ขับเคลื่อนโดยโมเดล pest-escalation-risk และข้อมูลอากาศ"
            },
            "features": {
                "en": ["Risk-probability gauge", "Weather overlay", "Top-5 hotspots"],
                "th": ["มาตรวัดความน่าจะเป็น", "เลเยอร์ข้อมูลอากาศ", "5 อันดับ hotspot"]
            },
            "screenshot": "analytics-pest-escalation.png"
        },
        {
            "id": "analytics-weather",
            "title": {"en": "Analytics — Weather", "th": "Analytics — อากาศ"},
            "route": "/analytics/weather",
            "description": {
                "en": "Weather overview per province / farm — temperature, humidity, rainfall — aggregated daily and compared against the seasonal baseline.",
                "th": "ภาพรวมอากาศต่อจังหวัด/ฟาร์ม — อุณหภูมิ ความชื้น ปริมาณฝน — รวมรายวันและเปรียบเทียบกับ baseline ของฤดู"
            },
            "features": {
                "en": ["Province selector", "Seasonal baseline overlay", "7-day forecast"],
                "th": ["เลือกจังหวัด", "ซ้อน baseline ของฤดู", "พยากรณ์ 7 วัน"]
            },
            "screenshot": "analytics-weather.png"
        },
        {
            "id": "analytics-yield",
            "title": {"en": "Analytics — Yield Prediction", "th": "Analytics — พยากรณ์ผลผลิต"},
            "route": "/analytics/yield",
            "description": {
                "en": "Predicted yield per farm and per province, driven by yield-ai model. Compares predicted vs. actual once harvest-report data arrives.",
                "th": "การพยากรณ์ผลผลิตต่อฟาร์มและต่อจังหวัด ใช้โมเดล yield-ai เปรียบเทียบค่าพยากรณ์กับค่าจริงเมื่อรายงานการเก็บเกี่ยวเข้ามา"
            },
            "features": {
                "en": ["Predicted vs. actual chart", "Per-farm drill-down", "Model-version badge"],
                "th": ["กราฟพยากรณ์เทียบกับจริง", "เจาะข้อมูลรายฟาร์ม", "ป้ายเวอร์ชันโมเดล"]
            },
            "screenshot": "analytics-yield.png"
        },
        {
            "id": "analytics-water",
            "title": {"en": "Analytics — Water & Irrigation", "th": "Analytics — น้ำและชลประทาน"},
            "route": "/analytics/water",
            "description": {
                "en": "Irrigation and water-level analytics — shows soil-moisture trends, canal levels, and pumping activity across the region.",
                "th": "การวิเคราะห์การชลประทานและระดับน้ำ — แสดงแนวโน้มความชื้นดิน ระดับน้ำในคลอง และกิจกรรมการสูบน้ำในภูมิภาค"
            },
            "features": {
                "en": ["Soil-moisture trend", "Canal water-level series", "Pumping hours"],
                "th": ["แนวโน้มความชื้นดิน", "ระดับน้ำในคลอง", "ชั่วโมงการสูบน้ำ"]
            },
            "screenshot": "analytics-water.png"
        },
        {
            "id": "analytics-compare",
            "title": {"en": "Analytics — Compare Farms", "th": "Analytics — เปรียบเทียบฟาร์ม"},
            "route": "/analytics/compare",
            "description": {
                "en": "Side-by-side comparison of up to four farms on the same metric (growth stage, soil pH, pest count, yield prediction).",
                "th": "เปรียบเทียบข้อมูลฟาร์มสูงสุด 4 แห่งในตัวชี้วัดเดียวกัน (ระยะการเติบโต pH ดิน จำนวนศัตรูพืช พยากรณ์ผลผลิต)"
            },
            "features": {
                "en": ["Up to 4 farms", "Metric selector", "Export PNG/CSV"],
                "th": ["สูงสุด 4 ฟาร์ม", "เลือกตัวชี้วัด", "Export PNG/CSV"]
            },
            "screenshot": "analytics-compare.png"
        },
        {
            "id": "analytics-timeseries",
            "title": {"en": "Analytics — Time-series Explorer", "th": "Analytics — สำรวจอนุกรมเวลา"},
            "route": "/analytics/timeseries",
            "description": {
                "en": "Free-form time-series explorer — pick any sensor/metric, any window, and overlay multiple series with smoothing and zoom.",
                "th": "เครื่องมือสำรวจอนุกรมเวลาแบบอิสระ — เลือกเซ็นเซอร์/ตัวชี้วัดใด ๆ ช่วงเวลาใด ๆ และซ้อนหลายชุดข้อมูลพร้อม smoothing และ zoom"
            },
            "features": {
                "en": ["Metric picker", "Overlay multiple series", "Smoothing + zoom", "Pin to dashboard"],
                "th": ["เลือกตัวชี้วัด", "ซ้อนหลายเส้น", "Smoothing + zoom", "ปักไว้บนแดชบอร์ด"]
            },
            "screenshot": "analytics-timeseries.png"
        },
        {
            "id": "analytics-sensor-analytics",
            "title": {"en": "Analytics — Sensor Analytics", "th": "Analytics — วิเคราะห์เซ็นเซอร์"},
            "route": "/analytics/sensor-analytics",
            "description": {
                "en": "Sensor-level analytics — health of each sensor, deviation from fleet baseline, and outlier detection useful to flag miscalibrated devices.",
                "th": "การวิเคราะห์ระดับเซ็นเซอร์ — สุขภาพของเซ็นเซอร์แต่ละตัว ค่าเบี่ยงเบนจาก baseline ของ fleet และการตรวจจับ outlier เพื่อระบุอุปกรณ์ที่สอบเทียบผิด"
            },
            "features": {
                "en": ["Fleet baseline comparison", "Outlier detection", "Calibration report"],
                "th": ["เปรียบเทียบกับ baseline ของ fleet", "ตรวจจับ outlier", "รายงานการสอบเทียบ"]
            },
            "screenshot": "analytics-sensor-analytics.png"
        },
        {
            "id": "analytics-prediction",
            "title": {"en": "Analytics — Prediction Workbench", "th": "Analytics — แผงพยากรณ์"},
            "route": "/analytics/prediction",
            "description": {
                "en": "Experimental what-if workbench — change inputs (weather, irrigation, planting date) and see how predicted yield or pest risk shifts.",
                "th": "แผงพยากรณ์เชิงทดลอง — เปลี่ยนอินพุต (อากาศ การให้น้ำ วันปลูก) และดูว่าพยากรณ์ผลผลิตหรือความเสี่ยงศัตรูพืชเปลี่ยนไปอย่างไร"
            },
            "features": {
                "en": ["What-if sliders", "Live model re-run", "Save scenario"],
                "th": ["เลื่อน what-if", "รันโมเดลใหม่สด", "บันทึกสถานการณ์"]
            },
            "screenshot": "analytics-prediction.png"
        },
        {
            "id": "analytics-reports",
            "title": {"en": "Analytics — Reports", "th": "Analytics — รายงาน"},
            "route": "/analytics/reports",
            "description": {
                "en": "Scheduled and ad-hoc reports — regional yield summaries, pest outbreak reports, and monthly executive PDFs emailed via SendGrid.",
                "th": "รายงานตามกำหนดและเฉพาะกิจ — สรุปผลผลิตระดับภูมิภาค รายงานการระบาดศัตรูพืช และ PDF รายเดือนส่งอีเมลผ่าน SendGrid"
            },
            "features": {
                "en": ["Scheduled + ad-hoc", "PDF + CSV export", "Email via SendGrid"],
                "th": ["ตามกำหนดและเฉพาะกิจ", "Export PDF และ CSV", "ส่งอีเมลผ่าน SendGrid"]
            },
            "screenshot": "analytics-reports.png"
        },
        {
            "id": "user-sentinel",
            "title": {"en": "Sentinel — Farmer Mobile PWA", "th": "Sentinel — Mobile PWA สำหรับเกษตรกร"},
            "route": "/user/",
            "description": {
                "en": "SvelteKit mobile PWA wrapped in a LINE LIFF. Shows live sensor gauges (soil moisture, pH, temperature, humidity), drought alerts, pest alerts, and a harvest-ready banner. Updates via Server-Sent Events from the Elysia API.",
                "th": "Mobile PWA ที่สร้างด้วย SvelteKit และห่อด้วย LINE LIFF แสดงเกจเซ็นเซอร์สด (ความชื้นดิน pH อุณหภูมิ ความชื้นอากาศ) แจ้งเตือนภัยแล้ง แจ้งเตือนศัตรูพืช และแบนเนอร์พร้อมเก็บเกี่ยว อัปเดตผ่าน Server-Sent Events จาก Elysia API"
            },
            "features": {
                "en": ["Sensor gauge grid", "Drought + pest alerts", "Harvest-ready banner", "Offline state", "LINE LIFF login"],
                "th": ["กริดเกจเซ็นเซอร์", "แจ้งเตือนภัยแล้งและศัตรูพืช", "แบนเนอร์พร้อมเก็บเกี่ยว", "สถานะออฟไลน์", "เข้าสู่ระบบด้วย LINE LIFF"]
            },
            "screenshot": "user-sentinel.png"
        },
        {
            "id": "admin-sentinel",
            "title": {"en": "Sentinel — Admin Demo Console", "th": "Sentinel — คอนโซลสาธิตสำหรับผู้ดูแล"},
            "route": "/admin/",
            "description": {
                "en": "SvelteKit admin console used to drive the Sentinel PoC investor demo. Triggers scripted scenarios — Day 1 install, Day 25 healthy, drought alert, pest detected, harvest ready — which flow through the API and update the farmer PWA in real time via SSE.",
                "th": "คอนโซลผู้ดูแลสร้างด้วย SvelteKit สำหรับขับเคลื่อนการสาธิต Sentinel PoC ให้ผู้ลงทุน มีปุ่มกดสถานการณ์ที่เขียนไว้ล่วงหน้า — Day 1 ติดตั้ง, Day 25 ปกติ, ภัยแล้ง, ตรวจพบแมลง, พร้อมเก็บเกี่ยว — ซึ่งจะไหลผ่าน API และอัปเดต Mobile PWA ของเกษตรกรผ่าน SSE แบบเรียลไทม์"
            },
            "features": {
                "en": ["Day 1 / Day 25 triggers", "Drought + pest triggers", "Harvest trigger", "Reset state", "SSE pushes to mobile"],
                "th": ["ปุ่ม Day 1 / Day 25", "ปุ่มภัยแล้งและศัตรูพืช", "ปุ่มเก็บเกี่ยว", "รีเซ็ตสถานะ", "ส่ง SSE ไปยัง Mobile"]
            },
            "screenshot": "admin-sentinel.png"
        },
    ]
}
