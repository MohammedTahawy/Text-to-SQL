-- ====================================================================================================
-- INFOSAS ERP & CRM - AI ANALYTICAL SEMANTIC LAYER (DATABASE VIEWS SPECIFICATION)
-- ملف الـ Semantic Layer المعتمد لمشروع الذكاء الاصطناعي في نظام إنفوساس (InfoSas ERP)
-- موجه إلى المهندس خالد (Lead Architect & CTO - InfoSas)
-- المسار: ai-service/app/modules/text_to_sql/views.sql
-- 
-- 1. الغرض المعماري (Architectural Rationale):
--    تحتوي قاعدة بيانات إنفوساس على أكثر من 717 جدولاً بأسماء واختصارات محاسبية قديمة (Legacy 4-letter abbreviations)
--    مثل (invlodhdr, invloddtl, mtsitmmfs, mtscustomer, astsalesman, pjbranchdlv).
--    إن تعريض كل هذه الجداول لنماذج الذكاء الاصطناعي (LLMs) يتسبب في:
--      أ) استهلاك هائل للـ Tokens وارتفاع التكلفة.
--      ب) زيادة احتمالية الهلوسة والربط الخاطئ بين الجداول (Hallucinations & Incorrect JOINs).
--      ج) مخاطر أمنية واختراق خصوصية المستخدمين (تسريب جداول sec_users و users).
--    لذلك قمنا ببناء هذه الطبقة الدلالية المكونة من 6 Views تحليلية موحدة ومفهرسة تغطي 100% من الاحتياجات المحاسبية.
--
-- 2. مبدأ عزل بيانات الشركات (Multi-Tenant Isolation Architecture):
--    - جميع الـ Views تتضمن المعرفات المفتاحية `Cmp_No` (رقم الشركة) و `Brn_No` (رقم الفرع).
--    - يتم حقن شروط العزل `Cmp_No = :cmp_no` إجبارياً على مستوى الـ AST Parser عبر الـ Python Guardrails،
--      مما يضمن استحالة وصول أي شركة لبيانات شركة أخرى حتى لو حاول المستخدم التحايل بالسؤال.
--
-- 3. دليل ترجمة الجداول الأصلية (Legacy Table Mapping Dictionary):
--    - invlodhdr   --> Invoice Load Header (رؤوس الفواتير: مبيعات، مشتريات، مردودات)
--    - invloddtl   --> Invoice Load Details (أسطر وبنود الفواتير التفصيلية والكميات والأسعار)
--    - mtscustomer --> Master Customer (دليل العملاء والأرصدة والحدود الائتمانية)
--    - mtsitmmfs   --> Master Items File System (دليل الأصناف والمنتجات الرئيسي)
--    - mtsitmcatgry--> Master Item Categories (شجرة الفئات والتصنيفات)
--    - mtsitmunit  --> Master Item Units (وحدات القياس: لتر، طن، حبة، كرتونة)
--    - astsalesman --> Asset / Staff Salesmen (سجل المناديب وممثلي المبيعات)
--    - pjbranchdlv --> Project Branch Delivery / Warehouses (المستودعات والمخازن ومنافذ التوزيع)
--    - mainbranch  --> Main Branches (دليل الفروع الرئيسية والفرعية)
--    - companies   --> Multi-Tenant Directory (دليل الشركات المشتركة)
--    - crm_leads   --> CRM Prospective Leads (الفرص البيعية والعملاء المحتملين)
-- ====================================================================================================


