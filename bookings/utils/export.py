import threading
from django.core.mail import EmailMessage
from openpyxl import Workbook
from io import BytesIO
from django.db import connection
from django.utils import timezone

EXPORT_SPINE = {
    "Booking ID": {"from": "serializer", "get": "id"},
    "Ref ID": {"from": "serializer", "get": "ref_id"},
    "Customer": {"from": "serializer", "get": "user_str"},
    "Status": {"from": "serializer", "get": "status"},
    
    "Payment Status": {"from": "serializer", "get": "payment_status"},
    "Initial Amount": {"from": "serializer", "get": "final_amount"},
    "Final Amount": {"from": "serializer", "get": "initial_amount"},

    "Created At": {"from": "serializer", "get": "created_at"},
    "Created By": {"from": "serializer", "get": "created_by_str"},
    "Scheduled Date": {"from": "serializer", "get": "scheduled_date"},
    "Scheduled Time Slot": {"from": "serializer", "get": "scheduled_time_slot"},
    "Location": {"from": "serializer", "get": "location_str"},
    "Address Str": {"from": "serializer", "get": "address_str"},
    "Test Count": {"from": "serializer", "get": "total_tests"},
    # Custom Function logic
    "Current Agent": {"from": "function", "get": "get_current_agent"},
    # "Export Status": {"from": "function", "get": "get_system_stamp"},
}

class ExportFunctions:
    """Namespace for custom functions used in the Spine"""
    @staticmethod
    def calculate_urgency(obj_dict):
        # Logic based on the serialized data
        amount = float(obj_dict.get('final_amount', 0) or 0)
        return "High Value" if amount > 5000 else "Standard"

    @staticmethod
    def get_current_agent(obj_dict):
        
        return obj_dict.get('view_stack')[-1] if obj_dict.get('view_stack') else ''

def generate_booking_excel_and_email(queryset, user_email, serializer_class):
    def run():
        try:
            # 1. Serialize
            serializer = serializer_class(queryset, many=True)
            serialized_data = serializer.data
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Data Export"

            # 2. Write Headers from Spine Keys
            headers = list(EXPORT_SPINE.keys())
            ws.append(headers)

            # 3. Process Rows based on Spine Logic
            for row_obj in serialized_data:
                excel_row = []
                
                for column_name, config in EXPORT_SPINE.items():
                    source = config.get("from")
                    target = config.get("get")

                    if source == "serializer":
                        val = row_obj.get(target, "")
                    
                    elif source == "function":
                        # Dynamically call the function from our helper class
                        func = getattr(ExportFunctions, target, None)
                        val = func(row_obj) if func else ""
                    
                    # Clean up lists (like view_stack) for Excel
                    if isinstance(val, list):
                        val = ", ".join(map(str, val))
                    
                    excel_row.append(val)
                
                ws.append(excel_row)

            # 4. Buffer & Send
            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)

            email = EmailMessage(
                subject="CRM Export Ready",
                body="Your requested data is attached.",
                to=[user_email],
            )
            email.attach('Export.xlsx', buffer.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            email.send()

        finally:
            connection.close()

    thread = threading.Thread(target=run)
    thread.start()