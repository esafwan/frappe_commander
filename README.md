# Commander

A lightweight CLI tool extending Frappe Bench to add support for creating DocTypes with fields through the command line to better support development using AI based IDEs.

> **Note:** This is experimental software, not recommended for production use. Commander is part of a wider initiative to make Frappe application development natively agentic—moving beyond low-code to "vibe codable" development from within. This works alongside [frappe_ElevenLabs](https://github.com/tridz-dev/frappe_ElevenLabs) (voice AI interface) and [agent_flo](https://github.com/tridz-dev/agent_flo) (multi model, multi agent workflows). We expect these initiatives to compound and merge over time.

## Overview

Commander eliminates the need to manually create DocTypes through the Desk UI or write JSON files. It provides a simple, declarative CLI interface to generate Frappe DocTypes with field definitions, validation rules, and permissions in seconds.


## Installation

```bash
# Get the app
cd /path/to/frappe-bench
bench get-app https://github.com/esafwan/frappe_commander.git

# Install on a site
bench --site your-site install-app commander
```

## Usage

### Basic Example

```bash
bench --site mysite new-doctype "Product" \
  -f "product_name:Data:*" \
  -f "price:Currency" \
  -f "description:Text" \
  -m "Custom"
```

### Field Definition Syntax

```
<fieldname>:<fieldtype>[:<attribute1>[:<attribute2>...]]
```

**Examples:**
- `name:Data:*` - Required Data field
- `email:Data:*:unique` - Required + unique
- `status:Select:options=Open,Closed` - Select with options
- `customer:Link:options=Customer` - Link to Customer DocType
- `amount:Currency:?=0` - Currency with default value
- `description:Text:readonly` - Read-only text field

### Supported Field Types

Data, Text, Int, Float, Date, Datetime, Select, Link, Table, Check, Currency, Percent

### Supported Attributes

| Attribute | Syntax | Effect |
|-----------|--------|--------|
| Required | `*` | Sets field as mandatory |
| Unique | `unique` | Adds unique constraint |
| Read-only | `readonly` | Makes field read-only |
| Options | `options=<val>` | Sets options for Select/Link/Table |
| Default | `?=<val>` | Sets default value |

## Examples

### E-commerce

```bash
# Product catalog
bench --site mysite new-doctype "Product" \
  -f "product_code:Data:*:unique" \
  -f "product_name:Data:*" \
  -f "description:Text" \
  -f "price:Currency:*:?=0" \
  -f "stock:Int:?=0" \
  -f "category:Select:options=Electronics,Clothing,Food" \
  -m "Inventory"

# Orders
bench --site mysite new-doctype "Order" \
  -f "order_number:Data:*:unique:readonly" \
  -f "customer:Link:*:options=Customer" \
  -f "order_date:Date:*:?=Today" \
  -f "status:Select:*:options=Pending,Confirmed,Shipped,Delivered" \
  -f "total:Currency:?=0" \
  -m "Sales"
```

### CRM

```bash
# Lead management
bench --site mysite new-doctype "Lead" \
  -f "lead_name:Data:*" \
  -f "email:Data:unique" \
  -f "company:Data" \
  -f "status:Select:options=New,Qualified,Lost" \
  -f "notes:Text" \
  -m "CRM"
```

### Project Management

```bash
# Projects
bench --site mysite new-doctype "Project" \
  -f "project_name:Data:*" \
  -f "client:Link:options=Customer" \
  -f "start_date:Date:*" \
  -f "end_date:Date" \
  -f "status:Select:*:options=Planning,Active,On Hold,Completed" \
  -m "Projects"

# Tasks
bench --site mysite new-doctype "Task" \
  -f "task_title:Data:*" \
  -f "project:Link:*:options=Project" \
  -f "assigned_to:Link:options=User" \
  -f "priority:Select:options=Low,Medium,High,Urgent" \
  -f "status:Select:*:options=Open,In Progress,Done" \
  -m "Projects"
```

## Features

- Rapid DocType scaffolding from command line
- Human-readable field definition syntax
- Automatic module management
- Built-in validation and error checking
- Seamless integration with bench CLI
- Perfect for prototyping and scripting

## Use Cases

1. **Rapid prototyping** - Quickly test data model ideas
2. **CI/CD pipelines** - Generate DocTypes programmatically
3. **Project scaffolding** - Set up initial schema structure
4. **Learning tool** - Understand Frappe schema structure

## Documentation

For comprehensive documentation including:
- Architecture & implementation details
- Extension guides
- API reference
- Best practices
- Troubleshooting

See [AGENTS.md](AGENTS.md) - Complete technical documentation for developers and AI agents.

## Command Reference

```bash
# Show help
bench new-doctype --help

# Create with fields
bench --site mysite new-doctype "DocType Name" \
  -f "field1:Type:*" \
  -f "field2:Type:?=default" \
  -m "Module"

# Create without fields (add later in Desk)
bench --site mysite new-doctype "Simple DocType"
```

## Limitations

- Limited to common field types (11 types supported)
- Creates standard DocTypes only (no Single, Tree, or Child DocTypes)
- Permissions fixed to System Manager role
- No controller class generation
- Best for initial structure; refine complex features in Desk

## REST API

Commander exposes all CLI features via REST API endpoints, enabling programmatic access from external applications, CI/CD pipelines, and AI agents.

### Base URL

All endpoints are available at:
```
/api/method/commander.api.<method_name>
```

### Authentication

Most endpoints require authentication with **System Manager** role. Use either:
- Session-based authentication (cookies)
- API Key authentication: `Authorization: token YOUR_API_KEY:YOUR_API_SECRET`

### Quick Start

```bash
# Get API documentation
curl https://your-site.com/api/method/commander.api.get_api_documentation

# Create DocType via API
curl -X POST https://your-site.com/api/method/commander.api.create_doctype_api \
  -H "Content-Type: application/json" \
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \
  -d '{
    "doctype_name": "Product",
    "fields": ["product_name:Data:*", "price:Currency:?=0"],
    "module": "Custom"
  }'
```

### Available Endpoints

#### 1. Create DocType

**Endpoint**: `POST /api/method/commander.api.create_doctype_api`

Create a new DocType with field definitions.

**Request**:
```json
{
  "doctype_name": "Product",
  "fields": [
    "product_name:Data:*",
    "price:Currency:?=0",
    "description:Text"
  ],
  "module": "Custom",
  "custom": false
}
```

**Response** (Success):
```json
{
  "success": true,
  "message": "DocType 'Product' created successfully in module 'Custom'",
  "data": {
    "doctype_name": "Product",
    "module": "Custom",
    "fields_count": 3,
    "custom": false
  }
}
```

**Response** (Error):
```json
{
  "success": false,
  "error": {
    "message": "DocType 'Product' already exists.",
    "code": "DOCTYPE_EXISTS",
    "details": {
      "doctype_name": "Product"
    }
  }
}
```

#### 2. Add Custom Field

**Endpoint**: `POST /api/method/commander.api.add_custom_field_api`

Add a custom field to an existing standard DocType.

**Request**:
```json
{
  "doctype": "Customer",
  "field_definition": "custom_industry:Data:*",
  "insert_after": "customer_name"
}
```

**Response** (Success):
```json
{
  "success": true,
  "message": "Custom field 'custom_industry' added successfully to DocType 'Customer'",
  "data": {
    "doctype": "Customer",
    "fieldname": "custom_industry",
    "fieldtype": "Data",
    "label": "Industry",
    "required": true,
    "unique": false,
    "read_only": false,
    "insert_after": "customer_name"
  }
}
```

#### 3. Add Property Setter

**Endpoint**: `POST /api/method/commander.api.add_property_setter_api`

Add a property setter to customize DocType or field properties.

**Request** (DocType property):
```json
{
  "doctype": "Sales Invoice",
  "property": "allow_copy",
  "value": "1",
  "property_type": "Check",
  "for_doctype": true
}
```

**Request** (Field property):
```json
{
  "doctype": "Sales Invoice",
  "field_name": "customer",
  "property": "reqd",
  "value": "1",
  "property_type": "Check"
}
```

**Response** (Success):
```json
{
  "success": true,
  "message": "Property setter for 'allow_copy' created successfully",
  "data": {
    "doctype": "Sales Invoice",
    "field_name": null,
    "property": "allow_copy",
    "value": "1",
    "property_type": "Check",
    "doctype_or_field": "DocType"
  }
}
```

#### 4. Get API Documentation

**Endpoint**: `GET /api/method/commander.api.get_api_documentation`

Get comprehensive REST API documentation with examples, error codes, and usage instructions.

**Response**:
```json
{
  "success": true,
  "documentation": {
    "title": "Commander REST API Documentation",
    "version": "1.0.0",
    "endpoints": [...],
    "error_codes": [...],
    "usage_examples": [...]
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `PERMISSION_DENIED` | 403 | User lacks System Manager role |
| `DOCTYPE_EXISTS` | 409 | DocType already exists |
| `DOCTYPE_NOT_FOUND` | 404 | DocType does not exist |
| `MODULE_NOT_FOUND` | 400 | Module or app not found |
| `CORE_DOCTYPE` | 400 | Cannot customize core DocTypes |
| `SINGLE_DOCTYPE` | 400 | Cannot customize single DocTypes |
| `CUSTOM_DOCTYPE` | 400 | Cannot customize custom DocTypes |
| `FIELD_EXISTS` | 409 | Custom field already exists |
| `FIELD_NOT_FOUND` | 404 | Field does not exist |
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Python Example

```python
import requests

# Create DocType
url = "https://your-site.com/api/method/commander.api.create_doctype_api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "token YOUR_API_KEY:YOUR_API_SECRET"
}
data = {
    "doctype_name": "Product",
    "fields": [
        "product_name:Data:*",
        "price:Currency:?=0",
        "description:Text"
    ],
    "module": "Custom"
}

