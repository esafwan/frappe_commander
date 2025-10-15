# Commander - Frappe DocType CLI Generator

## Project Overview

**Commander** is a pure CLI tool for rapidly creating Frappe DocTypes with fields through the command line. It eliminates the need to manually create DocTypes through the Desk UI or write JSON files, enabling rapid prototyping and scaffolding of data models.

**Primary Objective:** Provide a simple, declarative CLI interface to generate Frappe DocTypes with field definitions, validation rules, and permissions in seconds.

**Tech Stack:**
- **Language:** Python 3.10+
- **Framework:** Frappe Framework (CLI integration via Click)
- **CLI Library:** Click (command-line interface framework)
- **APIs Used:** Frappe ORM, DocType API, Module API

**Repository:** `/workspace/development/override/apps/commander`

---

## Quick Start

### Installation

```bash
# Get the app
cd /path/to/frappe-bench
bench get-app /workspace/development/override/apps/commander

# Install on a site
bench --site your-site install-app commander
```

### Basic Usage

```bash
# Create a simple DocType
bench --site mysite new-doctype "Product" \
  -f "product_name:Data:*" \
  -f "price:Currency" \
  -m "Custom"

# Output: DocType 'Product' created in module 'Custom'.
```

### Field Definition Syntax

```
<fieldname>:<fieldtype>[:<attribute1>[:<attribute2>...]]

Examples:
  name:Data:*                           → Required Data field
  email:Data:*:unique                   → Required + unique
  status:Select:options=Open,Closed     → Select with options
  customer:Link:options=Customer        → Link to Customer DocType
  amount:Currency:?=0                   → Currency with default 0
  description:Text:readonly             → Read-only text field
```

---

## Architecture & Implementation

### Directory Structure

```
commander/
├── __init__.py          # Package init with version
├── commands.py          # CLI command implementation (MAIN FILE)
├── hooks.py             # Frappe app metadata
└── patches.txt          # Database patches (empty)
```

### Core Components

#### 1. **CLI Command Registration** (`commands.py`)

**Location:** `commander/commands.py:129-163`

```python
@click.command("new-doctype")
@click.argument("doctype_name")
@click.option("-f", "--fields", multiple=True, help="Field definitions.")
@click.option("-m", "--module", default="Custom", help="Module name.")
@click.option("--no-interact", is_flag=True, default=False)
@pass_context
def new_doctype_cmd(context, doctype_name, fields, module, no_interact):
    """Create a new DocType with specified fields."""
    # Implementation...
```

**How it works:**
- Uses Click's `@click.command()` decorator to create `bench new-doctype`
- `@pass_context` passes Frappe bench context (site info)
- Registered in `commands` list at end of file for bench discovery

**Bench Integration:**
```python
# Line 163
commands = [new_doctype_cmd]
```

This list is automatically discovered by Frappe's command loader, making `bench new-doctype` available system-wide.

---

#### 2. **Field Parser** (`commands.py`)

**Location:** `commander/commands.py:13-67`

**Purpose:** Parse human-readable field definitions into Frappe field dictionaries.

**Implementation:**

```python
ALLOWED_FIELD_TYPES = {
    "Data", "Text", "Int", "Float", "Date", "Datetime",
    "Select", "Link", "Table", "Check", "Currency", "Percent"
}

def parse_field_definition(field_def):
    """
    Parse: "fieldname:fieldtype:attr1:attr2"
    Returns: {"fieldname": "...", "fieldtype": "...", "reqd": 1, ...}
    """
    parts = field_def.split(":")
    # ... parsing logic
```

**Supported Attributes:**

| Attribute | Syntax | Effect | Example |
|-----------|--------|--------|---------|
| Required | `*` | Sets `reqd=1` | `name:Data:*` |
| Unique | `unique` | Sets `unique=1` | `email:Data:unique` |
| Read-only | `readonly` | Sets `read_only=1` | `code:Data:readonly` |
| Options | `options=<val>` | Sets field options | `status:Select:options=Open,Closed` |
| Default | `?=<val>` | Sets default value | `count:Int:?=0` |

**Parsing Flow:**
```
Input: "customer_name:Data:*:unique"
  ↓
Split by ":" → ["customer_name", "Data", "*", "unique"]
  ↓
Parse fieldtype → "Data" (validate against ALLOWED_FIELD_TYPES)
  ↓
Parse attributes → {reqd: 1, unique: 1}
  ↓
Output: {
  "fieldname": "customer_name",
  "fieldtype": "Data",
  "label": "Customer Name",
  "reqd": 1,
  "unique": 1
}
```

