import re
import click
import frappe
from frappe.commands import get_site, pass_context

# Allowed field types
ALLOWED_FIELD_TYPES = {
    "Data", "Text", "Int", "Float", "Date", "Datetime",
    "Select", "Link", "Table", "Check", "Currency", "Percent"
}

# Field type descriptions for help
FIELD_TYPE_DESCRIPTIONS = {
    "Data": "Short text field (up to 140 characters)",
    "Text": "Long text field (multi-line)",
    "Int": "Integer number",
    "Float": "Decimal number",
    "Date": "Date picker",
    "Datetime": "Date and time picker",
    "Select": "Dropdown with predefined options",
    "Link": "Link to another DocType",
    "Table": "Child table (references another DocType)",
    "Check": "Boolean checkbox",
    "Currency": "Currency amount",
    "Percent": "Percentage value"
}


def parse_field_definition(field_def):
    parts = field_def.split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid field definition '{field_def}'. Expected <fieldname>:<fieldtype>.")
    fieldname = parts[0].strip()
    fieldtype = parts[1].strip().title()
    if fieldtype not in ALLOWED_FIELD_TYPES:
        raise ValueError(f"Unsupported field type '{fieldtype}' for '{fieldname}'.")
    field_dict = {
        "fieldname": fieldname,
        "fieldtype": fieldtype,
        "label": fieldname.replace("_", " ").title()
    }
    for attr in parts[2:]:
        attr = attr.strip()
        if not attr:
            continue
        if attr == "*":
            field_dict["reqd"] = 1
        elif attr.lower() == "unique":
            field_dict["unique"] = 1
        elif attr.lower() == "readonly":
            field_dict["read_only"] = 1
        elif attr.startswith("options="):
            options_value = attr[len("options="):]
            if fieldtype in {"Link", "Table"}:
                field_dict["options"] = options_value
            elif fieldtype == "Select":
                opts = [opt.strip() for opt in re.split(r"[|,]", options_value) if opt.strip()]
                field_dict["options"] = "\n".join(opts)
            else:
                raise ValueError(f"'options=' not valid for field type {fieldtype}.")
        elif attr.startswith("?="):
            default_val = attr[len("?="):]
            if fieldtype in {"Int", "Check"}:
                if default_val.lower() in {"1", "true", "yes"}:
                    field_dict["default"] = "1"
                elif default_val.lower() in {"0", "false", "no"}:
                    field_dict["default"] = "0"
                else:
                    if default_val.isdigit():
                        field_dict["default"] = default_val
                    else:
                        raise ValueError(f"Invalid default '{default_val}' for '{fieldname}'.")
            elif fieldtype in {"Float", "Currency", "Percent"}:
                try:
                    float(default_val)
                    field_dict["default"] = default_val
                except ValueError:
                    raise ValueError(f"Invalid default '{default_val}' for '{fieldname}'.")
            else:
                field_dict["default"] = default_val
        else:
            raise ValueError(f"Unrecognized attribute '{attr}' in '{field_def}'.")
    return field_dict


def parse_fields(field_list):
    return [parse_field_definition(f) for f in field_list]


def prompt_for_doctype_name():
    """Prompt user for DocType name."""
    while True:
        name = click.prompt(
            "\n📝 Enter DocType name",
            type=str,
            default=""
        ).strip()
        if name:
            # Validate name (basic validation)
            if not re.match(r'^[A-Za-z][A-Za-z0-9\s]*$', name):
                click.echo("❌ Invalid name. Use letters, numbers, and spaces. Must start with a letter.")
                continue
            return name
        click.echo("❌ DocType name cannot be empty.")


def prompt_for_module():
    """Prompt user for module name."""
    click.echo("\n📦 Module selection:")
    click.echo("   Enter module name (or press Enter for 'Custom')")
    
    module = click.prompt(
        "   Module",
        type=str,
        default="Custom"
    ).strip() or "Custom"
    
    return module


