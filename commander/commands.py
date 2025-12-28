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
    if not frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' does not exist.")
    
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
    
    return fieldname


def set_property_on_doctype(doctype_name, property_name, value, property_type, field_name=None):
    """
    Create a property setter for a DocType or DocField.
    
    Args:
        doctype_name: Name of the DocType
        property_name: Property to set (e.g., 'reqd', 'hidden', 'read_only')
        value: Value to set
        property_type: Type of property ('Check', 'Data', 'Int', etc.)
        field_name: Field name if setting field property (None for DocType property)
    """
    if not frappe.db.exists("DocType", doctype_name):
        raise Exception(f"DocType '{doctype_name}' does not exist.")
    
    # Use Frappe's make_property_setter
    frappe.make_property_setter(
        doctype=doctype_name,
        fieldname=field_name,
        property=property_name,
        value=value,
        property_type=property_type,
        for_doctype=(field_name is None)
    )
    frappe.db.commit()


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
    
    Example:
        bench --site mysite customize-doctype "Sales Invoice" \\
            -f "custom_notes:Text" \\
            -f "custom_priority:Select:options=Low,Medium,High" \\
            --insert-after "customer"
    """
    site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        
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
    help="Value to set for the property."
)
@click.option(
    "--property-type", required=True,
    help="Property type: 'Check', 'Data', 'Int', 'Select', etc."
)
@click.option(
    "--field", default=None,
    help="Field name if setting field property (omit for DocType-level property)."
)
@pass_context
def set_property_cmd(context, doctype_name, property, value, property_type, field):
    """
    Set a property on a DocType or DocField using Property Setter.
    
    Examples:
        # Make a field required
        bench --site mysite set-property "Sales Invoice" \\
            --property "reqd" --value "1" --property-type "Check" \\
            --field "customer"
        
        # Enable copy on DocType
        bench --site mysite set-property "Sales Invoice" \\
            --property "allow_copy" --value "1" --property-type "Check"
        
        # Hide a field
        bench --site mysite set-property "Sales Invoice" \\
            --property "hidden" --value "1" --property-type "Check" \\
            --field "remarks"
    """
    site = get_site(context)
    
    with frappe.init_site(site):
        frappe.connect()
        
        try:
            set_property_on_doctype(doctype_name, property, value, property_type, field)
            target = f"field '{field}'" if field else "DocType"
            click.echo(f"Set property '{property}' = '{value}' on {target} of '{doctype_name}'.")
        except Exception as e:
            click.echo(f"Error setting property: {e}", err=True)
            raise


# Register commands for bench to discover
commands = [new_doctype_cmd, customize_doctype_cmd, set_property_cmd]
