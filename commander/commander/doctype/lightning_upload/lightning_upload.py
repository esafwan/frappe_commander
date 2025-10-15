# Copyright (c) 2025, safwan@tridz.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
import os
import csv
import time
import random # Added for ToDo assignment
from frappe.utils import now_datetime # Import for timestamp

# Define chunk size for batch processing
CHUNK_SIZE = 1000

class LightningUpload(Document):
    def _execute_bulk_insert(self, records_to_insert, target_fields, current_total_imported, log_prefix=""):
        """Helper function to execute bulk insert for a chunk and log results."""
        if not records_to_insert:
            return 0

        count_before_chunk = frappe.db.count("CRM Lead")
        frappe.logger("lightning_upload").info(f"{log_prefix}Attempting to insert {len(records_to_insert)} records in this chunk.")
        frappe.logger("lightning_upload").info(f"{log_prefix}Sample record for this chunk (first 5 fields): {records_to_insert[0][:5] if records_to_insert else 'N/A'}")

        try:
            result = frappe.db.bulk_insert(
                "CRM Lead",
                fields=target_fields,
                values=records_to_insert,
                ignore_duplicates=False # Keep as False for now to catch issues
            )
            frappe.db.commit()
            frappe.logger("lightning_upload").info(f"{log_prefix}Chunk insert committed. bulk_insert result: {result}")

            count_after_chunk = frappe.db.count("CRM Lead")
            chunk_imported_count = count_after_chunk - count_before_chunk
            frappe.logger("lightning_upload").info(f"{log_prefix}CRM Lead count after chunk: {count_after_chunk}, actual chunk imported: {chunk_imported_count}")
            
            if chunk_imported_count == 0 and len(records_to_insert) > 0:
                 frappe.logger("lightning_upload").warning(f"{log_prefix}Zero records imported in this chunk despite {len(records_to_insert)} records attempted. This might indicate all were duplicates or a silent validation issue if ignore_duplicates were True.")
            
            # Create ToDo tasks for successfully imported leads in this chunk
            if chunk_imported_count > 0:
                frappe.logger("lightning_upload").info(f"{log_prefix}Attempting to create ToDo tasks for {chunk_imported_count} imported leads.")
                todos_created_count = 0
                users_for_assignment = ["safwan@tridz.com", "shah@tridz.com"]
                
                # Assuming if chunk_imported_count > 0, all records_to_insert were actually inserted
                # because ignore_duplicates=False would raise an error for any failed insert.
                # If chunk_imported_count is less than len(records_to_insert) despite no error,
                # it's an anomaly, but we'll proceed based on records_to_insert data.
                # We will iterate through records_to_insert, as these contain the generated lead names.
                
                for lead_data_tuple in records_to_insert:
                    try:
                        lead_name = lead_data_tuple[0] # 'name' is the first field in target_fields
                        allocated_user = random.choice(users_for_assignment)
                        
                        todo = frappe.new_doc("ToDo") # As per user prompt
                        todo.status = "Open"
                        todo.allocated_to = allocated_user
                        todo.description = f"Lead {lead_name} assigned to {allocated_user}"
                        todo.reference_type = "CRM Lead"
                        todo.reference_name = lead_name
                        todo.assigned_by = "safwan@tridz.com"
                        
                        todo.insert(ignore_permissions=True, ignore_mandatory=True) # Using ignore_mandatory as schema check failed
                        todos_created_count += 1
                    except Exception as e_todo:
                        frappe.logger("lightning_upload").error(f"{log_prefix}Error creating ToDo for Lead {lead_name if 'lead_name' in locals() else 'unknown'}: {str(e_todo)}")
                        # Optionally, collect these errors to report them later
                
                if todos_created_count > 0:
                    frappe.db.commit() # Commit ToDo creations
                    frappe.logger("lightning_upload").info(f"{log_prefix}Successfully created and committed {todos_created_count} ToDo tasks.")
                elif len(records_to_insert) > 0 : # records_to_insert were present but no todos made
                    frappe.logger("lightning_upload").warning(f"{log_prefix}No ToDo tasks were created despite having {len(records_to_insert)} records in the chunk (reported {chunk_imported_count} imported).")

            return chunk_imported_count
        except Exception as e:
            frappe.logger("lightning_upload").error(f"{log_prefix}Error during bulk insert for chunk: {str(e)}")
            frappe.logger("lightning_upload").error(f"{log_prefix}Exception type: {type(e).__name__}")
            import traceback
            frappe.logger("lightning_upload").error(f"{log_prefix}Traceback: {traceback.format_exc()}")
            # Re-raise the exception to be caught by the main try-except block in validate
            # This will then update self.outcome and frappe.throw appropriately
            raise  # Re-raise the caught exception

    def validate(self):
        # Check if a file has been uploaded to the 'data_file' field
        if not self.data_file:
            self.outcome = "<div class='text-orange'>Please upload a CSV file to the 'Data File' field first.</div>"
            return

        file_doc = None
        try:
            # Primary assumption: self.data_file is the NAME of the File document
            # Check if a File document with this name actually exists to avoid unnecessary get_doc error logging
            if frappe.db.exists("File", self.data_file):
                file_doc = frappe.get_doc("File", self.data_file)
            # If not frappe.db.exists, file_doc remains None, and we fall through to the DoesNotExistError-like handling
            
            if not file_doc: # If self.data_file is not an existing File document name
                # This simulates the DoesNotExistError path for the fallback logic
                raise frappe.DoesNotExistError 

        except frappe.DoesNotExistError:
            # Fallback: self.data_file might be a file URL
            if isinstance(self.data_file, str) and \
               (self.data_file.startswith('/files/') or self.data_file.startswith('/private/files/')):
                try:
                    # Search for a File document that has this URL
                    matching_files = frappe.get_all("File", filters={"file_url": self.data_file}, fields=["name"], order_by="creation desc", limit=1)
                    if matching_files:
                        file_doc = frappe.get_doc("File", matching_files[0].name) # Get the full doc
                    else:
                        self.outcome = f"<div class='text-red'>Error: The file path '{frappe.utils.escape_html(self.data_file)}' was provided, but no corresponding file metadata was found. Please ensure the file was uploaded correctly or re-upload.</div>"
                        frappe.throw("File metadata not found for the given path. Check 'Outcome'.")
                        return
                except frappe.DoesNotExistError: # Should not happen if matching_files gave a name, but for safety
                    self.outcome = f"<div class='text-red'>Error: Found a file reference for URL '{frappe.utils.escape_html(self.data_file)}' but could not load its metadata. Please re-upload.</div>"
                    frappe.throw("Error loading file metadata by URL. Check 'Outcome'.")
                    return
            
            if not file_doc: # If still no file_doc after primary and fallback attempts
                self.outcome = f"<div class='text-red'>Error: The uploaded file reference '{frappe.utils.escape_html(str(self.data_file))}' is invalid or the file metadata does not exist. Please re-upload the file.</div>"
                frappe.throw("File metadata not found. Check the 'Outcome' field for details.")
                return
        
        except Exception as e: # Catch other unexpected errors from the primary frappe.get_doc("File", self.data_file) attempt
            self.outcome = f"<div class='text-red'>Error: An unexpected error ({type(e).__name__}) occurred while trying to access file metadata for '{frappe.utils.escape_html(str(self.data_file))}': {frappe.utils.escape_html(str(e))}</div>"
            frappe.throw("Error accessing file metadata. Check the 'Outcome' field for details.")
            return

        # --- From this point, we should have a valid file_doc ---
        try:
            # Get the absolute path of the file on the server
            file_path = file_doc.get_full_path()
        except Exception as e:
            self.outcome = f"<div class='text-red'>Error: Could not get the file path: {frappe.utils.escape_html(str(e))}</div>"
            frappe.throw("Error getting file path. Check the 'Outcome' field for details.")
            return

        if not file_path or not os.path.exists(file_path):
            self.outcome = f"<div class='text-red'>Error: The system could not find the uploaded CSV file on disk. Path determined: {frappe.utils.escape_html(str(file_path)) if file_path else 'Not Available'}</div>"
            frappe.throw("Uploaded file not found on disk. Check the 'Outcome' field for details.")
            return

        # Start the import process
        start_time = time.time()
        
        # CSV column to CRM Lead field mapping
        column_mapping = {
            "First Name": "first_name",
            "Last Name": "last_name", 
            "Mobile No": "mobile_no",
            "Phone": "phone",
            "Annual Revenue": "annual_revenue",
            "Organization": "organization",
            "Email": "email",
            "Status": "status"
        }
        
        # Target DocType fields in the order for bulk_insert
        target_fields = [
            "name", "creation", "modified", 
            "first_name", "last_name", "mobile_no", "phone", 
            "annual_revenue", "organization", "email", "status"
        ]
        
        values = []
        total_rows = 0
        error_rows = []
        
        # Generate current timestamp once for the entire batch
        current_timestamp_for_batch = now_datetime()
        
        try:
            # Use 'utf-8-sig' to handle potential BOM in CSV files
            with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
                reader = csv.DictReader(csvfile)
                
                # Validate that required columns exist in CSV
                missing_columns = []
                for csv_col in column_mapping.keys():
                    if csv_col not in reader.fieldnames:
                        missing_columns.append(csv_col)
                
                if missing_columns:
                    self.outcome = f"<div class='text-red'>Error: Missing required columns in CSV: {', '.join(missing_columns)}<br>Available columns: {', '.join(reader.fieldnames)}</div>"
                    frappe.throw("Missing required columns in CSV. Check 'Outcome' field.")
                    return
                
                for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is headers
                    total_rows += 1
                    try:
                        # Generate a unique hash name for the CRM Lead record
                        lead_name = frappe.generate_hash(length=10)
                        # current_timestamp = now_datetime() # Moved outside loop
                        
                        # Extract and validate data for each field from CSV
                        row_data_mapped = {}
                        for csv_col_name, doctype_field_name in column_mapping.items():
                            value = row.get(csv_col_name, "").strip()
                            if doctype_field_name == "annual_revenue":
                                if value:
                                    try:
                                        clean_value = value.replace(",", "").replace("$", "").strip()
                                        value = float(clean_value) if clean_value else 0.0
                                    except ValueError:
                                        value = 0.0
                                        error_rows.append(f"Row {row_num}: Invalid annual revenue '{row.get(csv_col_name, '')}', set to 0.0")
                                else:
                                    value = 0.0
                            row_data_mapped[doctype_field_name] = value

                        # Construct the tuple for bulk_insert in the order of target_fields
                        current_row_values = [lead_name, current_timestamp_for_batch, current_timestamp_for_batch]
                        for field_name in target_fields[3:]: # Skip name, creation, modified
                            current_row_values.append(row_data_mapped.get(field_name, None))
                        
                        values.append(tuple(current_row_values))
                        
                    except Exception as e:
                        # Log the specific error for this row to frappe.log
                        row_identifier = f"CSV Row (approx. line {row_num + 1}) Content: { {k: row.get(k, '')[:50] for k in column_mapping.keys()} }"
                        log_message = f"Lightning Upload: Error processing row {row_num}. {row_identifier}. Error: {str(e)}"
                        frappe.logger("lightning_upload").error(log_message)
                        # Optionally, include traceback for very detailed debugging for a few rows
                        if row_num < 5: # Log traceback for first few errors
                            import traceback
                            frappe.logger("lightning_upload").error(f"Traceback for row {row_num}: {traceback.format_exc()}")
                        
                        error_detail = f"Row {row_num}: {str(e)} (Data sample: {row.get('First Name','N/A')} {row.get('Last Name','N/A')}, Email: {row.get('Email','N/A')})"
                        error_rows.append(error_detail)
                        continue
                        
        except FileNotFoundError:
            self.outcome = f"<div class='text-red'>Error: File not found at path '{frappe.utils.escape_html(str(file_path))}' during read attempt.</div>"
            frappe.throw("File not found during read. Check the 'Outcome' field for details.")
            return
        except Exception as e:
            self.outcome = f"<div class='text-red'>Error: Could not read the CSV file. Details: {frappe.utils.escape_html(str(e))} (Path: {frappe.utils.escape_html(str(file_path))})</div>"
            frappe.throw("Error reading CSV file. Check the 'Outcome' field for details.")
            return

        if not values:
            self.outcome = "<div class='text-orange'><strong>Import Problem:</strong> No valid data rows were found in the CSV file to import.</div>"
            
            # Display errors from error_rows
            if error_rows:
                max_errors_to_show = 20
                error_summary_html = "<br>".join([f"<li>{frappe.utils.escape_html(err)}</li>" for err in error_rows[:max_errors_to_show]])
                self.outcome += f"<br><br><div class='text-red'><strong>Errors encountered while processing rows (showing first {max_errors_to_show if len(error_rows) > max_errors_to_show else len(error_rows)} of {len(error_rows)}):</strong><ul>{error_summary_html}</ul></div>"
                if len(error_rows) > max_errors_to_show:
                    self.outcome += f"<p>...and {len(error_rows) - max_errors_to_show} more errors not shown here. Check frappe.log for all row errors.</p>"
            else:
                 self.outcome += "<br>The file might be empty or not in the expected CSV format."

            msg_text = f"No valid data found to import. Processed {total_rows} CSV rows. Encountered {len(error_rows)} errors during row processing. Check the 'Outcome' field for error details and frappe.log."
            frappe.msgprint(msg_text, title="Import Problem", indicator="orange", wide=True)
            return

        # Perform bulk insert
        imported_count = 0
        try:
            # First, verify that CRM Lead DocType exists
            if not frappe.db.exists("DocType", "CRM Lead"):
                # Maybe it's just "Lead"?
                available_lead_doctypes = frappe.get_all('DocType', filters=[['name', 'like', '%lead%']], pluck='name')
                self.outcome = f"<div class='text-red'>Error: CRM Lead DocType does not exist in this system.<br>Available Lead-related DocTypes: {', '.join(available_lead_doctypes)}<br>Available all DocTypes starting with 'C': {', '.join(frappe.get_all('DocType', filters=[['name', 'like', 'C%']], pluck='name')[:10])}</div>"
                frappe.throw("CRM Lead DocType not found. Check 'Outcome' field for alternatives.")
                return
            
            # Verify that all target fields exist in the CRM Lead DocType
            doctype_meta = frappe.get_meta("CRM Lead")
            doctype_fields_from_meta = [field.fieldname for field in doctype_meta.fields]
            
            # Log what fields are found in the metadata for debugging
            frappe.logger("lightning_upload").info(f"Lightning Upload: Fields found in CRM Lead Meta (from meta.fields): {doctype_fields_from_meta}")

            missing_fields = []
            for field_to_check in target_fields:
                # "name", "creation", "modified" are special system columns
                # required by bulk_insert but might not always appear in doctype_meta.fields
                # in the same way as user-defined fields.
                if field_to_check in ["name", "creation", "modified"]:
                    continue  # Skip validation against meta.fields for these specific system columns
                
                if field_to_check not in doctype_fields_from_meta:
                    missing_fields.append(field_to_check)
            
            if missing_fields:
                error_message_detail = (
                    f"Error: The following fields in your mapping do not exist as explicit "
                    f"fields in the CRM Lead DocType's metadata: {', '.join(missing_fields)}. "
                    f"Please check your CSV to DocType mapping for these fields."
                )
                available_fields_summary = (
                    f"Fields explicitly defined in CRM Lead metadata (first 20): "
                    f"{', '.join(doctype_fields_from_meta[:20])}"
                    f"{'...' if len(doctype_fields_from_meta) > 20 else ''}."
                )
                
                frappe.logger("lightning_upload").error(f"Field mismatch validation: {error_message_detail}")
                frappe.logger("lightning_upload").error(f"Field availability (from meta.fields): {available_fields_summary}")
                
                # Simplified throw message, directing to logs for full details
                frappe.throw(
                    f"Field mismatch: Mapped fields {', '.join(missing_fields)} not found in CRM Lead's "
                    f"explicit field definitions. Check server logs (search for 'lightning_upload') for details."
                )
                return
            
            # Log the bulk insert attempt
            frappe.logger("lightning_upload").info(f"Lightning Upload: Attempting to insert {len(values)} records into CRM Lead")
            frappe.logger("lightning_upload").info(f"Lightning Upload: Target fields for bulk_insert: {target_fields}")
            if values:
                frappe.logger("lightning_upload").info(f"Lightning Upload: Sample 2 records being sent to bulk_insert (first 5 fields): {[v[:5] for v in values[:2]]}")
            else:
                frappe.logger("lightning_upload").warning("Lightning Upload: No values to send to bulk_insert.")
            
            # Get count before insert for verification
            count_before = frappe.db.count("CRM Lead")
            frappe.logger().info(f"Lightning Upload: CRM Lead count before insert: {count_before}")
            
            # Test insert (using the first processed record)
            if values:
                test_record_tuple = values[0]
                test_doc_data = {}
                for i, field_name in enumerate(target_fields):
                    if field_name in ["name", "creation", "modified"]: continue # Handled by doc.insert
                    if i < len(test_record_tuple):
                        test_doc_data[field_name] = test_record_tuple[i]
                
                frappe.logger().info(f"Lightning Upload: Test doc data for single insert: {test_doc_data}")
                try:
                    test_doc = frappe.get_doc({"doctype": "CRM Lead", **test_doc_data})
                    test_doc.insert(ignore_permissions=True) # Consider ignore_permissions for system imports
                    frappe.db.commit()
                    frappe.logger().info(f"Lightning Upload: Test record created: {test_doc.name}, deleting...")
                    frappe.delete_doc("CRM Lead", test_doc.name, ignore_permissions=True)
                    frappe.db.commit()
                    frappe.logger().info("Lightning Upload: Test record deleted")
                except Exception as test_error:
                    tb = traceback.format_exc()
                    log_msg = f"Test record creation failed: {str(test_error)}. Data: {test_doc_data}. Traceback: {tb}"
                    frappe.logger("lightning_upload").error(log_msg)
                    frappe.throw(f"Test insert failed: {str(test_error)}. Check logs.")
                    return
            
            # Actual chunked bulk import
            total_successfully_imported = 0
            frappe.logger("lightning_upload").info(f"Starting chunked bulk insert. Total records to process: {len(values)}. Chunk size: {CHUNK_SIZE}")

            for i in range(0, len(values), CHUNK_SIZE):
                chunk_values = values[i : i + CHUNK_SIZE]
                log_prefix_chunk = f"Chunk {i//CHUNK_SIZE + 1}: "
                try:
                    imported_in_chunk = self._execute_bulk_insert(chunk_values, target_fields, total_successfully_imported, log_prefix=log_prefix_chunk)
                    total_successfully_imported += imported_in_chunk
                    frappe.logger("lightning_upload").info(f"{log_prefix_chunk}Imported {imported_in_chunk}. Running total: {total_successfully_imported}")
                except Exception as e: 
                    # Error already logged in _execute_bulk_insert, re-throw handled there.
                    # This main exception catch is for other unexpected issues.
                    tb = traceback.format_exc()
                    log_msg = f"Critical error during chunked import ({log_prefix_chunk}): {str(e)}. Traceback: {tb}"
                    frappe.logger("lightning_upload").error(log_msg)
                    frappe.throw(f"Import failed during chunk processing: {str(e)}. Check logs.")
                    return # Stop further processing

            end_time = time.time()
            time_taken = round(end_time - start_time, 2)

            if total_successfully_imported == 0 and len(values) > 0:
                 msg = f"Import process completed, but 0 new records were added to CRM Lead. Total CSV rows: {total_rows}. Processed for import: {len(values)}. Time: {time_taken}s. This might be due to all records being duplicates (if ignore_duplicates was True in future) or a persistent silent issue. Check logs for details."
                 frappe.logger("lightning_upload").warning(msg)
                 frappe.msgprint(msg, title="Import Result", indicator="orange", wide=True)
            else:
                msg = f"Import completed! Records processed from CSV: {total_rows}. Successfully imported to CRM Lead: {total_successfully_imported}. Time taken: {time_taken}s."
                if error_rows:
                    msg += f" Encountered {len(error_rows)} errors during row processing (see logs for details)."
                frappe.logger("lightning_upload").info(msg)
                frappe.msgprint(msg, title="CRM Lead Import Successful", indicator="green", wide=True)

        except Exception as e:
            tb = traceback.format_exc() # Get traceback
            log_msg = f"Overall error in Lightning Upload validate: {str(e)}. Traceback: {tb}"
            frappe.logger("lightning_upload").error(log_msg)
            frappe.throw(f"Critical error during import: {str(e)}. Check server logs (search for 'lightning_upload').")
            return