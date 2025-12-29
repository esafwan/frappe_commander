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

## Customizing Existing DocTypes

Commander supports customizing existing DocTypes (both standard and custom) by adding custom fields and modifying properties.

### Adding Custom Fields

Use `customize-doctype` to add custom fields to existing DocTypes.

**Simple Examples:**
```bash
# Add a single custom field
bench --site mysite customize-doctype "Sales Invoice" \
  -f "notes:Text"

# Add multiple fields (inserted sequentially)
bench --site mysite customize-doctype "Sales Invoice" \
  -f "priority:Select:options=Low,Medium,High" \
  -f "internal_notes:Text"

# Add fields after a specific field
bench --site mysite customize-doctype "Sales Invoice" \
  -f "custom_reference:Data" \
  -f "custom_contact:Link:options=Contact" \
  --insert-after "customer"
```

**Detailed Example:**
```bash
# Add complex custom fields with all attributes
bench --site mysite customize-doctype "Sales Invoice" \
  -f "custom_priority:Select:*:options=Low,Medium,High,Urgent:?=Medium" \
  -f "custom_notes:Text" \
  -f "custom_discount:Percent:?=0" \
  -f "custom_is_urgent:Check:?=0" \
  --insert-after "customer"
```

### Modifying Properties

Use `set-property` to modify DocType or field properties using Property Setters.

**Simple Examples:**
```bash
# Make a field required (property-type auto-detected)
bench --site mysite set-property "Sales Invoice" \
  --property "reqd" --value "1" \
  --field "customer"

# Hide a field
bench --site mysite set-property "Sales Invoice" \
  --property "hidden" --value "1" \
  --field "remarks"

# Enable copy on DocType
bench --site mysite set-property "Sales Invoice" \
  --property "allow_copy" --value "1"

# Make field read-only
bench --site mysite set-property "Sales Invoice" \
  --property "read_only" --value "1" \
  --field "grand_total"
```

**Detailed Examples:**
```bash
# Explicit property type specification
bench --site mysite set-property "Sales Invoice" \
  --property "label" --value "Customer Name" \
  --property-type "Data" \
  --field "customer"

# Set DocType-level property with explicit type
bench --site mysite set-property "Sales Invoice" \
  --property "title_field" --value "customer" \
  --property-type "Data"

# Set numeric property
bench --site mysite set-property "Sales Invoice" \
  --property "width" --value "200" \
  --property-type "Int" \
  --field "customer"
```

**Common Properties:**

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `reqd` | Check | Make field required | `--value "1"` |
| `hidden` | Check | Hide field | `--value "1"` |
| `read_only` | Check | Make field read-only | `--value "1"` |
| `allow_copy` | Check | Allow copying DocType | `--value "1"` |
| `in_list_view` | Check | Show in list view | `--value "1"` |
| `label` | Data | Change field label | `--value "New Label"` |
| `default` | Data | Set default value | `--value "Default"` |

### Complete Customization Workflow

```bash
# 1. Create a DocType
bench --site mysite new-doctype "Invoice" \
  -f "customer:Link:options=Customer" \
  -f "amount:Currency" \
  -m "Custom"

# 2. Add custom fields
bench --site mysite customize-doctype "Invoice" \
  -f "priority:Select:options=Low,Medium,High" \
  -f "notes:Text" \
  --insert-after "customer"

# 3. Modify properties
bench --site mysite set-property "Invoice" \
  --property "reqd" --value "1" \
  --field "customer"

bench --site mysite set-property "Invoice" \
  --property "allow_copy" --value "1"
```

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

- **Rapid DocType scaffolding** - Create DocTypes from command line
- **Customize existing DocTypes** - Add custom fields and modify properties
- **Human-readable syntax** - Simple, declarative field definitions
- **Smart defaults** - Auto-detects property types for common operations
- **Automatic module management** - Handles module creation and validation
- **Built-in validation** - Error checking and helpful messages
- **Seamless integration** - Works with standard bench CLI
- **Perfect for prototyping** - Rapid iteration and scripting

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

### new-doctype

Create a new DocType with specified fields.

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

### customize-doctype

Add custom fields to an existing DocType.

```bash
# Show help
bench customize-doctype --help

# Simple: Add fields
bench --site mysite customize-doctype "Sales Invoice" \
  -f "notes:Text" \
  -f "priority:Select:options=Low,Medium,High"

# With insertion point
bench --site mysite customize-doctype "Sales Invoice" \
  -f "custom_field:Data" \
  --insert-after "customer"
```

### set-property

Set properties on DocType or fields using Property Setters.

```bash
# Show help
bench set-property --help

# Simple: Make field required (auto-detects property-type)
bench --site mysite set-property "Sales Invoice" \
  --property "reqd" --value "1" \
  --field "customer"

# Simple: DocType-level property
bench --site mysite set-property "Sales Invoice" \
  --property "allow_copy" --value "1"

# Detailed: Explicit property type
bench --site mysite set-property "Sales Invoice" \
  --property "label" --value "Customer Name" \
  --property-type "Data" \
  --field "customer"
```

## Limitations

- Limited to common field types (11 types supported)
- Creates standard DocTypes only (no Single, Tree, or Child DocTypes)
- Permissions fixed to System Manager role
- No controller class generation
- Best for initial structure; refine complex features in Desk

## Roadmap

### Next Steps

**1. REST API Interface**
- Expose DocType creation via REST endpoints
- Enable external applications to generate DocTypes programmatically
- Standard HTTP interface for integration with any tech stack

**2. MCP (Model Context Protocol) Support**
- Implement MCP server for LLM integration
- Allow AI agents to create and modify DocTypes via MCP
- Enable conversational schema design through AI assistants

These additions will make Commander accessible beyond the command line, supporting both traditional API integrations and modern LLM-driven workflows.

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



