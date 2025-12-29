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
- **Interactive mode** - Guided prompts for missing information
- **Comprehensive help system** - Detailed documentation and examples
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



