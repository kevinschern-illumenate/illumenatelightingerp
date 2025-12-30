# ilLumenate Marketing Module - Admin Setup Guide

This guide provides step-by-step instructions for setting up and configuring the ilLumenate Marketing module, including the n8n integration for marketing automation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Configuration](#initial-configuration)
3. [n8n Integration Setup](#n8n-integration-setup)
4. [Marketing APIs](#marketing-apis)
5. [Reports Configuration](#reports-configuration)
6. [Promo Code Management](#promo-code-management)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before setting up the marketing module, ensure you have:

- ERPNext installed and running
- Admin access to the ERPNext instance
- n8n instance (self-hosted or cloud) for marketing automation
- SMTP server configured for sending emails

---

## Initial Configuration

### 1. Enable the Marketing Module

1. Navigate to **Settings > Module Settings**
2. Enable the "ilLumenate Marketing" module
3. Save and refresh the page

### 2. Configure Lead Sources

Lead sources track where your leads come from:

1. Go to **Marketing > ILL Lead Source**
2. Create entries for each lead source:
   - **Source Name**: e.g., "Google Ads", "Facebook", "Website Form"
   - **Source Type**: Select from Organic, Paid, Referral, Direct, Social, Email, Event, Other
   - **UTM Parameters**: Configure default UTM values for tracking

### 3. Configure Marketing Forms

Set up forms for lead capture:

1. Go to **Marketing > ILL Marketing Form**
2. Create forms for:
   - Contact forms
   - Dealer inquiry forms
   - Newsletter signups
3. Configure form settings:
   - **GDPR Consent**: Enable if required
   - **Notification Email**: Email address for notifications
   - **Default Lead Source**: Auto-assign source to leads

---

## n8n Integration Setup

### 1. Configure n8n Settings in ERPNext

1. Go to **Marketing > ILL n8n Settings**
2. Fill in the configuration:
   - **Enabled**: Check to enable integration
   - **n8n Webhook URL**: Your n8n webhook base URL (e.g., `https://n8n.yourdomain.com/webhook`)
   - **API Key**: Generate a secure API key for authentication

3. Configure event emission:
   - **Emit Lead Created**: Trigger on new lead creation
   - **Emit Lead Converted**: Trigger when lead converts to customer
   - **Emit Purchase Completed**: Trigger on sales invoice submission
   - **Emit Journey Changed**: Trigger on journey stage updates

### 2. Import n8n Workflow Templates

The module includes pre-built n8n workflow templates:

**Location**: `custom_erpnext/illumenate_marketing/fixtures/n8n_workflows/`

Available workflows:

1. **ltv_promo_code_generator.json**: Daily workflow to send promo codes to high-LTV customers
2. **lead_welcome_journey.json**: Lead nurturing workflow with follow-up emails

**To import a workflow in n8n:**

1. Open your n8n instance
2. Go to **Workflows > Add Workflow > Import from File**
3. Select the JSON file from the fixtures folder
4. Update the following in the imported workflow:
   - Environment variables (`ERPNEXT_URL`)
   - Credentials (ERPNext API Key, SMTP)
5. Activate the workflow

### 3. Configure n8n Credentials

In n8n, set up the following credentials:

**HTTP Header Auth (ERPNext API Key):**
- Name: `ERPNext API Key`
- Header Name: `X-API-Key`
- Header Value: Your API key from ILL n8n Settings

**SMTP Credentials:**
- Configure with your email server settings

**Environment Variables:**
- `ERPNEXT_URL`: Your ERPNext instance URL (e.g., `https://erp.illumenate.lighting`)

---

## Marketing APIs

The module provides RESTful APIs for marketing automation:

### Customer Lifetime Value (LTV) APIs

#### Get Customer LTV

```bash
POST /api/method/custom_erpnext.illumenate_marketing.api.get_customer_ltv
Content-Type: application/json

{
  "customer_name": "CUST-00001"
}
```

**Response:**
```json
{
  "message": {
    "lifetime_value": 5000.00,
    "order_count": 10,
    "last_order": "2024-01-15",
    "product_categories": ["Lighting", "Accessories"],
    "customer_name": "CUST-00001"
  }
}
```

#### Get High LTV Customers

```bash
POST /api/method/custom_erpnext.illumenate_marketing.api.get_high_ltv_customers
Content-Type: application/json

{
  "min_lifetime_value": 1000,
  "limit": 100
}
```

**Response:**
```json
{
  "message": [
    {
      "customer_name": "CUST-00001",
      "customer_display_name": "Acme Corp",
      "customer_email": "orders@acme.com",
      "lifetime_value": 5000.00,
      "order_count": 10,
      "last_order": "2024-01-15"
    }
  ]
}
```

### Promo Code APIs

#### Generate Promo Code

```bash
POST /api/method/custom_erpnext.illumenate_marketing.api.generate_promo_code
Content-Type: application/json

{
  "customer_name": "CUST-00001",
  "discount_percent": 50,
  "valid_days": 30,
  "campaign": "LTV Promotion"
}
```

**Response:**
```json
{
  "message": {
    "promo_code": "ILL-ABCD1234",
    "customer": "CUST-00001",
    "discount_percent": 50,
    "valid_from": "2024-01-01",
    "valid_until": "2024-01-31",
    "campaign": "LTV Promotion"
  }
}
```

#### Validate Promo Code

```bash
POST /api/method/custom_erpnext.illumenate_marketing.api.validate_promo_code
Content-Type: application/json

{
  "promo_code": "ILL-ABCD1234",
  "customer_name": "CUST-00001"
}
```

#### Redeem Promo Code

```bash
POST /api/method/custom_erpnext.illumenate_marketing.api.redeem_promo_code
Content-Type: application/json

{
  "promo_code": "ILL-ABCD1234",
  "customer_name": "CUST-00001"
}
```

---

## Reports Configuration

### Campaign Performance Report

Access the report at **Marketing > Campaign Performance**

**Features:**
- Lead counts by campaign/source
- Conversion rates (Lead → Customer)
- Attributed revenue per campaign
- Email open and click rates

**Filters:**
- **From Date / To Date**: Date range for the report
- **Exclude Internal Accounts**: Filter out @illumenate.lighting emails
- **Exclude Test Accounts**: Filter out test email accounts

### Unlinked Contacts Report

Access at **Marketing > Unlinked Contacts**

Identifies data quality issues:
- Contacts without linked Company
- Contacts without linked Customer
- Contacts without User account

---

## Promo Code Management

### Viewing Promo Codes

1. Go to **Marketing > ILL Promo Code**
2. View all generated promo codes with status

### Promo Code Fields

- **Promo Code**: Unique code (format: ILL-XXXXXXXX)
- **Customer**: Linked customer
- **Discount Percent**: Discount value (0-100%)
- **Valid From / Valid Until**: Validity period
- **Is Used**: Whether the code has been redeemed
- **Campaign**: Source campaign for tracking

---

## Troubleshooting

### n8n Webhook Not Receiving Events

1. Check that the n8n integration is enabled in ILL n8n Settings
2. Verify the webhook URL is correct
3. Check API key matches between ERPNext and n8n
4. Review frappe error logs for webhook failures

### Promo Code Generation Fails

1. Verify customer exists in the system
2. Check discount_percent is between 0-100
3. Check valid_days is at least 1

### Report Shows No Data

1. Verify leads exist with proper source assignments
2. Check date range filters
3. Ensure lead sources are configured in ILL Lead Source

### API Authentication Errors

1. Verify API key is correctly configured
2. Check header format: `X-API-Key: your-key` or `Authorization: Bearer your-key`
3. Ensure the API is being called with proper authentication

---

## Support

For additional support, contact the development team or refer to the technical documentation in the repository.