**Validation:**
- Checks fieldtype is in `ALLOWED_FIELD_TYPES`
- Validates `options=` only for Select/Link/Table
- Validates default values match fieldtype (e.g., numeric for Int)

---

#### 3. **DocType Creator** (`commands.py`)

**Location:** `commander/commands.py:74-127`

**Purpose:** Create Frappe DocType using parsed field definitions.

**Frappe APIs Used:**

```python
# 1. Check if DocType exists
frappe.db.exists("DocType", doctype_name)  # Line 76

# 2. Create/find module
frappe.get_doc("Module Def", module_name)  # Line 85
frappe.get_installed_apps()                # Line 86

# 3. Create new DocType
dt = frappe.new_doc("DocType")             # Line 103

# 4. Set DocType properties
dt.update({
    "name": doctype_name,
    "module": module_name,
    "custom": 1,                           # Custom DocType flag
    "fields": fields,                      # Parsed fields list
    "istable": 0,                          # Not a child table
    "issingle": 0,                         # Not a single doctype
    "document_type": "Document"            # Standard document
})

# 5. Set permissions
dt.set("permissions", [{
    "role": "System Manager",
    "read": 1, "write": 1, "create": 1,
    "delete": 1, "print": 1, "email": 1, "share": 1
}])

# 6. Save to database
dt.insert()                                # Line 124
frappe.db.commit()                         # Line 125
```

**Module Resolution Logic:**

```python
if module_name.lower() == "custom":
    custom = True              # Mark as custom DocType
elif frappe.db.exists("Module Def", module_name):
    module_doc = frappe.get_doc("Module Def", module_name)
elif module_name in frappe.get_installed_apps():
    # Create module if app exists but module doesn't
    mod = frappe.get_doc({
        "doctype": "Module Def",
        "module_name": module_name,
        "app_name": module_name
    })
    mod.insert()
    frappe.db.commit()
else:
    raise Exception(f"Module or App '{module_name}' not found.")
```

**Why this matters:**
- Allows creating DocTypes in existing app modules (e.g., "ERPNext")
- Automatically creates Module Def if app exists
- Falls back to "Custom" module for ad-hoc DocTypes

---

## Frappe Integration Points

### 1. **Command Discovery**

**File:** `commands.py:163`

```python
commands = [new_doctype_cmd]
```

**How Frappe finds it:**
1. Frappe scans installed apps for `commands.py` files
2. Imports the `commands` list
3. Registers each Click command as a bench subcommand
4. Makes them available via `bench <command-name>`

### 2. **Site Context**

**File:** `commands.py:145-148`

```python
@pass_context
def new_doctype_cmd(context, ...):
    site = get_site(context)           # Get current site from context
    with frappe.init_site(site):       # Initialize Frappe for site
        frappe.connect()                # Connect to database
        # ... create DocType
```

**Flow:**
```
bench --site mysite new-doctype "Product"
  ↓
Bench passes site="mysite" in context
  ↓
get_site(context) extracts site name
  ↓
frappe.init_site(site) loads site config
  ↓
frappe.connect() opens DB connection
  ↓
Create DocType in this site's database
```

### 3. **DocType Creation API**

**Frappe's DocType is a meta-DocType** (DocType that defines DocTypes):

```python
# DocType schema (simplified)
{
    "doctype": "DocType",
    "name": "Product",              # DocType name
    "module": "Custom",             # Module/app
    "custom": 1,                    # Custom vs standard
    "fields": [                     # Field definitions
        {
            "fieldname": "product_name",
            "fieldtype": "Data",
            "label": "Product Name",
            "reqd": 1
        }
    ],
    "permissions": [                # Role permissions
        {"role": "System Manager", "read": 1, "write": 1, ...}
    ]
}
```

When you call `dt.insert()`:
1. Frappe validates the DocType schema
2. Creates database table `tabProduct`
3. Creates field columns
4. Registers DocType in `tabDocType`
5. Caches schema for runtime use

---

## Capabilities

### What Commander Can Do

**1. Create Standard DocTypes**
```bash
bench --site mysite new-doctype "Customer" \
  -f "customer_name:Data:*" \
  -f "email:Data:unique" \
  -f "phone:Data" \
  -m "Custom"
```

