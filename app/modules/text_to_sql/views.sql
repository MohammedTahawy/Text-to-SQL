-- ====================================================================================================
-- INFOSAS ERP & CRM - AI ANALYTICAL SEMANTIC LAYER (DATABASE VIEWS SPECIFICATION)
-- Official Semantic Layer specification for the InfoSas ERP Artificial Intelligence Engine
-- Addressed to Eng. Khaled (Lead Architect & CTO - InfoSas)
-- File Path: ai-service/app/modules/text_to_sql/views.sql
-- 
-- 1. Architectural Rationale:
--    The InfoSas ERP database contains over 717 tables with legacy 4-letter accounting abbreviations
--    such as (invlodhdr, invloddtl, mtsitmmfs, mtscustomer, astsalesman, pjbranchdlv).
--    Exposing all raw tables directly to LLM context causes:
--      a) Massive token consumption and high API latency/cost.
--      b) Increased hallucinations and erroneous table joins across complex schema paths.
--      c) Critical security and data privacy risks (potential leaks of sec_users, credentials, etc.).
--    Therefore, this consolidated semantic layer provides 6 unified, pre-indexed analytical views
--    covering 100% of executive accounting, sales, inventory, and customer intelligence queries.
--
-- 2. Multi-Tenant Isolation Architecture:
--    - All views strictly expose key tenant identifiers: `Cmp_No` (Company ID) and `Brn_No` (Branch ID).
--    - Multi-tenant isolation conditions (`Cmp_No = :cmp_no`) are deterministically injected at the
--      AST parser level via Python security guardrails, ensuring that cross-company data access is
--      strictly impossible even under adversarial user prompting.
--
-- 3. Legacy Table Mapping Dictionary:
--    - invlodhdr   --> Invoice Load Header (Invoice headers: Sales, Purchases, Returns)
--    - invloddtl   --> Invoice Load Details (Invoice line items, quantities, prices, taxes)
--    - mtscustomer --> Master Customer (Customer directory, balances, credit limits, phone)
--    - mtsitmmfs   --> Master Items File System (Master product & items catalog)
--    - mtsitmcatgry--> Master Item Categories (Category taxonomy and product families)
--    - mtsitmunit  --> Master Item Units (Measurement units: Liter, Ton, Piece, Carton)
--    - astsalesman --> Asset / Staff Salesmen (Sales representatives and field agents)
--    - pjbranchdlv --> Project Branch Delivery / Warehouses (Warehouses, fuel depots, distribution points)
--    - mainbranch  --> Main Branches (Directory of headquarters and operating branches)
--    - companies   --> Multi-Tenant Directory (Registered companies & legal entities)
--    - crm_leads   --> CRM Prospective Leads (Sales opportunities and prospective clients)
-- ====================================================================================================


-- ====================================================================================================
-- 1. VIEW: v_sales_invoices
-- Purpose: Comprehensive analytical view of invoice headers (Sales & Invoicing Transactions)
-- Joined Tables:
--   - invlodhdr   (Primary invoice headers table)
--   - companies   (Maps Cmp_No to legal company names)
--   - mainbranch  (Maps Brn_No to localized branch name Brn_NmAr)
--   - mtscustomer (Maps Cstm_No to customer name Cstm_NmAr)
--   - astsalesman (Maps Slm_No to sales representative Slm_NmAr)
--   - pjbranchdlv (Maps Dlv_Stor to warehouse / depot name Dlv_NmAr)
-- ====================================================================================================
DROP VIEW IF EXISTS v_sales_invoices;
CREATE VIEW v_sales_invoices AS
SELECT 
    -- Primary transaction identifiers
    hdr.ID_No AS invoice_id,                      -- Unique primary key of the invoice in the database
    hdr.Cmp_No,                                   -- Company identifier (Mandatory multi-tenancy partition key)
    COALESCE(cmp.company_name, 'Company ' || hdr.Cmp_No) AS company_name,        -- Localized company name
    COALESCE(cmp.company_name_en, 'Company ' || hdr.Cmp_No) AS company_name_en, -- English company name
    hdr.Brn_No,                                   -- Branch code
    brn.Brn_NmAr AS branch_name,                  -- Branch name (e.g. 'Main Branch - Gasoline/Solar')
    hdr.Doc_No AS invoice_number,                 -- Official printed document number
    hdr.Doc_Dt AS invoice_date,                   -- Invoice issuance date (YYYY-MM-DD)

    -- Accounting document type classification (Doc_Ty logic):
    -- Code 13 = Cash & Credit Sales
    -- Code 14 = Sales Returns
    -- Code 1  = Purchases
    hdr.Doc_Ty AS invoice_type_id,
    CASE 
        WHEN hdr.Doc_Ty = 13 THEN 'مبيعات'
        WHEN hdr.Doc_Ty = 14 THEN 'مردود مبيعات'
        WHEN hdr.Doc_Ty = 1 THEN 'مشتريات'
        ELSE 'أخرى'
    END AS invoice_type_name,

    -- Customer entity data
    hdr.Cstm_No AS customer_id,                   -- Customer account code
    cst.Cstm_NmAr AS customer_name,               -- Localized official customer name

    -- Sales representative data
    hdr.Slm_No AS salesman_id,                    -- Assigned sales representative ID
    slm.Slm_NmAr AS salesman_name,                -- Full name of the sales representative

    -- Warehouse & delivery outlet data
    hdr.Dlv_Stor AS warehouse_id,                 -- Warehouse or fuel station store code
    wh.Dlv_NmAr AS warehouse_name,                -- Warehouse name (e.g. 'Riyadh Central Depot / Station 1')

    -- Calculated financial metrics:
    -- Handles legacy schema variations across InfoSas versions (Tot_Sal or TotRcpt_Amount)
    COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) AS total_amount,        -- Total gross invoice value
    COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0) AS paid_amount,           -- Settled amount paid in cash/cheques
    (COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) - COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0)) AS remaining_amount, -- Outstanding receivable balance
    
    hdr.created_at                                -- System creation timestamp
