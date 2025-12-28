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
        Name of the created custom field
    """
    # Validate DocType exists
    if not frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' does not exist.")
    
    # Get DocType to check if it's customizable
    dt = frappe.get_doc("DocType", doctype_name)
    
    # Check if DocType can be customized
    # Single DocTypes and some core DocTypes cannot be customized
    if dt.get("issingle"):
        raise Exception(f"Cannot add custom fields to Single DocType '{doctype_name}'.")
    
    # Check if custom field already exists
    # Frappe automatically prefixes fieldnames with 'custom_' if not already prefixed
    fieldname = field_dict.get("fieldname", "")
    normalized_fieldname = fieldname
    if not normalized_fieldname.startswith("custom_"):
        normalized_fieldname = f"custom_{normalized_fieldname}"
    
    # Check for both prefixed and non-prefixed versions
    existing = frappe.db.exists(
        "Custom Field",
        {"dt": doctype_name, "fieldname": normalized_fieldname}
    ) or frappe.db.exists(
        "Custom Field",
        {"dt": doctype_name, "fieldname": fieldname}
    )
    
    if existing:
        raise Exception(
            f"Custom field '{normalized_fieldname}' already exists on DocType '{doctype_name}'. "
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
        cf.insert()
        frappe.db.commit()
        return cf.name
    
    # Use Frappe's create_custom_field API
    # This handles fieldname prefixing, idx calculation, and DB updates
    create_custom_field(doctype_name, field_dict)
    frappe.db.commit()
    
    # Return the fieldname (may be prefixed with custom_)
    return field_dict.get("fieldname", fieldname)


@click.command("add-custom-field")
@click.argument("doctype_name")
@click.option(
    "-f", "--field",
    required=True,
    help="Field definition in format: <fieldname>:<fieldtype>[:<attributes>]"
)
@click.option(
    "--insert-after",
    help="Field name to insert this field after (for positioning)"
)
@pass_context
def add_custom_field_cmd(context, doctype_name, field, insert_after):
    """
    Add a custom field to an existing DocType.
    
    This command adds fields to standard DocTypes without modifying their JSON files.
    Custom fields are stored separately and merged at runtime.
    
    Examples:
    
    \b
    # Add a simple text field
    bench --site mysite add-custom-field "Customer" \\
      -f "custom_notes:Text"
    
    \b
    # Add required field with positioning
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "custom_delivery_notes:Text:*" \\
      --insert-after "customer"
    
    \b
    # Add field with all options
    bench --site mysite add-custom-field "Item" \\
      -f "custom_batch_no:Data:*:unique:inlist:desc=Batch number" \\
      --insert-after "item_name"
    
    \b
    # Add field with dependencies
    bench --site mysite add-custom-field "Sales Invoice" \\
      -f "custom_discount_percent:Percent:depends_on=eval:doc.apply_discount" \\
      --insert-after "grand_total"
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
