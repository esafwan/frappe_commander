# Commander

A lightweight CLI tool extending Frappe Bench to add support for creating DocTypes with fields through the command line to better support development using AI based IDEs.

> **Note:** This is experimental software, not recommended for production use. Commander is part of a wider initiative to make Frappe application development natively agentic—moving beyond low-code to "vibe codable" development from within. This works alongside [frappe_ElevenLabs](https://github.com/tridz-dev/frappe_ElevenLabs) (voice AI interface) and [agent_flo](https://github.com/tridz-dev/agent_flo) (multi model, multi agent workflows). We expect these initiatives to compound and merge over time.

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
| Fetch From | `fetch_from=<fieldname>` | Fetch value from linked document |
| Description | `description=<text>` or `desc=<text>` | Field help text/description |
| Width | `width=<number>` | Field width in pixels |
| Precision | `precision=<number>` or `prec=<number>` | Decimal precision for numeric fields |

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

### Why Custom Fields?

- ✅ **Safe**: Standard DocType JSON files remain untouched
- ✅ **Persistent**: Customizations survive Frappe updates
- ✅ **Flexible**: Full control over field properties and positioning
- ✅ **Version Control**: Can be exported and synced via fixtures

### Basic Custom Field Examples

#### Add Simple Fields to Standard DocTypes

```bash
# Add notes field to Customer
bench --site mysite add-custom-field "Customer" \
  -f "custom_notes:Text"

# Add required field with positioning
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_delivery_instructions:Text:*" \
  --insert-after "customer"

# Add field visible in list view
bench --site mysite add-custom-field "Item" \
  -f "custom_batch_no:Data:unique:inlist" \
  --insert-after "item_name"
```

#### Advanced Custom Field Examples

```bash
# Add field with description and help text
bench --site mysite add-custom-field "Customer" \
  -f "custom_tax_id:Data:*:desc=Tax identification number" \
  --insert-after "customer_name"

# Add field with dependencies (conditional display)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_discount_percent:Percent:depends_on=eval:doc.apply_discount==1" \
  --insert-after "grand_total"

# Add field that fetches from linked document
bench --site mysite add-custom-field "Sales Invoice Item" \
  -f "custom_item_category:Data:fetch_from=item.custom_category" \
  --insert-after "item_code"

# Add field with width and precision
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_service_charge:Currency:width=150:precision=2:?=0" \
  --insert-after "taxes_and_charges_total"

# Add translatable field
bench --site mysite add-custom-field "Item" \
  -f "custom_local_name:Data:translatable" \
  --insert-after "item_name"
```

### Real-World Examples: Extending Standard DocTypes

#### Extend Customer DocType

```bash
# Add customer segment
bench --site mysite add-custom-field "Customer" \
  -f "custom_segment:Select:options=Enterprise,SMB,Startup:inlist" \
  --insert-after "customer_name"

# Add credit limit
bench --site mysite add-custom-field "Customer" \
  -f "custom_credit_limit:Currency:width=150:precision=2:?=0" \
  --insert-after "credit_limit"

# Add internal notes (hidden from customer portal)
bench --site mysite add-custom-field "Customer" \
  -f "custom_internal_notes:Text:hidden:desc=Internal team notes only"
```

#### Extend Sales Invoice DocType

```bash
# Add delivery date
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_delivery_date:Date:*" \
  --insert-after "posting_date"

# Add delivery instructions
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_delivery_instructions:Text:desc=Special delivery instructions" \
  --insert-after "shipping_address"

# Add discount approval (conditional)
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_discount_approved_by:Link:options=User:depends_on=eval:doc.discount_amount>1000" \
  --insert-after "discount_amount"

# Add project reference
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_project:Link:options=Project" \
  --insert-after "customer"
```

#### Extend Item DocType

```bash
# Add batch tracking
bench --site mysite add-custom-field "Item" \
  -f "custom_batch_required:Check:?=0:inlist" \
  --insert-after "has_batch_no"

# Add expiry date tracking
bench --site mysite add-custom-field "Item" \
  -f "custom_expiry_tracking:Check:?=0" \
  --insert-after "has_expiry_date"

# Add custom category
bench --site mysite add-custom-field "Item" \
  -f "custom_category:Select:options=Premium,Standard,Economy:inlist:bold" \
  --insert-after "item_group"

# Add supplier part number
bench --site mysite add-custom-field "Item" \
  -f "custom_supplier_part_no:Data:desc=Supplier's part number" \
  --insert-after "item_code"
```

#### Extend Sales Order DocType

```bash
# Add expected delivery date
bench --site mysite add-custom-field "Sales Order" \
  -f "custom_expected_delivery:Date:*" \
  --insert-after "delivery_date"

# Add priority level
bench --site mysite add-custom-field "Sales Order" \
  -f "custom_priority:Select:options=Low,Medium,High,Urgent:?=Medium:inlist:bold" \
  --insert-after "status"

# Add special instructions
bench --site mysite add-custom-field "Sales Order" \
  -f "custom_special_instructions:Text:width=500" \
  --insert-after "terms"
```

### Field Positioning

Use `--insert-after` to control where your custom field appears in the form:

```bash
# Insert after a specific field
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_field:Data" \
  --insert-after "customer"

# Or use insert_after in field definition
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_field:Data:insert_after=customer"
```

**Common positioning targets:**
- `customer` - After customer field
- `item_code` - After item code
- `grand_total` - After grand total
- `status` - After status field
- `name` - At the beginning (after name field)

### Field Dependencies

Control field visibility based on other field values:

```bash
# Show field only when checkbox is checked
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_discount_reason:Text:depends_on=eval:doc.apply_discount==1" \
  --insert-after "discount_amount"

# Show field based on status
bench --site mysite add-custom-field "Sales Order" \
  -f "custom_cancellation_reason:Text:depends_on=eval:doc.status=='Cancelled'" \
  --insert-after "status"

# Multiple conditions
bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_approval:Link:options=User:depends_on=eval:doc.grand_total>10000 && doc.status=='Draft'"
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

1. **Always use `custom_` prefix** for field names (auto-added if omitted)
   ```bash
   # Good - explicit prefix
   -f "custom_notes:Text"
   
   # Also good - prefix added automatically
   -f "notes:Text"
   ```

2. **Position fields logically** using `--insert-after`
   ```bash
   # Group related fields together
   --insert-after "customer"  # Customer-related fields
   --insert-after "grand_total"  # Financial fields
   ```

3. **Use descriptions** for clarity
   ```bash
   -f "custom_field:Data:desc=Explain what this field is for"
   ```

4. **Test field dependencies** carefully
   ```bash
   # Always test depends_on expressions
   -f "custom_field:Data:depends_on=eval:doc.status=='Active'"
   ```

5. **Refresh browser** after adding custom fields to see changes

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

- **Rapid DocType scaffolding** from command line
- **Add custom fields** to existing standard DocTypes without touching JSON files
- **Human-readable field definition syntax** with comprehensive attribute support
- **Automatic module management** and field positioning
- **Built-in validation** and error checking
- **Seamless integration** with bench CLI
- **Perfect for prototyping** and scripting
- **Safe customization** that persists across Frappe updates

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

### Add Custom Field to Existing DocType

```bash
# Show help
bench add-custom-field --help

# Basic usage
bench --site mysite add-custom-field "DocType Name" \
  -f "fieldname:FieldType:attributes" \
  --insert-after "target_field"

# Examples
bench --site mysite add-custom-field "Customer" \
  -f "custom_notes:Text" \
  --insert-after "customer_name"

bench --site mysite add-custom-field "Sales Invoice" \
  -f "custom_delivery_date:Date:*:inlist" \
  --insert-after "posting_date"
```

## Limitations

### New DocType Creation
- Limited to common field types (11 types supported)
- Creates standard DocTypes only (no Single, Tree, or Child DocTypes)
- Permissions fixed to System Manager role
- No controller class generation
- Best for initial structure; refine complex features in Desk

### Custom Fields
- Cannot add custom fields to Single DocTypes
- Cannot add custom fields to custom DocTypes (only standard DocTypes)
- Cannot modify standard field properties (use Property Setters via Desk UI)
- Field type changes require deleting and recreating the field
- Some advanced field types may require Desk UI for full configuration

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



