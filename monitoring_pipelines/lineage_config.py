# Data Lineage Relationships Configuration
# Maps ETL Pipelines to their Source and Target tables

LINEAGE_MAP = {
    "Customer_Orders_Pipeline": {
        "sources": ["CUSTOMER", "ORDERS"],
        "targets": ["CUSTOMER_ORDERS"],
        "description": "Extracts customer and orders records from MySQL and syncs to CUSTOMER_ORDERS target table in Snowflake."
    },
    "Sales_Report_Pipeline": {
        "sources": ["ORDERS", "PRODUCT"],
        "targets": ["SALES_REPORT"],
        "description": "Extracts orders and product items from MySQL, joins them, and aggregates sales metrics into Snowflake SALES_REPORT target table."
    }
}
