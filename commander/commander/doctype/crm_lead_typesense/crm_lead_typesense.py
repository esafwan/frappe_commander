import frappe
import typesense
from frappe.model.document import Document

# Configure your Typesense client here (or read from site_config.json)
TS_CLIENT = typesense.Client({
    "nodes": [{
        "host": "typesense1",
        "port": "8108",
        "protocol": "http"
    }],
    "api_key": "123",
    "connection_timeout_seconds": 2
})

class CRMLeadTypesense(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize all attributes that Frappe expects for Document objects
        self._table_fieldnames = []
        self._child_doctype_map = {}
        self._table_fields = []
        self._valid_columns = []
        self._child_table_fields = []
        self.flags = frappe._dict()
        
        # Set doctype if not already set
        if not hasattr(self, 'doctype') or not self.doctype:
            self.doctype = "CRM Lead Typesense"
            
        # Ensure meta is available
        if not hasattr(self, 'meta'):
            try:
                self.meta = frappe.get_meta(self.doctype)
            except:
                # Create a minimal meta object if DocType meta is not available
                self.meta = frappe._dict({
                    'fields': [],
                    'table_fields': [],
                    'child_doctype_map': {},
                    'name': self.doctype
                })
        
    def db_insert(self, *args, **kwargs):
        raise NotImplementedError

    def load_from_db(self):
        try:
            doc = TS_CLIENT.collections["leads"].documents[self.name].retrieve()
        except Exception as e:
            frappe.throw(f"Typesense retrieve error: {e}")
        
        # Update the current object with the fetched data using update method
        self.update({
            "name": doc.get("id"),
            "owner": doc.get("email", "Administrator"),
            "creation": frappe.utils.now(),
            "modified": frappe.utils.now(),
            "modified_by": "Administrator",
            "_user_tags": "",
            "_comments": "",
            "_assign": "",
            "_liked_by": "",
            "docstatus": 0,
            "idx": 0,
            # Include the actual Typesense fields
            "first_name": doc.get("first_name"),
            "last_name": doc.get("last_name"),
            "email": doc.get("email"),
            "mobile_no": doc.get("mobile_no"),
            "phone": doc.get("phone"),
            "annual_revenue": doc.get("annual_revenue"),
            "organization": doc.get("organization"),
            "status": doc.get("status"),
            "sync": doc.get("sync", False)
        })

    def db_update(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def __getattr__(self, name):
        """Safety method to prevent AttributeError for any missing attributes"""
        # Common Frappe Document attributes with safe defaults
        if name == '_table_fieldnames':
            return []
        elif name == '_child_doctype_map':
            return {}
        elif name == '_table_fields':
            return []
        elif name == '_valid_columns':
            return []
        elif name == '_child_table_fields':
            return []
        elif name == 'flags':
            return frappe._dict()
        elif name == 'meta':
            try:
                return frappe.get_meta(self.doctype)
            except:
                return frappe._dict({'fields': [], 'table_fields': [], 'child_doctype_map': {}, 'name': self.doctype})
        elif name == 'doctype':
            return "CRM Lead Typesense"
        else:
            # For any other missing attribute, return None instead of raising AttributeError
            return None

    @property
    def table_fieldnames(self):
        """Property to ensure table_fieldnames is always available"""
        return getattr(self, '_table_fieldnames', [])

    @staticmethod
    def get_list(args):
        # Extract parameters from args
        filters = args.get("filters", {})
        page_length = args.get("page_length", 20)
        limit_start = args.get("limit_start", 0)
        
        # Build full-text query (use filters["q"] if provided, else wildcard)
        query_string = filters.get("q") if filters and filters.get("q") else "*"
        query_by = "first_name,last_name,organization"

        # Determine page number from Frappe's limit_start
        page = 1
        if limit_start is not None:
            offset = int(limit_start)
            page = offset // page_length + 1

        # Prepare Typesense search parameters
        search_parameters = {
            "q": query_string,
            "query_by": query_by,
            "per_page": page_length,
            "page": page
        }

        # Convert any non-"q" filters to Typesense filter_by clauses
        if filters:
            filter_clauses = []
            for field, value in filters.items():
                if field == "q":
                    continue
                # Exact match for strings, numbers, bools
                filter_clauses.append(f"{field}:={value}")
            if filter_clauses:
                search_parameters["filter_by"] = " && ".join(filter_clauses)

        try:
            ts_result = TS_CLIENT.collections["leads"].documents.search(search_parameters)
        except Exception as e:
            frappe.throw(f"Typesense search error: {e}")

        hits = []
        for hit in ts_result.get("hits", []):
            doc = hit["document"]
            # Create a frappe._dict object with the expected keys
            frappe_doc = frappe._dict({
                "name": doc.get("id"),
                "owner": doc.get("email", "Administrator"),
                "creation": frappe.utils.now(),
                "modified": frappe.utils.now(),
                "modified_by": "Administrator",
                "_user_tags": "",
                "_comments": "",
                "_assign": "",
                "_liked_by": "",
                "docstatus": 0,
                "idx": 0,
                # Include the actual Typesense fields
                "first_name": doc.get("first_name"),
                "last_name": doc.get("last_name"),
                "email": doc.get("email"),
                "mobile_no": doc.get("mobile_no"),
                "phone": doc.get("phone"),
                "annual_revenue": doc.get("annual_revenue"),
                "organization": doc.get("organization"),
                "status": doc.get("status"),
                "sync": doc.get("sync")
            })
            hits.append(frappe_doc)

        return hits

    @staticmethod
    def get_count(args):
        filters = args.get("filters", {})
        query_string = filters.get("q") if filters and filters.get("q") else "*"
        params = {
            "q": query_string,
            "query_by": "first_name,last_name,organization",
            "per_page": 0
        }

        if filters:
            filter_clauses = []
            for field, value in filters.items():
                if field == "q":
                    continue
                filter_clauses.append(f"{field}:={value}")
            if filter_clauses:
                params["filter_by"] = " && ".join(filter_clauses)

        try:
            res = TS_CLIENT.collections["leads"].documents.search(params)
        except Exception as e:
            frappe.throw(f"Typesense count error: {e}")

        return res.get("found", 0)

    @staticmethod
    def get_stats(args):
        filters = args.get("filters", {})
        group_by = args.get("group_by")
        
        if group_by == "status":
            params = {
                "q": filters.get("q") if filters and filters.get("q") else "*",
                "query_by": "first_name,last_name,organization",
                "facet_by": "status",
                "max_facet_values": 10,
                "per_page": 0
            }
            if filters:
                filter_clauses = []
                for field, value in filters.items():
                    if field == "q":
                        continue
                    filter_clauses.append(f"{field}:={value}")
                if filter_clauses:
                    params["filter_by"] = " && ".join(filter_clauses)
            try:
                res = TS_CLIENT.collections["leads"].documents.search(params)
            except Exception as e:
                frappe.throw(f"Typesense stats error: {e}")

            stats = {}
            for fc in res.get("facet_counts", []):
                field_name = fc.get("field_name")
                stats[field_name] = {c["value"]: c["count"] for c in fc.get("counts", [])}
            return stats

        return {}

    @staticmethod
    def get_doc(name):
        try:
            doc = TS_CLIENT.collections["leads"].documents[name].retrieve()
        except Exception as e:
            frappe.throw(f"Typesense retrieve error: {e}")
        
        # Return a frappe._dict object with all necessary fields
        return frappe._dict({
            "name": doc.get("id"),
            "owner": doc.get("email", "Administrator"),
            "creation": frappe.utils.now(),
            "modified": frappe.utils.now(),
            "modified_by": "Administrator",
            "_user_tags": "",
            "_comments": "",
            "_assign": "",
            "_liked_by": "",
            "docstatus": 0,
            "idx": 0,
            # Include the actual Typesense fields
            "first_name": doc.get("first_name"),
            "last_name": doc.get("last_name"),
            "email": doc.get("email"),
            "mobile_no": doc.get("mobile_no"),
            "phone": doc.get("phone"),
            "annual_revenue": doc.get("annual_revenue"),
            "organization": doc.get("organization"),
            "status": doc.get("status"),
            "sync": doc.get("sync")
        })