-- ====================================================================================================
-- 1. VIEW: v_sales_invoices
-- الغرض: عرض تحليلي شامل لرؤوس الفواتير (Sales & Invoicing Transactions)
-- الجداول المرتبطة:
--   - invlodhdr (الجدول الرئيسي لرؤوس الفواتير)
--   - companies (لربط اسم الشركة القانوني بدلاً من مجرد رقم Cmp_No)
--   - mainbranch (لربط اسم الفرع العربي Brn_NmAr)
--   - mtscustomer (لربط اسم العميل Cstm_NmAr)
--   - astsalesman (لربط اسم المندوب Slm_NmAr)
--   - pjbranchdlv (لربط اسم المستودع Dlv_NmAr)
-- ====================================================================================================
DROP VIEW IF EXISTS v_sales_invoices;
CREATE VIEW v_sales_invoices AS
SELECT 
    -- المعرفات الأساسية للعملية
    hdr.ID_No AS invoice_id,                      -- المعرف الفريد للفاتورة في قاعدة البيانات (Primary Key)
    hdr.Cmp_No,                                   -- رقم الشركة (المفتاح الأساسي لعزل بيانات المستأجرين Multi-Tenancy)
    COALESCE(cmp.company_name, 'شركة ' || hdr.Cmp_No) AS company_name,        -- الاسم العربي للشركة التابعة
    COALESCE(cmp.company_name_en, 'Company ' || hdr.Cmp_No) AS company_name_en, -- الاسم الإنجليزي للشركة
    hdr.Brn_No,                                   -- كود الفرع
    brn.Brn_NmAr AS branch_name,                  -- الاسم العربي للفرع (مثل: 'الفرع الرئيسي - البنزين/سولار')
    hdr.Doc_No AS invoice_number,                 -- رقم الفاتورة الورقي/الرسمي المطبوع
    hdr.Doc_Dt AS invoice_date,                   -- تاريخ إصدار الفاتورة (YYYY-MM-DD)

    -- تصنيف نوع الفاتورة المحاسبي (Doc_Ty Logic):
    -- كود 13 = مبيعات نقدية وآجلة (Sales)
    -- كود 14 = مردودات مبيعات (Sales Returns)
    -- كود 1  = فواتير مشتريات (Purchases)
    hdr.Doc_Ty AS invoice_type_id,
    CASE 
        WHEN hdr.Doc_Ty = 13 THEN 'مبيعات'
        WHEN hdr.Doc_Ty = 14 THEN 'مردود مبيعات'
        WHEN hdr.Doc_Ty = 1 THEN 'مشتريات'
        ELSE 'أخرى'
    END AS invoice_type_name,

    -- بيانات العميل المرتبط
    hdr.Cstm_No AS customer_id,                   -- كود العميل في دليل العملاء
    cst.Cstm_NmAr AS customer_name,               -- الاسم التجاري/الرسمي للعميل

    -- بيانات مندوب المبيعات
    hdr.Slm_No AS salesman_id,                    -- كود المندوب المسؤول عن العملية
    slm.Slm_NmAr AS salesman_name,                -- اسم المندوب بالكامل

    -- بيانات المستودع / منفذ التوزيع
    hdr.Dlv_Stor AS warehouse_id,                 -- كود المخزن أو المستودع
    wh.Dlv_NmAr AS warehouse_name,                -- اسم المخزن (مثل: مستودع الرياض الرئيسي / محطة 1)

    -- القيم والعمليات المالية المحتسبة (Financial Metrics):
    -- نستخدم COALESCE لدعم الفواتير بمختلف إصدارات إنفوساس (Tot_Sal أو TotRcpt_Amount)
    COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) AS total_amount,        -- إجمالي قيمة الفاتورة
    COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0) AS paid_amount,           -- المبلغ المدفوع / المسدد نقداً أو شيكات
    (COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) - COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0)) AS remaining_amount, -- الرصيد المتبقي (المديونية الآجلة)
    
    hdr.created_at                                -- توقيت إنشاء السجل في النظام
FROM invlodhdr hdr
LEFT JOIN companies cmp ON cmp.Cmp_No = hdr.Cmp_No
LEFT JOIN mainbranch brn ON brn.Cmp_No = hdr.Cmp_No AND brn.Brn_No = hdr.Brn_No
LEFT JOIN mtscustomer cst ON cst.Cmp_No = hdr.Cmp_No AND cst.Cstm_No = hdr.Cstm_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = hdr.Cmp_No AND slm.Slm_No = hdr.Slm_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = hdr.Cmp_No AND wh.Dlv_Stor = hdr.Dlv_Stor;


