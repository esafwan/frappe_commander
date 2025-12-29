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
commands = [new_doctype_cmd, customize_doctype_cmd, set_property_cmd]