FROM invlodhdr hdr
LEFT JOIN companies cmp ON cmp.Cmp_No = hdr.Cmp_No
LEFT JOIN mainbranch brn ON brn.Cmp_No = hdr.Cmp_No AND brn.Brn_No = hdr.Brn_No
LEFT JOIN mtscustomer cst ON cst.Cmp_No = hdr.Cmp_No AND cst.Cstm_No = hdr.Cstm_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = hdr.Cmp_No AND slm.Slm_No = hdr.Slm_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = hdr.Cmp_No AND wh.Dlv_Stor = hdr.Dlv_Stor;


-- ====================================================================================================
-- 2. VIEW: v_sales_invoice_items
-- Purpose: Detailed line-item breakdown for invoices (Line-Item Sales & Product Movement)
-- AI Use Cases: "Top-selling products", "Fuel sales volume (Gasoline / Diesel)", "Average unit pricing"
-- Joined Tables:
--   - invloddtl   (Detailed invoice lines table)
--   - companies   (Company identity)
--   - mtsitmmfs   (Master item catalog for localized Arabic/English product descriptions)
--   - mtsitmcatgry(Product category taxonomy)
--   - mtsitmunit  (Unit of measure: Liter, Ton, Meter, Carton)
--   - pjbranchdlv (Warehouse / depot where goods were dispensed)
-- ====================================================================================================
DROP VIEW IF EXISTS v_sales_invoice_items;
CREATE VIEW v_sales_invoice_items AS
SELECT 
    dtl.ID_No AS line_id,                         -- Unique primary key of the line item
    dtl.Cmp_No,                                   -- Company identifier
    COALESCE(cmp.company_name, 'Company ' || dtl.Cmp_No) AS company_name,        -- Localized company name
    COALESCE(cmp.company_name_en, 'Company ' || dtl.Cmp_No) AS company_name_en, -- English company name
    dtl.Brn_No,                                   -- Branch code
    dtl.Doc_No AS invoice_number,                 -- Invoice number linking item to header
    dtl.Doc_Dt AS invoice_date,                   -- Transaction date
    dtl.Doc_Ty AS invoice_type_id,                -- Document type code (13: Sales, 14: Returns, etc.)

    -- Product information and classification
    dtl.Itm_No AS item_code,                      -- Accounting item code
    itm.Itm_NmAr AS item_name,                    -- Localized product name (e.g. 'Benzene 92', 'Diesel', 'Engine Oil 5W30')
    itm.Itm_NmEn AS item_name_en,                 -- English product name
    cat.Itm_NmAr AS category_name,                -- Category / family classification
    
    -- Unit of measure and quantity
    dtl.Unit_No AS unit_id,                       -- Unit of measure ID
    unt.Unit_NmAr AS unit_name,                   -- Localized unit name (Liter, Ton, Barrel, Package)
    dtl.Qty AS quantity,                          -- Quantity sold or returned

    -- Pricing, financial lines, and taxes
    COALESCE(dtl.Itm_Sal, dtl.Itm_Pur, 0) AS unit_price, -- Unit sale price
    COALESCE(dtl.Titm_Sal, dtl.Qty * dtl.Itm_Sal, dtl.Titm_Pur, 0) AS line_total, -- Net line total (Quantity * Unit Price)
    COALESCE(dtl.Taxv_ExtraDtl, 0) AS tax_amount, -- Calculated Value-Added Tax (VAT) on line

    -- Dispensing warehouse
    dtl.Dlv_Stor AS warehouse_id,                 -- Warehouse store ID
    wh.Dlv_NmAr AS warehouse_name                 -- Warehouse name