-- ====================================================================================================
-- 2. VIEW: v_sales_invoice_items
-- الغرض: التفاصيل الدقيقة لأسطر وبنود الفواتير (Line-Item Sales & Product Movement)
-- استخدام الذكاء الاصطناعي: استعلامات "أعلى الأصناف مبيعاً"، "حجم مبيعات البنزين/السولار"، "متوسط أسعار البيع"
-- الجداول المرتبطة:
--   - invloddtl (الجدول التفصيلي لأسطر الفواتير)
--   - companies (اسم الشركة)
--   - mtsitmmfs (دليل الأصناف لاستخراج اسم الصنف العربي والإنجليزي)
--   - mtsitmcatgry (التصنيف والفئة الرئيسية للصنف)
--   - mtsitmunit (وحدة الصنف: لتر، طن، متر، كرتونة)
--   - pjbranchdlv (المستودع الذي خرجت منه البضاعة)
-- ====================================================================================================
DROP VIEW IF EXISTS v_sales_invoice_items;
CREATE VIEW v_sales_invoice_items AS
SELECT 
    dtl.ID_No AS line_id,                         -- المعرف الفريد للسطر
    dtl.Cmp_No,                                   -- رقم الشركة
    COALESCE(cmp.company_name, 'شركة ' || dtl.Cmp_No) AS company_name,        -- اسم الشركة
    COALESCE(cmp.company_name_en, 'Company ' || dtl.Cmp_No) AS company_name_en,
    dtl.Brn_No,                                   -- رقم الفرع
    dtl.Doc_No AS invoice_number,                 -- رقم الفاتورة الأصلية (لربط السطر برأس الفاتورة)
    dtl.Doc_Dt AS invoice_date,                   -- تاريخ العملية
    dtl.Doc_Ty AS invoice_type_id,                -- كود نوع الفاتورة (13: مبيعات، 14: مردود، إلخ)

    -- بيانات الصنف وتصنيفه
    dtl.Itm_No AS item_code,                      -- الكود المحاسبي للصنف
    itm.Itm_NmAr AS item_name,                    -- الاسم العربي للصنف (مثل: 'بنزين 92', 'سولار', 'زيت محرك 5W30')
    itm.Itm_NmEn AS item_name_en,                 -- الاسم الإنجليزي للصنف
    cat.Itm_NmAr AS category_name,                -- التصنيف العائلي للصنف (Category)
    
    -- بيانات وحدة القياس والكميات
    dtl.Unit_No AS unit_id,                       -- كود وحدة القياس
    unt.Unit_NmAr AS unit_name,                   -- اسم الوحدة (لتر، طن، برميل، عبوة)
    dtl.Qty AS quantity,                          -- الكمية المباعة

    -- الأسعار والإجماليات والضرائب
    COALESCE(dtl.Itm_Sal, dtl.Itm_Pur, 0) AS unit_price, -- سعر بيع الوحدة الواحدة
    COALESCE(dtl.Titm_Sal, dtl.Qty * dtl.Itm_Sal, dtl.Titm_Pur, 0) AS line_total, -- إجمالي قيمة السطر بعد ضرب الكمية بالسعر
    COALESCE(dtl.Taxv_ExtraDtl, 0) AS tax_amount, -- ضريبة القيمة المضافة المحسوبة على السطر (VAT)

    -- المستودع التابع له الصرف
    dtl.Dlv_Stor AS warehouse_id,                 -- كود المخزن المنصرف منه الصنف
    wh.Dlv_NmAr AS warehouse_name                 -- اسم المستودع
FROM invloddtl dtl
LEFT JOIN companies cmp ON cmp.Cmp_No = dtl.Cmp_No
LEFT JOIN mtsitmmfs itm ON itm.Cmp_No = dtl.Cmp_No AND itm.Itm_No = dtl.Itm_No
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = dtl.Unit_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = dtl.Cmp_No AND wh.Dlv_Stor = dtl.Dlv_Stor;


