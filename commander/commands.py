import re
import click
import frappe
from frappe.commands import get_site, pass_context

# Allowed field types
ALLOWED_FIELD_TYPES = {
    "Data", "Text", "Int", "Float", "Date", "Datetime",
    "Select", "Link", "Table", "Check", "Currency", "Percent"
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
@click.argument("doctype_name")
@click.option("-f", "--fields", multiple=True, help="Space-separated field definitions.")
@click.option(
    "-m", "--module", default="Custom",
    help="App or module to create the DocType in (defaults to Custom)."
)
@click.option(
    "--no-interact", is_flag=True, default=False,
    help="Don't prompt; fail if missing info."
)
@pass_context
def new_doctype_cmd(context, doctype_name, fields, module, no_interact):
    """
    Create a new DocType with specified fields in the given module (defaults to 'Custom').
    """
    site = get_site(context)

    with frappe.init_site(site):
        frappe.connect()

        if not fields:
            if no_interact:
                raise Exception("No fields provided. Use -f or remove --no-interact.")
            click.echo("No fields specified. You can add fields later.")
            parsed_fields = []
        else:
            parsed_fields = parse_fields(fields)

        new_dt = create_doctype(doctype_name, parsed_fields, module)
        click.echo(f"DocType '{new_dt}' created in module '{module}'.")


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
