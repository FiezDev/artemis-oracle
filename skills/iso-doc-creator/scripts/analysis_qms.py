"""QMS analysis payload consumed by doc13/doc15/doc19.

All 19 URLs the user listed are represented. Four are SPA fallback
placeholders (car-search aliases vehicle-search; vehicle-index-preview,
vehicle-classification-review, vehicle-training-monitor currently render
the empty dashboard) — those appear in Appendix C for coverage but carry
no screenshot so section 3 is not padded with duplicate images.
"""

analysis = {
    "description": {
        "en": "QMS (Queue Management System) is the middleware that fronts the STAR Search Engine GPU cluster. Operators, analysts, and data labelers use it to run face search, person-attribute search, vehicle search, live CCTV face matching, recording-quality QA, vehicle labeling + verification, and police-intelligence casing detection — all from a single URL, qms.nttagid.com.",
        "th": "QMS (Queue Management System) คือ middleware ที่อยู่ด้านหน้าของคลัสเตอร์ GPU ของ STAR Search Engine ผู้ปฏิบัติงาน นักวิเคราะห์ และผู้ติดฉลากใช้งานเพื่อค้นหาใบหน้า ค้นหาคนตามคุณลักษณะ ค้นหายานพาหนะ ค้นหาใบหน้าจากกล้องสด ตรวจสอบคุณภาพวิดีโอ ติดฉลาก + ตรวจสอบยานพาหนะ และวิเคราะห์ casing เพื่อข่าวกรองของตำรวจ ผ่าน URL เดียวคือ qms.nttagid.com"
    },
    "frontend_intro": {
        "en": "QMS exposes fifteen documented applications behind path aliases on qms.nttagid.com. Each sub-system is presented below with a live screenshot and a short description. The four routes rendered by the SPA fallback (car-search alias, vehicle-index-preview, vehicle-classification-review, vehicle-training-monitor) are listed only in Appendix C.",
        "th": "QMS นำเสนอแอปพลิเคชันที่บันทึกไว้ 15 ตัว ผ่าน path alias บน qms.nttagid.com แต่ละระบบย่อยจะถูกอธิบายด้านล่าง พร้อมภาพหน้าจอจริงและคำอธิบายสั้น ๆ เส้นทางสี่เส้นที่ถูก SPA fallback เรนเดอร์ (alias ของ car-search, vehicle-index-preview, vehicle-classification-review และ vehicle-training-monitor) จะถูกระบุเฉพาะในภาคผนวก C เท่านั้น"
    },
    "tech_stack": [
        ("Frontend", "Core dashboards + wizards", "PHP 8.x server-rendered + vanilla JS + Tailwind CSS", "8.x"),
        ("Frontend", "Live telemetry", "Socket.IO client (Node.js worker)", "4.x"),
        ("Frontend", "Vehicle Label / Verifier UI", "Static HTML + vanilla JS + Tailwind CSS", "—"),
        ("Frontend", "Casing PoC (CBDS)", "Static HTML + JS, FAISS JS viewer", "—"),
        ("Backend", "Application runtime", "PHP-FPM (Unix socket)", "8.x"),
        ("Backend", "Realtime worker", "Node.js Socket.IO (PM2-managed)", "18.x"),
        ("Backend", "Job queue + live stats", "Redis (DB 0 jobs, DB 8 GPU stats)", "7.x"),
        ("Backend", "Catalog database", "MySQL RDS (nt_tag_id_db, qms_*) ", "8.0"),
        ("Infrastructure", "Reverse proxy", "Nginx (HTTP/2, Let's Encrypt TLS)", "1.22"),
        ("Infrastructure", "Compute", "AWS EC2 (ec2-user@13.250.112.239)", "—"),
        ("Infrastructure", "Containerisation", "Docker + docker-compose", "24.x"),
        ("ML", "GPU inference cluster", "STAR Search Engine on NVIDIA H200 (8 GPU) + H100", "CUDA 12"),
        ("ML", "Vehicle classification", "PyTorch classifier + training monitor", "2.x"),
        ("ML", "Casing detection", "YOLO11 + MobileNetV3 (576-dim) + FAISS", "—"),
        ("Storage", "Media", "Amazon S3 (vehicle-reid-dataset bucket)", "—"),
        ("Storage", "Video delivery", "Amazon CloudFront (5-min edge TTL)", "—"),
    ],
    "api_services": [
        ("API-001", "Face Search API", "/api/face-search.php", "Enqueue face-search jobs, poll queue state, list per-search result pages"),
        ("API-002", "Face Queue API", "/api/face-queue.php", "List current queue, cancel, re-run; used by both dashboard and admin tooling"),
        ("API-003", "Vehicle Type Predict", "/api/vehicle-type-predict/predict/url", "ML proxy — scores a single image URL for type/colour/make and returns JSON"),
        ("API-004", "Vehicle Index Image", "/api/v0/vehicle-index-image/", "Returns stored vehicle crops by index id"),
        ("API-005", "Vehicle Label API", "/public/vehicle-label/api/index.php", "list-batches, list-images, save-label, flag-image, stats, export-labels, export-stats"),
        ("API-006", "Vehicle Verifier API", "/vehicle-verifier/?action=data|verify|image", "Paginated verification feed, verify POST, S3 image proxy"),
        ("API-007", "Socket.IO gateway", "/socket.io/", "Upgrades to WebSocket; pushes GPU server stats and search-progress frames"),
        ("API-008", "Casing Evidence API", "/casing/api/*.php", "Returns per-entity detections, cluster groupings, and CloudFront playback URL"),
    ],
    "db_tables": [
        ("qms_gpu_servers", "Registry of GPU servers (Kaytus H200, NT H100)", "id, server_id, name, redis_key, gpu_model"),
        ("qms_vehicle_labels", "Vehicle crop catalog + human labels (~108k rows)", "id, s3_key, labeler, type, color, brand, verify_status, verified_by, verified_at"),
        ("qms_face_searches", "Face-search job ledger", "search_id, project, camera_ids, date_from, date_to, status, queued_at, completed_at"),
        ("qms_attribute_searches", "Attribute-based search jobs", "search_id, filters_json, status, queued_at, completed_at"),
        ("qms_recording_checks", "Recording-quality QA outcomes", "segment_id, camera_id, ts, status (ok/warn/critical), checked_by"),
        ("qms_casing_cases", "CBDS case lifecycle", "case_id, title, status, s3_alerts, created_at, closed_at"),
        ("qms_casing_entities", "Per-case entity + suspicion score", "entity_tid, case_id, suspicion, classification, camera_ids"),
        ("nt_tag_id_db.cameras", "Shared camera registry", "camera_id, name, location, rtsp_url, is_active"),
    ],
    "infrastructure": [
        ("Web server", "Nginx 1.22", "TLS termination + path-based routing", "Single EC2 host (13.250.112.239)"),
        ("PHP runtime", "PHP-FPM 8.x", "Serves every /*.php endpoint via Unix socket", "Docker container (qms-php)"),
        ("Realtime worker", "Node.js 18 + Socket.IO", "Pushes GPU stats + search progress", "PM2 process"),
        ("Job queue", "Redis 7 (DB 0)", "ZSET face_recognition_search:{id} drives STAR workers", "13.215.187.94:6389"),
        ("Stats store", "Redis 7 (DB 8)", "server:stats:{server_key}:current + :history:{ts}", "13.215.187.94:6389"),
        ("Relational DB", "MySQL RDS 8.0", "Catalog (qms_* tables) + shared nt_tag_id_db", "AWS RDS"),
        ("Object storage", "Amazon S3", "Vehicle crops + ML manifests + QA exports", "vehicle-reid-dataset bucket"),
        ("Video delivery", "Amazon CloudFront", "Signed delivery of MJPEG live + recorded MP4", "5-min edge TTL"),
    ],
    "external_services": [
        ("STAR Search Engine", "Internal GPU cluster (H200 + H100)", "Runs face, attribute, and vehicle inference jobs", "Redis queue (DB 0) + Socket.IO progress"),
        ("Amazon S3", "AWS", "Vehicle crop storage + manifest + exports", "SigV4 pre-signed URLs, server-side only"),
        ("Amazon CloudFront", "AWS", "Edge cache for live MJPEG + recorded video", "Signed cookie scoped to internal network"),
        ("Amazon RDS (MySQL)", "AWS", "Catalog of labels, jobs, cases, and cameras", "Server-side connection, credentialed"),
        ("Amazon EC2", "AWS", "Single-host production environment", "SSH key deploy via rsync"),
        ("Nginx + Let's Encrypt", "Open source", "TLS termination + static/PHP routing", "Certbot renewals"),
    ],
    "security": [
        ("Network isolation", "Operations VPN / internal LAN", "QMS is accessed only from trusted networks; no public login UI"),
        ("TLS", "Let's Encrypt (cc.nttagid.com cert)", "All traffic to qms.nttagid.com is HTTP/2 over TLS 1.2+"),
        ("Labeler attribution", "Local dropdown + localStorage", "Every vehicle-label write is stamped with labeler name; no password — identity is scoped to trusted intranet"),
        ("Verifier attribution", "verified_by column", "Every QC decision records verified_by and verified_at in qms_vehicle_labels"),
        ("Secrets management", "config.php (not committed) + PM2 env", "DB credentials, S3 keys, and Redis password live server-side only; .gitignored"),
        ("S3 pre-signed URLs", "SigV4 + short TTL + server proxy refresh", "Image URLs expire quickly; vehicle-verifier re-signs on demand"),
        ("Upload limits", "Nginx client_max_body_size 50M + PHP upload limits", "Guards disk and GPU queue against oversized inputs"),
        ("Audit trail", "Per-table ts columns + Redis job ledger", "Queue and label tables retain created_at, updated_at, verified_at, completed_at"),
    ],
    "test_coverage": {
        "en": "Quality assurance spans four layers: (1) functional pass — manual walkthrough of every URL in this document to confirm the page loads and the headline metrics / wizard step render; (2) GPU-queue smoke — submit one face-search and one vehicle-search per day and verify results appear in /search-result/ within SLA; (3) labeling data integrity — nightly CSV export diffed against qms_vehicle_labels counts; (4) casing pipeline regression — weekly replay of a fixed video fixture through YOLO11 + MobileNetV3 + FAISS and verification of cluster counts and suspicion score.",
        "th": "การประกันคุณภาพครอบคลุมสี่ชั้น: (1) การทดสอบฟังก์ชัน — walkthrough ทุก URL ในเอกสารนี้ด้วยมือเพื่อยืนยันว่าหน้าโหลดได้และตัวเลขหลัก/ขั้นตอน wizard แสดงผลถูกต้อง (2) smoke test ของคิว GPU — ส่งงาน face-search หนึ่งรายการและ vehicle-search หนึ่งรายการต่อวัน และตรวจสอบว่าผลลัพธ์ปรากฏใน /search-result/ ภายใน SLA (3) ความสมบูรณ์ของข้อมูลการติดฉลาก — export CSV รายคืน แล้ว diff กับจำนวนแถวใน qms_vehicle_labels (4) regression ของ pipeline casing — รัน fixture วิดีโอคงที่ผ่าน YOLO11 + MobileNetV3 + FAISS ทุกสัปดาห์ และยืนยันจำนวนคลัสเตอร์และคะแนนความน่าสงสัย"
    },
    "frontend_modules": [
        {
            "id": "dashboard",
            "title": {"en": "Face Search Queue Dashboard", "th": "แดชบอร์ดคิว Face Search"},
            "route": "/",
            "description": {
                "en": "Root landing page. Shows totals (Total / Completed / Waiting / Failed), GPU performance trends (CPU, Memory, GPU, GPU-Memory over the last 24 hours), and a Face Search Analytics panel with videos, searches, average time, frames, top cameras, and performance metrics. Data pulled from Redis DB 8 via Socket.IO.",
                "th": "หน้าแรก แสดงยอดรวม (รวม/สำเร็จ/รอ/ล้มเหลว) กราฟประสิทธิภาพ GPU (CPU Memory GPU GPU-Memory ย้อน 24 ชั่วโมง) และแผง Face Search Analytics (วิดีโอ การค้น เวลาเฉลี่ย เฟรม กล้องยอดนิยม ประสิทธิภาพ) ดึงข้อมูลจาก Redis DB 8 ผ่าน Socket.IO"
            },
            "features": {
                "en": [
                    "Live counters auto-refresh over Socket.IO",
                    "24-hour GPU trend charts (CPU / Memory / GPU / GPU Memory)",
                    "Face Search Analytics: videos, searches, avg time, frames",
                    "Top cameras leaderboard",
                    "No auth — scoped to internal network"
                ],
                "th": [
                    "ตัวเลขสดอัปเดตอัตโนมัติผ่าน Socket.IO",
                    "กราฟแนวโน้ม GPU ย้อน 24 ชม. (CPU / Memory / GPU / GPU Memory)",
                    "สถิติ Face Search: วิดีโอ การค้น เวลาเฉลี่ย เฟรม",
                    "ตารางกล้องยอดนิยม",
                    "ไม่มีการยืนยันตัวตน — จำกัดเฉพาะเครือข่ายภายใน"
                ]
            },
            "screenshot": "dashboard.png"
        },
        {
            "id": "face-search",
            "title": {"en": "Face-Based Search", "th": "ค้นหาด้วยใบหน้า"},
            "route": "/face-search/",
            "description": {
                "en": "Four-step wizard that uploads a reference face image, selects cameras and a time window, reviews, and submits a job to STAR Search Engine. JPG, PNG, WebP, BMP, and GIF supported up to 10 MB. Results are linked to /search-result/ once STAR completes the job.",
                "th": "ตัวช่วยสี่ขั้นตอนสำหรับอัปโหลดภาพใบหน้าอ้างอิง เลือกกล้องและช่วงเวลา ตรวจทานและส่งงานให้ STAR Search Engine รองรับไฟล์ JPG PNG WebP BMP และ GIF ขนาดไม่เกิน 10 MB ผลลัพธ์จะลิงก์ไปยัง /search-result/ เมื่อ STAR ประมวลผลเสร็จ"
            },
            "features": {
                "en": [
                    "Step 1: Project + upload (drag/drop supported)",
                    "Step 2: Cameras + date/time range",
                    "Step 3: Review and submit",
                    "Step 4: Job queued notification + deep link to results",
                    "Image validation (format + size + face quality tips)"
                ],
                "th": [
                    "ขั้น 1: เลือกโครงการและอัปโหลด (ลาก-วางได้)",
                    "ขั้น 2: เลือกกล้องและช่วงวัน/เวลา",
                    "ขั้น 3: ตรวจทานและส่ง",
                    "ขั้น 4: แจ้งว่ามีงานเข้าคิว พร้อมลิงก์ไปดูผล",
                    "ตรวจสอบภาพ (รูปแบบ ขนาด และคำแนะนำคุณภาพใบหน้า)"
                ]
            },
            "screenshot": "face-search.png"
        },
        {
            "id": "attributes-search",
            "title": {"en": "Attributes-Based Search", "th": "ค้นหาตามคุณลักษณะ"},
            "route": "/attributes-search/",
            "description": {
                "en": "Four-step wizard that searches CCTV for people matching selected attributes — gender, race (Asian / Caucasian / African / Other), age band (Child / Teen / Young Adult / Middle Age / Senior), and clothing details. Same cameras + date-range step as face search.",
                "th": "ตัวช่วยสี่ขั้นตอนสำหรับค้นหาคนใน CCTV ที่ตรงกับคุณลักษณะที่เลือก ได้แก่ เพศ เชื้อชาติ (Asian / Caucasian / African / Other) ช่วงอายุ (เด็ก วัยรุ่น ผู้ใหญ่ตอนต้น วัยกลาง ผู้สูงอายุ) และเสื้อผ้า ใช้ขั้นเลือกกล้องและช่วงเวลาแบบเดียวกับ face search"
            },
            "features": {
                "en": [
                    "Person Attributes: gender + race + age band",
                    "Clothing attribute chips",
                    "Must select at least one attribute",
                    "Cameras + date/time step identical to face search",
                    "Review and submit creates a STAR job"
                ],
                "th": [
                    "คุณลักษณะบุคคล: เพศ เชื้อชาติ และช่วงอายุ",
                    "ชิปคุณลักษณะของเสื้อผ้า",
                    "ต้องเลือกอย่างน้อย 1 คุณลักษณะ",
                    "ขั้นเลือกกล้องและช่วงเวลาเหมือน face search",
                    "ตรวจทานและส่งเพื่อสร้างงาน STAR"
                ]
            },
            "screenshot": "attributes-search.png"
        },
        {
            "id": "attribute-search-direct",
            "title": {"en": "Quick Attribute Search", "th": "ค้นหาคุณลักษณะแบบด่วน"},
            "route": "/attribute-search-direct/",
            "description": {
                "en": "Single-page direct lookup over a pre-indexed pool of 31k person detections (May–Aug 2025). Mixes free-text Thai/English search, clothing-type chips (T-shirt / Long-sleeve / Jacket / Dress / Pants / Shorts / Skirt / Shoes / Hat), colour chips with fuzzy-colour option, camera-id filter, and date/time range.",
                "th": "หน้าเดียวสำหรับค้นหาตรงในชุดข้อมูลการตรวจจับบุคคล 31,000 รายการ (พ.ค.–ส.ค. 2025) รวมการค้นหาข้อความทั้งไทยและอังกฤษ ชิปประเภทเสื้อผ้า (T-shirt / Long-sleeve / Jacket / Dress / Pants / Shorts / Skirt / Shoes / Hat) ชิปสีพร้อมตัวเลือก fuzzy color ตัวกรองรหัสกล้อง และช่วงวัน/เวลา"
            },
            "features": {
                "en": [
                    "Bilingual text search (Thai + English)",
                    "Clothing-type chips",
                    "Colour chips + fuzzy-colour toggle",
                    "Camera IDs comma-separated filter",
                    "Explicit date-from / date-to + time-from / time-to"
                ],
                "th": [
                    "ค้นหาข้อความสองภาษา (ไทยและอังกฤษ)",
                    "ชิปประเภทเสื้อผ้า",
                    "ชิปสี พร้อมสลับ fuzzy color",
                    "ตัวกรองรหัสกล้องคั่นด้วยเครื่องหมายจุลภาค",
                    "กำหนดวันเริ่มต้น-สิ้นสุด และเวลาเริ่มต้น-สิ้นสุด"
                ]
            },
            "screenshot": "attribute-search-direct.png"
        },
        {
            "id": "vehicle-search",
            "title": {"en": "Vehicle Search", "th": "ค้นหายานพาหนะ"},
            "route": "/vehicle-search/",
            "description": {
                "en": "Four-step wizard for vehicle lookup. Step 1 lets the user pick type (Any / Car / Motorcycle / Truck / Pickup / Taxi / Six Wheeler) and colour chips (White / Black / Silver / Red / Blue / Green / Yellow / Orange / Brown / …). Subsequent steps match the face-search wizard.",
                "th": "ตัวช่วยสี่ขั้นตอนสำหรับค้นหายานพาหนะ ขั้น 1 ให้เลือกประเภท (Any / Car / Motorcycle / Truck / Pickup / Taxi / Six Wheeler) และชิปสี (White / Black / Silver / Red / Blue / Green / Yellow / Orange / Brown / …) ขั้นต่อ ๆ มาเหมือนกับ face search"
            },
            "features": {
                "en": [
                    "Vehicle type chips (7 options)",
                    "Colour chips (10+ options)",
                    "Attributes overview side panel",
                    "Cameras + date/time step",
                    "Review and submit creates a STAR job"
                ],
                "th": [
                    "ชิปประเภทยานพาหนะ (7 ตัวเลือก)",
                    "ชิปสี (10+ ตัวเลือก)",
                    "แผงสรุปคุณลักษณะด้านข้าง",
                    "ขั้นเลือกกล้องและช่วงเวลา",
                    "ตรวจทานและส่งเพื่อสร้างงาน STAR"
                ]
            },
            "screenshot": "vehicle-search.png"
        },
        {
            "id": "recording-quality",
            "title": {"en": "Recording Quality QA", "th": "ตรวจสอบคุณภาพการบันทึก"},
            "route": "/recording-quality/",
            "description": {
                "en": "Visual QA surface for CCTV segments. The operator loads a camera + date window, runs a HEAD request for every segment to detect size/access issues, and plays each segment through an inline CloudFront player at 0.1x–4x. Counters tally OK / Warning / Critical.",
                "th": "พื้นที่ตรวจสอบวิดีโอจาก CCTV ผู้ตรวจเลือกกล้องและช่วงวัน ระบบจะส่ง HEAD request ต่อทุก segment เพื่อตรวจขนาด/การเข้าถึง และเปิดผ่าน CloudFront player ในตัวที่ความเร็ว 0.1x–4x ตัวนับจะรวมสถานะ OK / Warning / Critical"
            },
            "features": {
                "en": [
                    "Inline CloudFront player (0.1x – 4x speed)",
                    "HEAD probe for size / access errors",
                    "Flag Jitter heuristic",
                    "Per-camera segment list + OK/Warning/Critical counts",
                    "Date range + camera search"
                ],
                "th": [
                    "CloudFront player ในตัว (0.1x – 4x)",
                    "HEAD probe ตรวจขนาด/การเข้าถึง",
                    "Heuristic Flag Jitter",
                    "รายการ segment ต่อกล้องพร้อมตัวนับ OK/Warning/Critical",
                    "ช่วงวันและค้นหาชื่อกล้อง"
                ]
            },
            "screenshot": "recording-quality.png"
        },
        {
            "id": "vehicle-label",
            "title": {"en": "Vehicle Label Workflow", "th": "กระบวนการติดฉลากยานพาหนะ"},
            "route": "/vehicle-label/",
            "description": {
                "en": "Human-in-the-loop labeling tool. On first visit the app asks the labeler to pick their name (Best / S / Jame / Opal), persisted in localStorage. The labeler sees batch dashboard, camera map, and per-image workspace where they record type / colour / make; AI suggestions come from manifest.csv on S3.",
                "th": "เครื่องมือติดฉลากโดยคน เมื่อเข้าระบบครั้งแรกจะให้เลือกชื่อ labeler (Best / S / Jame / Opal) และเก็บใน localStorage ผู้ติดฉลากจะเห็น dashboard ของ batch แผนที่กล้อง และหน้าทำงานต่อภาพที่บันทึกประเภท/สี/ยี่ห้อ โดยมีคำแนะนำจาก AI จาก manifest.csv บน S3"
            },
            "features": {
                "en": [
                    "Labeler identity dropdown + localStorage persistence",
                    "Batch dashboard + camera map",
                    "Label workspace (type, colour, make)",
                    "AI suggestions from manifest.csv",
                    "Export labels (CSV) and export stats (JSON/CSV)"
                ],
                "th": [
                    "Dropdown ระบุ labeler + บันทึกใน localStorage",
                    "Dashboard batch และแผนที่กล้อง",
                    "พื้นที่ติดฉลาก (ประเภท สี ยี่ห้อ)",
                    "คำแนะนำ AI จาก manifest.csv",
                    "Export ฉลาก (CSV) และสถิติ (JSON/CSV)"
                ]
            },
            "screenshot": "vehicle-label.png"
        },
        {
            "id": "vehicle-verifier",
            "title": {"en": "Vehicle Verifier (QC)", "th": "ตัวตรวจสอบการติดฉลาก (QC)"},
            "route": "/vehicle-verifier/",
            "description": {
                "en": "Supervisor QC tool. Two-pane layout — reference images on the left, comparison panel with Human Label vs AI Prediction on the right. Keyboard workflow: Y approve / N reject / C correct / ←→ navigate. Images below 20,000 pixels in area trigger an auto-reject suggestion.",
                "th": "เครื่องมือ QC สำหรับหัวหน้างาน แบ่งเป็นสองฝั่ง — รูปอ้างอิงฝั่งซ้าย แผงเปรียบเทียบ Human Label กับ AI Prediction ฝั่งขวา ใช้คีย์บอร์ด: Y อนุมัติ / N ปฏิเสธ / C แก้ไข / ←→ เลื่อนรายการ ภาพที่พื้นที่น้อยกว่า 20,000 พิกเซลจะมีการแนะนำให้ปฏิเสธอัตโนมัติ"
            },
            "features": {
                "en": [
                    "Reference Images panel (make / model)",
                    "Human Label vs AI Prediction side-by-side",
                    "Keyboard shortcuts (Y/N/C/←→/Enter/Esc)",
                    "S3 pre-signed URL proxy (fixes mid-session expiry)",
                    "Auto-reject suggestion for tiny images"
                ],
                "th": [
                    "แผง Reference Images (ยี่ห้อ / รุ่น)",
                    "Human Label กับ AI Prediction คู่กัน",
                    "คีย์บอร์ดลัด (Y/N/C/←→/Enter/Esc)",
                    "S3 pre-signed URL proxy (แก้ URL หมดอายุกลางทาง)",
                    "แนะนำให้ปฏิเสธภาพขนาดเล็กโดยอัตโนมัติ"
                ]
            },
            "screenshot": "vehicle-verifier.png"
        },
        {
            "id": "vehicle-verifier-report",
            "title": {"en": "Verifier Accuracy Report", "th": "รายงานความแม่นยำของฉลาก"},
            "route": "/vehicle-verifier/report",
            "description": {
                "en": "Reporting tab inside the verifier. Filter by labeler, status, and match; the paginated table shows row number, image, labeler name, date, human type/colour/brand, AI type/colour/brand, score, and status. Bottom summary reports Type / Colour / Brand / Overall accuracy.",
                "th": "แท็บรายงานภายในตัว verifier กรองตามชื่อ labeler สถานะ และผลการเปรียบเทียบ ตารางแบบแบ่งหน้าแสดงลำดับ ภาพ ชื่อผู้ติดฉลาก วันที่ ประเภท/สี/ยี่ห้อของคน ประเภท/สี/ยี่ห้อของ AI คะแนน และสถานะ สรุปด้านล่างรายงานความแม่นยำของประเภท/สี/ยี่ห้อ/รวม"
            },
            "features": {
                "en": [
                    "Filters: Labeler / Status / Match",
                    "Pagination (up to 244 pages at 15/page)",
                    "Per-labeler accuracy summary (Type / Colour / Brand / Overall)",
                    "AI Accuracy Report download",
                    "Shareable URL with filters baked in"
                ],
                "th": [
                    "ตัวกรอง: Labeler / สถานะ / การเปรียบเทียบ",
                    "แบ่งหน้า (สูงสุด 244 หน้าที่ 15 รายการ/หน้า)",
                    "สรุปความแม่นยำรายคน (ประเภท / สี / ยี่ห้อ / รวม)",
                    "ดาวน์โหลดรายงาน AI Accuracy",
                    "URL แบบ shareable ที่ฝังตัวกรองไว้แล้ว"
                ]
            },
            "screenshot": "vehicle-verifier-report.png"
        },
        {
            "id": "search-result",
            "title": {"en": "Search Result Viewer", "th": "หน้าดูผลการค้นหา"},
            "route": "/search-result/?search_id=…",
            "description": {
                "en": "Shared result viewer consumed by face-search, attributes-search, and vehicle-search. Loads the ZSET at Redis key face_recognition_search:{search_id} and renders match thumbnails, camera, timestamp, and jump-to-video links. When search_id is missing it shows a warning and a back-to-dashboard button.",
                "th": "หน้าดูผลที่ใช้ร่วมกันโดย face-search, attributes-search และ vehicle-search อ่าน ZSET จากคีย์ Redis face_recognition_search:{search_id} แล้วแสดงภาพตัวอย่างผลลัพธ์ กล้อง วันที่/เวลา และลิงก์ข้ามไปยังวิดีโอ หากไม่มี search_id จะแจ้งเตือนและมีปุ่มกลับไปยังแดชบอร์ด"
            },
            "features": {
                "en": [
                    "Reads ordered results from Redis ZSET",
                    "Thumbnail grid with camera + timestamp + score",
                    "Jump-to-source-video CloudFront link",
                    "Empty / error state with clear CTA",
                    "Back to Dashboard button"
                ],
                "th": [
                    "อ่านผลเรียงลำดับจาก ZSET ของ Redis",
                    "Grid ภาพตัวอย่างพร้อมกล้อง/เวลา/คะแนน",
                    "ลิงก์ข้ามไปยังวิดีโอต้นทางผ่าน CloudFront",
                    "สถานะว่างเปล่า/ข้อผิดพลาดพร้อม CTA ชัดเจน",
                    "ปุ่มกลับไปยังแดชบอร์ด"
                ]
            },
            "screenshot": "search-result.png"
        },
        {
            "id": "live-face-search",
            "title": {"en": "Live Face Search", "th": "ค้นหาใบหน้าแบบสด"},
            "route": "/live-face-search/",
            "description": {
                "en": "Four-step wizard (Project & Upload → Select Camera → Review & Submit → Live View) for realtime face matching over a live MJPEG CCTV feed. On submit the STAR Search Engine compares incoming frames to the reference face and Socket.IO streams match bounding-boxes back to the browser.",
                "th": "ตัวช่วยสี่ขั้นตอน (เลือกโครงการและอัปโหลด → เลือกกล้อง → ตรวจทานและส่ง → Live View) สำหรับจับคู่ใบหน้าบนสตรีม MJPEG แบบสด เมื่อส่งแล้ว STAR Search Engine จะเปรียบเทียบทุกเฟรมกับภาพอ้างอิง และ Socket.IO จะส่ง bounding-box กลับมายังเบราว์เซอร์"
            },
            "features": {
                "en": [
                    "Realtime MJPEG stream with face overlays",
                    "Project selector + reference image upload",
                    "Single-camera selection step",
                    "Review step shows project + camera before submit",
                    "Live View streams STAR matches over Socket.IO"
                ],
                "th": [
                    "สตรีม MJPEG สดพร้อมซ้อนกรอบใบหน้า",
                    "เลือกโครงการและอัปโหลดภาพอ้างอิง",
                    "เลือกกล้องทีละตัวในขั้นเลือก",
                    "ขั้นตรวจทานแสดงโครงการและกล้องก่อนส่ง",
                    "Live View สตรีมผลจับคู่ STAR ผ่าน Socket.IO"
                ]
            },
            "screenshot": "live-face-search.png"
        },
        {
            "id": "casing-overview",
            "title": {"en": "Casing Detection Overview", "th": "ภาพรวม Casing Detection"},
            "route": "/casing/",
            "description": {
                "en": "CBDS PoC v0.1 dashboard. Shows cluster-tier tabs (Resident / Co-habitat / Suspect), summary cards (Residents count, Strong Fit count, Cameras, Alert Types broken down by Time Anomaly / Multi Location / Prolonged Stay / Repeated Visit), Temporal Patterns (hour-of-day distribution + day-of-week × hour heatmap, off-hours band 22:00–05:00), and a surveillance camera map.",
                "th": "แดชบอร์ด CBDS PoC v0.1 แสดงแท็บตามชั้นคลัสเตอร์ (Resident / Co-habitat / Suspect) การ์ดสรุป (จำนวน Residents, Strong Fit, กล้อง, ประเภทการแจ้งเตือน — Time Anomaly / Multi Location / Prolonged Stay / Repeated Visit) Temporal Patterns (การแจกแจงชั่วโมงต่อวัน + heatmap วัน×ชั่วโมง โดยแถบนอกเวลาทำการ 22:00–05:00) และแผนที่กล้องเฝ้าระวัง"
            },
            "features": {
                "en": [
                    "Cluster tier tabs (Resident / Co-habitat / Suspect)",
                    "Metric cards with alert-type breakdown",
                    "Hour-of-day distribution chart",
                    "Day × hour heatmap with off-hours overlay",
                    "Camera location map"
                ],
                "th": [
                    "แท็บชั้นคลัสเตอร์ (Resident / Co-habitat / Suspect)",
                    "การ์ดสรุปพร้อมการแยกประเภทการแจ้งเตือน",
                    "กราฟการแจกแจงชั่วโมงต่อวัน",
                    "Heatmap วัน×ชั่วโมง ซ้อนแถบนอกเวลาทำการ",
                    "แผนที่ตำแหน่งกล้อง"
                ]
            },
            "screenshot": "casing.png"
        },
        {
            "id": "casing-app",
            "title": {"en": "CBDS Case Workbench", "th": "ห้องทำงานคดี CBDS"},
            "route": "/casing/app.php",
            "description": {
                "en": "Case management application. Active Cases sidebar lists open investigations (Test, Gold Shop Yaowarat A, Demo Case — Dr. Cherry Meeting, Test Casing 2, Test Casing, plus a Thai-labeled case) with their review state. Selecting one opens the full case view; + New Case button creates a fresh investigation.",
                "th": "แอปพลิเคชันจัดการคดี แถบข้าง Active Cases แสดงคดีที่ยังเปิดอยู่ (Test, Gold Shop Yaowarat A, Demo Case — Dr. Cherry Meeting, Test Casing 2, Test Casing และคดีที่ตั้งชื่อเป็นภาษาไทย) พร้อมสถานะการตรวจ เลือกคดีเพื่อเปิดมุมมองเต็ม ปุ่ม + New Case ใช้สร้างคดีใหม่"
            },
            "features": {
                "en": [
                    "Active cases sidebar with status tags",
                    "New Case button",
                    "Central workspace for the selected case",
                    "Counts by S3 alerts",
                    "Quick sidebar navigation (icons)"
                ],
                "th": [
                    "แถบข้างรายการคดีที่ยังเปิดพร้อมแท็กสถานะ",
                    "ปุ่ม New Case",
                    "พื้นที่ทำงานกลางสำหรับคดีที่เลือก",
                    "นับตาม S3 alerts",
                    "ไอคอนแถบข้างเพื่อเลื่อนดูเร็ว"
                ]
            },
            "screenshot": "casing-app.png"
        },
        {
            "id": "casing-wireframe",
            "title": {"en": "CBDS UI Reference (Wireframe)", "th": "แบบร่าง UI ของ CBDS"},
            "route": "/casing/wireframe.html",
            "description": {
                "en": "Living wireframe reference for CBDS screens. SCREEN 1 (Case List / Home) shows metric strip (S1 Residents, S2 Co-habitat, S3 Suspects, Cameras, Duration, Total Sightings), S3 alert panel with View Evidence CTA, and a Surveillance Area map. Used by engineers to align implementation with the intended design.",
                "th": "แบบร่าง (wireframe) ที่ยังอัปเดตอยู่ สำหรับหน้า CBDS SCREEN 1 (Case List / Home) แสดงแถบตัวเลข (S1 Residents, S2 Co-habitat, S3 Suspects, Cameras, Duration, Total Sightings) แผงแจ้งเตือน S3 พร้อมปุ่ม View Evidence และแผนที่ Surveillance Area ใช้สำหรับให้ทีมวิศวกรรมปรับงานให้ตรงกับดีไซน์"
            },
            "features": {
                "en": [
                    "Screen-by-screen annotated wireframes",
                    "Metric strip reference",
                    "S3 alert panel pattern",
                    "View Evidence call-to-action",
                    "Surveillance Area map"
                ],
                "th": [
                    "Wireframe อธิบายทีละหน้า",
                    "อ้างอิงแถบตัวเลข",
                    "แบบแผงแจ้งเตือน S3",
                    "ปุ่ม View Evidence",
                    "แผนที่ Surveillance Area"
                ]
            },
            "screenshot": "casing-wireframe.png"
        },
        {
            "id": "casing-evidence",
            "title": {"en": "Casing Evidence — Video Analysis", "th": "หลักฐาน Casing — วิเคราะห์วิดีโอ"},
            "route": "/casing/evidence.html",
            "description": {
                "en": "Deep-dive video analysis for a single entity (e.g. TID_30310, suspicion 0.8, MULTI_LOCATION alert). Pipeline: YOLO11 person detection → MobileNetV3 576-dim embeddings → FAISS cosine clustering (> 0.85). UI shows a 10-minute detection timeline, groups detected persons by identity cluster, and plays the source video from CloudFront.",
                "th": "วิเคราะห์วิดีโอแบบเจาะลึกต่อ entity เดียว (เช่น TID_30310 ความน่าสงสัย 0.8 การแจ้งเตือน MULTI_LOCATION) pipeline: YOLO11 ตรวจจับคน → MobileNetV3 embedding 576 มิติ → FAISS cosine clustering (> 0.85) UI แสดง timeline การตรวจจับ 10 นาที จัดกลุ่มคนที่ตรวจพบตาม identity cluster และเปิดวิดีโอต้นทางจาก CloudFront"
            },
            "features": {
                "en": [
                    "YOLO11 + MobileNetV3 + FAISS pipeline",
                    "Entity header (TID, suspicion, camera, persons, identities, vector dim)",
                    "10-minute detection timeline",
                    "Identity clusters with per-cluster sighting counts",
                    "CloudFront source-video playback"
                ],
                "th": [
                    "Pipeline: YOLO11 + MobileNetV3 + FAISS",
                    "หัวข้อ entity (TID ความน่าสงสัย กล้อง จำนวนคน identity มิติเวกเตอร์)",
                    "Timeline การตรวจจับ 10 นาที",
                    "คลัสเตอร์ identity พร้อมจำนวน sighting ต่อคลัสเตอร์",
                    "เปิดวิดีโอต้นทางผ่าน CloudFront"
                ]
            },
            "screenshot": "casing-evidence.png"
        },
        {
            "id": "car-search-alias",
            "title": {"en": "Car Search (alias)", "th": "Car Search (alias)"},
            "route": "/car-search/",
            "description": {
                "en": "Legacy path; renders the same wizard as /vehicle-search/ via an Nginx alias. Kept in the route inventory because several admin deep-links (dashboard.nttagid.com) continue to embed it as an iframe.",
                "th": "เส้นทางเดิม; เรนเดอร์ wizard เดียวกับ /vehicle-search/ ผ่าน alias ของ Nginx ยังคงไว้ในรายการเส้นทางเพราะหลาย deep-link ใน admin (dashboard.nttagid.com) ยัง embed เป็น iframe อยู่"
            },
            "screenshot": ""
        },
        {
            "id": "vehicle-index-preview",
            "title": {"en": "Vehicle Index Preview (placeholder)", "th": "Vehicle Index Preview (ยังไม่เปิดใช้งาน)"},
            "route": "/vehicle-index-preview/",
            "description": {
                "en": "Reserved path. Currently resolves to the Nginx SPA fallback (empty dashboard). Planned as a per-index preview surface for the vehicle-reid pipeline.",
                "th": "เส้นทางที่จองไว้ ปัจจุบัน Nginx ส่งคืน SPA fallback (แดชบอร์ดเปล่า) วางแผนให้เป็นหน้าพรีวิวของ index ในพายป์ไลน์ vehicle-reid"
            },
            "screenshot": ""
        },
        {
            "id": "vehicle-classification-review",
            "title": {"en": "Vehicle Classification Review (placeholder)", "th": "Vehicle Classification Review (ยังไม่เปิดใช้งาน)"},
            "route": "/vehicle-classification-review/",
            "description": {
                "en": "Reserved path. Currently resolves to the Nginx SPA fallback. Planned as a review surface for borderline vehicle-classifier predictions.",
                "th": "เส้นทางที่จองไว้ ปัจจุบันเรียก SPA fallback ของ Nginx วางแผนใช้เป็นหน้าตรวจสอบผลการจำแนกรถที่คลุมเครือ"
            },
            "screenshot": ""
        },
        {
            "id": "vehicle-training-monitor",
            "title": {"en": "Vehicle Training Monitor (placeholder)", "th": "Vehicle Training Monitor (ยังไม่เปิดใช้งาน)"},
            "route": "/vehicle-training-monitor/",
            "description": {
                "en": "Reserved path. Currently resolves to the Nginx SPA fallback. Planned as a live-metrics dashboard for vehicle-classifier training jobs.",
                "th": "เส้นทางที่จองไว้ ปัจจุบันเรียก SPA fallback ของ Nginx วางแผนให้เป็นแดชบอร์ดเมตริกการเทรนนิงของ vehicle-classifier"
            },
            "screenshot": ""
        }
    ]
}