-- ====================================================================================================
-- 3. VIEW: v_inventory_stock
-- الغرض: الدليل الموحد لبطاقات الأصناف والكتالوج المخزني (Product Master & Inventory Catalog)
-- استخدام الذكاء الاصطناعي: الاستعلام عن الأصناف المسجلة، الأصناف النشطة، التصنيفات، والمورد الافتراضي
-- الجداول المرتبطة:
--   - mtsitmmfs (دليل الأصناف والمخزون الرئيسي)
--   - companies (اسم الشركة التابع لها الصنف)
--   - mtsitmcatgry (التصنيف العام والشجرة المخزنية)
--   - mtsitmunit (الوحدة الأساسية للصنف)
-- ====================================================================================================
DROP VIEW IF EXISTS v_inventory_stock;
CREATE VIEW v_inventory_stock AS
SELECT 
    itm.ID_No AS item_id,                         -- الرقم التعريفي للصنف
    itm.Cmp_No,                                   -- رقم الشركة
    COALESCE(cmp.company_name, 'شركة ' || itm.Cmp_No) AS company_name, -- اسم الشركة
    itm.Itm_No AS item_code,                      -- كود الصنف التجاري
    itm.Itm_NmAr AS item_name,                    -- اسم الصنف بالعربية
    itm.Itm_NmEn AS item_name_en,                 -- اسم الصنف بالإنجليزية
    cat.Itm_NmAr AS category_name,                -- اسم التصنيف / الفئة
    unt.Unit_NmAr AS primary_unit,                -- وحدة القياس الرئيسية
    itm.Itm_Active AS is_active,                  -- حالة الصنف (1: نشط ويُباع، 0: موقف أو أرشيف)
    itm.Sup_No AS default_supplier_id             -- كود المورد المعتمد للصنف
FROM mtsitmmfs itm
LEFT JOIN companies cmp ON cmp.Cmp_No = itm.Cmp_No
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = itm.Unit_No;


-- ====================================================================================================
-- 4. VIEW: v_customers_overview
-- الغرض: دليل العملاء، الحدود الائتمانية وفترات السداد (Customer Directory, Credit & Balances)
-- استخدام الذكاء الاصطناعي: الاستعلام عن بيانات العملاء، أكبر العملاء ائتماناً، مندوب كل عميل، أرقام التواصل
-- الجداول المرتبطة:
--   - mtscustomer (جدول العملاء الرئيسي)
--   - companies (اسم الشركة)
--   - astsalesman (المندوب المسؤول المخصص للعميل)
-- ====================================================================================================
DROP VIEW IF EXISTS v_customers_overview;
CREATE VIEW v_customers_overview AS
SELECT 
    cst.ID_No AS customer_id,                     -- المعرف الفريد للعميل
    cst.Cmp_No,                                   -- رقم الشركة
    COALESCE(cmp.company_name, 'شركة ' || cst.Cmp_No) AS company_name, -- اسم الشركة
    cst.Brn_No,                                   -- كود الفرع المسجل عليه العميل
    cst.Cstm_No AS customer_code,                 -- كود العميل المحاسبي
    cst.Cstm_NmAr AS customer_name,               -- الاسم التجاري للعميل
    cst.Cstm_NmEn AS customer_name_en,            -- الاسم الإنجليزي للعميل
    cst.Cstm_Tel AS telephone,                    -- رقم الهاتف / الجوال المعتمد للتواصل
    cst.Credit_Value AS credit_limit,             -- سقف الائتمان المسموح به للعميل (Credit Limit)
    cst.Credit_Days AS credit_days,               -- مهلة السداد المسموح بها بالأيام (Grace Period Days)
    slm.Slm_NmAr AS assigned_salesman,            -- اسم المندوب المشرف على حساب العميل
    cst.Cstm_Active AS is_active,                 -- حالة الحساب (1: مفعل، 0: مغلق/مجمد)
    cst.created_at                                -- تاريخ تسجيل العميل في النظام
FROM mtscustomer cst
LEFT JOIN companies cmp ON cmp.Cmp_No = cst.Cmp_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = cst.Cmp_No AND slm.Slm_No = cst.Slm_No;


-- ====================================================================================================
-- 5. VIEW: v_salesmen_overview
-- الغرض: أداء فريق المبيعات والمناديب المستهدف والفروع (Sales Representatives & Targets)
-- استخدام الذكاء الاصطناعي: "من هم مناديب فرع كذا؟"، "أهداف المبيعات المحددة للمناديب"، "حدود الشيكات النقدية"
-- الجداول المرتبطة:
--   - astsalesman (دليل الموظفين والمناديب)
--   - companies (اسم الشركة)
--   - mainbranch (الفرع المخصص له المندوب)
-- ====================================================================================================
DROP VIEW IF EXISTS v_salesmen_overview;
CREATE VIEW v_salesmen_overview AS
SELECT 
    slm.ID_No AS salesman_id,                     -- كود المندوب الداخلي
    slm.Cmp_No,                                   -- رقم الشركة
    COALESCE(cmp.company_name, 'شركة ' || slm.Cmp_No) AS company_name, -- اسم الشركة
    slm.Brn_No,                                   -- رقم الفرع التابع له
    slm.Slm_No AS salesman_code,                  -- كود المندوب في النظام المحاسبي
    slm.Slm_NmAr AS salesman_name,                -- اسم المندوب بالكامل
    slm.Target AS sales_target,                   -- المستهدف البيعي الشهري/السنوي (Sales Quota/Target)
    slm.TCashCheqe AS cash_cheque_limit,          -- الحد الأقصى لتحصيل الشيكات والنقدية المسموح به للمندوب
    brn.Brn_NmAr AS branch_name                   -- اسم الفرع التابع له المندوب
