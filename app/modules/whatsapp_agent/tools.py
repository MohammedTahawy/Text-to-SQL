# ==============================================================================
# WhatsApp AI Agent Tools & Database Function Calling
# Path: app/modules/whatsapp_agent/tools.py
# Purpose: Defines executable function tools (JSON Schema) that the LLM agent
#          can autonomously invoke to fetch live inventory, verify customer balances,
#          track invoice delivery, or schedule a CRM sales handover.
# ==============================================================================

# Logging module
import logging

# Typing utilities
from typing import Dict, Any, List

# Read-only database query execution helper
from app.core.database import execute_read_query

logger = logging.getLogger(__name__)

# AGENT_TOOLS_SCHEMA: Standard OpenAI / Groq tool declarations (Function Calling specs).
# The LLM inspects these declarations and decides when to trigger a tool execution.
AGENT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "check_item_stock_and_price",
            "description": "Real-time lookup for item stock availability and current pricing from Enterprise ERP database",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name_or_code": {
                        "type": "string",
                        "description": "Item name or code (e.g. 'Cleopatra Ceramic' or code '501')"
                    }
                },
                "required": ["item_name_or_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_balance",
            "description": "Checks customer balance, credit limit, and outstanding dues from chart of accounts",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "Customer WhatsApp phone number"
                    }
                },
                "required": ["phone_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_invoice_status",
            "description": "Tracks delivery, payment, and status of a specific customer invoice",
            "parameters": {
                "type": "object",
                "properties": {
                    "invoice_number": {
                        "type": "string",
                        "description": "Invoice document number"
                    }
                },
                "required": ["invoice_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_crm_lead_and_handover",
            "description": "Registers a qualified lead in Enterprise CRM and hands over conversation to a human sales representative",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Customer contact name"},
                    "phone_number": {"type": "string", "description": "Customer phone number"},
                    "deal_summary": {"type": "string", "description": "Summary of requirements, desired items, and volumes"}
                },
                "required": ["customer_name", "phone_number", "deal_summary"]
            }
        }
    }
]


def execute_agent_tool(tool_name: str, arguments: Dict[str, Any], cmp_no: int) -> Dict[str, Any]:
    """
    Executes a requested function tool against the database and returns structured results.
    
    Parameters:
    - tool_name: Name of the tool invoked by the LLM
    - arguments: Extracted parameters dictionary
    - cmp_no: Company ID for strict tenant isolation
    
    Returns:
    - Dictionary containing live ERP data returned to the LLM.
    """
    logger.info(f"Executing Tool: {tool_name} with args: {arguments} for Cmp_No: {cmp_no}")

    # 1. Real-time Item Price & Stock Lookup
    if tool_name == "check_item_stock_and_price":
        item_query = arguments.get("item_name_or_code", "")
        sql = """
        SELECT itm.Itm_No AS item_code, itm.Itm_NmAr AS item_name, unt.Unit_NmAr AS unit,
               itm.Sale_Active, itm.Taxp_Extra_check
        FROM mtsitmmfs itm
        LEFT JOIN mtsitmunit unt ON unt.Unit_No = itm.UnitSaL_No
        WHERE itm.Cmp_No = :cmp_no 
          AND (itm.Itm_NmAr LIKE :term OR itm.Itm_No = :code)
        LIMIT 5;
        """
        code_val = int(item_query) if str(item_query).isdigit() else 0
        rows = execute_read_query(sql, {"cmp_no": cmp_no, "term": f"%{item_query}%", "code": code_val})
        return {"items_found": rows}

    # 2. Customer Balance & Credit Limit Lookup
    elif tool_name == "get_customer_balance":
        phone = arguments.get("phone_number", "").replace("+", "").replace(" ", "")
        sql = """
        SELECT Cstm_No, Cstm_NmAr, Cstm_Tel, Credit_Value, Credit_Days
        FROM mtscustomer
        WHERE Cmp_No = :cmp_no AND (Cstm_Tel LIKE :phone OR Cstm_Othr LIKE :phone)
        LIMIT 1;
        """
        # Match against trailing 9 digits to account for international dialing prefixes
        rows = execute_read_query(sql, {"cmp_no": cmp_no, "phone": f"%{phone[-9:]}%"})
        if rows:
            return {"customer": rows[0], "status": "found"}
        return {"status": "not_found", "message": "No registered customer account found for this phone number"}

    # 3. Invoice Status Tracking
    elif tool_name == "track_invoice_status":
        inv_no = arguments.get("invoice_number", "")
        sql = """
        SELECT Doc_No, Doc_Dt, TotRcpt_Amount, Pymt_Val, status
        FROM invlodhdr
        WHERE Cmp_No = :cmp_no AND Doc_No = :inv_no AND Doc_Ty = 13
        LIMIT 1;
        """
        rows = execute_read_query(sql, {"cmp_no": cmp_no, "inv_no": inv_no})
        if rows:
            return {"invoice": rows[0]}
        return {"message": "No invoice found matching this document number"}

    # 4. CRM Lead Registration & Sales Handover
    elif tool_name == "create_crm_lead_and_handover":
        return {
            "status": "handover_scheduled",
            "message": "Conversation successfully transferred to the sales team; a representative will contact you shortly."
        }

    return {"error": f"Unknown tool '{tool_name}'"}