def show_field_examples():
    """Display field definition examples."""
    click.echo("\n💡 Field definition examples:")
    click.echo("   • name:Data:*                    (required text field)")
    click.echo("   • email:Data:*:unique            (required unique text)")
    click.echo("   • price:Currency:?=0             (currency with default)")
    click.echo("   • status:Select:options=Open,Closed  (dropdown)")
    click.echo("   • customer:Link:options=Customer (link to DocType)")
    click.echo("   • description:Text:readonly      (read-only text)")
    click.echo("\n   Format: <fieldname>:<fieldtype>[:attributes...]")
    click.echo("   Type 'help' for more details, 'done' when finished")


def prompt_for_fields():
    """Interactively prompt for fields."""
    fields = []
    click.echo("\n🔧 Adding fields (leave empty to finish):")
    show_field_examples()
    
    field_num = 1
    while True:
        prompt_text = f"\n   Field {field_num}"
        field_def = click.prompt(prompt_text, type=str, default="").strip()
        
        if not field_def:
            if field_num == 1:
                click.echo("   ℹ️  No fields added. You can add them later in Desk.")
            break
        
        if field_def.lower() == "help":
            show_field_help()
            continue
        
        if field_def.lower() == "done":
            break
        
        try:
            parse_field_definition(field_def)
            fields.append(field_def)
            field_num += 1
            click.echo(f"   ✓ Added: {field_def}")
        except ValueError as e:
            click.echo(f"   ❌ Error: {e}")
            click.echo("   Try again or type 'help' for examples")
    
    return fields


def show_field_help():
    """Show detailed field help."""
    click.echo("\n" + "="*60)
    click.echo("FIELD DEFINITION HELP")
    click.echo("="*60)
    
    click.echo("\n📋 Supported Field Types:")
    for ftype, desc in sorted(FIELD_TYPE_DESCRIPTIONS.items()):
        click.echo(f"   • {ftype:12} - {desc}")
    
    click.echo("\n🔧 Supported Attributes:")
    click.echo("   • *              - Required field")
    click.echo("   • unique         - Unique constraint")
    click.echo("   • readonly       - Read-only field")
    click.echo("   • options=<val>   - Options for Select/Link/Table")
    click.echo("   • ?=<val>        - Default value")
    
    click.echo("\n📝 Examples:")
    click.echo("   name:Data:*")
    click.echo("   email:Data:*:unique")
    click.echo("   price:Currency:?=0")
    click.echo("   status:Select:options=Draft,Active,Archived")
    click.echo("   customer:Link:*:options=Customer")
    click.echo("   description:Text:readonly")
    click.echo("   quantity:Int:?=1")
    click.echo("   is_active:Check:?=1")
    
    click.echo("\n" + "="*60)


def show_help_command():
    """Display comprehensive help for commander."""
    click.echo("\n" + "="*70)
    click.echo("COMMANDER - Frappe DocType CLI Generator")
    click.echo("="*70)
    
    click.echo("\n📖 QUICK START")
    click.echo("-" * 70)
    click.echo("""
  Create a DocType with fields:
    bench --site mysite new-doctype "Product" \\
      -f "product_name:Data:*" \\
      -f "price:Currency" \\
      -m "Custom"

  Interactive mode (prompts for missing info):
    bench --site mysite new-doctype "Product"
    # Will prompt for fields and module if not provided
""")
    
    click.echo("\n📋 FIELD DEFINITION SYNTAX")
    click.echo("-" * 70)
    click.echo("""
  Format: <fieldname>:<fieldtype>[:<attribute1>[:<attribute2>...]]

  Examples:
    name:Data:*                    → Required text field
    email:Data:*:unique            → Required unique text
    price:Currency:?=0             → Currency with default 0
    status:Select:options=Open,Closed → Dropdown with options
    customer:Link:*:options=Customer → Required link to Customer
    description:Text:readonly       → Read-only text area
    quantity:Int:?=1              → Integer with default 1
    is_active:Check:?=1            → Checkbox default checked
""")
    
    click.echo("\n🔧 SUPPORTED FIELD TYPES")
    click.echo("-" * 70)
    for ftype, desc in sorted(FIELD_TYPE_DESCRIPTIONS.items()):
        click.echo(f"  {ftype:12} - {desc}")
    
    click.echo("\n⚙️  SUPPORTED ATTRIBUTES")
    click.echo("-" * 70)
    click.echo("""
  *              Make field required
  unique         Add unique constraint
  readonly       Make field read-only
  options=<val>  Set options (for Select/Link/Table fields)
  ?=<val>        Set default value
""")
    
    click.echo("\n💡 COMMON USE CASES")
    click.echo("-" * 70)
    click.echo("""
  E-commerce Product:
    bench --site mysite new-doctype "Product" \\
      -f "product_code:Data:*:unique" \\
      -f "product_name:Data:*" \\
      -f "price:Currency:*:?=0" \\
      -f "stock:Int:?=0" \\
      -f "category:Select:options=Electronics,Clothing,Food"

  CRM Lead:
    bench --site mysite new-doctype "Lead" \\
      -f "lead_name:Data:*" \\
      -f "email:Data:unique" \\
      -f "status:Select:options=New,Qualified,Lost" \\
      -m "CRM"

  Project Task:
    bench --site mysite new-doctype "Task" \\
      -f "task_title:Data:*" \\
      -f "project:Link:*:options=Project" \\
      -f "status:Select:*:options=Open,In Progress,Done" \\
      -m "Projects"
""")
    
    click.echo("\n🎯 INTERACTIVE MODE")
    click.echo("-" * 70)
    click.echo("""
  When you run the command without required arguments, Commander will
  prompt you interactively:

    bench --site mysite new-doctype "Product"
    # Prompts: Add fields? (y/n), then guides you through field creation

  Use --no-interact to disable prompts and fail if info is missing.
""")
    
    click.echo("\n📚 MORE INFORMATION")
    click.echo("-" * 70)
    click.echo("""
  • Full documentation: See AGENTS.md
  • Command help: bench new-doctype --help
  • During interactive mode: Type 'help' for field syntax help
""")
    
    click.echo("\n" + "="*70)