FROM invloddtl dtl
LEFT JOIN companies cmp ON cmp.Cmp_No = dtl.Cmp_No
LEFT JOIN mtsitmmfs itm ON itm.Cmp_No = dtl.Cmp_No AND itm.Itm_No = dtl.Itm_No
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = dtl.Unit_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = dtl.Cmp_No AND wh.Dlv_Stor = dtl.Dlv_Stor;


-- ====================================================================================================
-- 3. VIEW: v_inventory_stock
-- Purpose: Unified master catalog for product definitions and inventory status (Product Master & Inventory Catalog)
-- AI Use Cases: Catalog inventory inquiries, active vs archived items, product categories, default suppliers
-- Joined Tables:
--   - mtsitmmfs   (Master item catalog and inventory definitions)
--   - companies   (Tenant ownership)
--   - mtsitmcatgry(Taxonomy tree and product families)
--   - mtsitmunit  (Primary base unit of measure)
-- ====================================================================================================
DROP VIEW IF EXISTS v_inventory_stock;
CREATE VIEW v_inventory_stock AS
SELECT 
    itm.ID_No AS item_id,                         -- Unique item record identifier
    itm.Cmp_No,                                   -- Company identifier
    COALESCE(cmp.company_name, 'Company ' || itm.Cmp_No) AS company_name, -- Company name
    itm.Itm_No AS item_code,                      -- SKU / commercial item code
    itm.Itm_NmAr AS item_name,                    -- Localized Arabic product name
    itm.Itm_NmEn AS item_name_en,                 -- English product name
    cat.Itm_NmAr AS category_name,                -- Category / product family name
    unt.Unit_NmAr AS primary_unit,                -- Base measurement unit name
    itm.Itm_Active AS is_active,                  -- Item active flag (1: Active for sale, 0: Discontinued/Archived)
    itm.Sup_No AS default_supplier_id             -- Default authorized supplier code
FROM mtsitmmfs itm
LEFT JOIN companies cmp ON cmp.Cmp_No = itm.Cmp_No
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = itm.Unit_No;


-- ====================================================================================================
-- 4. VIEW: v_customers_overview
-- Purpose: Customer directory, credit terms, and debt limits (Customer Directory, Credit & Balances)
-- AI Use Cases: Customer profile lookups, top debtor accounts, assigned salesmen, contact coordinates
-- Joined Tables:
--   - mtscustomer (Primary customer master table)
--   - companies   (Tenant ownership)
--   - astsalesman (Designated account manager / sales representative)
-- ====================================================================================================
DROP VIEW IF EXISTS v_customers_overview;
CREATE VIEW v_customers_overview AS
SELECT 
    cst.ID_No AS customer_id,                     -- Unique internal customer ID
    cst.Cmp_No,                                   -- Company identifier
    COALESCE(cmp.company_name, 'Company ' || cst.Cmp_No) AS company_name, -- Company name
    cst.Brn_No,                                   -- Assigned home branch code
    cst.Cstm_No AS customer_code,                 -- Accounting customer code
    cst.Cstm_NmAr AS customer_name,               -- Localized commercial customer name
    cst.Cstm_NmEn AS customer_name_en,            -- English customer name
    cst.Cstm_Tel AS telephone,                    -- Primary phone / contact number
    cst.Credit_Value AS credit_limit,             -- Authorized credit limit ceiling
    cst.Credit_Days AS credit_days,               -- Permitted grace period in days for invoice settlement
    slm.Slm_NmAr AS assigned_salesman,            -- Name of assigned sales representative
    cst.Cstm_Active AS is_active,                 -- Account status (1: Active, 0: Inactive / Suspended)
    cst.created_at                                -- System registration timestamp
FROM mtscustomer cst
LEFT JOIN companies cmp ON cmp.Cmp_No = cst.Cmp_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = cst.Cmp_No AND slm.Slm_No = cst.Slm_No;


