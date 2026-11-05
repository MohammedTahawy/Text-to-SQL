#!/usr/bin/env python3
"""
==============================================================================
Enterprise ERP Demo Data Generator & Seeder
Author: Mohamed Tahawy
Repository: executive-erp-ai-copilot
Purpose:
    Generates a clean, realistic, multi-tenant SQLite database (demo_enterprise.db)
    with zero proprietary references. Includes multiple companies, branches,
    warehouses, products, corporate customers, sales representatives, CRM leads,
    and hundreds of verified invoice transactions.
==============================================================================
"""

import os
import random
import sqlite3
import sys
from datetime import datetime, timedelta

def seed_database(target_dir=None):
    if not target_dir:
        target_dir = os.path.dirname(__file__)
    db_path = os.path.join(target_dir, "demo_enterprise.db")

    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[*] Cleared previous database at {db_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("[*] Creating multi-tenant tables...")

    # 1. Companies Table
    cur.execute("""
    CREATE TABLE companies (
        Cmp_No INTEGER PRIMARY KEY,
        company_name TEXT NOT NULL,
        company_name_en TEXT NOT NULL,
        industry TEXT,
        country TEXT
    );
    """)

    companies = [
        (101, "شركة أوبكس العالمية للطاقة والوقود", "Apex Global Energy & Fuel Corp", "Energy & Petroleum", "Saudi Arabia"),
        (201, "شركة أطلس للملاحة والخدمات اللوجستية", "Atlas Maritime & Logistics Co.", "Shipping & Logistics", "Egypt"),
        (301, "مجموعة هورايزون للرعاية الطبية والمستشفيات", "Horizon Healthcare & Medical Centers", "Healthcare", "Saudi Arabia"),
        (401, "شركة فانجارد للتجارة والتوريدات العامة", "Vanguard General Trading & Distribution", "Wholesale & Retail", "UAE"),
    ]
    cur.executemany("INSERT INTO companies VALUES (?,?,?,?,?)", companies)

    # 2. Branches Table
    cur.execute("""
    CREATE TABLE mainbranch (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Brn_NmAr TEXT,
        Brn_NmEn TEXT,
        Cmp_Brn INTEGER,
        is_active INTEGER DEFAULT 1
    );
    """)

    branches = [
        # Apex Energy (101)
        (101, 10101, "الإدارة العامة - الرياض", "Riyadh General Management", 1),
        (101, 10102, "محطة النخيل - بنزين وسولار", "Al-Nakheel Station - Fuel", 2),
        (101, 10103, "محطة طريق الملك فهد - غاز وزيوت", "King Fahd Highway - Oils & Gas", 3),
        (101, 10104, "مركز خدمات وصيانة الشاحنات", "Fleet Maintenance Center", 4),
        # Atlas Logistics (201)
        (201, 20101, "المركز الرئيسي - الإسكندرية", "Alexandria HQ", 1),
        (201, 20102, "مكتب ميناء دمياط", "Damietta Port Terminal", 2),
        (201, 20103, "محطة ميناء الدخيلة اللوجستية", "El-Dekheila Container Hub", 3),
        # Horizon Healthcare (301)
        (301, 30101, "مستشفى هورايزون التخصصي - جدة", "Horizon Specialty Hospital - Jeddah", 1),
        (301, 30102, "مجمع العيادات الخارجية - الأندلس", "Al-Andalus Outpatient Clinics", 2),
        (301, 30103, "صيدلية الطوارئ المركزية", "Central Emergency Pharmacy", 3),
        # Vanguard Trading (401)
        (401, 40101, "الفرع الرئيسي - دبي", "Dubai Main Hub", 1),
        (401, 40102, "فرع أبوظبي للتوزيع", "Abu Dhabi Distribution Center", 2),
    ]
    cur.executemany("INSERT INTO mainbranch (Cmp_No, Brn_No, Brn_NmAr, Brn_NmEn, Cmp_Brn) VALUES (?,?,?,?,?)", branches)

    # 3. Warehouses Table
    cur.execute("""
    CREATE TABLE pjbranchdlv (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Dlv_Stor INTEGER,
        Dlv_NmAr TEXT,
        Dlv_NmEn TEXT
    );
    """)

    warehouses = [
        (101, 1010101, "المستودع البترولي المركزي - الرياض", "Central Fuel Terminal - Riyadh"),
        (101, 1010201, "مستودع الزيوت والشحوم - جدة", "Lubricants & Grease Depo - Jeddah"),
        (201, 2010101, "مستودع الحاويات الجافة - الدخيلة", "Dry Cargo Hub - El Dekheila"),
        (201, 2010201, "مستودع التبريد اللوجستي - دمياط", "Cold Storage Terminal - Damietta"),
        (301, 3010101, "المستودع الدوائي الرئيسي - جدة", "Main Pharmaceuticals Warehouse"),
        (401, 4010101, "مستودع السلع الاستهلاكية - جبل علي", "Consumer Goods Storage - Jebel Ali"),
    ]
    cur.executemany("INSERT INTO pjbranchdlv (Cmp_No, Dlv_Stor, Dlv_NmAr, Dlv_NmEn) VALUES (?,?,?,?)", warehouses)

    # 4. Product Categories & Items
    cur.execute("""
    CREATE TABLE mtsitmcatgry (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Itm_No INTEGER,
        Itm_NmAr TEXT,
        Itm_NmEn TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE mtsitmunit (
        Unit_No INTEGER PRIMARY KEY,
        Unit_NmAr TEXT,
        Unit_NmEn TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE mtsitmmfs (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Itm_No INTEGER,
        Itm_Parnt INTEGER,
        Itm_NmAr TEXT,
        Itm_NmEn TEXT,
        Unit_No INTEGER,
        Itm_Sal REAL,
        Itm_Pur REAL,
        Itm_Active INTEGER DEFAULT 1,
        Sup_No INTEGER DEFAULT 1
    );
    """)

    cur.executemany("INSERT INTO mtsitmunit VALUES (?,?,?)", [
        (1, "لتر", "Liter"),
        (2, "طن", "Ton"),
        (3, "برميل", "Barrel"),
        (4, "حاوية 40 قدم", "40ft Container"),
        (5, "علبة / عبوة", "Pack / Box"),
        (6, "كرتونة", "Carton"),
        (7, "قطعة", "Piece")
    ])

    categories = [
        (101, 10, "منتجات الوقود والمحروقات", "Fuels & Hydrocarbons"),
        (101, 20, "زيوت المحركات والشحوم الصناعية", "Motor Oils & Lubricants"),
        (201, 30, "خدمات الشحن البحري والترانزيت", "Ocean Freight & Transit"),
        (201, 40, "خدمات التخليص والمناولة الجمركية", "Customs Clearance & Handling"),
        (301, 50, "أدوية ومستحضرات طبية", "Pharmaceuticals"),
        (301, 60, "مستهلكات ومستلزمات المستشفيات", "Medical Consumables"),
        (401, 70, "أجهزة إلكترونية وتقنية", "Electronics & Devices"),
        (401, 80, "أدوات منزلية ومكتبية", "Home & Office Supplies"),
    ]
    cur.executemany("INSERT INTO mtsitmcatgry (Cmp_No, Itm_No, Itm_NmAr, Itm_NmEn) VALUES (?,?,?,?)", categories)

    items_data = [
        # Apex Energy
        (101, 1001, 10, "بنزين سوبر أوكتان 95", "Super Gasoline 95 Octane", 1, 2.33, 1.95),
        (101, 1002, 10, "بنزين ممتاز أوكتان 91", "Premium Gasoline 91 Octane", 1, 2.18, 1.80),
        (101, 1003, 10, "سولار ديزل منخفض الكبريت", "Ultra Low Sulfur Diesel", 1, 1.15, 0.90),
        (101, 1004, 20, "زيت محركات تخليقي 5W-40 (برميل)", "Synthetic Motor Oil 5W-40 (Barrel)", 3, 4200.0, 3100.0),
        (101, 1005, 20, "شحم صناعي عالي التحمل للتروس", "Heavy-Duty Gear Grease (Carton)", 6, 850.0, 620.0),
        # Atlas Logistics
        (201, 2001, 30, "خدمة شحن بحري حاوية 40 قدم - خط الخليج", "Ocean Freight 40ft - Gulf Route", 4, 18500.0, 14000.0),
        (201, 2002, 30, "خدمة شحن بحري حاوية 20 قدم - خط البحر المتوسط", "Ocean Freight 20ft - Med Route", 4, 11200.0, 8500.0),
        (201, 2003, 40, "رسوم تخليص جمركي ومناولة سريعة", "Expedited Customs Clearance", 7, 3500.0, 2200.0),
        (201, 2004, 40, "خدمة تخزين مبرد للشحنات الغذائية (شهري)", "Cold Storage Monthly Slot", 7, 7500.0, 5000.0),
        # Horizon Healthcare
        (301, 3001, 50, "محلول ملحي معقم وريدي 500 مل", "Sterile Saline IV Solution 500ml", 5, 45.0, 28.0),
        (301, 3002, 50, "مضاد حيوي واسع المجال أموكسيسيلين 1 جم", "Amoxicillin Broad Spectrum 1g", 5, 88.0, 55.0),
        (301, 3003, 60, "قفازات فحص طبية لاتكس معقمة (كرتونة)", "Medical Latex Gloves (Box)", 6, 220.0, 150.0),
        (301, 3004, 60, "شاش جراحي معقم عالي الامتصاص", "Sterile Surgical Gauze Pack", 5, 35.0, 20.0),
        # Vanguard Trading
        (401, 4001, 70, "شاشة ذكية فائقة الدقة 65 بوصة 4K", "Ultra HD Smart Screen 65-inch 4K", 7, 3400.0, 2600.0),
        (401, 4002, 70, "حاسوب محمول للأعمال Core i7 16GB", "Business Laptop Core i7 16GB", 7, 4800.0, 3900.0),
        (401, 4003, 80, "طابعة ليزر متعددة الوظائف لاسلكية", "Multifunction Wireless Laser Printer", 7, 1250.0, 950.0),
    ]
    cur.executemany("INSERT INTO mtsitmmfs (Cmp_No, Itm_No, Itm_Parnt, Itm_NmAr, Itm_NmEn, Unit_No, Itm_Sal, Itm_Pur) VALUES (?,?,?,?,?,?,?,?)", items_data)

    # 5. Sales Representatives Table
    cur.execute("""
    CREATE TABLE astsalesman (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Slm_No INTEGER,
        Slm_NmAr TEXT,
        Slm_NmEn TEXT,
        Target REAL,
        TCashCheqe REAL DEFAULT 0
    );
    """)

    salesmen = [
        (101, 10101, 10101, "م. طارق عبد الرحمن الجوهري", "Tarek Al-Gohary", 5000000.0),
        (101, 10102, 10102, "خالد بن عبد الله السبيعي", "Khaled Al-Subaie", 3500000.0),
        (101, 10103, 10103, "يوسف بن مسعود الشمري", "Yousef Al-Shammari", 4000000.0),
        (201, 20101, 20101, "أحمد فاروق المرسي", "Ahmed El-Morsy", 2500000.0),
        (201, 20102, 20102, "كريم علاء الدين الشاذلي", "Karim El-Shazly", 1800000.0),
        (301, 30101, 30101, "د. نهى سامي الطحاوي", "Dr. Noha Al-Tahawy", 1200000.0),
        (301, 30102, 30102, "مروان عصام الدسوقي", "Marwan El-Desouky", 900000.0),
        (401, 40101, 40101, "سلطان سالم المهيري", "Sultan Al-Mehairi", 2000000.0),
        (401, 40102, 40102, "عمر هشام الخاجة", "Omar Al-Khaja", 1500000.0),
    ]
    cur.executemany("INSERT INTO astsalesman (Cmp_No, Brn_No, Slm_No, Slm_NmAr, Slm_NmEn, Target) VALUES (?,?,?,?,?,?)", salesmen)

    # 6. Customers Table
    cur.execute("""
    CREATE TABLE mtscustomer (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Cstm_No INTEGER,
        Cstm_NmAr TEXT,
        Cstm_NmEn TEXT,
        Cstm_Tel TEXT,
        Credit_Value REAL,
        Credit_Days INTEGER,
        Slm_No INTEGER,
        Cstm_Active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    customers = [
        # Apex Energy Clients
        (101, 10101, 101001, "شركة الوفاق للنقل البري والخدمات اللوجستية", "Al-Wefaq Logistics & Transport", "+966501112233", 850000.0, 45, 10101),
        (101, 10102, 101002, "مؤسسة الرواد للتطوير الإنشائي والمقاولات", "Al-Rowad Contracting & Development", "+966502223344", 600000.0, 30, 10102),
        (101, 10103, 101003, "شركة أساطيل الخليج للشحن الثقيل", "Gulf Fleets Heavy Haulage", "+966503334455", 1200000.0, 60, 10103),
        (101, 10101, 101004, "مصانع الشرق لمواد البناء المتقدمة", "Al-Sharq Advanced Building Materials", "+966504445566", 450000.0, 30, 10101),
        # Atlas Logistics Clients
        (201, 20101, 201001, "الشركة المصرية الأوروبية للاستيراد والتصدير", "Egyptian European Import & Export", "+201011223344", 500000.0, 30, 20101),
        (201, 20102, 201002, "مجموعة الفرسان للتجارة الدولية والتوكيلات", "Al-Forsan International Agencies", "+201022334455", 750000.0, 45, 20102),
        (201, 20101, 201003, "شركة النيل للشحن والتوريدات العملاقة", "Nile Super Shipping & Supplies", "+201033445566", 900000.0, 60, 20101),
        # Horizon Healthcare Clients
        (301, 30101, 301001, "مستشفى دار الشفاء التخصصي", "Dar Al-Shifa Specialist Hospital", "+966551122334", 300000.0, 30, 30101),
        (301, 30102, 301002, "سلسلة صيدليات الرعاية الأولى", "First Care Pharmacy Chain", "+966552233445", 400000.0, 45, 30102),
        # Vanguard Trading Clients
        (401, 40101, 401001, "مؤسسة الأفق الذكي للتكنولوجيا", "Smart Horizon Tech Est.", "+971501234567", 650000.0, 30, 40101),
        (401, 40102, 401002, "شركة النخبة للتجهيزات الفندقية والمكتبية", "Elite Hotel & Office Outfitting", "+971509876543", 500000.0, 45, 40102),
    ]
    cur.executemany("INSERT INTO mtscustomer (Cmp_No, Brn_No, Cstm_No, Cstm_NmAr, Cstm_NmEn, Cstm_Tel, Credit_Value, Credit_Days, Slm_No) VALUES (?,?,?,?,?,?,?,?,?)", customers)

    # 7. CRM Leads Table
    cur.execute("""
    CREATE TABLE crm_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Lead_No INTEGER,
        Lead_NmAr TEXT,
        Lead_Value REAL,
        Lead_Tel TEXT,
        Lead_Email TEXT,
        Last_contact TEXT,
        Slm_No INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    leads = [
        (101, 10101, 501, "مشروع إمداد أسطول قطار الشرق السريع بالديزل", 2500000.0, "+966509988771", "fleet@orient-rail.sa", "2026-11-02", 10101),
        (101, 10102, 502, "عقد تزويد حافلات العمرة بالوقود والزيوت", 1800000.0, "+966509988772", "tenders@umrah-bus.sa", "2026-10-28", 10102),
        (201, 20101, 503, "صفقة استيراد وتخليص 120 حاوية حبوب زراعية", 1450000.0, "+201099887711", "import@agri-delta.com", "2026-11-01", 20101),
        (301, 30101, 504, "مناقصة توريد محاليل وريدية لمراكز الكلى", 850000.0, "+966559988773", "supplies@renal-care.org", "2026-10-30", 30101),
        (401, 40101, 505, "عقد تحديث وتجهيز الحواسب لجامعة دبي الحديثة", 1200000.0, "+971509988774", "procurement@dubai-uni.ae", "2026-11-03", 40101),
    ]
    cur.executemany("INSERT INTO crm_leads (Cmp_No, Brn_No, Lead_No, Lead_NmAr, Lead_Value, Lead_Tel, Lead_Email, Last_contact, Slm_No) VALUES (?,?,?,?,?,?,?,?,?)", leads)

    # 8. Sales Invoices Header & Details
    cur.execute("""
    CREATE TABLE invlodhdr (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Doc_No INTEGER,
        Doc_Dt TEXT,
        Doc_Ty INTEGER,
        Cstm_No INTEGER,
        Slm_No INTEGER,
        Dlv_Stor INTEGER,
        Tot_Sal REAL,
        Paid_Total REAL,
        Pymt_Val REAL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE invloddtl (
        ID_No INTEGER PRIMARY KEY AUTOINCREMENT,
        Cmp_No INTEGER,
        Brn_No INTEGER,
        Doc_No INTEGER,
        Doc_Ty INTEGER,
        Doc_Dt TEXT,
        Itm_No INTEGER,
        Unit_No INTEGER,
        Qty REAL,
        Itm_Sal REAL,
        Itm_Pur REAL,
        Titm_Sal REAL,
        Taxv_ExtraDtl REAL,
        Dlv_Stor INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    print("[*] Generating 320 enterprise sales transactions across 2026...")

    start_date = datetime(2026, 8, 1)
    end_date = datetime(2026, 11, 4)
    days_span = (end_date - start_date).days

    doc_counter = 10001
    invoices_hdr = []
    invoices_dtl = []

    cmp_items = {
        101: [i for i in items_data if i[0] == 101],
        201: [i for i in items_data if i[0] == 201],
        301: [i for i in items_data if i[0] == 301],
        401: [i for i in items_data if i[0] == 401],
    }

    cmp_customers = {
        101: [c for c in customers if c[0] == 101],
        201: [c for c in customers if c[0] == 201],
        301: [c for c in customers if c[0] == 301],
        401: [c for c in customers if c[0] == 401],
    }

    cmp_salesmen = {
        101: [s for s in salesmen if s[0] == 101],
        201: [s for s in salesmen if s[0] == 201],
        301: [s for s in salesmen if s[0] == 301],
        401: [s for s in salesmen if s[0] == 401],
    }

    cmp_wh = {
        101: 1010101,
        201: 2010101,
        301: 3010101,
        401: 4010101,
    }

    random.seed(42)

    for i in range(320):
        cmp_no = random.choices([101, 201, 301, 401], weights=[45, 25, 15, 15])[0]

        offset_days = random.choices(
            range(days_span),
            weights=[1 if d < 30 else 3 if d < 60 else 6 if d < 90 else 5 for d in range(days_span)]
        )[0]
        inv_date = (start_date + timedelta(days=offset_days)).strftime("%Y-%m-%d")

        cust = random.choice(cmp_customers[cmp_no])
        slm = random.choice(cmp_salesmen[cmp_no])
        brn_no = cust[1]
        cstm_no = cust[2]
        slm_no = slm[2]
        wh_no = cmp_wh[cmp_no]

        doc_no = doc_counter
        doc_counter += 1

        items_chosen = random.sample(cmp_items[cmp_no], k=random.randint(1, min(3, len(cmp_items[cmp_no]))))
        inv_total = 0.0

        for itm in items_chosen:
            qty = random.randint(10, 500) if cmp_no == 101 and itm[5] == 1 else random.randint(1, 20)
            price = itm[6]
            cost = itm[7]
            line_total = round(qty * price, 2)
            tax = round(line_total * 0.15, 2)
            inv_total += line_total

            invoices_dtl.append((
                cmp_no, brn_no, doc_no, 13, inv_date, itm[1], itm[5],
                qty, price, cost, line_total, tax, wh_no
            ))

        pay_type = random.choices(["full", "partial", "unpaid"], weights=[70, 20, 10])[0]
        if pay_type == "full":
            paid = inv_total
        elif pay_type == "partial":
            paid = round(inv_total * random.uniform(0.3, 0.7), 2)
        else:
            paid = 0.0

        invoices_hdr.append((
            cmp_no, brn_no, doc_no, inv_date, 13, cstm_no, slm_no, wh_no,
            round(inv_total, 2), round(paid, 2), round(paid, 2)
        ))

    cur.executemany("""
    INSERT INTO invlodhdr (Cmp_No, Brn_No, Doc_No, Doc_Dt, Doc_Ty, Cstm_No, Slm_No, Dlv_Stor, Tot_Sal, Paid_Total, Pymt_Val)
    VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, invoices_hdr)

    cur.executemany("""
    INSERT INTO invloddtl (Cmp_No, Brn_No, Doc_No, Doc_Ty, Doc_Dt, Itm_No, Unit_No, Qty, Itm_Sal, Itm_Pur, Titm_Sal, Taxv_ExtraDtl, Dlv_Stor)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, invoices_dtl)

    print(f"  [+] Inserted {len(invoices_hdr)} invoice headers and {len(invoices_dtl)} line items.")

    # -------------------------------------------------------------------------
    # 9. Create Curated Semantic Views
    # -------------------------------------------------------------------------
    print("[*] Creating analytical semantic views...")

    cur.execute("""
    CREATE VIEW v_sales_invoices AS
    SELECT 
        hdr.ID_No AS invoice_id,
        hdr.Cmp_No,
        cmp.company_name,
        cmp.company_name_en,
        hdr.Brn_No,
        brn.Brn_NmAr AS branch_name,
        hdr.Doc_No AS invoice_number,
        hdr.Doc_Dt AS invoice_date,
        hdr.Doc_Ty AS invoice_type_id,
        CASE 
            WHEN hdr.Doc_Ty = 13 THEN 'مبيعات'
            WHEN hdr.Doc_Ty = 14 THEN 'مردود مبيعات'
            WHEN hdr.Doc_Ty = 1 THEN 'مشتريات'
            ELSE 'أخرى'
        END AS invoice_type_name,
        hdr.Cstm_No AS customer_id,
        cst.Cstm_NmAr AS customer_name,
        hdr.Slm_No AS salesman_id,
        slm.Slm_NmAr AS salesman_name,
        hdr.Dlv_Stor AS warehouse_id,
        wh.Dlv_NmAr AS warehouse_name,
        COALESCE(hdr.Tot_Sal, 0) AS total_amount,
        COALESCE(hdr.Paid_Total, 0) AS paid_amount,
        (COALESCE(hdr.Tot_Sal, 0) - COALESCE(hdr.Paid_Total, 0)) AS remaining_amount,
        hdr.created_at
    FROM invlodhdr hdr
    LEFT JOIN companies cmp ON cmp.Cmp_No = hdr.Cmp_No
    LEFT JOIN mainbranch brn ON brn.Cmp_No = hdr.Cmp_No AND brn.Brn_No = hdr.Brn_No
    LEFT JOIN mtscustomer cst ON cst.Cmp_No = hdr.Cmp_No AND cst.Cstm_No = hdr.Cstm_No
    LEFT JOIN astsalesman slm ON slm.Cmp_No = hdr.Cmp_No AND slm.Slm_No = hdr.Slm_No
    LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = hdr.Cmp_No AND wh.Dlv_Stor = hdr.Dlv_Stor;
    """)

    cur.execute("""
    CREATE VIEW v_sales_invoice_items AS
    SELECT 
        dtl.ID_No AS line_id,
        dtl.Cmp_No,
        cmp.company_name,
        cmp.company_name_en,
        dtl.Brn_No,
        dtl.Doc_No AS invoice_number,
        dtl.Doc_Dt AS invoice_date,
        dtl.Doc_Ty AS invoice_type_id,
        dtl.Itm_No AS item_code,
        itm.Itm_NmAr AS item_name,
        itm.Itm_NmEn AS item_name_en,
        cat.Itm_NmAr AS category_name,
        dtl.Unit_No AS unit_id,
        unt.Unit_NmAr AS unit_name,
        dtl.Qty AS quantity,
        COALESCE(dtl.Itm_Sal, 0) AS unit_price,
        COALESCE(dtl.Titm_Sal, dtl.Qty * dtl.Itm_Sal, 0) AS line_total,
        COALESCE(dtl.Taxv_ExtraDtl, 0) AS tax_amount,
        dtl.Dlv_Stor AS warehouse_id,
        wh.Dlv_NmAr AS warehouse_name
    FROM invloddtl dtl
    LEFT JOIN companies cmp ON cmp.Cmp_No = dtl.Cmp_No
    LEFT JOIN mtsitmmfs itm ON itm.Cmp_No = dtl.Cmp_No AND itm.Itm_No = dtl.Itm_No
    LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
    LEFT JOIN mtsitmunit unt ON unt.Unit_No = dtl.Unit_No
    LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = dtl.Cmp_No AND wh.Dlv_Stor = dtl.Dlv_Stor;
    """)

    cur.execute("""
    CREATE VIEW v_inventory_stock AS
    SELECT 
        itm.ID_No AS item_id,
        itm.Cmp_No,
        cmp.company_name,
        itm.Itm_No AS item_code,
        itm.Itm_NmAr AS item_name,
        itm.Itm_NmEn AS item_name_en,
        cat.Itm_NmAr AS category_name,
        unt.Unit_NmAr AS primary_unit,
        itm.Itm_Sal AS selling_price,
        itm.Itm_Active AS is_active
    FROM mtsitmmfs itm
    LEFT JOIN companies cmp ON cmp.Cmp_No = itm.Cmp_No
    LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
    LEFT JOIN mtsitmunit unt ON unt.Unit_No = itm.Unit_No;
    """)

    cur.execute("""
    CREATE VIEW v_customers_overview AS
    SELECT 
        cst.ID_No AS customer_id,
        cst.Cmp_No,
        cmp.company_name,
        cst.Brn_No,
        cst.Cstm_No AS customer_code,
        cst.Cstm_NmAr AS customer_name,
        cst.Cstm_NmEn AS customer_name_en,
        cst.Cstm_Tel AS telephone,
        cst.Credit_Value AS credit_limit,
        cst.Credit_Days AS credit_days,
        slm.Slm_NmAr AS assigned_salesman,
        cst.Cstm_Active AS is_active,
        cst.created_at
    FROM mtscustomer cst
    LEFT JOIN companies cmp ON cmp.Cmp_No = cst.Cmp_No
    LEFT JOIN astsalesman slm ON slm.Cmp_No = cst.Cmp_No AND slm.Slm_No = cst.Slm_No;
    """)

    cur.execute("""
    CREATE VIEW v_salesmen_overview AS
    SELECT 
        slm.ID_No AS salesman_id,
        slm.Cmp_No,
        cmp.company_name,
        slm.Brn_No,
        slm.Slm_No AS salesman_code,
        slm.Slm_NmAr AS salesman_name,
        slm.Target AS sales_target,
        brn.Brn_NmAr AS branch_name
    FROM astsalesman slm
    LEFT JOIN companies cmp ON cmp.Cmp_No = slm.Cmp_No
    LEFT JOIN mainbranch brn ON brn.Cmp_No = slm.Cmp_No AND brn.Brn_No = slm.Brn_No;
    """)

    cur.execute("""
    CREATE VIEW v_crm_leads_overview AS
    SELECT 
        lead.id AS lead_id,
        lead.Cmp_No,
        cmp.company_name,
        lead.Brn_No,
        lead.Lead_No AS lead_number,
        lead.Lead_NmAr AS lead_name,
        lead.Lead_Value AS estimated_value,
        lead.Lead_Tel AS phone,
        lead.Lead_Email AS email,
        lead.Last_contact AS last_contact_date,
        slm.Slm_NmAr AS assigned_salesman,
        lead.created_at
    FROM crm_leads lead
    LEFT JOIN companies cmp ON cmp.Cmp_No = lead.Cmp_No
    LEFT JOIN astsalesman slm ON slm.Cmp_No = lead.Cmp_No AND slm.Slm_No = lead.Slm_No;
    """)

    conn.commit()
    conn.close()
    print(f"[✓] Database demo seeding complete: {db_path}")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    seed_database(target)
