import re
import click
import frappe
from frappe.commands import get_site, pass_context

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


# Register commands for bench to discover
commands = [new_doctype_cmd]
