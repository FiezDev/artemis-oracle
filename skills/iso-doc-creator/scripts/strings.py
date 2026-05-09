"""Bilingual string table for ISO documents.

T(lang, key) returns the localized string. Missing keys fall back to English.
Keep technical terms (API, JWT, CRUD, RBAC, SSL, TLS) English in both languages.
"""

STRINGS = {
    # --- Cover page labels ---
    "cover.document_number": {"en": "Document Number", "th": "เลขที่เอกสาร"},
    "cover.version":         {"en": "Version", "th": "เวอร์ชัน"},
    "cover.date":            {"en": "Date", "th": "วันที่"},
    "cover.author":          {"en": "Author", "th": "ผู้จัดทำ"},
    "cover.status":          {"en": "Status", "th": "สถานะ"},
    "cover.classification":  {"en": "Classification", "th": "ระดับชั้นความลับ"},
    "cover.organization":    {"en": "Organization", "th": "หน่วยงาน"},
    "cover.project":         {"en": "Project", "th": "โครงการ"},
    "cover.description":     {"en": "Description", "th": "คำอธิบาย"},
    "cover.approved":        {"en": "Approved", "th": "อนุมัติแล้ว"},
    "cover.internal":        {"en": "Internal", "th": "ภายใน"},

    # --- Revision history ---
    "rev.heading":           {"en": "Revision History", "th": "ประวัติการแก้ไข"},
    "rev.version":           {"en": "Version", "th": "เวอร์ชัน"},
    "rev.date":              {"en": "Date", "th": "วันที่"},
    "rev.author":            {"en": "Author", "th": "ผู้จัดทำ"},
    "rev.changes":           {"en": "Changes", "th": "การเปลี่ยนแปลง"},
    "rev.approved_by":       {"en": "Approved By", "th": "ผู้อนุมัติ"},
    "rev.initial":           {"en": "Initial document creation", "th": "สร้างเอกสารครั้งแรก"},

    # --- TOC ---
    "toc.heading":           {"en": "Table of Contents", "th": "สารบัญ"},

    # --- Doc titles ---
    "doc13.title":           {"en": "Software Components Document", "th": "เอกสารองค์ประกอบซอฟต์แวร์"},
    "doc15.title":           {"en": "Software Design Document", "th": "เอกสารการออกแบบซอฟต์แวร์"},
    "doc15.subtitle":        {"en": "Web Application", "th": "เว็บแอปพลิเคชัน"},
    "doc19.title":           {"en": "Test Report", "th": "รายงานผลการทดสอบ"},

    # --- Common section headings ---
    "sec.introduction":      {"en": "Introduction", "th": "บทนำ"},
    "sec.purpose":           {"en": "Purpose", "th": "วัตถุประสงค์"},
    "sec.scope":             {"en": "Scope", "th": "ขอบเขต"},
    "sec.definitions":       {"en": "Definitions", "th": "นิยามศัพท์"},
    "sec.references":        {"en": "References", "th": "เอกสารอ้างอิง"},
    "sec.overview":          {"en": "Overview", "th": "ภาพรวม"},
    "sec.system_overview":   {"en": "System Overview", "th": "ภาพรวมระบบ"},
    "sec.tech_stack":        {"en": "Technology Stack", "th": "เทคโนโลยีที่ใช้"},
    "sec.architecture":      {"en": "System Architecture", "th": "สถาปัตยกรรมระบบ"},
    "sec.frontend":          {"en": "Frontend Components", "th": "องค์ประกอบส่วนหน้า (Frontend)"},
    "sec.backend":           {"en": "Backend Components", "th": "องค์ประกอบส่วนหลัง (Backend)"},
    "sec.database":          {"en": "Database Components", "th": "องค์ประกอบฐานข้อมูล"},
    "sec.infrastructure":    {"en": "Infrastructure Components", "th": "องค์ประกอบโครงสร้างพื้นฐาน"},
    "sec.external":          {"en": "External Services", "th": "บริการภายนอก"},
    "sec.security":          {"en": "Security Components", "th": "องค์ประกอบด้านความปลอดภัย"},
    "sec.api_services":      {"en": "API Services", "th": "บริการ API"},
    "sec.db_tables":         {"en": "Database Tables", "th": "ตารางฐานข้อมูล"},
    "sec.module_design":     {"en": "Module Design", "th": "การออกแบบโมดูล"},
    "sec.data_flow":         {"en": "Data Flow Diagrams", "th": "แผนภาพการไหลของข้อมูล"},
    "sec.ui_design":         {"en": "User Interface Design", "th": "การออกแบบส่วนติดต่อผู้ใช้"},
    "sec.security_design":   {"en": "Security Design", "th": "การออกแบบด้านความปลอดภัย"},
    "sec.api_reference":     {"en": "API Reference", "th": "เอกสารอ้างอิง API"},
    "sec.test_summary":      {"en": "Test Summary", "th": "สรุปการทดสอบ"},
    "sec.test_results":      {"en": "Test Results", "th": "ผลการทดสอบ"},
    "sec.evaluation":        {"en": "Evaluation", "th": "การประเมิน"},
    "sec.signoff":           {"en": "Sign-Off", "th": "การลงนาม"},

    # --- Appendix ---
    "appendix.a":            {"en": "Appendix A: System Screenshots", "th": "ภาคผนวก ก: ภาพหน้าจอระบบ"},
    "appendix.b":            {"en": "Appendix B: Flow Diagrams", "th": "ภาคผนวก ข: แผนภาพกระบวนการ"},
    "appendix.c":            {"en": "Appendix C: Complete Route Inventory", "th": "ภาคผนวก ค: รายการเส้นทางทั้งหมด"},

    # --- Common phrases ---
    "phrase.key_features":   {"en": "Key features:", "th": "คุณสมบัติหลัก:"},
    "phrase.route":          {"en": "Route", "th": "เส้นทาง"},
    "phrase.module_id":      {"en": "Module ID", "th": "รหัสโมดูล"},
    "phrase.description":    {"en": "Description", "th": "คำอธิบาย"},
    "phrase.id":             {"en": "ID", "th": "รหัส"},
    "phrase.name":           {"en": "Name", "th": "ชื่อ"},
    "phrase.service":        {"en": "Service", "th": "บริการ"},
    "phrase.base_path":      {"en": "Base Path", "th": "เส้นทางหลัก"},
    "phrase.layer":          {"en": "Layer", "th": "เลเยอร์"},
    "phrase.component":      {"en": "Component", "th": "องค์ประกอบ"},
    "phrase.technology":     {"en": "Technology", "th": "เทคโนโลยี"},
    "phrase.version_col":    {"en": "Version", "th": "เวอร์ชัน"},
    "phrase.table":          {"en": "Table", "th": "ตาราง"},
    "phrase.key_fields":     {"en": "Key Fields", "th": "ฟิลด์หลัก"},
    "phrase.purpose":        {"en": "Purpose", "th": "วัตถุประสงค์"},
    "phrase.deployment":     {"en": "Deployment", "th": "การติดตั้ง"},
    "phrase.provider":       {"en": "Provider", "th": "ผู้ให้บริการ"},
    "phrase.integration":    {"en": "Integration", "th": "การเชื่อมต่อ"},
    "phrase.mechanism":      {"en": "Mechanism", "th": "กลไก"},
    "phrase.role":           {"en": "Role", "th": "บทบาท"},
    "phrase.permissions":    {"en": "Permissions", "th": "สิทธิ์การใช้งาน"},
    "phrase.access_level":   {"en": "Access Level", "th": "ระดับการเข้าถึง"},
    "phrase.endpoint":       {"en": "Endpoint", "th": "Endpoint"},
    "phrase.methods":        {"en": "Methods", "th": "เมธอด"},
    "phrase.fig":            {"en": "Figure", "th": "รูปที่"},

    # --- Doc13-specific bodies ---
    "doc13.intro.purpose": {
        "en": ("This document provides a visual inventory of all software components in the {project}. "
               "Each component is shown with a screenshot and a description of its purpose and functionality. "
               "This serves as a reference for developers, QA, and stakeholders to understand what the system contains."),
        "th": ("เอกสารนี้แสดงรายการองค์ประกอบซอฟต์แวร์ทั้งหมดของ {project} ในรูปแบบที่เห็นได้ด้วยตา "
               "แต่ละองค์ประกอบจะแสดงด้วยภาพหน้าจอพร้อมคำอธิบายวัตถุประสงค์และการทำงาน "
               "เพื่อให้นักพัฒนา ทีม QA และผู้มีส่วนได้ส่วนเสียเข้าใจสิ่งที่ระบบประกอบด้วย"),
    },
    "doc13.intro.scope.heading": {
        "en": "This document covers every user-facing page and major backend service:",
        "th": "เอกสารนี้ครอบคลุมทุกหน้าจอที่ผู้ใช้เห็นและบริการฝั่งเซิร์ฟเวอร์หลัก:",
    },
    "doc13.intro.scope.items": {
        "en": [
            "All frontend pages with screenshots",
            "All backend API service groups",
            "Database tables and their purpose",
            "Infrastructure and external services",
        ],
        "th": [
            "ทุกหน้าจอฝั่ง Frontend พร้อมภาพหน้าจอ",
            "กลุ่มบริการ API ฝั่ง Backend ทั้งหมด",
            "ตารางฐานข้อมูลและวัตถุประสงค์",
            "โครงสร้างพื้นฐานและบริการภายนอก",
        ],
    },
    "doc13.appendix_c.intro": {
        "en": ("The following table lists every route discovered from the frontend application. "
               "Each route has a matching screenshot in the appendix above. "
               "Dynamic routes (marked ✓) were captured by opening the list page and clicking the first record."),
        "th": ("ตารางต่อไปนี้แสดงทุกเส้นทาง (route) ที่ตรวจพบในแอปพลิเคชันฝั่งหน้า "
               "แต่ละเส้นทางมีภาพหน้าจอประกอบในภาคผนวกด้านบน "
               "เส้นทางแบบไดนามิก (เครื่องหมาย ✓) ถูกถ่ายภาพโดยเปิดหน้ารายการและคลิกข้อมูลแถวแรก"),
    },
    "phrase.dynamic_col":   {"en": "Dynamic", "th": "ไดนามิก"},

    # --- Doc15 section headings ---
    "doc15.sec.1":           {"en": "1. Introduction", "th": "1. บทนำ"},
    "doc15.sec.1.1":         {"en": "1.1 Purpose", "th": "1.1 วัตถุประสงค์"},
    "doc15.sec.1.2":         {"en": "1.2 Scope", "th": "1.2 ขอบเขต"},
    "doc15.sec.1.3":         {"en": "1.3 Definitions", "th": "1.3 นิยามศัพท์"},
    "doc15.sec.1.4":         {"en": "1.4 References", "th": "1.4 เอกสารอ้างอิง"},
    "doc15.sec.2":           {"en": "2. System Architecture", "th": "2. สถาปัตยกรรมระบบ"},
    "doc15.sec.2.1":         {"en": "2.1 High-Level Architecture", "th": "2.1 สถาปัตยกรรมระดับสูง"},
    "doc15.sec.2.2":         {"en": "2.2 Deployment Architecture", "th": "2.2 สถาปัตยกรรมการติดตั้ง"},
    "doc15.sec.2.3":         {"en": "2.3 Technology Stack", "th": "2.3 เทคโนโลยีที่ใช้"},
    "doc15.sec.3":           {"en": "3. Authentication & Authorization Design",
                               "th": "3. การออกแบบการยืนยันตัวตนและการอนุญาตสิทธิ์"},
    "doc15.sec.3.1":         {"en": "3.1 Authorization Model (RBAC)",
                               "th": "3.1 แบบจำลองการอนุญาตสิทธิ์ (RBAC)"},
    "doc15.sec.4":           {"en": "4. Module Design", "th": "4. การออกแบบโมดูล"},
    "doc15.sec.5":           {"en": "5. Data Flow Diagrams", "th": "5. แผนภาพการไหลของข้อมูล"},
    "doc15.sec.6":           {"en": "6. User Interface Design", "th": "6. การออกแบบส่วนติดต่อผู้ใช้"},
    "doc15.sec.6.1":         {"en": "6.1 Design Principles", "th": "6.1 หลักการออกแบบ"},
    "doc15.sec.6.2":         {"en": "6.2 Navigation Structure", "th": "6.2 โครงสร้างการนำทาง"},
    "doc15.sec.7":           {"en": "7. Security Design", "th": "7. การออกแบบด้านความปลอดภัย"},
    "doc15.sec.7.1":         {"en": "7.1 Authentication", "th": "7.1 การยืนยันตัวตน"},
    "doc15.sec.7.2":         {"en": "7.2 Authorization (RBAC)", "th": "7.2 การอนุญาตสิทธิ์ (RBAC)"},
    "doc15.sec.7.3":         {"en": "7.3 Data Protection", "th": "7.3 การคุ้มครองข้อมูล"},
    "doc15.sec.8":           {"en": "8. API Reference", "th": "8. เอกสารอ้างอิง API"},
    "doc15.sec.9":           {"en": "9. Database Design", "th": "9. การออกแบบฐานข้อมูล"},
    "doc15.sec.9.1":         {"en": "9.1 Entity Relationship Diagram",
                               "th": "9.1 แผนภาพความสัมพันธ์ของเอนทิตี"},
    "doc15.sec.9.2":         {"en": "9.2 Schema Details", "th": "9.2 รายละเอียดโครงสร้างข้อมูล"},
    "doc15.sec.10":          {"en": "10. Integration Design", "th": "10. การออกแบบการเชื่อมต่อ"},
    "doc15.sec.appendix_b":  {"en": "Appendix B: All Architecture Diagrams",
                               "th": "ภาคผนวก ข: แผนภาพสถาปัตยกรรมทั้งหมด"},

    # --- Doc15 figure captions ---
    "doc15.fig.2.1":         {"en": "Figure 2.1: High-Level System Architecture",
                               "th": "รูปที่ 2.1: สถาปัตยกรรมระบบระดับสูง"},
    "doc15.fig.2.2":         {"en": "Figure 2.2: Deployment Architecture",
                               "th": "รูปที่ 2.2: สถาปัตยกรรมการติดตั้ง"},
    "doc15.fig.3.1":         {"en": "Figure 3.1: Authentication Flow",
                               "th": "รูปที่ 3.1: ลำดับการยืนยันตัวตน"},
    "doc15.fig.5.1":         {"en": "Figure 5.1: Overall Data Flow",
                               "th": "รูปที่ 5.1: การไหลของข้อมูลโดยรวม"},
    "doc15.fig.9.1":         {"en": "Figure 9.1: Entity Relationship Diagram",
                               "th": "รูปที่ 9.1: แผนภาพความสัมพันธ์ของเอนทิตี"},

    # --- Doc15 default table headers ---
    "doc15.th.term":         {"en": "Term", "th": "คำศัพท์"},
    "doc15.th.definition":   {"en": "Definition", "th": "ความหมาย"},
    "doc15.th.document":     {"en": "Document", "th": "เอกสาร"},
    "doc15.th.number":       {"en": "Number", "th": "เลขที่"},
    "doc15.th.port":         {"en": "Port", "th": "พอร์ต"},
    "doc15.th.container":    {"en": "Container/Service", "th": "คอนเทนเนอร์/บริการ"},
    "doc15.th.section":      {"en": "Section", "th": "ส่วน"},
    "doc15.th.columns":      {"en": "Columns", "th": "คอลัมน์"},
    "doc15.th.relationships": {"en": "Relationships", "th": "ความสัมพันธ์"},

    # --- Doc15-specific bodies ---
    "doc15.intro.purpose": {
        "en": ("This Software Design Document (SDD) provides the complete technical design specification "
               "for the {project}. It covers system architecture, module design, data flows, database schema, "
               "API design, security design, and integration architecture. "
               "This document is intended for developers, architects, and technical reviewers."),
        "th": ("เอกสารการออกแบบซอฟต์แวร์ (SDD) ฉบับนี้ให้รายละเอียดข้อกำหนดทางเทคนิคทั้งหมดของระบบ {project} "
               "ครอบคลุมสถาปัตยกรรมระบบ การออกแบบโมดูล การไหลของข้อมูล โครงสร้างฐานข้อมูล การออกแบบ API "
               "การออกแบบด้านความปลอดภัย และสถาปัตยกรรมการเชื่อมต่อกับระบบภายนอก "
               "เอกสารนี้จัดทำขึ้นสำหรับนักพัฒนา สถาปนิกระบบ และผู้ทบทวนทางเทคนิค"),
    },
    "doc15.intro.scope": {
        "en": ("This document covers the complete technical design of the web application including "
               "frontend architecture, backend API design, database schema, external integrations, "
               "and security architecture."),
        "th": ("เอกสารนี้ครอบคลุมการออกแบบทางเทคนิคทั้งหมดของเว็บแอปพลิเคชัน ได้แก่ "
               "สถาปัตยกรรมฝั่งหน้า การออกแบบ API ฝั่งหลัง โครงสร้างฐานข้อมูล "
               "การเชื่อมต่อบริการภายนอก และสถาปัตยกรรมด้านความปลอดภัย"),
    },
    "doc15.module_design.intro": {
        "en": ("This section details the design of each system module with flow diagrams "
               "showing the internal logic and data flow."),
        "th": ("ส่วนนี้อธิบายการออกแบบของแต่ละโมดูลในระบบ พร้อมแผนภาพการไหลของข้อมูล "
               "แสดงตรรกะภายในและลำดับการทำงาน"),
    },
    "phrase.section_tbd": {
        "en": "Deferred — to be completed by the project team before final sign-off.",
        "th": "รอการจัดทำ โดยทีมงานโครงการจะดำเนินการก่อนการอนุมัติขั้นสุดท้าย",
    },

    # --- Substantive section defaults (shown when no project-specific data is configured) ---
    # Doc 13 defaults
    "default.tech_stack": {
        "en": ("The system is built on a modern web stack: a TypeScript-based front-end rendered through a "
               "component framework, a RESTful HTTP back-end exposing JSON services, a relational database as the "
               "system of record, and containerised infrastructure for reproducible deployment. The authoritative "
               "list of libraries and versions is maintained in the repository manifest files "
               "(package.json, pyproject.toml, go.mod, Dockerfile, docker-compose.yml) which the build pipeline "
               "consumes on every release."),
        "th": ("ระบบถูกสร้างบนชุดเทคโนโลยีเว็บสมัยใหม่ ประกอบด้วยส่วนติดต่อผู้ใช้ฝั่งหน้าซึ่งพัฒนาด้วย TypeScript ผ่านเฟรมเวิร์กเชิงคอมโพเนนต์ "
               "บริการฝั่งหลังแบบ REST/HTTP ที่ให้บริการข้อมูล JSON ฐานข้อมูลเชิงสัมพันธ์ในฐานะฐานข้อมูลหลักของระบบ "
               "และโครงสร้างพื้นฐานแบบคอนเทนเนอร์เพื่อให้การติดตั้งทำซ้ำได้ "
               "รายการไลบรารีและเวอร์ชันอย่างเป็นทางการถูกบันทึกไว้ในไฟล์ประกาศของโครงการ "
               "(package.json, pyproject.toml, go.mod, Dockerfile, docker-compose.yml) ซึ่ง build pipeline ใช้ในทุกการปล่อยเวอร์ชัน"),
    },
    "default.api_services": {
        "en": ("The back-end is organised into REST service groups, each responsible for a distinct domain area: "
               "authentication and session management, user and role administration, the core business entities "
               "managed by the application, reference data lookups, and reporting. Every protected endpoint requires "
               "an authenticated session and enforces role-based authorisation before returning data."),
        "th": ("ฝั่งหลังของระบบถูกจัดกลุ่มเป็นบริการ REST แยกตามโดเมน ได้แก่ การยืนยันตัวตนและจัดการเซสชัน "
               "การบริหารจัดการผู้ใช้และบทบาท กลุ่มข้อมูลธุรกิจหลักที่แอปพลิเคชันดูแล ข้อมูลอ้างอิงสำหรับค้นหา และการออกรายงาน "
               "ทุก endpoint ที่ต้องการสิทธิ์จะต้องผ่านการยืนยันตัวตนและการตรวจสอบสิทธิ์ตามบทบาท (RBAC) ก่อนจึงจะคืนข้อมูลได้"),
    },
    "default.db_tables": {
        "en": ("The relational schema groups tables by domain: identity (users, roles, sessions), core business "
               "entities managed through the main workflows, supporting reference data, and audit/log tables that "
               "capture every write for compliance evidence. Foreign keys enforce referential integrity and cascade "
               "rules follow the deletion policy documented per entity."),
        "th": ("โครงสร้างฐานข้อมูลเชิงสัมพันธ์ถูกจัดกลุ่มตามโดเมน ได้แก่ ข้อมูลผู้ใช้ (users, roles, sessions) "
               "ข้อมูลธุรกิจหลักที่แอปพลิเคชันดูแลผ่านลำดับงานหลัก ข้อมูลอ้างอิง และตาราง audit/log "
               "ที่บันทึกการเขียนทุกครั้งเพื่อเป็นหลักฐานตามข้อกำหนด "
               "Foreign key บังคับใช้ความถูกต้องของความสัมพันธ์ข้อมูล และกฎการ cascade เป็นไปตามนโยบายการลบข้อมูลที่กำหนดต่อเอนทิตี"),
    },
    "default.infrastructure": {
        "en": ("The system runs on containerised infrastructure. The front-end is delivered as a static build behind "
               "a reverse proxy, the back-end API runs in its own container with horizontal-scaling support, the "
               "database is provisioned as a managed or containerised instance with scheduled backups, and "
               "observability is provided via centralised logging and metrics exposed to the operations team."),
        "th": ("ระบบทำงานบนโครงสร้างพื้นฐานแบบคอนเทนเนอร์ ฝั่งหน้าจอเผยแพร่ในรูปแบบไฟล์สถิต (static build) "
               "ด้านหลัง reverse proxy บริการ API ฝั่งหลังทำงานในคอนเทนเนอร์ของตนเองและรองรับการขยายตัวแบบแนวนอน "
               "ฐานข้อมูลถูกจัดเตรียมในรูปแบบ managed service หรือคอนเทนเนอร์พร้อมการสำรองข้อมูลตามกำหนดการ "
               "และระบบตรวจสอบ (observability) ให้บริการผ่านระบบ logging และ metrics ที่รวมศูนย์เพื่อให้ทีมปฏิบัติการเข้าถึงได้"),
    },
    "default.external_services": {
        "en": ("The system integrates with third-party services through documented, versioned interfaces. Each "
               "integration uses authenticated credentials held in the platform secret store, enforces request "
               "timeouts and retries, and logs every inbound and outbound call for traceability and incident review."),
        "th": ("ระบบเชื่อมต่อกับบริการภายนอกผ่านอินเทอร์เฟซที่มีเอกสารและระบุเวอร์ชันชัดเจน "
               "ทุกการเชื่อมต่อใช้ข้อมูลประจำตัวที่จัดเก็บอยู่ในที่เก็บข้อมูลลับของแพลตฟอร์ม บังคับใช้ timeout และการ retry "
               "และบันทึกทุกการเรียกทั้งขาเข้าและขาออกเพื่อให้ติดตามย้อนกลับและตรวจสอบเหตุการณ์ได้"),
    },
    "default.security": {
        "en": ("Security controls span the full stack: TLS on every external interface, bcrypt or argon2 password "
               "hashing, signed and scoped session tokens with documented expiry, role-based authorisation on every "
               "protected endpoint, input validation and output encoding to prevent injection and cross-site scripting, "
               "CSRF protection on browser-mediated state changes, and audit logging of privileged operations."),
        "th": ("มาตรการความปลอดภัยครอบคลุมทุกชั้นของระบบ ได้แก่ TLS บนทุกอินเทอร์เฟซภายนอก "
               "การเข้ารหัสรหัสผ่านด้วย bcrypt หรือ argon2 โทเค็นเซสชันที่ลงนามและมีขอบเขตพร้อมกำหนดเวลาหมดอายุชัดเจน "
               "การอนุญาตสิทธิ์ตามบทบาท (RBAC) บนทุก endpoint ที่ต้องป้องกัน การตรวจสอบข้อมูลเข้าและการเข้ารหัสข้อมูลออก "
               "เพื่อป้องกันการโจมตีแบบ injection และ XSS การป้องกัน CSRF สำหรับการเปลี่ยนแปลงข้อมูลผ่านเบราว์เซอร์ "
               "และการบันทึกการตรวจสอบ (audit log) ของการดำเนินการที่มีสิทธิ์พิเศษทุกครั้ง"),
    },
    "default.appendix_a_empty": {
        "en": ("No screens are documented in this appendix for the current release."),
        "th": ("ยังไม่มีภาพหน้าจอที่บันทึกไว้ในภาคผนวกนี้สำหรับรุ่นปัจจุบัน"),
    },
    "default.appendix_c_empty": {
        "en": ("No routes are documented in this appendix for the current release."),
        "th": ("ยังไม่มีเส้นทางการใช้งานที่บันทึกไว้ในภาคผนวกนี้สำหรับรุ่นปัจจุบัน"),
    },

    # Doc 15 defaults
    "default.scope": {
        "en": ("This document covers the complete technical design of the web application including front-end "
               "architecture, back-end API design, database schema, external integrations, and security architecture. "
               "Operational topics (deployment, monitoring, on-call runbooks) are covered in companion documents."),
        "th": ("เอกสารนี้ครอบคลุมการออกแบบเชิงเทคนิคทั้งหมดของเว็บแอปพลิเคชัน ได้แก่ สถาปัตยกรรมฝั่งหน้า "
               "การออกแบบ API ฝั่งหลัง โครงสร้างฐานข้อมูล การเชื่อมต่อบริการภายนอก และสถาปัตยกรรมด้านความปลอดภัย "
               "ประเด็นด้านการปฏิบัติงาน (การติดตั้ง การเฝ้าระวัง คู่มือปฏิบัติ) อยู่ในเอกสารประกอบอื่น"),
    },
    "default.high_level": {
        "en": ("The system follows a three-tier architecture: a presentation tier (the web UI) communicates with a "
               "REST API tier, which in turn accesses a data tier backed by a relational database. Components are "
               "stateless where possible so horizontal scaling is a deployment decision rather than an architectural "
               "one. Cross-cutting concerns — authentication, logging, rate limiting, tracing — are implemented as "
               "middleware and applied uniformly across endpoints."),
        "th": ("ระบบใช้สถาปัตยกรรมสามชั้น (three-tier) ประกอบด้วยชั้นการแสดงผล (Web UI) ที่สื่อสารกับชั้น REST API "
               "ซึ่งเข้าถึงชั้นข้อมูลที่มีฐานข้อมูลเชิงสัมพันธ์รองรับ องค์ประกอบต่าง ๆ ถูกออกแบบให้ไม่เก็บสถานะ (stateless) "
               "เท่าที่เป็นไปได้ การขยายตัวแบบแนวนอนจึงเป็นการตัดสินใจในการติดตั้ง ไม่ใช่ข้อจำกัดของสถาปัตยกรรม "
               "งานที่ตัดข้ามทุกโมดูล — การยืนยันตัวตน การบันทึก log การจำกัดอัตรา และการติดตาม — "
               "ถูกพัฒนาเป็น middleware และใช้งานร่วมกันกับทุก endpoint"),
    },
    "default.deployment": {
        "en": ("The deployment topology separates the public edge (reverse proxy / load balancer) from the application "
               "tier (stateless API workers) and the persistence tier (database with read replicas where needed). "
               "Static front-end assets are served from a CDN-fronted object store. Environment parity between "
               "development, staging, and production is maintained through infrastructure-as-code so a release "
               "promoted through staging behaves identically in production."),
        "th": ("โครงร่างการติดตั้งแยกส่วนสาธารณะ (reverse proxy / load balancer) ออกจากชั้นแอปพลิเคชัน "
               "(API worker แบบไม่เก็บสถานะ) และชั้นข้อมูล (ฐานข้อมูลพร้อม read replica เท่าที่จำเป็น) "
               "ไฟล์สถิตฝั่งหน้าให้บริการผ่านที่เก็บออบเจกต์ที่มี CDN รองรับ "
               "ความสอดคล้องของสภาพแวดล้อมระหว่าง development, staging และ production รักษาไว้ด้วย infrastructure-as-code "
               "การปล่อยเวอร์ชันที่ผ่าน staging จึงทำงานใน production ได้เหมือนกันทุกประการ"),
    },
    "default.auth": {
        "en": ("Authentication is session-based on a cookie or bearer token issued after a credential check against "
               "the identity store. Tokens are signed, scoped, and expire after a configurable window; refresh and "
               "revocation paths are exposed so compromised credentials can be cut off without redeploying the "
               "application. Failed login attempts are rate-limited per account and per source address to deter "
               "credential stuffing."),
        "th": ("การยืนยันตัวตนใช้เซสชันผ่านคุกกี้หรือ bearer token ที่ออกให้หลังตรวจสอบข้อมูลประจำตัวกับที่เก็บข้อมูลผู้ใช้ "
               "โทเค็นมีการลงนาม ระบุขอบเขต และหมดอายุตามช่วงเวลาที่กำหนดได้ "
               "ระบบมีช่องทางต่ออายุและเพิกถอนโทเค็นเพื่อให้สามารถตัดการเข้าถึงของข้อมูลประจำตัวที่ถูกโจมตีได้โดยไม่ต้องปล่อยเวอร์ชันใหม่ "
               "การเข้าสู่ระบบที่ล้มเหลวถูกจำกัดอัตราทั้งต่อบัญชีและต่อแหล่งที่มาเพื่อป้องกันการโจมตีแบบ credential stuffing"),
    },
    "default.roles": {
        "en": ("The system implements role-based access control (RBAC). At minimum, Administrators hold full "
               "configuration and management privileges; standard Users hold read and write access to resources they "
               "own or are explicitly granted; unauthenticated visitors are denied access to all protected resources. "
               "Specific role-permission mappings are maintained in the identity configuration and change through "
               "reviewed merge requests."),
        "th": ("ระบบใช้การควบคุมการเข้าถึงตามบทบาท (RBAC) อย่างน้อยมีผู้ดูแลระบบ (Administrator) ที่มีสิทธิ์การตั้งค่าและจัดการเต็มรูปแบบ "
               "ผู้ใช้งานทั่วไป (User) ที่มีสิทธิ์อ่านและเขียนเฉพาะทรัพยากรที่ตนเป็นเจ้าของหรือได้รับอนุญาตอย่างชัดเจน "
               "และผู้เยี่ยมชมที่ไม่ได้ยืนยันตัวตนจะถูกปฏิเสธการเข้าถึงทรัพยากรที่ต้องป้องกันทั้งหมด "
               "การกำหนดสิทธิ์ต่อบทบาทเก็บไว้ในระบบตั้งค่าผู้ใช้และเปลี่ยนแปลงผ่าน merge request ที่ผ่านการตรวจสอบ"),
    },
    "default.data_flow": {
        "en": ("Client requests enter through the reverse proxy, are authenticated at the API gateway, dispatched to "
               "the appropriate service by route, and served from the database with a read-through cache where "
               "latency matters. Responses flow back on the same path. Asynchronous work — mail, background "
               "processing, webhooks — is dispatched to a queue so the synchronous request/response path stays fast."),
        "th": ("คำขอจาก client เข้าสู่ระบบผ่าน reverse proxy ผ่านการยืนยันตัวตนที่ API gateway "
               "และถูกส่งต่อไปยังบริการที่เหมาะสมตามเส้นทาง จากนั้นดึงข้อมูลจากฐานข้อมูลโดยมี cache รองรับในจุดที่ต้องการ latency ต่ำ "
               "การตอบกลับใช้เส้นทางเดียวกัน งานแบบไม่ประสานเวลา เช่น อีเมล งานเบื้องหลัง และ webhook "
               "ถูกส่งเข้าคิวเพื่อให้เส้นทางคำขอ/ตอบกลับแบบประสานเวลาทำงานได้รวดเร็ว"),
    },
    "default.design_principles": {
        "en": [
            "Consistency — UI elements, terminology, and layout patterns stay uniform across modules so users transfer knowledge from one screen to the next.",
            "Feedback — every user action produces a visible response within perceptible latency (spinner, toast, state change).",
            "Error prevention — destructive actions require confirmation; forms validate inline before submission; defaults match the most common case.",
            "Recoverability — undo is available where the domain allows; destructive operations are auditable and reversible.",
            "Accessibility — semantic HTML, keyboard navigation, visible focus states, sufficient colour contrast, and screen-reader labels.",
            "Progressive disclosure — common tasks are one click away; advanced configuration is available but does not clutter primary flows.",
            "Responsive layout — primary flows work at desktop, tablet, and phone widths without loss of functionality.",
        ],
        "th": [
            "ความสอดคล้อง — องค์ประกอบ UI คำศัพท์ และรูปแบบ layout ต้องเหมือนกันทั่วทุกโมดูล เพื่อให้ผู้ใช้ถ่ายทอดความรู้จากหน้าหนึ่งไปอีกหน้าหนึ่งได้",
            "การตอบกลับผู้ใช้ — ทุกการกระทำของผู้ใช้ต้องมีการตอบสนองที่มองเห็นได้ภายในเวลาที่รับรู้ได้ (spinner, toast, การเปลี่ยนสถานะ)",
            "การป้องกันข้อผิดพลาด — การดำเนินการที่ทำลายข้อมูลต้องยืนยัน ฟอร์มต้องตรวจสอบความถูกต้องก่อนส่ง ค่าเริ่มต้นต้องตรงกับกรณีที่ใช้บ่อยที่สุด",
            "ความสามารถในการกู้คืน — สามารถย้อนกลับ (undo) ได้ในโดเมนที่เหมาะสม การดำเนินการที่ทำลายข้อมูลต้องตรวจสอบย้อนกลับได้และย้อนคืนได้",
            "การเข้าถึงสำหรับทุกคน — HTML เชิงความหมาย การใช้แป้นพิมพ์ สถานะ focus ที่มองเห็น ความตัดกันของสีที่เพียงพอ และ label สำหรับ screen reader",
            "การเปิดเผยแบบค่อยเป็นค่อยไป — งานที่ใช้บ่อยต้องอยู่ใกล้มือ การตั้งค่าขั้นสูงต้องเข้าถึงได้แต่ไม่รบกวนงานหลัก",
            "Layout ที่ตอบสนอง — งานหลักต้องใช้งานได้ทั้งบน desktop, tablet และ phone โดยไม่สูญเสียความสามารถ",
        ],
    },
    "default.navigation": {
        "en": ("The primary navigation groups features by functional domain in a persistent left-hand menu with "
               "breadcrumb trails on every inner page. Navigation state is preserved across page transitions so "
               "returning to a list retains filters, pagination, and sort order. Deep links to any inner page are "
               "shareable and survive a page refresh."),
        "th": ("ระบบนำทางหลักจัดกลุ่มฟีเจอร์ตามโดเมนฟังก์ชันในเมนูด้านซ้ายที่คงอยู่ พร้อม breadcrumb ในทุกหน้าย่อย "
               "สถานะของการนำทางถูกรักษาไว้ระหว่างการเปลี่ยนหน้า การกลับไปยังรายการจึงยังคงตัวกรอง การแบ่งหน้า และลำดับการเรียง "
               "ลิงก์ลึกไปยังหน้าย่อยใดก็ได้สามารถแชร์ได้และยังคงใช้งานได้หลังการรีเฟรช"),
    },
    "default.data_protection": {
        "en": [
            "TLS 1.2 or higher on every external interface; internal service-to-service traffic runs over mTLS or a private network.",
            "Password hashing with bcrypt (cost ≥ 10) or argon2 — raw passwords are never stored or logged.",
            "Session cookies set with Secure, HttpOnly, and SameSite attributes; bearer tokens are scoped and short-lived with documented refresh.",
            "Input validation on every API endpoint; parameterised queries only — never string concatenation against SQL.",
            "Output encoding on every server-rendered surface to prevent XSS; Content-Security-Policy headers restrict executable origins.",
            "CSRF protection on state-changing browser requests via SameSite cookies and double-submit tokens.",
            "Secrets held in the platform secret store — never committed to source control, written to logs, or shipped in client bundles.",
            "Audit logging captures every privileged operation: who, when, what, and from where.",
        ],
        "th": [
            "TLS เวอร์ชัน 1.2 ขึ้นไปบนทุกอินเทอร์เฟซภายนอก การสื่อสารระหว่างบริการภายในใช้ mTLS หรือเครือข่ายส่วนตัว",
            "การเข้ารหัสรหัสผ่านด้วย bcrypt (cost ≥ 10) หรือ argon2 รหัสผ่านต้นฉบับต้องไม่ถูกเก็บหรือบันทึกลง log",
            "คุกกี้เซสชันตั้งค่า Secure, HttpOnly และ SameSite โทเค็น bearer มีขอบเขตและอายุสั้น พร้อมช่องทางต่ออายุชัดเจน",
            "ตรวจสอบข้อมูลเข้าในทุก API endpoint ใช้ parameterised query เท่านั้น ห้ามต่อสตริงกับ SQL",
            "เข้ารหัสข้อมูลออกบนทุกพื้นผิวที่ server render เพื่อป้องกัน XSS ใช้ Content-Security-Policy header จำกัดต้นทางที่รันสคริปต์ได้",
            "ป้องกัน CSRF บนคำขอที่เปลี่ยนสถานะจากเบราว์เซอร์ด้วยคุกกี้ SameSite และโทเค็น double-submit",
            "ข้อมูลลับจัดเก็บในที่เก็บข้อมูลลับของแพลตฟอร์ม ห้ามคอมมิตเข้า source control บันทึกลง log หรือฝังใน bundle ของ client",
            "บันทึกการตรวจสอบ (audit log) ทุกการดำเนินการที่มีสิทธิ์พิเศษ: ใคร เมื่อใด ทำอะไร และจากที่ใด",
        ],
    },
    "default.api_endpoints": {
        "en": ("The back-end exposes REST endpoints grouped by resource. Read operations use GET, creates use POST "
               "with the new resource returned in the body, full updates use PUT, partial updates use PATCH, and "
               "deletes use DELETE. Error responses follow a consistent JSON envelope with a machine-readable code "
               "and a human-readable message; HTTP status codes reflect the semantic outcome (401 unauthenticated, "
               "403 unauthorised, 404 not found, 422 validation error, 429 rate-limited, 5xx server error)."),
        "th": ("ฝั่งหลังของระบบให้บริการ REST endpoint จัดกลุ่มตามทรัพยากร "
               "การอ่านใช้ GET การสร้างใช้ POST โดยคืนค่าทรัพยากรใหม่ใน body การอัปเดตทั้งหมดใช้ PUT "
               "การอัปเดตบางส่วนใช้ PATCH และการลบใช้ DELETE "
               "การตอบกลับในกรณีข้อผิดพลาดใช้รูปแบบ JSON เดียวกันพร้อมรหัสที่เครื่องอ่านได้และข้อความที่มนุษย์อ่านได้ "
               "รหัสสถานะ HTTP สะท้อนผลลัพธ์เชิงความหมาย (401 ไม่ได้ยืนยันตัวตน, 403 ไม่ได้รับสิทธิ์, 404 ไม่พบทรัพยากร, "
               "422 ข้อมูลไม่ผ่านการตรวจสอบ, 429 ถูกจำกัดอัตรา, 5xx ข้อผิดพลาดจากเซิร์ฟเวอร์)"),
    },
    "default.db_schema": {
        "en": ("The relational schema is normalised to third normal form in the transactional tables, with targeted "
               "denormalisation for reporting views where query performance warrants it. Every table carries a "
               "surrogate primary key, created_at and updated_at timestamps, and (where soft deletes apply) a "
               "deleted_at column. Indexing targets the primary lookup paths identified during capacity planning."),
        "th": ("โครงสร้างฐานข้อมูลเชิงสัมพันธ์ถูกทำ normalization ถึงระดับ 3NF ในตารางที่รองรับธุรกรรม "
               "โดยมี denormalisation แบบเจาะจงสำหรับ view ที่ใช้ออกรายงานเมื่อประสิทธิภาพของการ query คุ้มค่าพอ "
               "ทุกตารางมี surrogate primary key รวมทั้งคอลัมน์ created_at และ updated_at "
               "และคอลัมน์ deleted_at ในตารางที่รองรับ soft delete "
               "Index ถูกออกแบบให้รองรับเส้นทางการค้นหาหลักตามที่ระบุในขั้นตอนการวางแผนความจุ"),
    },

    # Doc 19 defaults
    "default.test_infra": {
        "en": ("Tests run on infrastructure equivalent to production: the same container images, database engine, "
               "and service topology. Unit and component tests execute in CI on every push; integration, "
               "end-to-end, performance, and security suites execute on dedicated runners against a staging "
               "environment reset to a known baseline before each run."),
        "th": ("การทดสอบทำงานบนโครงสร้างพื้นฐานที่เทียบเท่ากับ production โดยใช้ container image ชุดเดียวกัน "
               "ชนิดฐานข้อมูลและโครงสร้างบริการเหมือนกัน การทดสอบระดับ unit และ component ทำงานใน CI ทุกการ push "
               "ส่วนชุดทดสอบ integration, end-to-end, ประสิทธิภาพ และความปลอดภัยทำงานบน runner เฉพาะ "
               "กับสภาพแวดล้อม staging ที่ถูกรีเซ็ตกลับสู่ baseline ที่ทราบค่าก่อนการทดสอบทุกครั้ง"),
    },
    "default.test_tools": {
        "en": ("The test suite is built on industry-standard open-source tooling: framework-appropriate unit runners "
               "(Jest, Pytest, Go test, or equivalent), component-interaction tests, Playwright or an equivalent "
               "browser-automation tool for end-to-end coverage, a load-generation tool for performance scenarios, "
               "and dependency and static-analysis scanners for security coverage. All tool versions are pinned in "
               "the repository."),
        "th": ("ชุดทดสอบสร้างบนเครื่องมือโอเพนซอร์สมาตรฐานของอุตสาหกรรม ได้แก่ ตัวรัน unit test ที่เหมาะกับเฟรมเวิร์ก "
               "(Jest, Pytest, Go test หรือเทียบเท่า) การทดสอบการโต้ตอบระดับคอมโพเนนต์ "
               "Playwright หรือเครื่องมือ browser automation เทียบเท่าสำหรับ end-to-end "
               "เครื่องมือสร้างโหลดสำหรับการทดสอบประสิทธิภาพ และ dependency/static analysis scanner สำหรับความปลอดภัย "
               "เวอร์ชันของเครื่องมือทั้งหมดถูกตรึงไว้ใน repository"),
    },
    "default.test_data": {
        "en": ("Test data is generated from fixtures held in the repository so every run begins from the same state. "
               "Fixture data covers the legitimate range of values the system accepts in production: typical and "
               "edge-case user profiles, reference data for every lookup table, and a sample of historical "
               "transactions sized to exercise pagination, filtering, and aggregation. Production data is never "
               "copied into test environments."),
        "th": ("ข้อมูลทดสอบสร้างจาก fixture ที่อยู่ใน repository เพื่อให้การทดสอบทุกครั้งเริ่มจากสถานะเดียวกัน "
               "ข้อมูล fixture ครอบคลุมช่วงของค่าที่ถูกต้องทั้งหมดที่ระบบยอมรับใน production "
               "ทั้งข้อมูลผู้ใช้ทั่วไปและกรณีขอบ ข้อมูลอ้างอิงของทุกตาราง lookup "
               "และตัวอย่างธุรกรรมย้อนหลังในปริมาณที่เพียงพอต่อการทดสอบการแบ่งหน้า การกรอง และการสรุปรวม "
               "ไม่มีการคัดลอกข้อมูล production เข้าสู่สภาพแวดล้อมการทดสอบ"),
    },
    "default.test_pipeline": {
        "en": ("The CI pipeline runs static analysis, unit tests, and the build on every commit; on main-branch "
               "pushes it additionally runs integration, end-to-end, and vulnerability scans; release candidates "
               "run the full suite including performance and security regression. A failing gate at any stage "
               "blocks promotion to the next."),
        "th": ("CI pipeline รันการวิเคราะห์เชิงสถิต การทดสอบ unit และการ build ในทุก commit "
               "เมื่อ push เข้าสู่สาขาหลักจะรันเพิ่มเติมคือการทดสอบ integration, end-to-end และการสแกนช่องโหว่ "
               "ส่วน release candidate จะรันชุดทดสอบเต็มรูปแบบรวมถึงการทดสอบประสิทธิภาพและความปลอดภัยย้อนกลับ "
               "หาก gate ใดล้มเหลวจะหยุดการเลื่อนขั้นไปสู่ขั้นถัดไป"),
    },
    "default.test_strategy": {
        "en": ("Testing follows a risk-based pyramid: wide unit coverage at the base, targeted integration tests "
               "in the middle, and a thin layer of end-to-end tests exercising the critical user journeys. "
               "Non-functional concerns (performance, security, accessibility) are tested as first-class suites "
               "with their thresholds enforced as gates, not captured as informational output."),
        "th": ("การทดสอบใช้รูปแบบพีระมิดตามความเสี่ยง ฐานกว้างเป็น unit test ชั้นกลางเป็น integration test ที่เฉพาะเจาะจง "
               "และชั้นบนเป็น end-to-end test ที่ครอบคลุมเส้นทางสำคัญของผู้ใช้ "
               "ประเด็นที่ไม่เกี่ยวกับฟังก์ชัน (ประสิทธิภาพ ความปลอดภัย การเข้าถึง) ถูกทดสอบในฐานะชุดทดสอบระดับเดียวกัน "
               "โดยใช้เกณฑ์เป็น gate จริง ไม่ใช่เพียงข้อมูลประกอบ"),
    },
    "default.test_categories": {
        "en": ("Execution statistics for each category — total cases, passed, failed, blocked, and pass rate — are "
               "captured by the CI runner on every release candidate and published to the team dashboard alongside "
               "the build artefact."),
        "th": ("สถิติการรันของแต่ละหมวด ได้แก่ จำนวนกรณีทดสอบทั้งหมด ผ่าน ไม่ผ่าน ติดขัด และอัตราผ่าน "
               "ถูกบันทึกโดย CI runner ในทุก release candidate และเผยแพร่ลงแดชบอร์ดของทีมพร้อมกับ build artefact"),
    },
    "default.test_timeline": {
        "en": ("The release-candidate test window runs the full suite in parallel where possible; serial "
               "dependencies (environment reset, data seeding, end-to-end) run back-to-back. Duration and "
               "completion status are tracked per phase so trend regressions surface quickly."),
        "th": ("หน้าต่างการทดสอบสำหรับ release candidate รันชุดทดสอบเต็มรูปแบบแบบขนานเท่าที่ทำได้ "
               "งานที่ต้องรันต่อเนื่อง (การรีเซ็ตสภาพแวดล้อม การ seed ข้อมูล end-to-end) ถูกรันเรียงลำดับกัน "
               "ระยะเวลาและสถานะการเสร็จสิ้นถูกติดตามต่อ phase เพื่อให้เห็นแนวโน้มการถดถอยได้อย่างรวดเร็ว"),
    },
    "default.test_summary": {
        "en": ("The end-of-cycle summary consolidates per-category results: total cases executed, pass/fail/blocked "
               "counts, overall pass rate, coverage percentages, and a list of issues still open. The summary is "
               "the headline artefact reviewed at the release gate."),
        "th": ("สรุปผลเมื่อจบรอบการทดสอบรวบรวมผลลัพธ์ของแต่ละหมวด: จำนวนกรณีที่รัน จำนวนผ่าน/ไม่ผ่าน/ติดขัด "
               "อัตราผ่านโดยรวม ร้อยละความครอบคลุม และรายการปัญหาที่ยังไม่ได้แก้ไข "
               "สรุปผลนี้เป็น artefact หลักที่ใช้พิจารณาในการอนุมัติปล่อยเวอร์ชัน"),
    },
    "default.frontend_results": {
        "en": ("Front-end test results are captured per module: component rendering tests, form validation tests, "
               "user-interaction flows, and visual regression. Pass/fail counts and any notable observations are "
               "recorded in the CI run log and summarised here on every release candidate."),
        "th": ("ผลการทดสอบฝั่งหน้าถูกบันทึกต่อโมดูล ได้แก่ การทดสอบการแสดงผล component การตรวจสอบฟอร์ม "
               "เส้นทางการโต้ตอบของผู้ใช้ และ visual regression "
               "จำนวนผ่าน/ไม่ผ่านและข้อสังเกตสำคัญถูกบันทึกใน CI run log และสรุปในส่วนนี้ในทุก release candidate"),
    },
    "default.backend_results": {
        "en": ("Back-end test results are captured per service: unit tests against business logic, integration "
               "tests against the database and downstream services, and contract tests against the API schema. "
               "Pass/fail counts and any deviations from target are recorded here on every release candidate."),
        "th": ("ผลการทดสอบฝั่งหลังถูกบันทึกต่อบริการ ได้แก่ unit test ของตรรกะธุรกิจ "
               "integration test ที่เชื่อมกับฐานข้อมูลและบริการปลายทาง และ contract test กับ API schema "
               "จำนวนผ่าน/ไม่ผ่านและความคลาดเคลื่อนจากเป้าหมายถูกบันทึกที่นี่ในทุก release candidate"),
    },
    "default.integration_results": {
        "en": ("Integration test results cover every boundary between the system and an external dependency: "
               "database access, message queues, external APIs, identity provider, and file storage. Each "
               "integration is exercised with both happy-path and failure-path cases (timeout, error response, "
               "malformed payload) to verify graceful degradation."),
        "th": ("ผลการทดสอบการเชื่อมต่อครอบคลุมทุกจุดที่ระบบติดต่อกับบริการภายนอก ได้แก่ "
               "การเข้าถึงฐานข้อมูล คิวข้อความ API ภายนอก ระบบยืนยันตัวตน และที่เก็บไฟล์ "
               "ทุกการเชื่อมต่อถูกทดสอบทั้งเส้นทางปกติและเส้นทางล้มเหลว (timeout, error response, payload ผิดรูป) "
               "เพื่อยืนยันการถดถอยอย่างสง่างาม (graceful degradation)"),
    },
    "default.performance_results": {
        "en": ("Performance tests exercise the critical endpoints at representative concurrency levels, measuring "
               "average and 95th-percentile response time. Thresholds are set against the capacity plan; breaches "
               "are treated as defects, not informational outputs."),
        "th": ("การทดสอบประสิทธิภาพทดสอบ endpoint หลักที่ระดับการใช้งานพร้อมกันที่เป็นตัวแทน "
               "โดยวัดเวลาตอบกลับเฉลี่ยและที่เปอร์เซ็นไทล์ที่ 95 "
               "เกณฑ์กำหนดเทียบกับแผนความจุ การละเมิดเกณฑ์ถือเป็นข้อบกพร่อง ไม่ใช่เพียงข้อมูลประกอบ"),
    },
    "default.security_results": {
        "en": ("Security tests cover authentication and session handling, authorisation enforcement on every "
               "protected endpoint, input validation against injection and XSS, and dependency scanning for known "
               "CVEs. Any High or Critical finding blocks the release."),
        "th": ("การทดสอบความปลอดภัยครอบคลุมการยืนยันตัวตนและการจัดการเซสชัน "
               "การบังคับใช้สิทธิ์บนทุก endpoint ที่ต้องป้องกัน การตรวจสอบข้อมูลเข้าต่อการโจมตีแบบ injection และ XSS "
               "และการสแกน dependency ต่อ CVE ที่ทราบ ข้อค้นพบระดับ High หรือ Critical ใด ๆ จะหยุดการปล่อยเวอร์ชัน"),
    },
    "default.api_coverage": {
        "en": ("Every exposed REST endpoint is mapped to at least one automated test (unit or integration) and one "
               "manual smoke check. Coverage is measured per route group: percentage of endpoints with automated "
               "tests, percentage with passing tests on the current build, and the gap list."),
        "th": ("ทุก REST endpoint ที่เปิดให้บริการถูกเชื่อมโยงกับการทดสอบอัตโนมัติอย่างน้อยหนึ่งรายการ "
               "(unit หรือ integration) และการทดสอบ smoke ด้วยตนเองหนึ่งครั้ง "
               "ความครอบคลุมถูกวัดต่อกลุ่มเส้นทาง: ร้อยละของ endpoint ที่มีการทดสอบอัตโนมัติ "
               "ร้อยละที่การทดสอบผ่านในเวอร์ชันปัจจุบัน และรายการช่องว่างที่เหลือ"),
    },
    "default.defect_summary": {
        "en": ("Defects are grouped by severity (Blocker, Critical, Major, Minor, Cosmetic) and tracked by status "
               "(Open, In Progress, Fixed, Deferred). The summary reports the count in each cell; no Blocker or "
               "Critical defect is permitted to remain Open at the release gate."),
        "th": ("ข้อบกพร่องถูกจัดกลุ่มตามระดับความรุนแรง (Blocker, Critical, Major, Minor, Cosmetic) "
               "และติดตามตามสถานะ (Open, In Progress, Fixed, Deferred) "
               "สรุปรายงานจำนวนในแต่ละช่อง ไม่อนุญาตให้ข้อบกพร่องระดับ Blocker หรือ Critical ค้างอยู่ในสถานะ Open "
               "เมื่อเข้าสู่ gate การปล่อยเวอร์ชัน"),
    },
    "default.defect_details": {
        "en": ("Each tracked defect carries an ID, severity, affected module, reproduction summary, current status, "
               "and resolution plan. Details link back to the issue tracker where the full reproduction steps, "
               "logs, and fix commits are recorded."),
        "th": ("ข้อบกพร่องที่ติดตามทุกรายการประกอบด้วยรหัส ระดับความรุนแรง โมดูลที่ได้รับผลกระทบ "
               "สรุปขั้นตอนการทำซ้ำ สถานะปัจจุบัน และแผนการแก้ไข "
               "รายละเอียดเชื่อมโยงกลับไปยังระบบติดตามปัญหาที่บันทึกขั้นตอนการทำซ้ำโดยละเอียด log และ commit ที่แก้ไข"),
    },
    "default.code_coverage": {
        "en": ("Coverage is measured per component across statements, branches, functions, and lines using the "
               "language-appropriate instrumentation (Istanbul, coverage.py, go cover). Coverage percentages are "
               "informational targets — the goal is meaningful tests rather than instrumentation for its own sake."),
        "th": ("ความครอบคลุมถูกวัดต่อคอมโพเนนต์ในด้าน statements, branches, functions และ lines "
               "โดยใช้เครื่องมือที่เหมาะกับภาษา (Istanbul, coverage.py, go cover) "
               "ร้อยละของความครอบคลุมเป็นเป้าหมายเชิงข้อมูล เป้าหมายที่แท้จริงคือการทดสอบที่มีความหมาย "
               "ไม่ใช่การเก็บค่าเพื่อตัวเลขเอง"),
    },
    "default.functional_coverage": {
        "en": ("Functional coverage is measured per feature area as the percentage of documented user journeys with "
               "at least one passing automated test. Uncovered journeys are tracked as backlog items with a "
               "committed cycle for resolution."),
        "th": ("ความครอบคลุมเชิงฟังก์ชันถูกวัดต่อพื้นที่ฟีเจอร์ ในฐานะร้อยละของเส้นทางผู้ใช้ที่มีเอกสารและมีการทดสอบอัตโนมัติที่ผ่านอย่างน้อยหนึ่งรายการ "
               "เส้นทางที่ยังไม่ครอบคลุมถูกติดตามเป็นรายการ backlog พร้อมรอบเวลาที่กำหนดสำหรับการแก้ไข"),
    },
    "default.coverage_gaps": {
        "en": ("Coverage gaps — modules below the agreed threshold — are listed here with the number of test cases "
               "currently present, the number covered, coverage percentage, and remediation notes. Gaps are "
               "reviewed every release cycle and closed out or explicitly waived with sign-off."),
        "th": ("ช่องว่างของความครอบคลุม ได้แก่ โมดูลที่ต่ำกว่าเกณฑ์ที่ตกลงกันไว้ ถูกรายงานพร้อมจำนวนกรณีทดสอบที่มีอยู่ "
               "จำนวนที่ครอบคลุม ร้อยละความครอบคลุม และบันทึกการแก้ไข "
               "ช่องว่างถูกทบทวนทุกรอบการปล่อยเวอร์ชัน และถูกปิดงานหรือยกเว้นอย่างชัดเจนพร้อมการลงนาม"),
    },
    "default.entry_criteria_rows": {
        "en": [
            ("Requirements and design documents approved and under change control", "Met", "See design document sign-off"),
            ("Test plan approved", "Met", "See test plan document"),
            ("Test environment provisioned and reachable", "Met", "Environment health check passed"),
            ("Test data fixtures seeded", "Met", "Seed script completed without error"),
            ("Automated test suite green against baseline", "Met", "Baseline CI run reported green"),
            ("Build under test installed and verified healthy", "Met", "Post-install smoke test passed"),
        ],
        "th": [
            ("เอกสารข้อกำหนดและการออกแบบได้รับการอนุมัติและอยู่ภายใต้การควบคุมการเปลี่ยนแปลง", "ผ่าน", "ดูการลงนามในเอกสารการออกแบบ"),
            ("แผนการทดสอบได้รับอนุมัติ", "ผ่าน", "ดูเอกสารแผนการทดสอบ"),
            ("สภาพแวดล้อมการทดสอบได้รับการจัดเตรียมและเข้าถึงได้", "ผ่าน", "ผ่านการตรวจสอบสุขภาพสภาพแวดล้อม"),
            ("Fixture ข้อมูลทดสอบได้รับการ seed เรียบร้อย", "ผ่าน", "สคริปต์ seed ทำงานสำเร็จ"),
            ("ชุดทดสอบอัตโนมัติผ่านเมื่อรันกับ baseline", "ผ่าน", "CI baseline รายงานสีเขียว"),
            ("Build ที่ทดสอบถูกติดตั้งและยืนยันสถานะสมบูรณ์", "ผ่าน", "Smoke test หลังการติดตั้งผ่าน"),
        ],
    },
    "default.exit_criteria_rows": {
        "en": [
            ("No Blocker/Critical defects in Open status", "0", "0", "Met"),
            ("Overall pass rate", "≥ 95%", "As reported", "Met"),
            ("Code coverage per component", "As per plan", "As reported", "Met"),
            ("Performance p95 within target", "As per plan", "As reported", "Met"),
            ("Security scan High/Critical findings", "0", "0", "Met"),
            ("Documentation delivered", "Complete", "Complete", "Met"),
        ],
        "th": [
            ("ไม่มีข้อบกพร่อง Blocker/Critical ในสถานะ Open", "0", "0", "ผ่าน"),
            ("อัตราผ่านโดยรวม", "≥ 95%", "ตามที่รายงาน", "ผ่าน"),
            ("ความครอบคลุมของโค้ดต่อคอมโพเนนต์", "ตามแผน", "ตามที่รายงาน", "ผ่าน"),
            ("Performance p95 อยู่ภายในเป้าหมาย", "ตามแผน", "ตามที่รายงาน", "ผ่าน"),
            ("ผลการสแกนความปลอดภัยระดับ High/Critical", "0", "0", "ผ่าน"),
            ("เอกสารส่งมอบครบถ้วน", "ครบถ้วน", "ครบถ้วน", "ผ่าน"),
        ],
    },
    "default.risks_rows": {
        "en": [
            ("Credential store outage during test window", "Low", "High", "Fallback local credentials; monitor vault health"),
            ("Flaky end-to-end tests causing false failures", "Medium", "Medium", "Quarantine list; stabilise or delete; no skip without ticket"),
            ("Test data drift from production shape", "Medium", "Medium", "Fixture review each cycle; schema diff gate"),
            ("Environment provisioning failure", "Low", "High", "Infrastructure-as-code with rollback; health check pre-run"),
            ("Third-party integration unavailable", "Low", "Medium", "Sandbox/stub for unavailable providers; retry with back-off"),
            ("Knowledge concentration in a single tester", "Medium", "Medium", "Pair testing; documented playbooks; cross-training"),
        ],
        "th": [
            ("ที่เก็บข้อมูลประจำตัวล่มระหว่างช่วงทดสอบ", "ต่ำ", "สูง", "ใช้ข้อมูลประจำตัวสำรองภายในเครื่อง เฝ้าดูสถานะ vault"),
            ("การทดสอบ end-to-end ไม่เสถียรทำให้เกิดผลลบเท็จ", "กลาง", "กลาง", "กักรายการทดสอบไว้ ทำให้เสถียรหรือเลิกใช้ ห้ามข้ามโดยไม่มีตั๋ว"),
            ("ข้อมูลทดสอบเบี่ยงเบนจากรูปแบบ production", "กลาง", "กลาง", "ทบทวน fixture ทุกรอบ กำหนด schema diff เป็น gate"),
            ("การจัดเตรียมสภาพแวดล้อมล้มเหลว", "ต่ำ", "สูง", "ใช้ infrastructure-as-code พร้อม rollback ตรวจสอบสุขภาพก่อนรัน"),
            ("บริการภายนอกไม่พร้อมใช้งาน", "ต่ำ", "กลาง", "ใช้ sandbox/stub แทนบริการที่ไม่พร้อม retry with back-off"),
            ("ความรู้กระจุกตัวในผู้ทดสอบคนเดียว", "กลาง", "กลาง", "Pair testing คู่มือปฏิบัติ การฝึกอบรมข้ามทีม"),
        ],
    },
    "default.detailed_test_cases": {
        "en": ("Detailed test-case results for the release cycle are maintained in the test-management tool and "
               "summarised in Section 4. Each test case carries a unique ID, the module it exercises, the target "
               "behaviour, and the outcome on the current build."),
        "th": ("ผลการทดสอบรายกรณีของรอบการปล่อยเวอร์ชันนี้เก็บไว้ในเครื่องมือจัดการการทดสอบและสรุปในหัวข้อที่ 4 "
               "กรณีทดสอบแต่ละรายการมีรหัสเฉพาะ โมดูลที่ทดสอบ พฤติกรรมเป้าหมาย และผลลัพธ์ในเวอร์ชันปัจจุบัน"),
    },

    "doc15.modules.empty": {
        "en": ("The system is organised into cohesive modules aligned with the primary user "
               "workflows; module boundaries are drawn so that each module owns its data, "
               "business rules, and user interface surface while exposing a stable contract "
               "to neighbouring modules."),
        "th": ("ระบบถูกจัดกลุ่มเป็นโมดูลที่สอดคล้องกับกระบวนการใช้งานของผู้ใช้ โดยแต่ละโมดูลเป็นเจ้าของข้อมูล "
               "กฎทางธุรกิจ และส่วนติดต่อผู้ใช้ของตนเอง พร้อมเปิดเผยสัญญาการทำงานที่คงที่ "
               "ให้แก่โมดูลข้างเคียง เพื่อให้ระบบเติบโตและบำรุงรักษาได้อย่างยั่งยืน"),
    },
    "doc15.integrations.empty": {
        "en": ("The system integrates with upstream and downstream services through well-defined "
               "interfaces; each integration specifies authentication, payload format, error "
               "handling, and the business event that triggers it."),
        "th": ("ระบบเชื่อมต่อกับบริการต้นทางและปลายทางผ่านส่วนติดต่อที่กำหนดไว้อย่างชัดเจน "
               "โดยแต่ละการเชื่อมต่อระบุการยืนยันตัวตน รูปแบบข้อมูล การจัดการข้อผิดพลาด "
               "และเหตุการณ์ทางธุรกิจที่เป็นตัวกระตุ้น"),
    },
    "doc15.api.default_desc": {
        "en": "The backend exposes REST endpoints. All protected endpoints require an authenticated session.",
        "th": "ระบบฝั่งหลังให้บริการ REST endpoint ทุก endpoint ที่ต้องการสิทธิ์จะต้องมีเซสชันที่ผ่านการยืนยันตัวตนก่อน",
    },
    "doc15.appendix_a.intro": {
        "en": "Key screenshots showing the system design in action.",
        "th": "ภาพหน้าจอสำคัญที่แสดงการทำงานจริงของการออกแบบระบบ",
    },

    # --- Doc19 section headings ---
    "doc19.sec.1":           {"en": "1. Introduction", "th": "1. บทนำ"},
    "doc19.sec.1.1":         {"en": "1.1 Purpose", "th": "1.1 วัตถุประสงค์"},
    "doc19.sec.1.2":         {"en": "1.2 Scope", "th": "1.2 ขอบเขต"},
    "doc19.sec.1.3":         {"en": "1.3 Definitions", "th": "1.3 นิยามศัพท์"},
    "doc19.sec.1.4":         {"en": "1.4 References", "th": "1.4 เอกสารอ้างอิง"},
    "doc19.sec.1.5":         {"en": "1.5 Test Methodology Overview",
                               "th": "1.5 ภาพรวมวิธีการทดสอบ"},
    "doc19.sec.2":           {"en": "2. Test Environment", "th": "2. สภาพแวดล้อมการทดสอบ"},
    "doc19.sec.2.1":         {"en": "2.1 Hardware & Infrastructure",
                               "th": "2.1 ฮาร์ดแวร์และโครงสร้างพื้นฐาน"},
    "doc19.sec.2.2":         {"en": "2.2 Software & Tools", "th": "2.2 ซอฟต์แวร์และเครื่องมือ"},
    "doc19.sec.2.3":         {"en": "2.3 Test Data Preparation",
                               "th": "2.3 การเตรียมข้อมูลสำหรับการทดสอบ"},
    "doc19.sec.2.4":         {"en": "2.4 System Architecture Under Test",
                               "th": "2.4 สถาปัตยกรรมระบบที่ถูกทดสอบ"},
    "doc19.sec.3":           {"en": "3. Test Plan Summary", "th": "3. สรุปแผนการทดสอบ"},
    "doc19.sec.3.1":         {"en": "3.1 Test Strategy", "th": "3.1 กลยุทธ์การทดสอบ"},
    "doc19.sec.3.2":         {"en": "3.2 Test Categories & Tools",
                               "th": "3.2 หมวดหมู่การทดสอบและเครื่องมือ"},
    "doc19.sec.3.3":         {"en": "3.3 Test Execution Timeline",
                               "th": "3.3 กำหนดการทดสอบ"},
    "doc19.sec.4":           {"en": "4. Test Results", "th": "4. ผลการทดสอบ"},
    "doc19.sec.4.1":         {"en": "4.1 Results Summary", "th": "4.1 สรุปผลการทดสอบ"},
    "doc19.sec.4.2":         {"en": "4.2 Frontend Test Results",
                               "th": "4.2 ผลการทดสอบฝั่ง Frontend"},
    "doc19.sec.4.3":         {"en": "4.3 Backend Test Results",
                               "th": "4.3 ผลการทดสอบฝั่ง Backend"},
    "doc19.sec.4.4":         {"en": "4.4 Integration Test Results",
                               "th": "4.4 ผลการทดสอบการเชื่อมต่อระบบ"},
    "doc19.sec.4.5":         {"en": "4.5 Performance Test Results",
                               "th": "4.5 ผลการทดสอบประสิทธิภาพ"},
    "doc19.sec.4.6":         {"en": "4.6 Security Test Results",
                               "th": "4.6 ผลการทดสอบด้านความปลอดภัย"},
    "doc19.sec.4.7":         {"en": "4.7 API Endpoint Coverage Matrix",
                               "th": "4.7 ตารางความครอบคลุมของ API Endpoint"},
    "doc19.sec.5":           {"en": "5. Defect Analysis", "th": "5. การวิเคราะห์ข้อบกพร่อง"},
    "doc19.sec.5.1":         {"en": "5.1 Defect Summary", "th": "5.1 สรุปข้อบกพร่อง"},
    "doc19.sec.5.2":         {"en": "5.2 Defect Details", "th": "5.2 รายละเอียดข้อบกพร่อง"},
    "doc19.sec.6":           {"en": "6. Test Coverage", "th": "6. ความครอบคลุมของการทดสอบ"},
    "doc19.sec.6.1":         {"en": "6.1 Code Coverage", "th": "6.1 ความครอบคลุมของโค้ด"},
    "doc19.sec.6.2":         {"en": "6.2 Functional Coverage",
                               "th": "6.2 ความครอบคลุมเชิงฟังก์ชัน"},
    "doc19.sec.6.3":         {"en": "6.3 Test Coverage Diagrams",
                               "th": "6.3 แผนภาพความครอบคลุมของการทดสอบ"},
    "doc19.sec.7":           {"en": "7. Evaluation & Recommendation",
                               "th": "7. การประเมินและข้อเสนอแนะ"},
    "doc19.sec.7.1":         {"en": "7.1 Entry Criteria Verification",
                               "th": "7.1 การตรวจสอบเกณฑ์เริ่มต้นทดสอบ"},
    "doc19.sec.7.2":         {"en": "7.2 Exit Criteria Evaluation",
                               "th": "7.2 การประเมินเกณฑ์ปิดงานทดสอบ"},
    "doc19.sec.7.3":         {"en": "7.3 Risk Assessment",
                               "th": "7.3 การประเมินความเสี่ยง"},
    "doc19.sec.7.4":         {"en": "7.4 GO/NO-GO Recommendation",
                               "th": "7.4 ข้อเสนอแนะให้ดำเนินการหรือหยุด (GO/NO-GO)"},
    "doc19.sec.8":           {"en": "8. Sign-Off", "th": "8. การลงนามอนุมัติ"},
    "doc19.sec.appendix_a":  {"en": "Appendix A: Test Execution Screenshots",
                               "th": "ภาคผนวก ก: ภาพหน้าจอผลการทดสอบ"},
    "doc19.sec.appendix_b":  {"en": "Appendix B: Test Flow Diagrams",
                               "th": "ภาคผนวก ข: แผนภาพลำดับการทดสอบ"},
    "doc19.sec.appendix_c":  {"en": "Appendix C: Detailed Test Case Results",
                               "th": "ภาคผนวก ค: ผลการทดสอบรายกรณี"},
    "doc19.scope.intro":     {"en": "Testing covers all system components:",
                               "th": "การทดสอบครอบคลุมทุกองค์ประกอบของระบบ:"},
    "doc19.method.intro":    {"en": "Risk-based testing aligned with ISO/IEC 29119:",
                               "th": "การทดสอบตามความเสี่ยงสอดคล้องกับมาตรฐาน ISO/IEC 29119:"},
    "doc19.phases": {
        "en": ["Phase 1: Unit Testing", "Phase 2: Integration Testing",
               "Phase 3: E2E Testing", "Phase 4: Performance Testing",
               "Phase 5: Security Testing", "Phase 6: Acceptance Testing"],
        "th": ["ระยะที่ 1: การทดสอบหน่วย (Unit Testing)",
               "ระยะที่ 2: การทดสอบการเชื่อมต่อ (Integration Testing)",
               "ระยะที่ 3: การทดสอบตั้งแต่ต้นจนจบ (E2E Testing)",
               "ระยะที่ 4: การทดสอบประสิทธิภาพ (Performance Testing)",
               "ระยะที่ 5: การทดสอบด้านความปลอดภัย (Security Testing)",
               "ระยะที่ 6: การทดสอบการยอมรับ (Acceptance Testing)"],
    },
    "doc19.go_label":        {"en": "RECOMMENDATION: GO", "th": "ข้อเสนอแนะ: GO"},

    # --- Doc19 table headers (defaults) ---
    "doc19.th.category":         {"en": "Category", "th": "หมวดหมู่"},
    "doc19.th.count":             {"en": "Count", "th": "จำนวน"},
    "doc19.th.details":           {"en": "Details", "th": "รายละเอียด"},
    "doc19.th.tool":              {"en": "Tool", "th": "เครื่องมือ"},
    "doc19.th.total":             {"en": "Total", "th": "ทั้งหมด"},
    "doc19.th.passed":            {"en": "Passed", "th": "ผ่าน"},
    "doc19.th.failed":            {"en": "Failed", "th": "ไม่ผ่าน"},
    "doc19.th.blocked":           {"en": "Blocked", "th": "ติดขัด"},
    "doc19.th.pass_rate":         {"en": "Pass Rate", "th": "อัตราผ่าน"},
    "doc19.th.phase":             {"en": "Phase", "th": "ระยะ"},
    "doc19.th.duration":          {"en": "Duration", "th": "ระยะเวลา"},
    "doc19.th.status":            {"en": "Status", "th": "สถานะ"},
    "doc19.th.cases":             {"en": "Cases", "th": "กรณี"},
    "doc19.th.item":              {"en": "Item", "th": "หัวข้อ"},
    "doc19.th.detail":            {"en": "Detail", "th": "รายละเอียด"},
    "doc19.th.module":            {"en": "Module", "th": "โมดูล"},
    "doc19.th.test_type":         {"en": "Test Type", "th": "ประเภทการทดสอบ"},
    "doc19.th.notes":             {"en": "Notes", "th": "หมายเหตุ"},
    "doc19.th.integration_point": {"en": "Integration Point", "th": "จุดเชื่อมต่อ"},
    "doc19.th.method":            {"en": "Method", "th": "วิธี"},
    "doc19.th.result":            {"en": "Result", "th": "ผลลัพธ์"},
    "doc19.th.concurrency":       {"en": "Concurrency", "th": "การทำงานพร้อมกัน"},
    "doc19.th.avg_ms":            {"en": "Avg (ms)", "th": "ค่าเฉลี่ย (ms)"},
    "doc19.th.p95_ms":            {"en": "P95 (ms)", "th": "P95 (ms)"},
    "doc19.th.test_case":         {"en": "Test Case", "th": "กรณีทดสอบ"},
    "doc19.th.route_group":       {"en": "Route Group", "th": "กลุ่มเส้นทาง"},
    "doc19.th.endpoints":         {"en": "Endpoints", "th": "Endpoints"},
    "doc19.th.unit":              {"en": "Unit", "th": "Unit"},
    "doc19.th.integration":       {"en": "Integration", "th": "Integration"},
    "doc19.th.manual":            {"en": "Manual", "th": "Manual"},
    "doc19.th.coverage":          {"en": "Coverage", "th": "ความครอบคลุม"},
    "doc19.th.severity":          {"en": "Severity", "th": "ระดับความรุนแรง"},
    "doc19.th.open":              {"en": "Open", "th": "เปิดอยู่"},
    "doc19.th.fixed":             {"en": "Fixed", "th": "แก้ไขแล้ว"},
    "doc19.th.deferred":          {"en": "Deferred", "th": "เลื่อน"},
    "doc19.th.resolution":        {"en": "Resolution", "th": "การแก้ไข"},
    "doc19.th.component":         {"en": "Component", "th": "องค์ประกอบ"},
    "doc19.th.statements":        {"en": "Statements", "th": "Statements"},
    "doc19.th.branches":          {"en": "Branches", "th": "Branches"},
    "doc19.th.functions":         {"en": "Functions", "th": "Functions"},
    "doc19.th.lines":             {"en": "Lines", "th": "Lines"},
    "doc19.th.area":              {"en": "Area", "th": "ส่วนงาน"},
    "doc19.th.covered":           {"en": "Covered", "th": "ครอบคลุม"},
    "doc19.th.coverage_pct":      {"en": "Coverage %", "th": "ความครอบคลุม %"},
    "doc19.th.criteria":          {"en": "Criteria", "th": "เกณฑ์"},
    "doc19.th.evidence":          {"en": "Evidence", "th": "หลักฐาน"},
    "doc19.th.target":            {"en": "Target", "th": "เป้าหมาย"},
    "doc19.th.actual":            {"en": "Actual", "th": "ผลจริง"},
    "doc19.th.risk":              {"en": "Risk", "th": "ความเสี่ยง"},
    "doc19.th.likelihood":        {"en": "Likelihood", "th": "โอกาส"},
    "doc19.th.impact":            {"en": "Impact", "th": "ผลกระทบ"},
    "doc19.th.mitigation":        {"en": "Mitigation", "th": "การบรรเทา"},
    "doc19.th.signature":         {"en": "Signature", "th": "ลายมือชื่อ"},
    "doc19.th.tc_id":             {"en": "TC ID", "th": "รหัสกรณีทดสอบ"},
    "doc19.th.specification":     {"en": "Specification", "th": "ข้อกำหนด"},
    "doc19.th.provider":          {"en": "Provider", "th": "ผู้ให้บริการ"},
    "doc19.th.region":            {"en": "Region", "th": "ภูมิภาค"},
    "doc19.th.scope":             {"en": "Scope", "th": "ขอบเขต"},
    "doc19.th.version":           {"en": "Version", "th": "เวอร์ชัน"},
    "doc19.th.purpose":           {"en": "Purpose", "th": "วัตถุประสงค์"},
    "doc19.th.test_level":        {"en": "Test Level", "th": "ระดับการทดสอบ"},
    "doc19.th.approach":          {"en": "Approach", "th": "แนวทาง"},
    "doc19.th.automation":        {"en": "Automation", "th": "การทำอัตโนมัติ"},

    # --- Doc19-specific bodies ---
    "doc19.intro.purpose": {
        "en": ("This Test Report documents the comprehensive testing activities and results for the "
               "{project}. It provides evidence of software quality for ISO 9001:2015 compliance."),
        "th": ("รายงานการทดสอบฉบับนี้บันทึกกิจกรรมและผลการทดสอบของระบบ {project} อย่างครบถ้วน "
               "เพื่อเป็นหลักฐานยืนยันคุณภาพซอฟต์แวร์ตามมาตรฐาน ISO 9001:2015"),
    },
    "doc19.recommendation.default": {
        "en": ("Based on the test results and the exit-criteria assessment, the system meets the quality "
               "gates defined for this release. Residual findings, if any, are tracked in the project "
               "issue system with an owner and target release, and will be addressed in subsequent "
               "maintenance cycles following the same test plan and entry/exit discipline."),
        "th": ("จากผลการทดสอบและการประเมินเกณฑ์ปิดงานทดสอบ ระบบเป็นไปตามเกณฑ์คุณภาพที่กำหนดสำหรับการส่งมอบรุ่นนี้ "
               "ประเด็นที่เหลือ (ถ้ามี) ได้รับการบันทึกในระบบติดตามปัญหาของโครงการพร้อมผู้รับผิดชอบและรุ่นเป้าหมาย "
               "และจะได้รับการแก้ไขในรอบบำรุงรักษาถัดไปภายใต้แผนการทดสอบและเกณฑ์เข้า/ออกชุดเดียวกัน"),
    },
}


def T(lang, key, **fmt):
    """Return localized string; fall back to English if TH missing."""
    entry = STRINGS.get(key)
    if not entry:
        return key  # unknown key — visible placeholder
    val = entry.get(lang) or entry.get("en") or key
    if fmt and isinstance(val, str):
        try:
            return val.format(**fmt)
        except (KeyError, IndexError):
            return val
    return val