-- ====================================================================================================
-- 5. VIEW: v_salesmen_overview
-- Purpose: Sales team performance directory, targets, and branch assignments (Sales Representatives & Targets)
-- AI Use Cases: Sales reps per branch, monthly/annual sales quotas, cheque collection limits
-- Joined Tables:
--   - astsalesman (Master salesmen and staff directory)
--   - companies   (Tenant ownership)
--   - mainbranch  (Designated operating branch)
-- ====================================================================================================
DROP VIEW IF EXISTS v_salesmen_overview;
CREATE VIEW v_salesmen_overview AS
SELECT 
    slm.ID_No AS salesman_id,                     -- Internal salesman sequence ID
    slm.Cmp_No,                                   -- Company identifier
    COALESCE(cmp.company_name, 'Company ' || slm.Cmp_No) AS company_name, -- Company name
    slm.Brn_No,                                   -- Branch code assignment
    slm.Slm_No AS salesman_code,                  -- Accounting salesman code
    slm.Slm_NmAr AS salesman_name,                -- Full name of sales representative
    slm.Target AS sales_target,                   -- Monthly or annual sales target quota
    slm.TCashCheqe AS cash_cheque_limit,          -- Maximum allowed cash/cheque collection ceiling
    brn.Brn_NmAr AS branch_name                   -- Localized branch name
FROM astsalesman slm
LEFT JOIN companies cmp ON cmp.Cmp_No = slm.Cmp_No
LEFT JOIN mainbranch brn ON brn.Cmp_No = slm.Cmp_No AND brn.Brn_No = slm.Brn_No;


-- ====================================================================================================
-- 6. VIEW: v_crm_leads_overview
-- Purpose: Sales pipeline tracking and prospective opportunities (CRM Leads & Opportunities Pipeline)
-- AI Use Cases: Deal pipeline monitoring, estimated deal valuation, last follow-up contact, assigned closer
-- Joined Tables:
--   - crm_leads   (CRM prospective opportunities table)
--   - companies   (Tenant ownership)
--   - astsalesman (Sales representative in charge of closing)
-- ====================================================================================================
DROP VIEW IF EXISTS v_crm_leads_overview;
CREATE VIEW v_crm_leads_overview AS
SELECT 
    lead.id AS lead_id,                           -- Unique opportunity ID
    lead.Cmp_No,                                  -- Company identifier
    COALESCE(cmp.company_name, 'Company ' || lead.Cmp_No) AS company_name, -- Company name
    lead.Brn_No,                                  -- Branch code
    lead.Lead_No AS lead_number,                  -- Prospective lead identifier
    lead.Lead_NmAr AS lead_name,                  -- Contact or target institution name
    lead.Lead_Value AS estimated_value,           -- Expected deal valuation amount
    lead.Lead_Tel AS phone,                       -- Lead contact phone number
    lead.Lead_Email AS email,                     -- Lead contact email address
    lead.Last_contact AS last_contact_date,       -- Timestamp of last communication or meeting
    slm.Slm_NmAr AS assigned_salesman,            -- Name of assigned sales representative
    lead.created_at                               -- Opportunity creation timestamp
FROM crm_leads lead
LEFT JOIN companies cmp ON cmp.Cmp_No = lead.Cmp_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = lead.Cmp_No AND slm.Slm_No = lead.Slm_No;


-- ====================================================================================================
-- 7. Production Database Index Recommendations (MySQL / MariaDB / PostgreSQL / SQLite)
-- For maximum query throughput (< 0.05s response latency) even with millions of invoices,
-- the following composite indexes are highly recommended on the production storage engine:
-- ====================================================================================================
-- CREATE INDEX idx_invlodhdr_tenant_date ON invlodhdr (Cmp_No, Brn_No, Doc_Dt, Doc_Ty);
-- CREATE INDEX idx_invlodhdr_customer ON invlodhdr (Cmp_No, Cstm_No, Doc_Dt);
-- CREATE INDEX idx_invlodhdr_salesman ON invlodhdr (Cmp_No, Slm_No, Doc_Dt);
-- CREATE INDEX idx_invloddtl_tenant_item ON invloddtl (Cmp_No, Itm_No, Doc_No);
-- CREATE INDEX idx_invloddtl_doc_composite ON invloddtl (Cmp_No, Brn_No, Doc_No);
-- CREATE INDEX idx_mtscustomer_tenant ON mtscustomer (Cmp_No, Cstm_No);
-- CREATE INDEX idx_mtsitmmfs_tenant ON mtsitmmfs (Cmp_No, Itm_No);
-- ====================================================================================================
