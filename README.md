# Commander

A lightweight CLI tool extending Frappe Bench to add support for creating DocTypes with fields through the command line to better support development using AI based IDEs.

> **Note:** This is experimental software, not recommended for production use. Commander is part of a wider initiative to make Frappe application development natively agentic—moving beyond low-code to "vibe codable" development from within. This works alongside [frappe_ElevenLabs](https://github.com/tridz-dev/frappe_ElevenLabs) (voice AI interface) and [Huf](https://github.com/tridz-dev/huf) (multi model, multi agent infrastructure build on Frappe). We expect these initiatives to compound and merge over time.

## Overview

Commander eliminates the need to manually create DocTypes through the Desk UI or write JSON files. It provides a simple, declarative CLI interface to generate Frappe DocTypes with field definitions, validation rules, and permissions in seconds.

**Key Features:**
- Create new DocTypes with fields via CLI
- Add custom fields to existing standard DocTypes without modifying JSON files
- Full control over field properties, positioning, and behavior
- Safe customization that persists across Frappe updates


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
# Non-interactive mode (all arguments provided)
bench --site mysite new-doctype "Product" \
  -f "product_name:Data:*" \
  -f "price:Currency" \
  -f "description:Text" \
  -m "Custom"

# Interactive mode (prompts for missing info)
bench --site mysite new-doctype "Product"
# Will guide you through adding fields and selecting module

# Show comprehensive help
bench commander-help
bench commander-help --field-types
bench commander-help --examples
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

#### Basic Attributes (for new DocTypes and custom fields)

| Attribute | Syntax | Effect |
|-----------|--------|--------|
| Required | `*` | Sets field as mandatory |
| Unique | `unique` | Adds unique constraint |
| Read-only | `readonly` | Makes field read-only |
| Options | `options=<val>` | Sets options for Select/Link/Table |
| Default | `?=<val>` | Sets default value |
| Label | `label=<text>` | Custom field label |

#### Custom Field Only Attributes

| Attribute | Syntax | Effect |
|-----------|--------|--------|
| Insert After | `insert_after=<fieldname>` or `--insert-after <fieldname>` | Position field after specified field |
| Hidden | `hidden` | Hide field from form view |
| In List View | `in_list_view` or `inlist` | Show field in list view |
| In Standard Filter | `in_standard_filter` or `infilter` | Show in standard filter dropdown |
| Bold | `bold` | Display field label in bold |
| Translatable | `translatable` | Enable field label translation |
| Bulk Edit | `allow_bulk_edit` or `bulk` | Allow bulk editing |
| Depends On | `depends_on=<expression>` | Show/hide based on condition |
| Mandatory Depends On | `mandatory_depends_on=<expression>` or `mandatory=<expression>` | Make field required based on condition |
| Read-only Depends On | `read_only_depends_on=<expression>` | Make field read-only based on condition |
| Fetch From | `fetch_from=<fieldname>` or `fetch=<fieldname>` | Fetch value from linked document |
| Description | `description=<text>` or `desc=<text>` | Field help text/description |
| Width | `width=<number>` | Field width in pixels |
| Precision | `precision=<number>` or `prec=<number>` | Decimal precision for numeric fields |

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

## Adding Custom Fields to Existing DocTypes

Commander allows you to add custom fields to **standard Frappe DocTypes** (like Customer, Sales Invoice, Item, etc.) without modifying their JSON files. Custom fields are stored separately and persist across Frappe updates.

### Quick Reference

```bash
# Simplest: Just fieldname and type (placed at end)
bench --site mysite add-custom-field "Customer" -f "notes:Text"

# Recommended: With positioning
bench --site mysite add-custom-field "Customer" \
  -f "notes:Text" \
  --insert-after "customer_name"

# Required field
bench --site mysite add-custom-field "Sales Invoice" \
  -f "delivery_date:Date:*" \
  --insert-after "posting_date"

# Field in list view
bench --site mysite add-custom-field "Item" \
  -f "batch_no:Data:inlist" \
  --insert-after "item_name"
```

### Why Custom Fields?

- ✅ **Safe**: Standard DocType JSON files remain untouched
- ✅ **Persistent**: Customizations survive Frappe updates
- ✅ **Flexible**: Full control over field properties and positioning
- ✅ **Version Control**: Can be exported and synced via fixtures

### Sensible Defaults

Commander applies sensible defaults automatically:

- ✅ **Fieldname**: Auto-prefixed with `custom_` if not already prefixed
- ✅ **Label**: Auto-generated from fieldname (e.g., `notes` → `Notes`, `custom_notes` → `Custom Notes`)
- ✅ **Position**: Placed at the end of the form if `--insert-after` is not specified
- ✅ **Visibility**: Field is visible (not hidden) by default
- ✅ **List View**: Field is not shown in list view by default
- ✅ **Standard Filter**: Field is not in standard filter by default

### Quick Start: Simple Examples

These examples show the simplest way to add custom fields. All defaults are applied automatically.

```bash
# Minimal: Just fieldname and type (placed at end, auto-prefixed with custom_)
bench --site mysite add-custom-field "Customer" -f "notes:Text"

# With positioning (recommended for better UX)
bench --site mysite add-custom-field "Customer" \
  -f "notes:Text" \
  --insert-after "customer_name"

# Required field
bench --site mysite add-custom-field "Sales Invoice" \
  -f "delivery_instructions:Text:*" \
  --insert-after "customer"

# Field visible in list view
bench --site mysite add-custom-field "Item" \
  -f "batch_no:Data:inlist" \
  --insert-after "item_name"

# Multiple attributes: required + unique + in list
bench --site mysite add-custom-field "Item" \
  -f "batch_no:Data:*:unique:inlist" \
  --insert-after "item_name"
```

**Note**: You don't need to prefix fieldnames with `custom_` - Commander does this automatically. Both `notes:Text` and `custom_notes:Text` work the same way.

### Detailed Examples: Full Control

These examples show advanced usage with all available options.

#### Field with Description and Help Text

```bash
bench --site mysite add-custom-field "Customer" \
  -f "tax_id:Data:*:desc=Tax identification number for compliance" \
  --insert-after "customer_name"
```

#### Conditional Field (Dependencies)

```bash
# Show field only when checkbox is checked
bench --site mysite add-custom-field "Sales Invoice" \
  -f "discount_reason:Text:depends_on=eval:doc.apply_discount==1" \
  --insert-after "discount_amount"

# Show field based on status
bench --site mysite add-custom-field "Sales Order" \
  -f "cancellation_reason:Text:depends_on=eval:doc.status=='Cancelled'" \
  --insert-after "status"

# Make field required based on condition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "approval_notes:Text:mandatory_depends_on=eval:doc.grand_total>10000" \
  --insert-after "grand_total"

# Make field read-only based on condition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "final_amount:Currency:read_only_depends_on=eval:doc.status=='Submitted'" \
  --insert-after "grand_total"
```

#### Fetch Value from Linked Document

```bash
# Fetch customer email from Customer DocType
bench --site mysite add-custom-field "Sales Invoice" \
  -f "customer_email:Data:fetch_from=customer.email_id" \
  --insert-after "customer"

# Fetch item category from Item DocType
bench --site mysite add-custom-field "Sales Invoice Item" \
  -f "item_category:Data:fetch_from=item.custom_category" \
  --insert-after "item_code"
```

#### Numeric Field with Precision and Width

```bash
bench --site mysite add-custom-field "Sales Invoice" \
  -f "service_charge:Currency:?=0:width=150:precision=2" \
  --insert-after "grand_total"
```

#### Select Field with Options and Styling

```bash
bench --site mysite add-custom-field "Customer" \
  -f "segment:Select:options=Enterprise,SMB,Startup:bold:translatable:inlist" \
  --insert-after "customer_name"
```

#### Hidden Field (Internal Use Only)

```bash
bench --site mysite add-custom-field "Customer" \
  -f "internal_notes:Text:hidden:desc=Internal team notes only"
```

#### Read-only Field with Default

```bash
bench --site mysite add-custom-field "Sales Invoice" \
  -f "invoice_number:Data:*:readonly:?=AUTO" \
  --insert-after "name"
```

### Real-World Examples: Extending Standard DocTypes

Complete examples showing how to extend common Frappe DocTypes.

#### Extend Customer DocType

```bash
# Customer segment (simple)
bench --site mysite add-custom-field "Customer" \
  -f "segment:Select:options=Enterprise,SMB,Startup:inlist" \
  --insert-after "customer_name"

# Credit limit (with formatting)
bench --site mysite add-custom-field "Customer" \
  -f "credit_limit:Currency:width=150:precision=2:?=0" \
  --insert-after "credit_limit"

# Internal notes (hidden from portal)
bench --site mysite add-custom-field "Customer" \
  -f "internal_notes:Text:hidden:desc=Internal team notes only"
```

#### Extend Sales Invoice DocType

```bash
# Delivery date (required)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "delivery_date:Date:*" \
  --insert-after "posting_date"

# Delivery instructions
bench --site mysite add-custom-field "Sales Invoice" \
  -f "delivery_instructions:Text:desc=Special delivery instructions" \
  --insert-after "shipping_address"

# Discount approval (conditional - shows only for large discounts)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "discount_approved_by:Link:options=User:depends_on=eval:doc.discount_amount>1000" \
  --insert-after "discount_amount"

# Project reference
bench --site mysite add-custom-field "Sales Invoice" \
  -f "project:Link:options=Project" \
  --insert-after "customer"
```

#### Extend Item DocType

```bash
# Batch tracking flag
bench --site mysite add-custom-field "Item" \
  -f "batch_required:Check:?=0:inlist" \
  --insert-after "has_batch_no"

# Expiry tracking flag
bench --site mysite add-custom-field "Item" \
  -f "expiry_tracking:Check:?=0" \
  --insert-after "has_expiry_date"

# Custom category (with styling)
bench --site mysite add-custom-field "Item" \
  -f "category:Select:options=Premium,Standard,Economy:inlist:bold" \
  --insert-after "item_group"

# Supplier part number
bench --site mysite add-custom-field "Item" \
  -f "supplier_part_no:Data:desc=Supplier's part number" \
  --insert-after "item_code"
```

#### Extend Sales Order DocType

```bash
# Expected delivery date
bench --site mysite add-custom-field "Sales Order" \
  -f "expected_delivery:Date:*" \
  --insert-after "delivery_date"

# Priority level (with default)
bench --site mysite add-custom-field "Sales Order" \
  -f "priority:Select:options=Low,Medium,High,Urgent:?=Medium:inlist:bold" \
  --insert-after "status"

# Special instructions (wide field)
bench --site mysite add-custom-field "Sales Order" \
  -f "special_instructions:Text:width=500" \
  --insert-after "terms"
```

### Field Positioning

Use `--insert-after` to control where your custom field appears in the form. If not specified, the field is placed at the end.

```bash
# Insert after a specific field (recommended)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "field:Data" \
  --insert-after "customer"

# Or use insert_after in field definition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "field:Data:insert_after=customer"

# No positioning = placed at end (default)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "field:Data"
```

**Common positioning targets:**
- `customer` / `customer_name` - After customer field
- `item_code` - After item code
- `grand_total` - After grand total
- `status` - After status field
- `name` - At the beginning (after name field)
- `posting_date` - After posting date
- `shipping_address` - After shipping address

### Field Dependencies

Control field visibility, requirement, and read-only state based on other field values:

```bash
# Show/hide field based on condition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "discount_reason:Text:depends_on=eval:doc.apply_discount==1" \
  --insert-after "discount_amount"

# Show field based on status
bench --site mysite add-custom-field "Sales Order" \
  -f "cancellation_reason:Text:depends_on=eval:doc.status=='Cancelled'" \
  --insert-after "status"

# Make field required based on condition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "approval_notes:Text:mandatory_depends_on=eval:doc.grand_total>10000" \
  --insert-after "grand_total"

# Make field read-only based on condition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "final_amount:Currency:read_only_depends_on=eval:doc.status=='Submitted'" \
  --insert-after "grand_total"

# Multiple conditions
bench --site mysite add-custom-field "Sales Invoice" \
  -f "approval:Link:options=User:depends_on=eval:doc.grand_total>10000 && doc.status=='Draft'"
```

### Fetching Values from Linked Documents

Automatically populate fields from linked DocTypes:

```bash
# Fetch customer email from Customer
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_customer_email:Data:fetch_from=customer.email_id" \
  --insert-after "customer"

# Fetch item category from Item
bench --site mysite add-custom-field "Sales Invoice Item" \
  -f "custom_item_category:Data:fetch_from=item.custom_category" \
  --insert-after "item_code"
```

### Best Practices

1. **Don't worry about `custom_` prefix** - Commander adds it automatically
   ```bash
   # Both work the same way
   -f "notes:Text"           # Auto-prefixed to custom_notes
   -f "custom_notes:Text"    # Explicit prefix (also works)
   ```

2. **Always position fields** using `--insert-after` for better UX
   ```bash
   # Group related fields together
   --insert-after "customer"      # Customer-related fields
   --insert-after "grand_total"   # Financial fields
   --insert-after "status"        # Status-related fields
   ```

3. **Use descriptions** for clarity and help text
   ```bash
   -f "field:Data:desc=Explain what this field is for"
   ```

4. **Test field dependencies** carefully
   ```bash
   # Always test depends_on expressions in Desk UI after creation
   -f "field:Data:depends_on=eval:doc.status=='Active'"
   ```

5. **Refresh browser** after adding custom fields to see changes immediately

6. **Start simple, then enhance** - Add basic fields first, then add attributes as needed
   ```bash
   # Step 1: Add basic field
   bench --site mysite add-custom-field "Customer" -f "notes:Text" --insert-after "customer_name"
   
   # Step 2: Later, if needed, you can enhance it via Desk UI or recreate with more options
   ```

### Limitations

- ❌ Cannot add custom fields to Single DocTypes
- ❌ Cannot add custom fields to custom DocTypes (only standard DocTypes)
- ❌ Cannot modify standard field properties (use Property Setters via Desk UI)
- ❌ Field type changes require deleting and recreating the field

### Viewing Custom Fields

After adding custom fields, you can view them:

1. **In Desk UI**: Go to the DocType form and refresh
2. **Via Console**:
   ```python
   bench --site mysite console
   >>> frappe.get_meta("Sales Invoice").get_field("custom_notes")
   ```

### Removing Custom Fields

To remove a custom field, use Frappe console:

```python
bench --site mysite console
>>> frappe.delete_doc("Custom Field", "Sales Invoice-custom_notes")
>>> frappe.db.commit()
```

## Features

- Rapid DocType scaffolding from command line
- **Interactive mode** - Guided prompts for missing information
- **Comprehensive help system** - Detailed documentation and examples
- Human-readable field definition syntax
- Automatic module management
- Built-in validation and error checking
- Seamless integration with bench CLI
- Perfect for prototyping and scripting
- **Rapid DocType scaffolding** from command line
- **Add custom fields** to existing standard DocTypes without touching JSON files
- **Human-readable field definition syntax** with comprehensive attribute support
- **Automatic module management** and field positioning
- **Built-in validation** and error checking
- **Seamless integration** with bench CLI
- **Perfect for prototyping** and scripting
- **Safe customization** that persists across Frappe updates
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
4. **Extending standard DocTypes** - Add custom fields to Customer, Sales Invoice, Item, etc.
5. **Learning tool** - Understand Frappe schema structure
6. **Customization management** - Version control custom fields via CLI

## Documentation

For comprehensive documentation including:
- Architecture & implementation details
- Extension guides
- API reference
- Best practices
- Troubleshooting

See [AGENTS.md](AGENTS.md) - Complete technical documentation for developers and AI agents.

## Command Reference

### Create New DocType
### new-doctype

Create a new DocType with specified fields.

```bash
# Show command help
bench new-doctype --help

# Show comprehensive help
bench commander-help
bench commander-help --field-types
bench commander-help --examples

# Create with fields (non-interactive)
bench --site mysite new-doctype "DocType Name" \
  -f "field1:Type:*" \
  -f "field2:Type:?=default" \
  -m "Module"

# Interactive mode (prompts for missing info)
bench --site mysite new-doctype "DocType Name"
# Prompts for fields and module if not provided

# Create without fields (add later in Desk)
bench --site mysite new-doctype "Simple DocType"

# Disable interactive mode (fail if missing info)
bench --site mysite new-doctype "Product" --no-interact
```

## Interactive Mode

Commander supports an intuitive interactive mode that guides you through DocType creation:

```bash
$ bench --site mysite new-doctype "Product"

📦 Module selection:
   Module [Custom]: Inventory

❓ Add fields now? [Y/n]: y

🔧 Adding fields (leave empty to finish):
💡 Field definition examples:
   • name:Data:*                    (required text field)
   • price:Currency:?=0             (currency with default)
   ...

   Field 1: product_name:Data:*
   ✓ Added: product_name:Data:*

   Field 2: price:Currency:?=0
   ✓ Added: price:Currency:?=0

   Field 3: [Enter]

✅ DocType 'Product' created successfully in module 'Inventory'.
```

**Interactive Features:**
- Prompts only for missing information
- Validates fields as you enter them
- Type `help` during field entry for syntax assistance
- Type `done` or leave empty to finish
- Clear error messages with suggestions
### Add Custom Field to Existing DocType

```bash
# Show help
bench add-custom-field --help

# SIMPLE: Minimal command (all defaults applied)
bench --site mysite add-custom-field "Customer" -f "notes:Text"

# RECOMMENDED: With positioning
bench --site mysite add-custom-field "Customer" \
  -f "notes:Text" \
  --insert-after "customer_name"

# DETAILED: Full control with all options
bench --site mysite add-custom-field "Sales Invoice" \
  -f "delivery_date:Date:*:inlist:desc=Expected delivery date" \
  --insert-after "posting_date"

# More examples
bench --site mysite add-custom-field "Item" \
  -f "batch_no:Data:*:unique:inlist" \
  --insert-after "item_name"

bench --site mysite add-custom-field "Sales Invoice" \
  -f "discount_reason:Text:depends_on=eval:doc.apply_discount==1" \
  --insert-after "discount_amount"
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

### New DocType Creation
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

> **💡 Tip**: For customizing DocTypes, use `customize_doctype_api` (endpoint #4) - it's the easiest way with simplified property names and bulk operations.

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

#### 3. Add Property Setter (Advanced)

**Endpoint**: `POST /api/method/commander.api.add_property_setter_api`

Low-level endpoint to add a property setter. For most use cases, use `customize_doctype_api` instead.

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

#### 4. Customize DocType (Simplified) ⭐ Recommended

**Endpoint**: `POST /api/method/commander.api.customize_doctype_api`

Simplified endpoint to customize a DocType - add custom fields and modify field properties in one call. Uses intuitive property names and auto-infers property types.

**Request**:
```json
{
  "doctype": "Customer",
  "custom_fields": [
    {
      "field_definition": "custom_industry:Data:*",
      "insert_after": "customer_name"
    },
    {
      "field_definition": "custom_tax_id:Data",
      "insert_after": "custom_industry"
    }
  ],
  "field_properties": {
    "customer_name": {
      "required": true,
      "bold": true
    },
    "email_id": {
      "readonly": false,
      "in_list_view": true
    }
  },
  "doctype_properties": {
    "allow_copy": true,
    "track_changes": true
  }
}
```

**Response** (Success):
```json
{
  "success": true,
  "message": "DocType 'Customer' customized successfully",
  "data": {
    "doctype": "Customer",
    "custom_fields_added": 2,
    "field_properties_modified": 2,
    "doctype_properties_modified": 2,
    "errors": []
  }
}
```

**Simplified Property Names**:
- `required` / `mandatory` → Sets field as required
- `readonly` / `read_only` → Makes field read-only
- `hidden` → Hides field
- `label` → Changes field label
- `default` → Sets default value
- `options` → Sets options (for Select/Link fields)
- `description` → Sets field description
- `in_list_view` → Shows field in list view
- `in_standard_filter` → Shows in standard filters
- `bold` → Makes label bold
- `collapsible` → Makes section collapsible

**DocType Properties**:
- `allow_copy` → Allow copying documents
- `track_changes` → Track document changes
- `track_seen` → Track if document was seen
- `title_field` → Set title field
- `search_fields` → Set search fields (comma-separated)
- `sort_field` → Set default sort field
- `max_attachments` → Maximum attachments allowed

**Benefits**:
- ✅ No need to know Frappe internal property names (`reqd` vs `required`)
- ✅ Property types auto-inferred (no need to specify `property_type`)
- ✅ Bulk operations - modify multiple fields at once
- ✅ Single call to add fields and modify properties
- ✅ Intuitive property names

#### 5. Get API Documentation

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

### Simplified Customization Example

The `customize_doctype_api` endpoint makes it easy to customize DocTypes without deep Frappe knowledge:

```python
import requests

url = "https://your-site.com/api/method/commander.api.customize_doctype_api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "token YOUR_API_KEY:YOUR_API_SECRET"
}