**2. Create DocTypes with Complex Fields**
```bash
bench --site mysite new-doctype "Invoice" \
  -f "invoice_number:Data:*:readonly" \
  -f "customer:Link:*:options=Customer" \
  -f "date:Date:*:?=Today" \
  -f "total:Currency:?=0" \
  -f "status:Select:options=Draft,Submitted,Paid" \
  -m "Accounting"
```

**3. Rapid Prototyping**
```bash
# Create related DocTypes quickly
bench --site mysite new-doctype "Project" \
  -f "project_name:Data:*" \
  -f "start_date:Date" \
  -m "Projects"

bench --site mysite new-doctype "Task" \
  -f "task_name:Data:*" \
  -f "project:Link:options=Project" \
  -f "status:Select:options=Open,Done" \
  -m "Projects"
```

**4. Module Management**
- Creates DocTypes in any installed app's module
- Auto-creates Module Def if app exists but module doesn't
- Falls back to "Custom" module safely

**5. Validation**
- Prevents duplicate DocType names
- Validates field types against allowed list
- Validates attribute combinations
- Checks module/app existence

---

## Limitations & Constraints

### Current Limitations

**1. Field Types**
- **Limited to 11 types:** Data, Text, Int, Float, Date, Datetime, Select, Link, Table, Check, Currency, Percent
- **Missing:** Attach, HTML, Code, Markdown, Color, Rating, Duration, etc.
- **Why:** Simplicity and common use cases; can be extended easily

**2. Field Attributes**
- **Supported:** Required, Unique, Readonly, Options, Default
- **Missing:** 
  - Field descriptions/help text
  - Field dependencies (`depends_on`)
  - Fetch from (`fetch_from`)
  - Field width/precision
  - In list view/standard filter flags
- **Why:** Most common attributes covered; others require more complex syntax

**3. DocType Features**
- **No support for:**
  - Child tables (Table fields defined but not populated)
  - Naming rules (always auto-naming with hash)
  - Workflows
  - Document states
  - Custom permissions per field
  - Field groups/sections/columns
- **Why:** CLI complexity vs UI; these are better done post-creation in Desk

**4. Advanced Schema**
- **Cannot create:**
  - Single DocTypes (issingle=1)
  - Child DocTypes (istable=1)
  - Virtual DocTypes (is_virtual=1)
  - Tree DocTypes (is_tree=1)
- **Why:** These require special setup; focus is on standard documents

**5. Permissions**
- **Fixed to System Manager only** with full CRUD
- **Cannot specify:** Custom roles, granular permissions, dynamic permissions
- **Why:** Permissions are complex; better configured in Desk after creation

**6. Validation & Business Logic**
- **No support for:**
  - Custom validation methods
  - Controller class generation
  - Client scripts (JS)
  - Server scripts (Python)
- **Why:** These require code generation; out of scope for CLI tool

---

## Extension Points

### How to Extend Commander

**1. Add New Field Types**

```python
# In commands.py:7
ALLOWED_FIELD_TYPES = {
    "Data", "Text", "Int", ...,
    "Attach",        # Add file upload
    "HTML",          # Add rich text
    "Code",          # Add code editor
}
```

**2. Add New Attributes**

```python
# In parse_field_definition():65
elif attr.startswith("help="):
    field_dict["description"] = attr[len("help="):]
elif attr.startswith("width="):
    field_dict["width"] = attr[len("width="):]
elif attr.startswith("depends_on="):
    field_dict["depends_on"] = attr[len("depends_on="):]
```

**Usage:**
```bash
bench --site mysite new-doctype "Product" \
  -f "name:Data:*:help=Enter product name" \
  -f "price:Currency:depends_on=eval:doc.is_sellable"
```

**3. Add DocType Options**

```python
# Add click options to new_doctype_cmd():
@click.option("--single", is_flag=True, help="Create Single DocType")
@click.option("--tree", is_flag=True, help="Create Tree DocType")
@click.option("--naming", default="hash", help="Naming rule")
def new_doctype_cmd(context, ..., single, tree, naming):
    # In create_doctype():
    dt.update({
        "issingle": 1 if single else 0,
        "is_tree": 1 if tree else 0,
        "autoname": naming,
        # ...
    })
```

**4. Generate Controller Class**

```python
def generate_controller(doctype_name, module_name):
    """Generate Python controller file."""
    template = f'''
"""
{doctype_name} DocType
"""

import frappe
from frappe.model.document import Document

class {doctype_name.replace(" ", "")}(Document):
    def validate(self):
        """Validate document before saving."""
        pass
    
    def on_submit(self):
        """After document submission."""
        pass
'''
    
    # Write to: apps/{app}/doctype/{snake_case}/
    path = frappe.get_module_path(module_name, "doctype", doctype_name.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    with open(f"{path}/{doctype_name.lower().replace(' ', '_')}.py", "w") as f:
        f.write(template)
```