def create_doctype(doctype_name, fields, module_name, custom=False):
    # Frappe is already connected to the correct site at this point
    if frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' already exists.")

    module_doc = None
    if module_name:
        if module_name.lower() == "custom":
            custom = True
        else:
            if frappe.db.exists("Module Def", module_name):
                module_doc = frappe.get_doc("Module Def", module_name)
            elif module_name in frappe.get_installed_apps():
                if not frappe.db.exists("Module Def", module_name):
                    mod = frappe.get_doc({
                        "doctype": "Module Def",
                        "module_name": module_name,
                        "app_name": module_name
                    })
                    mod.insert()
                    frappe.db.commit()
                module_doc = frappe.get_doc("Module Def", module_name)
            else:
                raise Exception(f"Module or App '{module_name}' not found.")
        module_name = module_doc.name if module_doc else module_name
    else:
        module_name = "Custom"
        custom = True

    dt = frappe.new_doc("DocType")
    dt.update({
        "name": doctype_name,
        "module": module_name,
        "custom": 1 if custom else 0,
        "fields": fields,
        "istable": 0,
        "issingle": 0,
        "document_type": "Document"
    })
    # Only include permissions valid for a non-submittable, non-importable DocType
    dt.set("permissions", [{
        "role": "System Manager",
        "read": 1,
        "write": 1,
        "create": 1,
        "delete": 1,
        "print": 1,
        "email": 1,
        "share": 1
    }])
    dt.insert()
    frappe.db.commit()
    return dt.name


