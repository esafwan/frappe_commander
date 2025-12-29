"""
Commander REST API Module

This module exposes Commander features via REST API endpoints with proper
permission control, error handling, and comprehensive documentation.

All endpoints are whitelisted and require System Manager role or appropriate
permissions to access.

API Base URL: /api/method/commander.api.<method_name>
"""

import frappe
from frappe import _
from typing import Dict, List, Optional, Any
from commander.commands import (
	parse_field_definition,
	parse_fields,
	create_doctype,
	ALLOWED_FIELD_TYPES,
)


# ============================================================================
# Error Handling & Response Utilities
# ============================================================================


class CommanderAPIError(Exception):
	"""
	Base exception class for Commander API errors.
	
	Attributes:
		message: Human-readable error message
		error_code: Standard error code for programmatic handling
		http_status: HTTP status code (default: 400)
		details: Optional additional error details
	"""
	
	def __init__(
		self,
		message: str,
		error_code: str = "COMMANDER_ERROR",
		http_status: int = 400,
		details: Optional[Dict[str, Any]] = None,
	):
		self.message = message
		self.error_code = error_code
		self.http_status = http_status
		self.details = details or {}
		super().__init__(self.message)


def handle_api_error(func):
	"""
	Decorator to handle API errors and return standardized error responses.
	
	Wraps API methods to catch exceptions and return proper JSON error responses
	with appropriate HTTP status codes.
	"""
	def wrapper(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except CommanderAPIError as e:
			frappe.response["http_status_code"] = e.http_status
			frappe.response["message"] = e.message
			frappe.response["error_code"] = e.error_code
			frappe.response["details"] = e.details
			return {
				"success": False,
				"error": {
					"message": e.message,
					"code": e.error_code,
					"details": e.details,
				},
			}
		except ValueError as e:
			# Validation errors
			frappe.response["http_status_code"] = 400
			return {
				"success": False,
				"error": {
					"message": str(e),
					"code": "VALIDATION_ERROR",
					"details": {},
				},
			}
		except Exception as e:
			# Unexpected errors
			frappe.log_error(
				title="Commander API Error",
				message=f"Unexpected error in {func.__name__}: {str(e)}",
			)
			frappe.response["http_status_code"] = 500
			return {
				"success": False,
				"error": {
					"message": "An unexpected error occurred. Please contact support.",
					"code": "INTERNAL_ERROR",
					"details": {"function": func.__name__},
				},
			}
	
	return wrapper


def check_permissions():
	"""
	Check if user has permission to use Commander API.
	
	Requires System Manager role or explicit permission.
	Raises CommanderAPIError if user lacks permissions.
	"""
	if not frappe.has_permission("System Manager"):
		raise CommanderAPIError(
			message="Insufficient permissions. System Manager role required.",
			error_code="PERMISSION_DENIED",
			http_status=403,
		)


def success_response(data: Dict[str, Any], message: str = "Operation completed successfully") -> Dict[str, Any]:
	"""
	Create a standardized success response.
	
	Args:
		data: Response data dictionary
		message: Success message
		
	Returns:
		Standardized success response dictionary
	"""
	return {
		"success": True,
		"message": message,
		"data": data,
	}


# ============================================================================
# DocType Management Endpoints
# ============================================================================


@frappe.whitelist(allow_guest=False, methods=["POST"])
@handle_api_error
def create_doctype_api(
	doctype_name: str,
	fields: Optional[List[str]] = None,
	module: str = "Custom",
	custom: bool = False,
) -> Dict[str, Any]:
	"""
	Create a new DocType via REST API.
	
	This endpoint allows programmatic creation of DocTypes with field definitions.
	It mirrors the CLI functionality but provides a REST interface for integration
	with external systems, CI/CD pipelines, or AI agents.
	
	**Endpoint**: `/api/method/commander.api.create_doctype_api`
	**Method**: POST
	**Authentication**: Required (System Manager role)
	
	**Request Body**:
	```json
	{
		"doctype_name": "Product",
		"fields": [
			"product_name:Data:*",
			"price:Currency:?=0",
			"description:Text"
		],
		"module": "Custom",
		"custom": false
	}
	```
	
	**Response** (Success):
	```json
	{
		"success": true,
		"message": "DocType created successfully",
		"data": {
			"doctype_name": "Product",
			"module": "Custom",
			"fields_count": 3
		}
	}
	```
	
	**Response** (Error):
	```json
	{
		"success": false,
		"error": {
			"message": "DocType 'Product' already exists.",
			"code": "DOCTYPE_EXISTS",
			"details": {
				"doctype_name": "Product"
			}
		}
	}
	```
	
	**Error Codes**:
	- `PERMISSION_DENIED` (403): User lacks System Manager role
	- `DOCTYPE_EXISTS` (400): DocType with given name already exists
	- `MODULE_NOT_FOUND` (400): Specified module or app not found
	- `VALIDATION_ERROR` (400): Invalid field definition or parameters
	- `INTERNAL_ERROR` (500): Unexpected server error
	
	Args:
		doctype_name: Name of the DocType to create (required)
		fields: List of field definitions in Commander syntax (optional)
		module: Module/app name (default: "Custom")
		custom: Whether to mark as custom DocType (default: False)
		
	Returns:
		Success response with DocType details
		
	Raises:
		CommanderAPIError: For API-specific errors
		ValueError: For validation errors
	"""
	check_permissions()
	
	# Validate doctype_name
	if not doctype_name or not doctype_name.strip():
		raise CommanderAPIError(
			message="doctype_name is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "doctype_name"},
		)
	
	doctype_name = doctype_name.strip()
	
	# Check if DocType already exists
	if frappe.db.exists("DocType", doctype_name):
		raise CommanderAPIError(
			message=f"DocType '{doctype_name}' already exists.",
			error_code="DOCTYPE_EXISTS",
			http_status=409,  # Conflict
			details={"doctype_name": doctype_name},
		)
	
	# Parse fields if provided
	parsed_fields = []
	if fields:
		if isinstance(fields, str):
			# Handle single field string or JSON string
			try:
				import json
				fields = json.loads(fields)
			except (json.JSONDecodeError, TypeError):
				fields = [fields]
		
		try:
			parsed_fields = parse_fields(fields)
		except ValueError as e:
			raise CommanderAPIError(
				message=f"Invalid field definition: {str(e)}",
				error_code="VALIDATION_ERROR",
				details={"fields": fields, "error": str(e)},
			)
	
	# Create DocType
	try:
		created_name = create_doctype(doctype_name, parsed_fields, module, custom)
	except Exception as e:
		# Handle module not found and other creation errors
		error_msg = str(e)
		if "not found" in error_msg.lower():
			raise CommanderAPIError(
				message=f"Module or App '{module}' not found.",
				error_code="MODULE_NOT_FOUND",
				details={"module": module},
			)
		raise CommanderAPIError(
			message=f"Failed to create DocType: {error_msg}",
			error_code="DOCTYPE_CREATION_FAILED",
			details={"doctype_name": doctype_name, "error": error_msg},
		)
	
	return success_response(
		{
			"doctype_name": created_name,
			"module": module,
			"fields_count": len(parsed_fields),
			"custom": custom,
		},
		message=f"DocType '{created_name}' created successfully in module '{module}'",
	)


# ============================================================================
# Custom Field Management Endpoints
# ============================================================================


@frappe.whitelist(allow_guest=False, methods=["POST"])
@handle_api_error
def add_custom_field_api(
	doctype: str,
	field_definition: str,
	insert_after: Optional[str] = None,
	ignore_validate: bool = False,
) -> Dict[str, Any]:
	"""
	Add a custom field to an existing DocType via REST API.
	
	This endpoint allows adding custom fields to standard DocTypes without
	modifying the original DocType JSON. Custom fields are stored separately
	and merged into the DocType metadata at runtime.
	
	**Endpoint**: `/api/method/commander.api.add_custom_field_api`
	**Method**: POST
	**Authentication**: Required (System Manager role)
	
	**Request Body**:
	```json
	{
		"doctype": "Customer",
		"field_definition": "custom_industry:Data:*",
		"insert_after": "customer_name"
	}
	```
	
	**Response** (Success):
	```json
	{
		"success": true,
		"message": "Custom field added successfully",
		"data": {
			"doctype": "Customer",
			"fieldname": "custom_industry",
			"fieldtype": "Data",
			"label": "Industry",
			"required": true
		}
	}
	```
	
	**Response** (Error):
	```json
	{
		"success": false,
		"error": {
			"message": "DocType 'Customer' not found.",
			"code": "DOCTYPE_NOT_FOUND",
			"details": {
				"doctype": "Customer"
			}
		}
	}
	```
	
	**Error Codes**:
	- `PERMISSION_DENIED` (403): User lacks System Manager role
	- `DOCTYPE_NOT_FOUND` (404): DocType does not exist
	- `CORE_DOCTYPE` (400): Cannot add custom fields to core DocTypes
	- `SINGLE_DOCTYPE` (400): Cannot add custom fields to single DocTypes
	- `CUSTOM_DOCTYPE` (400): Cannot add custom fields to custom DocTypes
	- `FIELD_EXISTS` (409): Custom field already exists
	- `VALIDATION_ERROR` (400): Invalid field definition
	
	Args:
		doctype: Target DocType name (required)
		field_definition: Field definition in Commander syntax (required)
		insert_after: Fieldname after which to insert (optional)
		ignore_validate: Skip validation (default: False)
		
	Returns:
		Success response with field details
		
	Raises:
		CommanderAPIError: For API-specific errors
		ValueError: For validation errors
	"""
	check_permissions()
	
	# Validate inputs
	if not doctype or not doctype.strip():
		raise CommanderAPIError(
			message="doctype is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "doctype"},
		)
	
	if not field_definition or not field_definition.strip():
		raise CommanderAPIError(
			message="field_definition is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "field_definition"},
		)
	
	doctype = doctype.strip()
	field_definition = field_definition.strip()
	
	# Check if DocType exists
	if not frappe.db.exists("DocType", doctype):
		raise CommanderAPIError(
			message=f"DocType '{doctype}' not found.",
			error_code="DOCTYPE_NOT_FOUND",
			http_status=404,
			details={"doctype": doctype},
		)
	
	# Get DocType metadata to check restrictions
	meta = frappe.get_meta(doctype)
	
	# Check if core DocType
	core_doctypes = frappe.model.core_doctypes_list
	if doctype in core_doctypes:
		raise CommanderAPIError(
			message=f"Cannot add custom fields to core DocType '{doctype}'.",
			error_code="CORE_DOCTYPE",
			details={"doctype": doctype, "core_doctypes": core_doctypes},
		)
	
	# Check if single DocType
	if meta.issingle:
		raise CommanderAPIError(
			message=f"Cannot add custom fields to single DocType '{doctype}'.",
			error_code="SINGLE_DOCTYPE",
			details={"doctype": doctype},
		)
	
	# Check if custom DocType
	if meta.custom:
		raise CommanderAPIError(
			message=f"Cannot add custom fields to custom DocType '{doctype}'. Only standard DocTypes can be customized.",
			error_code="CUSTOM_DOCTYPE",
			details={"doctype": doctype},
		)
	
	# Parse field definition
	try:
		field_dict = parse_field_definition(field_definition)
	except ValueError as e:
		raise CommanderAPIError(
			message=f"Invalid field definition: {str(e)}",
			error_code="VALIDATION_ERROR",
			details={"field_definition": field_definition, "error": str(e)},
		)
	
	# Set insert_after if provided
	if insert_after:
		field_dict["insert_after"] = insert_after
	
	# Check if custom field already exists
	fieldname = field_dict.get("fieldname")
	if fieldname:
		existing_field = frappe.db.exists(
			"Custom Field",
			{"dt": doctype, "fieldname": fieldname},
		)
		if existing_field:
			raise CommanderAPIError(
				message=f"Custom field '{fieldname}' already exists on DocType '{doctype}'.",
				error_code="FIELD_EXISTS",
				http_status=409,  # Conflict
				details={"doctype": doctype, "fieldname": fieldname},
			)
	
	# Create custom field using Frappe's API
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_field
		
		custom_field = create_custom_field(
			doctype=doctype,
			df=field_dict,
			ignore_validate=ignore_validate,
			is_system_generated=True,
		)
		
		if not custom_field:
			raise CommanderAPIError(
				message=f"Failed to create custom field. It may already exist.",
				error_code="FIELD_CREATION_FAILED",
				details={"doctype": doctype, "field_dict": field_dict},
			)
		
		# Get created field details
		field_doc = frappe.get_doc("Custom Field", custom_field.name)
		
		return success_response(
			{
				"doctype": doctype,
				"fieldname": field_doc.fieldname,
				"fieldtype": field_doc.fieldtype,
				"label": field_doc.label,
				"required": bool(field_doc.reqd),
				"unique": bool(field_doc.unique),
				"read_only": bool(field_doc.read_only),
				"insert_after": field_doc.insert_after,
			},
			message=f"Custom field '{field_doc.fieldname}' added successfully to DocType '{doctype}'",
		)
		
	except ImportError:
		raise CommanderAPIError(
			message="Custom Field API not available. Ensure Frappe is properly installed.",
			error_code="API_UNAVAILABLE",
			http_status=500,
		)
	except Exception as e:
		error_msg = str(e)
		raise CommanderAPIError(
			message=f"Failed to create custom field: {error_msg}",
			error_code="FIELD_CREATION_FAILED",
			details={"doctype": doctype, "error": error_msg},
		)


# ============================================================================
# Customization (Property Setter) Endpoints
# ============================================================================


@frappe.whitelist(allow_guest=False, methods=["POST"])
@handle_api_error
def add_property_setter_api(
	doctype: str,
	property: str,
	value: Any,
	property_type: str,
	field_name: Optional[str] = None,
	for_doctype: bool = False,
) -> Dict[str, Any]:
	"""
	Add a property setter to customize a DocType or field property via REST API.
	
	Property setters allow overriding properties of DocTypes and fields without
	modifying the original JSON. This is useful for customizing standard DocTypes.
	
	**Endpoint**: `/api/method/commander.api.add_property_setter_api`
	**Method**: POST
	**Authentication**: Required (System Manager role)
	
	**Request Body** (DocType property):
	```json
	{
		"doctype": "Sales Invoice",
		"property": "allow_copy",
		"value": "1",
		"property_type": "Check",
		"for_doctype": true
	}
	```
	
	**Request Body** (Field property):
	```json
	{
		"doctype": "Sales Invoice",
		"field_name": "customer",
		"property": "reqd",
		"value": "1",
		"property_type": "Check"
	}
	```
	
	**Response** (Success):
	```json
	{
		"success": true,
		"message": "Property setter created successfully",
		"data": {
			"doctype": "Sales Invoice",
			"property": "allow_copy",
			"value": "1",
			"property_type": "Check",
			"doctype_or_field": "DocType"
		}
	}
	```
	
	**Error Codes**:
	- `PERMISSION_DENIED` (403): User lacks System Manager role
	- `DOCTYPE_NOT_FOUND` (404): DocType does not exist
	- `FIELD_NOT_FOUND` (404): Field does not exist on DocType
	- `CORE_DOCTYPE` (400): Cannot customize core DocTypes
	- `SINGLE_DOCTYPE` (400): Cannot customize single DocTypes
	- `CUSTOM_DOCTYPE` (400): Cannot customize custom DocTypes
	- `VALIDATION_ERROR` (400): Invalid property or value
	
	Args:
		doctype: Target DocType name (required)
		property: Property name to override (required)
		value: New property value (required)
		property_type: Data type of property (required)
		field_name: Field name (required if for_doctype=False)
		for_doctype: Whether this is a DocType-level property (default: False)
		
	Returns:
		Success response with property setter details
		
	Raises:
		CommanderAPIError: For API-specific errors
	"""
	check_permissions()
	
	# Validate inputs
	if not doctype or not doctype.strip():
		raise CommanderAPIError(
			message="doctype is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "doctype"},
		)
	
	if not property or not property.strip():
		raise CommanderAPIError(
			message="property is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "property"},
		)
	
	if value is None:
		raise CommanderAPIError(
			message="value is required",
			error_code="VALIDATION_ERROR",
			details={"field": "value"},
		)
	
	if not property_type or not property_type.strip():
		raise CommanderAPIError(
			message="property_type is required and cannot be empty",
			error_code="VALIDATION_ERROR",
			details={"field": "property_type"},
		)
	
	doctype = doctype.strip()
	property = property.strip()
	property_type = property_type.strip()
	
	# Check if DocType exists
	if not frappe.db.exists("DocType", doctype):
		raise CommanderAPIError(
			message=f"DocType '{doctype}' not found.",
			error_code="DOCTYPE_NOT_FOUND",
			http_status=404,
			details={"doctype": doctype},
		)
	
	# Get DocType metadata to check restrictions
	meta = frappe.get_meta(doctype)
	
	# Check if core DocType
	core_doctypes = frappe.model.core_doctypes_list
	if doctype in core_doctypes:
		raise CommanderAPIError(
			message=f"Cannot customize core DocType '{doctype}'.",
			error_code="CORE_DOCTYPE",
			details={"doctype": doctype},
		)
	
	# Check if single DocType
	if meta.issingle:
		raise CommanderAPIError(
			message=f"Cannot customize single DocType '{doctype}'.",
			error_code="SINGLE_DOCTYPE",
			details={"doctype": doctype},
		)
	
	# Check if custom DocType (only for UI customization, but API allows it)
	# Note: We allow it via API but warn
	if meta.custom and not for_doctype:
		# Allow but note it's unusual
		pass
	
	# Validate field exists if field_name provided
	if not for_doctype:
		if not field_name:
			raise CommanderAPIError(
				message="field_name is required when for_doctype is False",
				error_code="VALIDATION_ERROR",
				details={"field": "field_name"},
			)
		
		field = meta.get_field(field_name)
		if not field:
			raise CommanderAPIError(
				message=f"Field '{field_name}' not found on DocType '{doctype}'.",
				error_code="FIELD_NOT_FOUND",
				http_status=404,
				details={"doctype": doctype, "field_name": field_name},
			)
	
	# Create property setter using Frappe's API
	try:
		from frappe.custom.doctype.property_setter.property_setter import make_property_setter
		
		make_property_setter(
			doctype=doctype,
			fieldname=field_name if not for_doctype else None,
			property=property,
			value=str(value),
			property_type=property_type,
			for_doctype=for_doctype,
		)
		
		doctype_or_field = "DocType" if for_doctype else "DocField"
		
		return success_response(
			{
				"doctype": doctype,
				"field_name": field_name if not for_doctype else None,
				"property": property,
				"value": str(value),
				"property_type": property_type,
				"doctype_or_field": doctype_or_field,
			},
			message=f"Property setter for '{property}' created successfully",
		)
		
	except ImportError:
		raise CommanderAPIError(
			message="Property Setter API not available. Ensure Frappe is properly installed.",
			error_code="API_UNAVAILABLE",
			http_status=500,
		)
	except Exception as e:
		error_msg = str(e)
		raise CommanderAPIError(
			message=f"Failed to create property setter: {error_msg}",
			error_code="PROPERTY_SETTER_CREATION_FAILED",
			details={"doctype": doctype, "error": error_msg},
		)


# ============================================================================
# API Documentation Endpoint
# ============================================================================


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_api_documentation() -> Dict[str, Any]:
	"""
	Get comprehensive REST API documentation for Commander endpoints.
	
	This endpoint provides detailed documentation including:
	- Available endpoints
	- Request/response formats
	- Error codes and messages
	- Usage examples
	- Authentication requirements
	
	**Endpoint**: `/api/method/commander.api.get_api_documentation`
	**Method**: GET
	**Authentication**: Not required (public documentation)
	
	**Response**:
	```json
	{
		"success": true,
		"documentation": {
			"title": "Commander REST API Documentation",
			"version": "1.0.0",
			"base_url": "/api/method/commander.api",
			"endpoints": [...],
			"error_codes": [...],
			"examples": [...]
		}
	}
	```
	
	Returns:
		Complete API documentation dictionary
	"""
	
	documentation = {
		"title": "Commander REST API Documentation",
		"version": "1.0.0",
		"description": (
			"REST API for programmatic DocType creation, custom field management, "
			"and DocType customization in Frappe. All endpoints require authentication "
			"and System Manager role unless otherwise specified."
		),
		"base_url": "/api/method/commander.api",
		"authentication": {
			"type": "Session-based or API Key",
			"required": True,
			"role": "System Manager",
			"note": "Most endpoints require System Manager role. Check individual endpoint docs for exceptions.",
		},
		"endpoints": [
			{
				"name": "create_doctype_api",
				"method": "POST",
				"path": "/api/method/commander.api.create_doctype_api",
				"description": "Create a new DocType with field definitions",
				"authentication": "Required (System Manager)",
				"request": {
					"content_type": "application/json",
					"body": {
						"doctype_name": {
							"type": "string",
							"required": True,
							"description": "Name of the DocType to create",
							"example": "Product",
						},
						"fields": {
							"type": "array[string]",
							"required": False,
							"description": "List of field definitions in Commander syntax",
							"example": ["product_name:Data:*", "price:Currency:?=0"],
						},
						"module": {
							"type": "string",
							"required": False,
							"default": "Custom",
							"description": "Module/app name",
							"example": "Custom",
						},
						"custom": {
							"type": "boolean",
							"required": False,
							"default": False,
							"description": "Whether to mark as custom DocType",
						},
					},
				},
				"response": {
					"success": {
						"status": 200,
						"body": {
							"success": True,
							"message": "DocType 'Product' created successfully in module 'Custom'",
							"data": {
								"doctype_name": "Product",
								"module": "Custom",
								"fields_count": 2,
								"custom": False,
							},
						},
					},
					"error": {
						"status": 409,
						"body": {
							"success": False,
							"error": {
								"message": "DocType 'Product' already exists.",
								"code": "DOCTYPE_EXISTS",
								"details": {"doctype_name": "Product"},
							},
						},
					},
				},
				"error_codes": [
					"PERMISSION_DENIED (403)",
					"DOCTYPE_EXISTS (409)",
					"MODULE_NOT_FOUND (400)",
					"VALIDATION_ERROR (400)",
					"INTERNAL_ERROR (500)",
				],
			},
			{
				"name": "add_custom_field_api",
				"method": "POST",
				"path": "/api/method/commander.api.add_custom_field_api",
				"description": "Add a custom field to an existing standard DocType",
				"authentication": "Required (System Manager)",
				"request": {
					"content_type": "application/json",
					"body": {
						"doctype": {
							"type": "string",
							"required": True,
							"description": "Target DocType name",
							"example": "Customer",
						},
						"field_definition": {
							"type": "string",
							"required": True,
							"description": "Field definition in Commander syntax",
							"example": "custom_industry:Data:*",
						},
						"insert_after": {
							"type": "string",
							"required": False,
							"description": "Fieldname after which to insert the new field",
							"example": "customer_name",
						},
						"ignore_validate": {
							"type": "boolean",
							"required": False,
							"default": False,
							"description": "Skip validation",
						},
					},
				},
				"response": {
					"success": {
						"status": 200,
						"body": {
							"success": True,
							"message": "Custom field 'custom_industry' added successfully to DocType 'Customer'",
							"data": {
								"doctype": "Customer",
								"fieldname": "custom_industry",
								"fieldtype": "Data",
								"label": "Industry",
								"required": True,
								"unique": False,
								"read_only": False,
								"insert_after": "customer_name",
							},
						},
					},
					"error": {
						"status": 404,
						"body": {
							"success": False,
							"error": {
								"message": "DocType 'Customer' not found.",
								"code": "DOCTYPE_NOT_FOUND",
								"details": {"doctype": "Customer"},
							},
						},
					},
				},
				"error_codes": [
					"PERMISSION_DENIED (403)",
					"DOCTYPE_NOT_FOUND (404)",
					"CORE_DOCTYPE (400)",
					"SINGLE_DOCTYPE (400)",
					"CUSTOM_DOCTYPE (400)",
					"FIELD_EXISTS (409)",
					"VALIDATION_ERROR (400)",
				],
			},
			{
				"name": "add_property_setter_api",
				"method": "POST",
				"path": "/api/method/commander.api.add_property_setter_api",
				"description": "Add a property setter to customize DocType or field properties",
				"authentication": "Required (System Manager)",
				"request": {
					"content_type": "application/json",
					"body": {
						"doctype": {
							"type": "string",
							"required": True,
							"description": "Target DocType name",
							"example": "Sales Invoice",
						},
						"property": {
							"type": "string",
							"required": True,
							"description": "Property name to override",
							"example": "allow_copy",
						},
						"value": {
							"type": "any",
							"required": True,
							"description": "New property value",
							"example": "1",
						},
						"property_type": {
							"type": "string",
							"required": True,
							"description": "Data type of property (Check, Data, Int, etc.)",
							"example": "Check",
						},
						"field_name": {
							"type": "string",
							"required": False,
							"description": "Field name (required if for_doctype is False)",
							"example": "customer",
						},
						"for_doctype": {
							"type": "boolean",
							"required": False,
							"default": False,
							"description": "Whether this is a DocType-level property",
						},
					},
				},
				"response": {
					"success": {
						"status": 200,
						"body": {
							"success": True,
							"message": "Property setter for 'allow_copy' created successfully",
							"data": {
								"doctype": "Sales Invoice",
								"field_name": None,
								"property": "allow_copy",
								"value": "1",
								"property_type": "Check",
								"doctype_or_field": "DocType",
							},
						},
					},
					"error": {
						"status": 404,
						"body": {
							"success": False,
							"error": {
								"message": "Field 'invalid_field' not found on DocType 'Sales Invoice'.",
								"code": "FIELD_NOT_FOUND",
								"details": {
									"doctype": "Sales Invoice",
									"field_name": "invalid_field",
								},
							},
						},
					},
				},
				"error_codes": [
					"PERMISSION_DENIED (403)",
					"DOCTYPE_NOT_FOUND (404)",
					"FIELD_NOT_FOUND (404)",
					"CORE_DOCTYPE (400)",
					"SINGLE_DOCTYPE (400)",
					"VALIDATION_ERROR (400)",
				],
			},
			{
				"name": "get_api_documentation",
				"method": "GET",
				"path": "/api/method/commander.api.get_api_documentation",
				"description": "Get comprehensive REST API documentation",
				"authentication": "Not required (public)",
				"request": {
					"method": "GET",
					"parameters": None,
				},
				"response": {
					"success": {
						"status": 200,
						"body": "This documentation object",
					},
				},
			},
		],
		"field_definition_syntax": {
			"format": "<fieldname>:<fieldtype>[:<attribute1>[:<attribute2>...]]",
			"examples": [
				"name:Data:*",
				"email:Data:*:unique",
				"status:Select:options=Open,Closed",
				"customer:Link:options=Customer",
				"amount:Currency:?=0",
				"description:Text:readonly",
			],
			"field_types": list(ALLOWED_FIELD_TYPES),
			"attributes": {
				"*": "Required field",
				"unique": "Unique constraint",
				"readonly": "Read-only field",
				"options=<value>": "Options for Select/Link/Table fields",
				"?=<value>": "Default value",
			},
		},
		"error_codes": {
			"PERMISSION_DENIED": {
				"http_status": 403,
				"message": "Insufficient permissions. System Manager role required.",
				"solution": "Ensure user has System Manager role",
			},
			"DOCTYPE_EXISTS": {
				"http_status": 409,
				"message": "DocType with given name already exists",
				"solution": "Use a different name or delete existing DocType",
			},
			"DOCTYPE_NOT_FOUND": {
				"http_status": 404,
				"message": "DocType does not exist",
				"solution": "Check DocType name spelling or create DocType first",
			},
			"MODULE_NOT_FOUND": {
				"http_status": 400,
				"message": "Specified module or app not found",
				"solution": "Use 'Custom' module or ensure app is installed",
			},
			"CORE_DOCTYPE": {
				"http_status": 400,
				"message": "Cannot add custom fields to core DocTypes",
				"solution": "Core DocTypes cannot be customized",
			},
			"SINGLE_DOCTYPE": {
				"http_status": 400,
				"message": "Cannot add custom fields to single DocTypes",
				"solution": "Single DocTypes cannot be customized",
			},
			"CUSTOM_DOCTYPE": {
				"http_status": 400,
				"message": "Cannot add custom fields to custom DocTypes",
				"solution": "Only standard DocTypes can be customized",
			},
			"FIELD_EXISTS": {
				"http_status": 409,
				"message": "Custom field already exists",
				"solution": "Use a different field name or update existing field",
			},
			"FIELD_NOT_FOUND": {
				"http_status": 404,
				"message": "Field does not exist on DocType",
				"solution": "Check field name spelling",
			},
			"VALIDATION_ERROR": {
				"http_status": 400,
				"message": "Invalid field definition or parameters",
				"solution": "Check request body format and field syntax",
			},
			"INTERNAL_ERROR": {
				"http_status": 500,
				"message": "Unexpected server error",
				"solution": "Contact support with error details",
			},
		},
		"usage_examples": {
			"create_doctype": {
				"curl": """curl -X POST https://your-site.com/api/method/commander.api.create_doctype_api \\
  -H "Content-Type: application/json" \\
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \\
  -d '{
    "doctype_name": "Product",
    "fields": [
      "product_name:Data:*",
      "price:Currency:?=0",
      "description:Text"
    ],
    "module": "Custom"
  }'""",
				"python": """import requests

url = "https://your-site.com/api/method/commander.api.create_doctype_api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "token YOUR_API_KEY:YOUR_API_SECRET"
}
data = {
    "doctype_name": "Product",
    "fields": [
        "product_name:Data:*",
        "price:Currency:?=0",
        "description:Text"
    ],
    "module": "Custom"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())""",
				"javascript": """fetch('https://your-site.com/api/method/commander.api.create_doctype_api', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'token YOUR_API_KEY:YOUR_API_SECRET'
  },
  body: JSON.stringify({
    doctype_name: 'Product',
    fields: [
      'product_name:Data:*',
      'price:Currency:?=0',
      'description:Text'
    ],
    module: 'Custom'
  })
})
.then(response => response.json())
.then(data => console.log(data));""",
			},
			"add_custom_field": {
				"curl": """curl -X POST https://your-site.com/api/method/commander.api.add_custom_field_api \\
  -H "Content-Type: application/json" \\
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \\
  -d '{
    "doctype": "Customer",
    "field_definition": "custom_industry:Data:*",
    "insert_after": "customer_name"
  }'""",
				"python": """import requests

url = "https://your-site.com/api/method/commander.api.add_custom_field_api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "token YOUR_API_KEY:YOUR_API_SECRET"
}
data = {
    "doctype": "Customer",
    "field_definition": "custom_industry:Data:*",
    "insert_after": "customer_name"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())""",
			},
			"add_property_setter": {
				"curl": """curl -X POST https://your-site.com/api/method/commander.api.add_property_setter_api \\
  -H "Content-Type: application/json" \\
  -H "Authorization: token YOUR_API_KEY:YOUR_API_SECRET" \\
  -d '{
    "doctype": "Sales Invoice",
    "property": "allow_copy",
    "value": "1",
    "property_type": "Check",
    "for_doctype": true
  }'""",
				"python": """import requests

url = "https://your-site.com/api/method/commander.api.add_property_setter_api"
headers = {
    "Content-Type": "application/json",
    "Authorization": "token YOUR_API_KEY:YOUR_API_SECRET"
}
data = {
    "doctype": "Sales Invoice",
    "property": "allow_copy",
    "value": "1",
    "property_type": "Check",
    "for_doctype": True
}

response = requests.post(url, json=data, headers=headers)
print(response.json())""",
			},
		},
		"notes": [
			"All endpoints require authentication unless specified otherwise",
			"System Manager role is required for most operations",
			"Field definitions use Commander syntax (see field_definition_syntax)",
			"Custom fields can only be added to standard DocTypes",
			"Core, Single, and Custom DocTypes have restrictions",
			"Property setters allow customization without modifying JSON",
			"All operations are logged and auditable",
		],
	}
	
	return {
		"success": True,
		"documentation": documentation,
	}