**5. Add More Commands**

```python
# In commands.py:

@click.command("update-doctype")
@click.argument("doctype_name")
@click.option("-f", "--add-field", multiple=True)
@pass_context
def update_doctype_cmd(context, doctype_name, add_field):
    """Add fields to existing DocType."""
    site = get_site(context)
    with frappe.init_site(site):
        frappe.connect()
        dt = frappe.get_doc("DocType", doctype_name)
        for field_def in add_field:
            field = parse_field_definition(field_def)
            dt.append("fields", field)
        dt.save()
        frappe.db.commit()
        click.echo(f"Updated {doctype_name}")

# Register new command
commands = [new_doctype_cmd, update_doctype_cmd]
```

**Usage:**
```bash
bench --site mysite update-doctype "Product" \
  --add-field "weight:Float" \
  --add-field "dimensions:Text"
```

---

## Code Reference

### Key Methods

| Method | Location | Purpose |
|--------|----------|---------|
| `parse_field_definition()` | `commands.py:13` | Parse field syntax into dict |
| `parse_fields()` | `commands.py:70` | Parse list of field definitions |
| `create_doctype()` | `commands.py:74` | Create DocType using Frappe API |
| `new_doctype_cmd()` | `commands.py:129` | CLI command entry point |

### Frappe API Reference

| API | Usage | Purpose |
|-----|-------|---------|
| `frappe.init_site(site)` | `commands.py:147` | Initialize site context |
| `frappe.connect()` | `commands.py:148` | Connect to database |
| `frappe.db.exists()` | `commands.py:76` | Check if record exists |
| `frappe.get_doc()` | `commands.py:85` | Load existing document |
| `frappe.new_doc()` | `commands.py:103` | Create new document |
| `frappe.get_installed_apps()` | `commands.py:86` | List installed apps |
| `doc.insert()` | `commands.py:124` | Save document to database |
| `frappe.db.commit()` | `commands.py:125` | Commit transaction |

### Click Decorators

| Decorator | Usage | Purpose |
|-----------|-------|---------|
| `@click.command()` | `commands.py:129` | Define CLI command |
| `@click.argument()` | `commands.py:130` | Required positional argument |
| `@click.option()` | `commands.py:131` | Optional flag/parameter |
| `@pass_context` | `commands.py:140` | Pass bench context to function |

---

## Usage Examples

### Basic DocType Creation

```bash
# Minimal DocType (no fields)
bench --site dev.localhost new-doctype "Note"

# With required fields
bench --site dev.localhost new-doctype "Contact" \
  -f "full_name:Data:*" \
  -f "email:Data" \
  -f "phone:Data"
```

### E-commerce Example

```bash
# Product catalog
bench --site shop.localhost new-doctype "Product" \
  -f "product_code:Data:*:unique" \
  -f "product_name:Data:*" \
  -f "description:Text" \
  -f "price:Currency:*:?=0" \
  -f "stock:Int:?=0" \
  -f "category:Select:options=Electronics,Clothing,Food" \
  -f "active:Check:?=1" \
  -m "Inventory"

# Orders
bench --site shop.localhost new-doctype "Order" \
  -f "order_number:Data:*:unique:readonly" \
  -f "customer:Link:*:options=Customer" \
  -f "order_date:Date:*:?=Today" \
  -f "delivery_date:Date" \
  -f "status:Select:*:options=Pending,Confirmed,Shipped,Delivered" \
  -f "total:Currency:?=0" \
  -m "Sales"
```

### CRM Example

```bash
# Lead management
bench --site crm.localhost new-doctype "Lead" \
  -f "lead_name:Data:*" \
  -f "email:Data:unique" \
  -f "phone:Data" \
  -f "company:Data" \
  -f "status:Select:options=New,Qualified,Lost" \
  -f "source:Select:options=Website,Referral,Cold Call" \
  -f "notes:Text" \
  -m "CRM"

# Deal tracking
bench --site crm.localhost new-doctype "Deal" \
  -f "deal_name:Data:*" \
  -f "lead:Link:options=Lead" \
  -f "value:Currency" \
  -f "probability:Percent:?=50" \
  -f "stage:Select:options=Proposal,Negotiation,Closed Won,Closed Lost" \
  -f "expected_close_date:Date" \
  -m "CRM"
```

