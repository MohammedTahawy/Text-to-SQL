-- ========================================================================
-- Enterprise ERP AI Semantic Layer - Database Views for Natural Language Querying
-- Purpose: Translates legacy abbreviated tables into clean analytical views
-- Discovered & Validated against Production Database (enterprise-demo-db)
-- ========================================================================

-- 1. Sales & Invoicing Analytical View
DROP VIEW IF EXISTS v_sales_invoices;
CREATE VIEW v_sales_invoices AS
SELECT 
    hdr.ID_No AS invoice_id,
    hdr.Cmp_No,
    hdr.Brn_No,
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
    COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) AS total_amount,
    COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0) AS paid_amount,
    (COALESCE(hdr.Tot_Sal, hdr.TotRcpt_Amount, 0) - COALESCE(hdr.Paid_Total, hdr.Pymt_Val, 0)) AS remaining_amount,
    hdr.created_at
FROM invlodhdr hdr
LEFT JOIN mtscustomer cst ON cst.Cmp_No = hdr.Cmp_No AND cst.Cstm_No = hdr.Cstm_No
LEFT JOIN astsalesman slm ON slm.Cmp_No = hdr.Cmp_No AND slm.Slm_No = hdr.Slm_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = hdr.Cmp_No AND wh.Dlv_Stor = hdr.Dlv_Stor;

-- 2. Sales Item Details Analytical View
DROP VIEW IF EXISTS v_sales_invoice_items;
CREATE VIEW v_sales_invoice_items AS
SELECT 
    dtl.ID_No AS line_id,
    dtl.Cmp_No,
    dtl.Brn_No,
    dtl.Doc_No AS invoice_number,
    dtl.Doc_Ty AS invoice_type_id,
    dtl.Itm_No AS item_code,
    itm.Itm_NmAr AS item_name,
    itm.Itm_NmEn AS item_name_en,
    cat.Itm_NmAr AS category_name,
    dtl.Unit_No AS unit_id,
    unt.Unit_NmAr AS unit_name,
    dtl.Qty AS quantity,
    COALESCE(dtl.Itm_Sal, dtl.Itm_Pur, 0) AS unit_price,
    COALESCE(dtl.Titm_Sal, dtl.Qty * dtl.Itm_Sal, dtl.Titm_Pur, 0) AS line_total,
    COALESCE(dtl.Taxv_ExtraDtl, 0) AS tax_amount,
    dtl.Dlv_Stor AS warehouse_id,
    wh.Dlv_NmAr AS warehouse_name
FROM invloddtl dtl
LEFT JOIN mtsitmmfs itm ON itm.Cmp_No = dtl.Cmp_No AND itm.Itm_No = dtl.Itm_No
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = dtl.Unit_No
LEFT JOIN pjbranchdlv wh ON wh.Cmp_No = dtl.Cmp_No AND wh.Dlv_Stor = dtl.Dlv_Stor;

-- 3. Inventory & Stock Levels View
DROP VIEW IF EXISTS v_inventory_stock;
CREATE VIEW v_inventory_stock AS
SELECT 
    itm.ID_No AS item_id,
    itm.Cmp_No,
    itm.Itm_No AS item_code,
    itm.Itm_NmAr AS item_name,
    itm.Itm_NmEn AS item_name_en,
    cat.Itm_NmAr AS category_name,
    unt.Unit_NmAr AS primary_unit,
    itm.Itm_Active AS is_active,
    itm.Sup_No AS default_supplier_id
FROM mtsitmmfs itm
LEFT JOIN mtsitmcatgry cat ON cat.Cmp_No = itm.Cmp_No AND cat.Itm_No = itm.Itm_Parnt
LEFT JOIN mtsitmunit unt ON unt.Unit_No = itm.Unit_No;

-- 4. Customer Master & Balances View
DROP VIEW IF EXISTS v_customers_overview;
CREATE VIEW v_customers_overview AS
SELECT 
    cst.ID_No AS customer_id,
    cst.Cmp_No,
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
LEFT JOIN astsalesman slm ON slm.Cmp_No = cst.Cmp_No AND slm.Slm_No = cst.Slm_No;

-- 5. Sales Representatives & Performance View
DROP VIEW IF EXISTS v_salesmen_overview;
CREATE VIEW v_salesmen_overview AS
SELECT 
    slm.ID_No AS salesman_id,
    slm.Cmp_No,
    slm.Brn_No,
    slm.Slm_No AS salesman_code,
    slm.Slm_NmAr AS salesman_name,
    slm.Target AS sales_target,
    slm.TCashCheqe AS cash_cheque_limit,
    brn.Brn_NmAr AS branch_name
FROM astsalesman slm
LEFT JOIN mainbranch brn ON brn.Cmp_No = slm.Cmp_No AND brn.Brn_No = slm.Brn_No;

-- 6. CRM Prospective Leads View
DROP VIEW IF EXISTS v_crm_leads_overview;
CREATE VIEW v_crm_leads_overview AS
SELECT 
    lead.id AS lead_id,
    lead.Cmp_No,
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
LEFT JOIN astsalesman slm ON slm.Cmp_No = lead.Cmp_No AND slm.Slm_No = lead.Slm_No;
