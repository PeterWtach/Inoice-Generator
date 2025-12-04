import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from babel.numbers import format_currency
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from num2words import num2words
from pyreportjasper import PyReportJasper
import json

INVOICE_DATE_FORMAT = '%d-%b-%y'
DATE_INPUT_FORMAT = "%Y-%m-%d"
PAYMENT_DUE_DATE_PERIOD = 15
SAC_NO = 998319
INVOICE_BILL_PERIOD_VIEW_FORMAT = "{start_date} - {end_date}"

late_payment_fee = 500


def format_to_inr(cost_value) -> str:
    """
    Formats a numeric value as a currency string in Indian Rupees (INR), excluding the currency symbol.

    This function is particularly useful in scenarios where the numeric currency value needs to be displayed
    or processed without the INR symbol (₹), ensuring only the numeric part of the formatted string is returned.

    Parameters:
    - cost_value (float): The numeric value representing the cost to be formatted as currency.

    Returns:
    - str: The formatted currency string without the INR currency symbol.
    """
    # Format the numeric value as a currency string in INR, using the 'en_IN' locale to get the correct
    # formatting conventions for Indian Rupees. This includes the currency symbol, decimal places, and grouping.
    formatted_total_cost = format_currency(cost_value, 'INR', locale='en_IN')

    # Remove the INR currency symbol (₹) from the formatted currency string. This is done by replacing
    # the symbol with an empty string, leaving only the numeric part of the formatted currency value.
    formatted_unit_cost_without_symbol = formatted_total_cost.replace('\u20B9', '')

    return formatted_unit_cost_without_symbol


def round_off_amount(amount):
    try:
        amount = Decimal(amount)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid amount format: {amount}")

    # Round the amount to the nearest integer
    rounded_amount = amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    # Convert the rounded amount to an integer
    rounded_amount_int = int(rounded_amount)
    return rounded_amount_int


def get_amount_due(previous_balance, payments_received, adjustments, current_period_charges):
    return round_off_amount(previous_balance - payments_received - adjustments + current_period_charges)


def get_previous_balance(month, bank_name, payment_details):
    previous_balance = payment_details.get(f"{month}-{bank_name}")
    if previous_balance is not None:
        return previous_balance.get("Previous Balance")
    return 0


def get_adjustments(month, bank_name, payment_details):
    previous_balance = payment_details.get(f"{month}-{bank_name}")
    if previous_balance is not None:
        return previous_balance.get("Adjustments")
    return 0


def get_payments_received(month, bank_name, payment_details):
    previous_balance = payment_details.get(f"{month}-{bank_name}")
    if previous_balance is not None:
        return previous_balance.get("Payment Received")
    return 0


def get_po_number(month, bank_name, payment_details):
    previous_balance = payment_details.get(f"{month}-{bank_name}")
    if previous_balance is not None:
        return previous_balance.get("PO Number")
    return "-"


def get_tax_rates(org_state):
    sgst_rate = 0.09
    cgst_rate = 0.09
    igst_rate = 0.18
    platform_state = "karnataka"
    return (sgst_rate, cgst_rate, float(0.00)) if org_state.lower() == platform_state.lower() else (
        float(0.00), float(0.00), igst_rate)


def generate_report_using_jasper(parameters, bill_summaries, report_name, target_folder_name):
    # Create an instance of PyReportJasper
    report = PyReportJasper()

    # Iterate over the list and construct the new keys
    for index, item in enumerate(bill_summaries, start=1):  # start=1 for 1-based indexing
        for key, value in item.items():
            new_key = f"{key}_{index}"  # Create new key
            print(new_key)
            parameters[new_key] = value  # Add to the new dictionary
    current_dir = os.getcwd()
    resources_path = os.path.join(current_dir, 'resources')
    report_template_path = os.path.join(resources_path, 'invoice_template_long_service_description.jrxml')

    output_report_path = os.path.join(tempfile.gettempdir(), report_name)
    parameters["net.sf.jasperreports.awt.ignore.missing.font"] = "true"
    parameters["JASPER_REPORTS_FONT_PATH"] = "/System/Library/Fonts:/Library/Fonts:~/Library/Fonts"
    report.process(
        input_file=report_template_path,
        output_file=output_report_path,
        format_list=["pdf"],
        parameters=parameters,
    )

    upload_file_to_drive(file_path= f"{output_report_path}.pdf", target_folder_name=target_folder_name)