### Project Management Example

```bash
# Projects
bench --site pm.localhost new-doctype "Project" \
  -f "project_name:Data:*" \
  -f "client:Link:options=Customer" \
  -f "start_date:Date:*" \
  -f "end_date:Date" \
  -f "status:Select:*:options=Planning,Active,On Hold,Completed" \
  -f "budget:Currency" \
  -m "Projects"

# Tasks
bench --site pm.localhost new-doctype "Task" \
  -f "task_title:Data:*" \
  -f "project:Link:*:options=Project" \
  -f "assigned_to:Link:options=User" \
  -f "priority:Select:options=Low,Medium,High,Urgent" \
  -f "status:Select:*:options=Open,In Progress,Done" \
  -f "due_date:Date" \
  -m "Projects"
```

---

## Troubleshooting

### Common Issues

#### Issue: "DocType already exists"

**Symptom:**
```
Exception: DocType 'Product' already exists.
```

**Solution:**
```bash
# Delete existing DocType first
bench --site mysite console
>>> frappe.delete_doc("DocType", "Product")
>>> frappe.db.commit()
>>> exit()

# Or use a different name
bench --site mysite new-doctype "Product V2" ...
```

---

#### Issue: "Module not found"

**Symptom:**
```
Exception: Module or App 'MyModule' not found.
```

**Solution:**
```bash
# Use "Custom" module (always exists)
bench --site mysite new-doctype "Product" ... -m "Custom"

# Or install the app first
bench get-app myapp
bench --site mysite install-app myapp

# Or create module manually
bench --site mysite console
>>> frappe.get_doc({"doctype": "Module Def", "module_name": "MyModule", "app_name": "frappe"}).insert()
>>> frappe.db.commit()
```

---

#### Issue: "Invalid field type"

**Symptom:**
```
ValueError: Unsupported field type 'Attachment' for 'document'.
```

**Solution:**
Use supported field types only:
- Supported: `Data`, `Text`, `Int`, `Float`, `Currency`, `Percent`
- Supported: `Date`, `Datetime`
- Supported: `Select`, `Link`, `Table`
- Supported: `Check`
- Not supported: `Attach`, `HTML`, `Code`, etc. (not supported yet)

---

#### Issue: "No site specified"

**Symptom:**
```
Usage: bench new-doctype [OPTIONS] DOCTYPE_NAME
Error: --site option is required
```

**Solution:**
Always specify site:
```bash
bench --site mysite new-doctype "Product" ...
```

---

## Development Workflow

### Making Changes to Commander

```bash
# 1. Edit command logic
cd /workspace/development/override/apps/commander
vim commander/commands.py

# 2. Test changes
cd /workspace/development/override  # or develop
bench --site test.localhost new-doctype "TestDoc" ...

# 3. Check for errors
tail -f logs/error.log

# 4. Iterate
```

### Adding New Features

**Example: Add field description support**

```python
# 1. Update parser (commands.py:13)
def parse_field_definition(field_def):
    # ... existing code ...
    elif attr.startswith("desc="):
        field_dict["description"] = attr[len("desc="):]
    # ...

# 2. Test
bench --site mysite new-doctype "Product" \
  -f "name:Data:*:desc=Product name" \
  -f "price:Currency:desc=Selling price"

# 3. Verify in Desk
# Go to Product DocType → Fields
# Check if description appears in field definition
```

### Testing

```bash
# Create test DocType
bench --site test.localhost new-doctype "Test Product" \
  -f "name:Data:*" \
  -f "price:Currency" \
  -m "Custom"

# Verify in console
bench --site test.localhost console
>>> dt = frappe.get_doc("DocType", "Test Product")
>>> print(dt.name)  # Should print: Test Product
>>> print(len(dt.fields))  # Should show field count
>>> exit()

# Clean up
bench --site test.localhost console
>>> frappe.delete_doc("DocType", "Test Product", force=1)
>>> frappe.db.commit()
```

---

## Best Practices

### 1. **Start with Custom Module**

```bash
# Good: Start in Custom
bench --site mysite new-doctype "Product" ... -m "Custom"

# Later, if needed, move to proper module via Desk
```

### 2. **Use Descriptive Field Names**

```bash
# Bad
-f "n:Data" -f "p:Currency"

# Good
-f "product_name:Data" -f "price:Currency"
```

### 3. **Mark Required Fields Explicitly**

```bash
# Good
-f "customer_name:Data:*"  # Clear that it's required
```