response = requests.post(url, json=data, headers=headers)
result = response.json()

if result.get("success"):
    print(f"Created: {result['data']['doctype_name']}")
else:
    print(f"Error: {result['error']['message']}")
```

### JavaScript Example

```javascript
// Create DocType
fetch('https://your-site.com/api/method/commander.api.create_doctype_api', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'token YOUR_API_KEY:YOUR_API_SECRET'
  },
  body: JSON.stringify({
    doctype_name: 'Product',
    fields: [
      'product_name:Data:*',
      'price:Currency:?=0',
      'description:Text'
    ],
    module: 'Custom'
  })
})
.then(response => response.json())
.then(data => {
  if (data.success) {
    console.log('Created:', data.data.doctype_name);
  } else {
    console.error('Error:', data.error.message);
  }
});
```

### Restrictions

- **Custom fields** can only be added to **standard DocTypes** (not custom DocTypes)
- **Core DocTypes** (DocType, User, Role, etc.) cannot be customized
- **Single DocTypes** cannot have custom fields
- All operations require **System Manager** role

### Complete Documentation

For complete API documentation including all endpoints, error codes, and examples, call:

```bash
curl https://your-site.com/api/method/commander.api.get_api_documentation
```

Or visit the endpoint in your browser while authenticated.

## Roadmap

### Completed

✅ **REST API Interface**
- Expose DocType creation via REST endpoints
- Enable external applications to generate DocTypes programmatically
- Standard HTTP interface for integration with any tech stack
- Comprehensive error handling and documentation

### Next Steps

**1. MCP (Model Context Protocol) Support**
- Implement MCP server for LLM integration
- Allow AI agents to create and modify DocTypes via MCP
- Enable conversational schema design through AI assistants

**2. Additional Features**
- Bulk operations endpoint
- DocType update endpoint
- Field update/delete endpoints
- Customization export endpoint

## Development

```bash
# Clone repository
git clone https://github.com/esafwan/frappe_commander.git
cd frappe_commander

# Install in development mode
bench get-app /path/to/frappe_commander
bench --site mysite install-app commander

# Test
bench --site mysite new-doctype "Test Doc" -f "name:Data:*"
```


## License

MIT

## Links

- GitHub: https://github.com/esafwan/frappe_commander
- Documentation: [AGENTS.md](AGENTS.md)
- Frappe Framework: https://frappeframework.com
- Bench CLI: https://github.com/frappe/bench