@click.command("new-doctype")
@click.argument("doctype_name", required=False)
@click.option("-f", "--fields", multiple=True, help="Field definitions in format: <name>:<type>[:attributes...]")
@click.option(
    "-m", "--module", default=None,
    help="App or module to create the DocType in (defaults to 'Custom')."
)
@click.option(
    "--no-interact", is_flag=True, default=False,
    help="Don't prompt; fail if missing required info."
)
@pass_context
def new_doctype_cmd(context, doctype_name, fields, module, no_interact):
    """
    Create a new DocType with specified fields.

    Interactive mode: If doctype_name or fields are missing, Commander will
    prompt you for the information. Type 'help' during field entry for syntax help.

    Examples:
      bench --site mysite new-doctype "Product" -f "name:Data:*" -f "price:Currency"
      bench --site mysite new-doctype "Product"  # Interactive mode
      bench --site mysite new-doctype --help     # Show detailed help
    """
    site = get_site(context)

    with frappe.init_site(site):
        frappe.connect()

        # Interactive mode: prompt for doctype_name if missing
        if not doctype_name:
            if no_interact:
                raise click.UsageError("DocType name is required. Provide it as argument or remove --no-interact for interactive mode.")
            doctype_name = prompt_for_doctype_name()

        # Interactive mode: prompt for module if not provided
        if module is None:
            if no_interact:
                module = "Custom"
            else:
                module = prompt_for_module()

        # Interactive mode: prompt for fields if not provided
        if not fields:
            if no_interact:
                click.echo("ℹ️  No fields provided. Creating DocType without fields.")
                click.echo("   You can add fields later in Desk UI.")
                parsed_fields = []
            else:
                click.echo(f"\n✨ Creating DocType: {doctype_name}")
                click.echo(f"📦 Module: {module}")
                
                add_fields = click.confirm("\n❓ Add fields now?", default=True)
                if add_fields:
                    fields = prompt_for_fields()
                    parsed_fields = parse_fields(fields) if fields else []
                else:
                    click.echo("ℹ️  Skipping fields. You can add them later in Desk UI.")
                    parsed_fields = []
        else:
            parsed_fields = parse_fields(fields)

        # Create the DocType
        try:
            new_dt = create_doctype(doctype_name, parsed_fields, module)
            click.echo(f"\n✅ DocType '{new_dt}' created successfully in module '{module}'.")
            if parsed_fields:
                click.echo(f"   Added {len(parsed_fields)} field(s).")
            else:
                click.echo("   No fields added. Add them in Desk UI or update via CLI.")
        except Exception as e:
            click.echo(f"\n❌ Error creating DocType: {e}", err=True)
            raise click.Abort()


@click.command("help")
@click.option("--field-types", is_flag=True, help="Show detailed field type information")
@click.option("--examples", is_flag=True, help="Show usage examples")
def help_cmd(field_types, examples):
    """
    Show comprehensive help for Commander.

    Examples:
      bench help                    # Show full help
      bench help --field-types      # Show field types only
      bench help --examples         # Show examples only
    """
    if field_types:
        click.echo("\n🔧 FIELD TYPES")
        click.echo("="*70)
        for ftype, desc in sorted(FIELD_TYPE_DESCRIPTIONS.items()):
            click.echo(f"\n{ftype}")
            click.echo(f"  {desc}")
            if ftype == "Select":
                click.echo("  Example: status:Select:options=Open,Closed")
            elif ftype == "Link":
                click.echo("  Example: customer:Link:*:options=Customer")
            elif ftype in {"Int", "Float", "Currency", "Percent"}:
                click.echo(f"  Example: amount:{ftype}:?=0")
        click.echo("\n" + "="*70)
    elif examples:
        click.echo("\n💡 USAGE EXAMPLES")
        click.echo("="*70)
        click.echo("""
Basic Examples:
  # Simple DocType
  bench --site mysite new-doctype "Note"

  # With fields
  bench --site mysite new-doctype "Product" \\
    -f "name:Data:*" \\
    -f "price:Currency"

  # Interactive mode
  bench --site mysite new-doctype "Product"
  # Will prompt for fields and module

E-commerce:
  bench --site mysite new-doctype "Product" \\
    -f "product_code:Data:*:unique" \\
    -f "product_name:Data:*" \\
    -f "price:Currency:*:?=0" \\
    -f "stock:Int:?=0" \\
    -f "category:Select:options=Electronics,Clothing,Food" \\
    -m "Inventory"

CRM:
  bench --site mysite new-doctype "Lead" \\
    -f "lead_name:Data:*" \\
    -f "email:Data:unique" \\
    -f "phone:Data" \\
    -f "status:Select:options=New,Qualified,Lost" \\
    -m "CRM"

Project Management:
  bench --site mysite new-doctype "Task" \\
    -f "task_title:Data:*" \\
    -f "project:Link:*:options=Project" \\
    -f "assigned_to:Link:options=User" \\
    -f "status:Select:*:options=Open,In Progress,Done" \\
    -f "due_date:Date" \\
    -m "Projects"
""")
        click.echo("="*70)
    else:
        show_help_command()


# Register commands for bench to discover
commands = [new_doctype_cmd, help_cmd]