### 4. **Set Sensible Defaults**

```bash
# Good
-f "status:Select:*:options=Draft,Active:?=Draft"
-f "quantity:Int:?=1"
```

### 5. **Create Related DocTypes in Logical Order**

```bash
# Good: Create parent first
bench --site mysite new-doctype "Customer" -f "name:Data:*"
bench --site mysite new-doctype "Order" -f "customer:Link:options=Customer"

# Bad: Link to non-existent DocType will work but show warning
bench --site mysite new-doctype "Order" -f "customer:Link:options=Customer"
bench --site mysite new-doctype "Customer" -f "name:Data:*"
```

---

## Future Enhancements

### Planned Features

**1. Update Existing DocTypes**
```bash
bench update-doctype "Product" \
  --add-field "weight:Float" \
  --remove-field "old_field" \
  --rename-field "name:product_name"
```

**2. DocType Templates**
```bash
bench new-doctype-from-template "invoice" \
  --name "Sales Invoice" \
  --module "Accounting"
```

**3. Bulk Import from CSV**
```bash
bench import-doctypes-from-csv schema.csv
# CSV format: doctype_name,field_name,field_type,attributes,module
```

**4. Generate Controller Classes**
```bash
bench new-doctype "Product" ... --generate-controller
# Creates: apps/custom/custom/doctype/product/product.py
```

**5. Interactive Mode**
```bash
bench new-doctype --interactive
# Prompts for: name, module, fields one by one
```

**6. JSON/YAML Import**
```bash
bench new-doctype-from-json schema.json
bench new-doctype-from-yaml schema.yml
```

---

## AI Agent Guidelines

### When Working with Commander

**1. Understanding the Codebase:**
- Single file focus: `commands.py` contains all logic
- Three main functions: parse, create, command
- Uses Click for CLI, Frappe ORM for database

**2. Making Changes:**
- Test every change with `bench new-doctype`
- Validate field parser with edge cases
- Check Frappe docs for API changes

**3. Extending Functionality:**
- Add field types in `ALLOWED_FIELD_TYPES`
- Add attributes in `parse_field_definition()`
- Add new commands by copying `new_doctype_cmd()` pattern
- Always register in `commands` list at end

**4. Debugging:**
- Use `click.echo()` for output, not `print()`
- Check `frappe.log_error()` for Frappe-specific errors
- Test with `bench --site test.localhost` first

**5. Code Style:**
- Follow existing conventions (snake_case, docstrings)
- Keep parser logic in separate functions
- Use Click's built-in validation where possible
- Document new features in this AGENTS.md

**6. Common Pitfalls:**
- Don't forget `frappe.db.commit()` after changes
- Always check DocType existence before creating
- Validate module exists or use "Custom"
- Remember Click collects multiple `-f` flags in a tuple

---

## Resources

### Official Documentation

**Frappe:**
- [DocType API](https://frappeframework.com/docs/user/en/api/document) - Document methods
- [Database API](https://frappeframework.com/docs/user/en/api/database) - DB operations
- [CLI Guide](https://frappeframework.com/docs/user/en/bench/frappe-commands) - Bench commands

**Click:**
- [Documentation](https://click.palletsprojects.com/) - CLI framework
- [Options Guide](https://click.palletsprojects.com/en/8.1.x/options/) - Command options
- [Arguments](https://click.palletsprojects.com/en/8.1.x/arguments/) - Positional args

### Related Tools

- [Frappe Docker](https://github.com/frappe/frappe_docker) - Containerized setup
- [Bench](https://github.com/frappe/bench) - Development tool
- [ERPNext](https://github.com/frappe/erpnext) - Example Frappe app

---

## Summary

**Commander** is a lightweight CLI tool that brings rapid DocType creation to Frappe. It:

- Parses human-readable field definitions
- Creates DocTypes using Frappe's meta-DocType API
- Handles module management automatically
- Provides sensible defaults and validation
- Integrates seamlessly with `bench` CLI

**Primary Use Cases:**
1. Rapid prototyping of data models
2. Scripted DocType generation (CI/CD)
3. Quick scaffolding for new projects
4. Learning Frappe schema structure

**Not Intended For:**
- Complex DocTypes with workflows/dependencies
- DocTypes requiring custom controllers
- Production schema management (use migrations)
- Replacing Desk UI for detailed configuration

**Philosophy:** Create fast, refine in Desk. Get 80% of DocType structure via CLI, polish the remaining 20% in UI.

---

*This documentation is comprehensive and current as of October 2025.*