def _strip_decimal_parts(cost):
    # If the formatted string ends with ".00", remove it
    if cost.endswith('.00'):
        return cost[:-3]
    return cost


def convert_amount_to_words(amount):
    # Convert the amount to words in Indian currency (INR)
    amount_in_words = num2words(amount, to='currency', lang='en_IN')
    # Replace "euro" with "rupees" and "cents" with "paise"
    amount_in_words = amount_in_words.replace("euro", "rupees").replace("cents", "paise")
    # Remove "zero paise"
    amount_in_words = amount_in_words.replace(" zero paise", "")
    # Remove commas
    amount_in_words = amount_in_words.replace(',', '')
    # Capitalize the first letter
    amount_in_words = amount_in_words.capitalize()
    return str(amount_in_words)


def get_future_date_ist(days, format_str, current_date_ist):
    """
    Calculates a future date from the current date in Indian Standard Time (IST) by adding a specified number of days.

    Parameters:
    - days (int): The number of days to add to the current date to calculate the future date.
    - format_str (str): A string specifying the format in which to return the future date. If None or not provided,
                        the function returns the future date in its default format.
    - current_date_ist (datetime): The current date from which to calculate the future date, represented as a datetime object.

    Returns:
    - str or datetime: The future date calculated from the current date, returned as a string if format_str is provided,
                       or as a datetime object if format_str is None or not provided.
    """

    # Calculate the future date by adding 'days'
    future_date_ist = current_date_ist + timedelta(days=days)

    # Return the future date in IST
    if format_str:
        # Return the current date in the specified format
        return future_date_ist.strftime(format_str)
    # Return the current date in the default format if no format is provided
    return future_date_ist


def get_formatted_date(date_str, input_format_str, output_format_str):
    """
    Converts a date string from one format to another.

    Parameters:
    - date_str (str): The date string to be converted.
    - input_format_str (str): The format of the input date string.
    - output_format_str (str): The desired format of the output date string.

    Returns:
    - str: The date string converted to the desired format.
    """

    # Parse the date string into a datetime object
    date_obj = datetime.strptime(date_str, input_format_str)

    # Return the formatted date string
    return date_obj.strftime(output_format_str)


def get_month_start_end_dates(input_date):
    # Parse the input string to a datetime object
    date_obj = datetime.strptime(input_date, "%B-%Y")

    # Get the first day of the month
    start_date = date_obj.replace(day=1)

    # Get the first day of the next month and subtract one day to get the last day of the current month
    next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = next_month - timedelta(days=1)

    # Format the dates as 'YYYY-MM-DD'
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    return start_date_str, end_date_str


def get_month_start_end_dates_for_report_name(input_date):
    # Parse the input string to a datetime object
    date_obj = datetime.strptime(input_date, "%B-%Y")

    # Get the first day of the month
    start_date = date_obj.replace(day=1)

    # Get the first day of the next month and subtract one day to get the last day of the current month
    next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = next_month - timedelta(days=1)

    # Format the dates as 'YYYY-MM-DD'
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')
    return f"{start_date_str}_{end_date_str}"


