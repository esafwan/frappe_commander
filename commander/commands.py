import re
import click
import frappe
from frappe.commands import get_site, pass_context

try:
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
except ImportError:
    # Fallback for older Frappe versions
    create_custom_field = None

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


def parse_field_definition(field_def, for_custom_field=False):
    """
    Parse field definition string into a dictionary.
    
    Args:
        field_def: Field definition string in format <fieldname>:<fieldtype>[:<attr1>[:<attr2>...]]
        for_custom_field: If True, parse additional custom field properties
    
    Returns:
        Dictionary with field properties
    """
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
        elif attr.lower() == "hidden":
            if for_custom_field:
                field_dict["hidden"] = 1
            else:
                raise ValueError(f"'hidden' attribute only valid for custom fields.")
        elif attr.lower() == "in_list_view" or attr.lower() == "inlist":
            if for_custom_field:
                field_dict["in_list_view"] = 1
            else:
                raise ValueError(f"'in_list_view' attribute only valid for custom fields.")
        elif attr.lower() == "in_standard_filter" or attr.lower() == "infilter":
            if for_custom_field:
                field_dict["in_standard_filter"] = 1
            else:
                raise ValueError(f"'in_standard_filter' attribute only valid for custom fields.")
        elif attr.lower() == "bold":
            if for_custom_field:
                field_dict["bold"] = 1
            else:
                raise ValueError(f"'bold' attribute only valid for custom fields.")
        elif attr.lower() == "translatable":
            if for_custom_field:
                field_dict["translatable"] = 1
            else:
                raise ValueError(f"'translatable' attribute only valid for custom fields.")
        elif attr.lower() == "allow_bulk_edit" or attr.lower() == "bulk":
            if for_custom_field:
                field_dict["allow_bulk_edit"] = 1
            else:
                raise ValueError(f"'allow_bulk_edit' attribute only valid for custom fields.")
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
        elif attr.startswith("insert_after=") or attr.startswith("after="):
            if for_custom_field:
                field_dict["insert_after"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'insert_after' attribute only valid for custom fields.")
        elif attr.startswith("depends_on="):
            if for_custom_field:
                field_dict["depends_on"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'depends_on' attribute only valid for custom fields.")
        elif attr.startswith("mandatory_depends_on=") or attr.startswith("mandatory="):
            if for_custom_field:
                field_dict["mandatory_depends_on"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'mandatory_depends_on' attribute only valid for custom fields.")
        elif attr.startswith("read_only_depends_on=") or attr.startswith("readonly_depends_on="):
            if for_custom_field:
                field_dict["read_only_depends_on"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'read_only_depends_on' attribute only valid for custom fields.")
        elif attr.startswith("fetch_from=") or attr.startswith("fetch="):
            if for_custom_field:
                field_dict["fetch_from"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'fetch_from' attribute only valid for custom fields.")
        elif attr.startswith("description=") or attr.startswith("desc="):
            if for_custom_field:
                field_dict["description"] = attr.split("=", 1)[1].strip()
            else:
                raise ValueError(f"'description' attribute only valid for custom fields.")
        elif attr.startswith("width="):
            if for_custom_field:
                try:
                    field_dict["width"] = int(attr.split("=", 1)[1].strip())
                except ValueError:
                    raise ValueError(f"Invalid width value in '{attr}'.")
            else:
                raise ValueError(f"'width' attribute only valid for custom fields.")
        elif attr.startswith("precision=") or attr.startswith("prec="):
            if for_custom_field:
                try:
                    field_dict["precision"] = int(attr.split("=", 1)[1].strip())
                except ValueError:
                    raise ValueError(f"Invalid precision value in '{attr}'.")
            else:
                raise ValueError(f"'precision' attribute only valid for custom fields.")
        elif attr.startswith("label="):
            field_dict["label"] = attr.split("=", 1)[1].strip()
        else:
            raise ValueError(f"Unrecognized attribute '{attr}' in '{field_def}'.")
    return field_dict


def parse_fields(field_list, for_custom_field=False):
    return [parse_field_definition(f, for_custom_field=for_custom_field) for f in field_list]


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
  • Comprehensive help: bench commander-help
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


@click.command("commander-help")
@click.option("--field-types", is_flag=True, help="Show detailed field type information")
@click.option("--examples", is_flag=True, help="Show usage examples")
def commander_help_cmd(field_types, examples):
    """
    Show comprehensive help for Commander.

    Examples:
      bench commander-help                    # Show full help
      bench commander-help --field-types      # Show field types only
      bench commander-help --examples         # Show examples only
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


def add_custom_field(doctype_name, field_dict):
    """
    Add a custom field to an existing DocType using Frappe's Custom Field API.
    
    Args:
        doctype_name: Name of the DocType to add field to
        field_dict: Dictionary with field properties
    
    Returns:
        Name of the created custom field (with custom_ prefix if auto-added)
    
    Defaults applied:
    - Fieldname is auto-prefixed with 'custom_' if not already prefixed
    - Label is auto-generated from fieldname if not provided
    - Field is positioned at the end if insert_after is not specified
    - Field is visible (not hidden) by default
    - Field is not in list view by default
    - Field is not in standard filter by default
    """
    # Validate DocType exists
    if not frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' does not exist.")
    
    # Get DocType to check if it's customizable
    dt = frappe.get_doc("DocType", doctype_name)
    
    # Check if DocType can be customized
    # Restrictions per Frappe documentation:
    # 1. Cannot customize Single DocTypes
    if dt.get("issingle"):
        raise Exception(
            f"Cannot add custom fields to Single DocType '{doctype_name}'. "
            f"Single DocTypes cannot be customized."
        )
    
    # 2. Cannot customize custom DocTypes (only standard DocTypes can be customized)
    if dt.get("custom"):
        raise Exception(
            f"Cannot add custom fields to custom DocType '{doctype_name}'. "
            f"Only standard DocTypes can be customized. Custom DocTypes should be modified directly."
        )
    
    # 3. Check for core/system DocTypes that shouldn't be customized
    # Core DocTypes are typically in 'frappe' app and have restricted customization
    # Note: This is a soft check - Frappe's create_custom_field will enforce stricter rules
    if dt.get("module") and dt.module.lower() in ["core", "setup"]:
        # Warn but don't block - Frappe's API will handle actual restrictions
        pass
    
    # Apply sensible defaults
    # Frappe's create_custom_field will handle:
    # - Auto-prefixing fieldname with 'custom_' if not prefixed
    # - Auto-generating label from fieldname if not provided
    # - Auto-calculating idx if insert_after is not provided (places at end)
    
    # Normalize fieldname for existence check (Frappe will prefix it)
    fieldname = field_dict.get("fieldname", "")
    normalized_fieldname = fieldname
    if normalized_fieldname and not normalized_fieldname.startswith("custom_"):
        normalized_fieldname = f"custom_{normalized_fieldname}"
    
    # Check for both prefixed and non-prefixed versions
    existing = False
    if normalized_fieldname:
        existing = frappe.db.exists(
            "Custom Field",
            {"dt": doctype_name, "fieldname": normalized_fieldname}
        )
    if not existing and fieldname:
        existing = frappe.db.exists(
            "Custom Field",
            {"dt": doctype_name, "fieldname": fieldname}
        )
    
    if existing:
        raise Exception(
            f"Custom field '{normalized_fieldname or fieldname}' already exists on DocType '{doctype_name}'. "
            f"Use 'update-custom-field' or delete it first."
        )
    
    # Import Frappe's create_custom_field function
    try:
        from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    except ImportError:
        # Fallback: create Custom Field document directly
        cf = frappe.new_doc("Custom Field")
        cf.update({
            "dt": doctype_name,
            **field_dict
        })
        # Frappe will auto-prefix fieldname and set defaults
        cf.insert()
        frappe.db.commit()
        return cf.fieldname
    
    # Use Frappe's create_custom_field API
    # This handles:
    # - Fieldname prefixing (adds 'custom_' if not present)
    # - Label generation (from fieldname if not provided)
    # - idx calculation (from insert_after or end of form)
    # - Database schema updates
    create_custom_field(doctype_name, field_dict)
    frappe.db.commit()
    
    # Return the actual fieldname (Frappe may have prefixed it)
    # Get the actual fieldname from the created Custom Field
    actual_fieldname = field_dict.get("fieldname", "")
    if actual_fieldname and not actual_fieldname.startswith("custom_"):
        actual_fieldname = f"custom_{actual_fieldname}"
    elif not actual_fieldname:
        # If fieldname was generated from label, Frappe will have set it
        # Query to get the actual fieldname
        custom_fields = frappe.get_all(
            "Custom Field",
            filters={"dt": doctype_name},
            fields=["fieldname"],
            order_by="creation desc",
            limit=1
        )
        if custom_fields:
            actual_fieldname = custom_fields[0].fieldname
    
    return actual_fieldname or fieldname


@click.command("add-custom-field")
@click.argument("doctype_name")
@click.option(
    "-f", "--field",
    required=True,
    help="Field definition in format: <fieldname>:<fieldtype>[:<attributes>]"
)
@click.option(
    "--insert-after",
    default=None,
    help="Field name to insert this field after (defaults to end of form if not specified)"
)
@pass_context
def add_custom_field_cmd(context, doctype_name, field, insert_after):
    """
    Add a custom field to an existing DocType.
    
    This command adds fields to standard DocTypes without modifying their JSON files.
    Custom fields are stored separately and merged at runtime.
    
    \b
    SENSIBLE DEFAULTS:
    - Fieldname is auto-prefixed with 'custom_' if not already prefixed
    - Label is auto-generated from fieldname (e.g., 'custom_notes' -> 'Custom Notes')
    - Field is positioned at the end if --insert-after is not specified
    - Field is visible (not hidden) by default
    - Field is not in list view by default
    
    \b
    SIMPLE EXAMPLES:
    
    \b
    # Minimal: Just fieldname and type (placed at end)
    bench --site mysite add-custom-field "Customer" -f "notes:Text"
    
    \b
    # With positioning (recommended)
    bench --site mysite add-custom-field "Customer" \\
      -f "notes:Text" \\
      --insert-after "customer_name"
    
    \b
    # Required field
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "delivery_instructions:Text:*" \\
      --insert-after "customer"
    
    \b
    # Field visible in list view
    bench --site mysite add-custom-field "Item" \\
      -f "batch_no:Data:inlist" \\
      --insert-after "item_name"
    
    \b
    DETAILED EXAMPLES:
    
    \b
    # Full control: required, unique, in list, with description
    bench --site mysite add-custom-field "Item" \\
      -f "batch_no:Data:*:unique:inlist:desc=Batch number for tracking" \\
      --insert-after "item_name"
    
    \b
    # Conditional field (shows only when condition is met)
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "discount_reason:Text:depends_on=eval:doc.apply_discount==1" \\
      --insert-after "discount_amount"
    
    \b
    # Conditional requirement (required only when condition is met)
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "approval_notes:Text:mandatory_depends_on=eval:doc.grand_total>10000" \\
      --insert-after "grand_total"
    
    \b
    # Conditional read-only (read-only when condition is met)
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "final_amount:Currency:read_only_depends_on=eval:doc.status=='Submitted'" \\
      --insert-after "grand_total"
    
    \b
    # Fetch value from linked document
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "customer_email:Data:fetch_from=customer.email_id" \\
      --insert-after "customer"
    
    \b
    # Numeric field with precision and width
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "service_charge:Currency:?=0:width=150:precision=2" \\
      --insert-after "grand_total"
    
    \b
    # Select field with options, bold label, translatable
    bench --site mysite add-custom-field "Customer" \\
      -f "segment:Select:options=Enterprise,SMB,Startup:bold:translatable:inlist" \\
      --insert-after "customer_name"
def validate_customization_allowed(doctype_name):
    """
    Validate that a DocType can be customized according to Frappe restrictions.
    
    Restrictions:
    - Cannot customize core DocTypes
    - Cannot customize Single DocTypes
    - Cannot customize custom DocTypes (only standard)
    """
    if not frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' does not exist.")
    
    dt = frappe.get_doc("DocType", doctype_name)
    
    # Check if it's a core DocType (system DocTypes that shouldn't be customized)
    core_doctypes = {"DocType", "DocField", "Custom Field", "Property Setter", "Customize Form"}
    if dt.name in core_doctypes:
        raise Exception(f"Cannot customize core DocType '{doctype_name}'.")
    
    # Check if it's a Single DocType
    if dt.get("issingle"):
        raise Exception(f"Cannot customize Single DocType '{doctype_name}'. Single DocTypes cannot be customized.")
    
    # Check if it's already a custom DocType (can only customize standard DocTypes)
    if dt.get("custom"):
        raise Exception(f"Cannot customize custom DocType '{doctype_name}'. Only standard DocTypes can be customized.")
    
    return dt


def clear_doctype_cache(doctype_name):
    """Clear metadata cache for a DocType after customization."""
    try:
        frappe.clear_cache(doctype=doctype_name)
        frappe.cache().delete_key(f"doctype_meta::{doctype_name}")
    except Exception:
        # Cache clearing is best-effort, don't fail if it doesn't work
        pass


def add_custom_field_to_doctype(doctype_name, field_dict, insert_after=None):
    """
    Add a custom field to an existing DocType.
    
    Args:
        doctype_name: Name of the DocType to customize
        field_dict: Dictionary with field properties
        insert_after: Field name to insert after (optional)
    
    Returns:
        The fieldname of the created custom field
    """
    # Validate customization is allowed
    validate_customization_allowed(doctype_name)
    
    # Ensure fieldname is prefixed with custom_ if not already
    fieldname = field_dict.get("fieldname", "")
    if fieldname and not fieldname.startswith("custom_"):
        field_dict["fieldname"] = f"custom_{fieldname}"
        fieldname = field_dict["fieldname"]
    
    # Set insert_after if provided
    if insert_after:
        field_dict["insert_after"] = insert_after
    
    # Use Frappe's create_custom_field if available
    if create_custom_field:
        create_custom_field(doctype_name, field_dict)
    else:
        # Fallback: create Custom Field document directly
        custom_field = frappe.new_doc("Custom Field")
        custom_field.update({
            "dt": doctype_name,
            **field_dict
        })
        custom_field.insert()
        frappe.db.commit()
    
    # Update database schema
    frappe.db.updatedb(doctype_name)
    frappe.db.commit()
    
    # Clear cache after customization
    clear_doctype_cache(doctype_name)
    
    return fieldname


def infer_property_type(property_name, value):
    """
    Infer property type from property name and value.
    
    Common boolean properties default to 'Check'.
    If value is '0' or '1', assume 'Check'.
    Otherwise, try to infer from property name patterns.
    """
    # Common boolean/check properties
    boolean_properties = {
        'reqd', 'hidden', 'read_only', 'allow_copy', 'track_changes',
        'allow_rename', 'allow_import', 'allow_export', 'allow_print',
        'allow_email', 'allow_share', 'in_list_view', 'in_standard_filter',
        'bold', 'collapsible', 'ignore_user_permissions', 'no_copy',
        'permlevel', 'search_index', 'translatable', 'unique'
    }
    
    if property_name.lower() in boolean_properties:
        return 'Check'
    
    # If value is 0 or 1, likely a Check field
    if value in ('0', '1', 'true', 'false', 'True', 'False'):
        return 'Check'
    
    # Try to infer from value type
    if value.isdigit():
        return 'Int'
    
    try:
        float(value)
        return 'Float'
    except ValueError:
        pass
    
    # Default to Data for unknown types
    return 'Data'


def validate_field_exists(doctype_name, field_name):
    """Validate that a field exists in the DocType."""
    if not field_name:
        return True  # DocType-level property, no field validation needed
    
    dt = frappe.get_doc("DocType", doctype_name)
    
    # Check standard fields
    standard_fields = [f.fieldname for f in dt.fields if not f.get("is_custom_field")]
    if field_name in standard_fields:
        return True
    
    # Check custom fields
    custom_fields = frappe.db.get_all(
        "Custom Field",
        filters={"dt": doctype_name, "fieldname": field_name},
        fields=["name"]
    )
    if custom_fields:
        return True
    
    raise Exception(f"Field '{field_name}' does not exist in DocType '{doctype_name}'.")


def set_property_on_doctype(doctype_name, property_name, value, property_type=None, field_name=None, row_name=None):
    """
    Create a property setter for a DocType, DocField, or DocType Link/Action/State.
    
    Args:
        doctype_name: Name of the DocType
        property_name: Property to set (e.g., 'reqd', 'hidden', 'read_only')
        value: Value to set
        property_type: Type of property ('Check', 'Data', 'Int', etc.). If None, will be inferred.
        field_name: Field name if setting field property (None for DocType property)
        row_name: Row name for DocType Link/Action/State (None for DocType/DocField)
    """
    # Validate customization is allowed (only for standard DocTypes)
    dt = validate_customization_allowed(doctype_name)
    
    # Validate field exists if setting field property
    if field_name:
        validate_field_exists(doctype_name, field_name)
    
    # Infer property type if not provided
    if property_type is None:
        property_type = infer_property_type(property_name, value)
    
    # Use Frappe's make_property_setter (supports DocType and DocField)
    # For DocType Link/Action/State, we need to create Property Setter manually
    if row_name:
        # Create Property Setter for DocType Link/Action/State manually
        # Try to infer doctype_or_field from property name or default to DocType Link
        if "action" in property_name.lower():
            doctype_or_field = "DocType Action"
        elif "state" in property_name.lower():
            doctype_or_field = "DocType State"
        else:
            doctype_or_field = "DocType Link"  # Default
        
        # Create Property Setter document directly
        ps = frappe.new_doc("Property Setter")
        ps.update({
            "doc_type": doctype_name,
            "doctype_or_field": doctype_or_field,
            "row_name": row_name,
            "property": property_name,
            "property_type": property_type,
            "value": value
        })
        ps.insert()
    else:
        # Use Frappe's make_property_setter for DocType and DocField
        frappe.make_property_setter(
            doctype=doctype_name,
            fieldname=field_name,
            property=property_name,
            value=value,
            property_type=property_type,
            for_doctype=(field_name is None)
        )
    
    frappe.db.commit()
    
    # Clear cache after customization
    clear_doctype_cache(doctype_name)


@click.command("customize-doctype")
@click.argument("doctype_name")
@click.option(
    "-f", "--fields", multiple=True,
    help="Custom field definitions to add (same syntax as new-doctype)."
)
@click.option(
    "--insert-after", default=None,
    help="Field name to insert custom fields after (defaults to end)."
)
@pass_context
def customize_doctype_cmd(context, doctype_name, fields, insert_after):
    """
    Add custom fields to an existing DocType.
    
    Restrictions:
    - Only standard DocTypes can be customized (not custom DocTypes)
    - Cannot customize Single DocTypes
    - Cannot customize core DocTypes (DocType, DocField, etc.)
    
    Example:
        bench --site mysite customize-doctype "Sales Invoice" \\
            -f "custom_notes:Text" \\
            -f "custom_priority:Select:options=Low,Medium,High" \\
            --insert-after "customer"
    """
    site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        
        # Parse field definition
        try:
            field_dict = parse_field_definition(field, for_custom_field=True)
        except ValueError as e:
            raise click.ClickException(str(e))
        
        # Override insert_after if provided via option
        if insert_after:
            field_dict["insert_after"] = insert_after
        
        # Add custom field
        try:
            field_name = add_custom_field(doctype_name, field_dict)
            click.echo(
                f"Custom field '{field_name}' added to DocType '{doctype_name}'. "
                f"Refresh your browser to see the changes."
            )
        except Exception as e:
            raise click.ClickException(str(e))


# Register commands for bench to discover
commands = [new_doctype_cmd, add_custom_field_cmd]
        if not fields:
            raise click.UsageError("No fields provided. Use -f to specify custom fields.")
        
        parsed_fields = parse_fields(fields)
        
        # Track the last inserted field for sequential insertion
        last_inserted = insert_after
        
        for field_dict in parsed_fields:
            try:
                # Use last_inserted if insert_after was specified, otherwise None
                current_insert_after = last_inserted if insert_after else None
                fieldname = add_custom_field_to_doctype(doctype_name, field_dict, current_insert_after)
                click.echo(f"Added custom field '{fieldname}' to '{doctype_name}'.")
                # Update last_inserted for next iteration (sequential insertion)
                last_inserted = fieldname
            except Exception as e:
                click.echo(f"Error adding field '{field_dict.get('fieldname', 'unknown')}': {e}", err=True)
                raise
        
        click.echo(f"Customized DocType '{doctype_name}' with {len(parsed_fields)} field(s).")


@click.command("set-property")
@click.argument("doctype_name")
@click.option(
    "--property", required=True,
    help="Property name to set (e.g., 'reqd', 'hidden', 'read_only', 'allow_copy')."
)
@click.option(
    "--value", required=True,
    help="Value to set for the property (e.g., '1' or '0' for Check fields)."
)
@click.option(
    "--property-type", default=None,
    help="Property type: 'Check', 'Data', 'Int', 'Select', etc. (auto-detected if omitted)."
)
@click.option(
    "--field", default=None,
    help="Field name if setting field property (omit for DocType-level property)."
)
@click.option(
    "--row-name", default=None,
    help="Row name for DocType Link/Action/State properties (omit for DocType/DocField properties)."
)
@pass_context
def set_property_cmd(context, doctype_name, property, value, property_type, field, row_name):
    """
    Set a property on a DocType, DocField, or DocType Link/Action/State using Property Setter.
    
    Restrictions:
    - Only standard DocTypes can be customized (not custom DocTypes)
    - Cannot customize Single DocTypes
    - Cannot customize core DocTypes
    - Field must exist before setting its properties
    
    Property type is auto-detected for common properties (reqd, hidden, etc.).
    For boolean properties, use '1' for true and '0' for false.
    
    Examples:
        # Simple: Make a field required (property-type auto-detected)
        bench --site mysite set-property "Sales Invoice" \\
            --property "reqd" --value "1" --field "customer"
        
        # Simple: Hide a field
        bench --site mysite set-property "Sales Invoice" \\
            --property "hidden" --value "1" --field "remarks"
        
        # Simple: Enable copy on DocType
        bench --site mysite set-property "Sales Invoice" \\
            --property "allow_copy" --value "1"
        
        # Detailed: Explicit property type
        bench --site mysite set-property "Sales Invoice" \\
            --property "label" --value "Customer Name" --property-type "Data" \\
            --field "customer"
    """
    site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        
        try:
            inferred_type = infer_property_type(property, value) if property_type is None else property_type
            set_property_on_doctype(doctype_name, property, value, inferred_type, field, row_name)
            
            # Determine target description
            if row_name:
                target = f"row '{row_name}'"
            elif field:
                target = f"field '{field}'"
            else:
                target = "DocType"
            
            type_info = f" (type: {inferred_type})" if property_type is None else ""
            click.echo(f"Set property '{property}' = '{value}' on {target} of '{doctype_name}'{type_info}.")
        except Exception as e:
            click.echo(f"Error setting property: {e}", err=True)
            raise


# Register commands for bench to discover
commands = [new_doctype_cmd, commander_help_cmd]
commands = [new_doctype_cmd, customize_doctype_cmd, set_property_cmd]