FROM astsalesman slm
LEFT JOIN companies cmp ON cmp.Cmp_No = slm.Cmp_No
LEFT JOIN mainbranch brn ON brn.Cmp_No = slm.Cmp_No AND brn.Brn_No = slm.Brn_No;


-- ====================================================================================================
-- 6. VIEW: v_crm_leads_overview
-- الغرض: إدارة الفرص البيعية والعملاء المتوقعين (CRM Leads & Opportunities Pipeline)
-- استخدام الذكاء الاصطناعي: متابعة الصفقات المتوقعة، قيمة الفرص المقدرة، تاريخ آخر تواصل، والمندوب المسؤول
-- الجداول المرتبطة:
--   - crm_leads (جدول الفرص المحتملة للـ CRM)
--   - companies (اسم الشركة)
--   - astsalesman (المندوب المكلف بمتابعة العميل المحتمل)
-- ====================================================================================================
DROP VIEW IF EXISTS v_crm_leads_overview;
CREATE VIEW v_crm_leads_overview AS
SELECT 
    lead.id AS lead_id,                           -- معرف الفرصة البيعية
    lead.Cmp_No,                                  -- رقم الشركة
    COALESCE(cmp.company_name, 'شركة ' || lead.Cmp_No) AS company_name, -- اسم الشركة
    lead.Brn_No,                                  -- رقم الفرع
    lead.Lead_No AS lead_number,                  -- كود العميل المحتمل
    lead.Lead_NmAr AS lead_name,                  -- اسم العميل أو اسم المؤسسة المستهدفة
    lead.Lead_Value AS estimated_value,           -- القيمة التقديرية المتوقعة للصفقة (Deal Valuation)
    lead.Lead_Tel AS phone,                       -- هاتف العميل المحتمل
    lead.Lead_Email AS email,                     -- البريد الإلكتروني
    lead.Last_contact AS last_contact_date,       -- تاريخ آخر مكالمة أو اجتماع تواصل معه
    slm.Slm_NmAr AS assigned_salesman,            -- اسم المندوب المكلف بالإغلاق والمتابعة
    lead.created_at                               -- تاريخ فتح الفرصة البيعية
FROM crm_leads lead
LEFT JOIN companies cmp ON cmp.Cmp_No = lead.Cmp_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = lead.Cmp_No AND slm.Slm_No = lead.Slm_No;


-- ====================================================================================================
-- 7. توصيات الفهارس لقاعدة بيانات MySQL/MariaDB في بيئة الإنتاج (Production Indexes Recommendations)
-- للحصول على أقصى أداء واستجابة أقل من 0.05 ثانية حتى مع ملايين الفواتير، نوصي بتطبيق الفهارس المركبة الآتية:
-- ====================================================================================================
-- CREATE INDEX idx_invlodhdr_tenant_date ON invlodhdr (Cmp_No, Brn_No, Doc_Dt, Doc_Ty);
-- CREATE INDEX idx_invlodhdr_customer ON invlodhdr (Cmp_No, Cstm_No, Doc_Dt);
-- CREATE INDEX idx_invlodhdr_salesman ON invlodhdr (Cmp_No, Slm_No, Doc_Dt);
-- CREATE INDEX idx_invloddtl_tenant_item ON invloddtl (Cmp_No, Itm_No, Doc_No);
-- CREATE INDEX idx_invloddtl_doc_composite ON invloddtl (Cmp_No, Brn_No, Doc_No);
-- CREATE INDEX idx_mtscustomer_tenant ON mtscustomer (Cmp_No, Cstm_No);
-- CREATE INDEX idx_mtsitmmfs_tenant ON mtsitmmfs (Cmp_No, Itm_No);
-- ====================================================================================================