# Add custom fields and modify existing field properties in one call
data = {
    "doctype": "Customer",
    "custom_fields": [
        {
            "field_definition": "custom_industry:Data:*",
            "insert_after": "customer_name"
        }
    ],
    "field_properties": {
        "customer_name": {
            "required": True,      # Use 'required' instead of 'reqd'
            "bold": True          # Use 'bold' instead of checking property types
        },
        "email_id": {
            "readonly": False,    # Use 'readonly' instead of 'read_only'
            "in_list_view": True  # Simple boolean, no property_type needed
        }
    },
    "doctype_properties": {
        "allow_copy": True,       # Simple boolean
        "track_changes": True
    }
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### Complete Documentation

For complete API documentation including all endpoints, error codes, and examples, call:

```bash
curl https://your-site.com/api/method/commander.api.get_api_documentation
```

Or visit the endpoint in your browser while authenticated.
### Custom Fields

**Restrictions (per Frappe framework):**
- ❌ Cannot add custom fields to **Single DocTypes** (issingle=1)
- ❌ Cannot add custom fields to **custom DocTypes** (only standard DocTypes can be customized)
- ❌ Cannot customize **core DocTypes** (enforced by Frappe API)
- ❌ Cannot modify standard field properties (use Property Setters via Desk UI)
- ❌ Field type changes require deleting and recreating the field

**Supported:**
- ✅ All standard Frappe DocTypes (Customer, Sales Invoice, Item, etc.)
- ✅ All common field types (Data, Text, Int, Float, Date, Datetime, Select, Link, Table, Check, Currency, Percent)
- ✅ All custom field properties available in Desk UI
- ✅ Field positioning, dependencies, and conditional logic

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

# Test new DocType creation
bench --site mysite new-doctype "Test Doc" -f "name:Data:*"

# Test custom field addition
bench --site mysite add-custom-field "Customer" \
  -f "custom_test_field:Data" \
  --insert-after "customer_name"
```


## License

MIT

## Links

- GitHub: https://github.com/esafwan/frappe_commander
- Documentation: [AGENTS.md](AGENTS.md)
- Frappe Framework: https://frappeframework.com
- Bench CLI: https://github.com/frappe/bench