def generate_report(invoices_for_month, invoice_summaries, payment_details, invoice_date, organization_application):
    start_date, end_date = get_month_start_end_dates(invoices_for_month)
    current_dir = os.getcwd()
    resources_path = os.path.join(current_dir, 'resources')
    logo_file_path = os.path.join(resources_path, 'rbih_logo.png')
    rbih_logo_file_path = os.path.abspath(logo_file_path)
    report_footer = os.path.join(resources_path, 'footer.png')
    report_footer_file_path = os.path.abspath(report_footer)
    invoice_date = datetime.strptime(invoice_date, "%d-%m-%Y")

    for invoice_summary in invoice_summaries:
        sgst_rate, cgst_rate, igst_rate = get_tax_rates(invoice_summary.get("organization").get("state"))
        unformatted_amount = Decimal(invoice_summary.get("transaction_summary").get("total_cost"))
        # unformatted_amount = Decimal(invoice_summary.get("transaction_summary").get("successful_transactions") * invoice_summary.get("transaction_summary").get("unit_cost"))
        formatted_amount = format_to_inr(unformatted_amount)
        sgst, cgst, igst = unformatted_amount * Decimal(sgst_rate), unformatted_amount * Decimal(
            cgst_rate), unformatted_amount * Decimal(igst_rate)
        total_tax = round_off_amount(round(sgst, 2)) + round_off_amount(round(cgst, 2)) + round_off_amount(round(igst, 2))
        total_tax = round(total_tax, 2)
        total_due = unformatted_amount + total_tax
        roundedoff_total_due = round_off_amount(total_due)
        previous_balance = get_previous_balance(invoices_for_month, invoice_summary.get("organization").get("name"),
                                                payment_details)
        po_number = get_po_number(invoices_for_month, invoice_summary.get("organization").get("name"),
                                  payment_details)
        amount_due = float(previous_balance) + float(roundedoff_total_due)
        txt_credit_limit = format_to_inr(0)
        payments_received = get_payments_received(invoices_for_month, invoice_summary.get("organization").get("name"),
                                                  payment_details)
        txt_pmnt_received = format_to_inr(payments_received)
        adjustments = get_adjustments(invoices_for_month, invoice_summary.get("organization").get("name"),
                                      payment_details)
        po_number = get_po_number(invoices_for_month, invoice_summary.get("organization").get("name"), payment_details)
        txt_pmnt_adj = format_to_inr(adjustments)
        txt_prev_balance = format_to_inr(previous_balance)
        txt_curr_period_charges = format_to_inr(roundedoff_total_due)
        payment_due = get_amount_due(float(previous_balance), float(payments_received), float(adjustments),
                                     roundedoff_total_due)
        txt_pmnt_due = txt_curr_period_charges
        txt_sgst = format_to_inr(round_off_amount(round(sgst, 2)))
        txt_cgst = format_to_inr(round_off_amount(round(cgst, 2)))
        txt_igst = format_to_inr(round_off_amount(round(igst, 2)))
        pmnt_after_due_date = roundedoff_total_due + Decimal(late_payment_fee)
        roundedoff_pmnt_after_due_date = round_off_amount(pmnt_after_due_date)
        txt_pmnt_after_due_date_2 = format_to_inr(roundedoff_pmnt_after_due_date)
        txt_total_curr_period_charges = format_to_inr(payment_due)
        txt_pmnt_after_due_date = format_to_inr(late_payment_fee)
        txt_taxable_value = formatted_amount
        cbill_date = invoice_date
        cbill_date = cbill_date.strftime(INVOICE_DATE_FORMAT)
        pan_number = invoice_summary.get("organization").get("pan_number")
        address = invoice_summary.get("organization").get("address")
        gstin = invoice_summary.get("organization").get("gstin")
        organization_name = invoice_summary.get("organization").get("name")
        total_transactions = invoice_summary.get("transaction_summary").get("total_transactions")
        total_successful_transactions = invoice_summary.get("transaction_summary").get("successful_transactions")
        total_failed_transactions = invoice_summary.get("transaction_summary").get("failed_transactions")
        state = invoice_summary.get("organization").get("state")
        invoice_number = invoice_summary.get("invoice_number")
        fields = {
            'txt_bill_address': address,
            'txt_bill_gstn': gstin,
            'txt_bill_name': str(organization_name),
            'txt_bill_pan': pan_number,
            'txt_bill_po_number': po_number if po_number is not None else "-",
            'txt_amount_words': convert_amount_to_words(Decimal(roundedoff_total_due)),
            'txt_payment_due_date': str(
                get_future_date_ist(int(PAYMENT_DUE_DATE_PERIOD), INVOICE_DATE_FORMAT, invoice_date)),
            'txt_credit_limit': _strip_decimal_parts(txt_credit_limit),
            'txt_state_code': 'No',
            'txt_prev_balance': _strip_decimal_parts(txt_prev_balance),
            'txt_pmnt_received': _strip_decimal_parts(txt_pmnt_received),
            'txt_pmnt_adj': _strip_decimal_parts(txt_pmnt_adj),
            'txt_curr_period_charges': _strip_decimal_parts(txt_curr_period_charges),
            'txt_pmnt_due': _strip_decimal_parts(txt_total_curr_period_charges),  # amount due
            'txt_pmnt_after_due_date': _strip_decimal_parts(txt_pmnt_after_due_date),  # late payment fee
            'txt_total_transactions_count': total_transactions,
            'txt_total_successful_transactions': total_successful_transactions,
            'txt_total_failed_transactions': total_failed_transactions,
            'txt_invoice_number': invoice_number,  # self._get_invoice_number(invoice_number, isum.invoice_number),
            'txt_bill_period': INVOICE_BILL_PERIOD_VIEW_FORMAT.format(
                start_date=get_formatted_date(start_date, DATE_INPUT_FORMAT,
                                              INVOICE_DATE_FORMAT),
                end_date=get_formatted_date(end_date, DATE_INPUT_FORMAT, INVOICE_DATE_FORMAT)),
            # 'txt_bill_period': '01-Jan-25 - 31-Mar-25',
            # 'txt_bill_period': 'Till December 2024',
            'txt_bill_date': cbill_date,
            'txt_total_curr_period_charges': _strip_decimal_parts(txt_pmnt_due),
            'txt_sgst': _strip_decimal_parts(txt_sgst),
            'txt_cgst': _strip_decimal_parts(txt_cgst),
            'txt_igst': _strip_decimal_parts(txt_igst),
            'txt_pmnt_after_due_date_2': _strip_decimal_parts(str(txt_pmnt_after_due_date_2)),
            # total payable after due date
            'txt_gst_number': gstin,
            'txt_sac_no': SAC_NO,
            'txt_liable_to_reverse_charge': "No",
            'txt_service_description': "Other Information Technology Services",
            'txt_late_fee': "500",
            'txt_place_of_supply': state,
            'txt_taxable_value': _strip_decimal_parts(txt_taxable_value),
            'rbih_logo_path': rbih_logo_file_path,
            'footer_path': report_footer_file_path
        }
        application_name = organization_application.get(organization_name)
        start_end_date_for_report_name = get_month_start_end_dates_for_report_name(invoices_for_month)
        provider = invoice_summary.get("transaction_summary").get("billing_summary")[0].get("provider")
        report_name = f"{application_name}_INVOICE_{start_end_date_for_report_name}_{provider.upper()}"

        nic_payload_version = "1.1"
        invoice_type: str = "INV"
        supply_type: str = "B2B"
        hsn_code: str = "998319"

        json_data = {
            "Version": nic_payload_version,
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": supply_type,
                "IgstOnIntra": "N",
                "RegRev": "N",
                "EcmGstin": None,
            },
            "DocDtls": {
                "Typ": invoice_type,
                "No": invoice_number,
                "Dt": fields["txt_bill_date"],
            },
            "SellerDtls": {
                "Gstin": "29AAKCR9018A1ZB",
                "LglNm": "RESERVE BANK INNOVATION HUB",
                "Addr1": "Regd. Office:- Keonics-K wing, 4th Floor 27th Main, Sector 1,",
                "Addr2": "7TH Cross Road,HSR Layout",
                "Loc": "Bengaluru",
                "Pin": 560102,
                "Stcd": "29",
                "Ph": "9986032787",
                "Em": "swethabelagodu@rbihub.in"
            },
            "BuyerDtls": {
                "Gstin": fields["txt_gst_number"],
                "LglNm": fields["txt_bill_name"],
                "Addr1": fields["txt_bill_address"],
                "Addr2": "",
                "Loc": "",
                "Pin": "",
                "Pos": "",
                "Stcd": "",
                "Ph": "",
                "Em": "",
            },
            "ValDtls": {
                "AssVal": fields.get("txt_taxable_value", 0),
                "IgstVal": fields.get("txt_igst", 0),
                "CgstVal": fields.get("txt_cgst", 0),
                "SgstVal": fields.get("txt_sgst", 0),
                "CesVal": 0,
                "StCesVal": 0,
                "Discount": 0,
                "OthChrg": 0,
                "RndOffAmt": 0,
                "TotInvVal": fields.get("txt_taxable_value", 0),
            },
            "RefDtls": {"InvRm": "NICGEPP2.0"},
            "ItemList": [
                {
                    "SlNo": "1",
                    "PrdDesc": "Other Information Technology",
                    "IsServc": "Y",
                    "HsnCd": "998319",
                    "Qty": 1,
                    "FreeQty": 0,
                    "Unit": "UNT",
                    "UnitPrice": fields.get("txt_taxable_value", 0),
                    "TotAmt": fields.get("txt_taxable_value", 0),
                    "Discount": 0,
                    "PreTaxVal": 0,
                    "AssAmt": fields.get("txt_taxable_value", 0),
                    "GstRt": 18,
                    "IgstAmt": float(igst),
                    "CgstAmt": float(cgst),
                    "SgstAmt": float(sgst),
                    "CesRt": 0,
                    "CesAmt": 0,
                    "CesNonAdvlAmt": 0,
                    "StateCesRt": 0,
                    "StateCesAmt": 0,
                    "StateCesNonAdvlAmt": 0,
                    "OthChrg": 0,
                    "TotItemVal": fields.get("txt_total_curr_period_charges", 0),
                }
            ],
        }
        with open(f"{report_name}.json", "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)
        generate_report_using_jasper(fields, invoice_summary.get("transaction_summary").get("billing_summary"),
                                     report_name, application_name)


# Function to check if a folder exists and return its ID
def get_folder_id(service, folder_name, parent_folder_id=None):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    if parent_folder_id:
        query += f" and '{parent_folder_id}' in parents"

    results = service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
    items = results.get('files', [])

    if items:
        return items[0]['id']
    return None


# Function to create a folder
def create_folder(service, folder_name, parent_folder_id=None):
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_folder_id:
        folder_metadata['parents'] = [parent_folder_id]

    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')


def upload_file_to_drive(file_path, target_folder_name):
    current_dir = os.getcwd()
    creds_template_path = os.path.join(os.path.join(current_dir, 'creds'),
                                       'invoice-generation-443205-60eafd4715eb.json')
    credentials = service_account.Credentials.from_service_account_file(
        creds_template_path, scopes=["https://www.googleapis.com/auth/drive"]
    )

    # Build the Google Drive service object.
    google_drive_service = build('drive', 'v3', credentials=credentials)

    parent_folder_id = "1ixhKIqNF1ep-JmjAl887VEGYepQjDgy2"

    # Check if the folder exists, create it if not
    folder_id = get_folder_id(google_drive_service, target_folder_name, parent_folder_id)
    if not folder_id:
        folder_id = create_folder(google_drive_service, target_folder_name, parent_folder_id)

    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    # Upload the file to Google Drive
    file = google_drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f"File uploaded successfully! File ID: {file.get('id')}")
