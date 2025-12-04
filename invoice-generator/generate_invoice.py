import sys
sys.path.append('./lib')   # ← yeh line add kar de

from builder.report_builder import generate_report
from data.google_ds_reader import *
from summary.report_summary import get_invoice_summary, combine_invoice_summaries_and_add_billing_summary
import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar


def get_transaction_summary(invoices_for_month, custom_invoice_data, organization_application,
                            api_details_by_provider_and_api_name):
    transaction_summary = []
    if custom_invoice_data is not None and len(custom_invoice_data) > 1:
        for custom_invoice_details in custom_invoice_data:
            if custom_invoice_details.get('Month - Year') == invoices_for_month:
                transaction_summary.append(
                    {"application_name": organization_application.get(custom_invoice_details.get('Bank name')),
                     "provider_api_name": api_details_by_provider_and_api_name.get(
                         custom_invoice_details.get('Provider Name') + custom_invoice_details.get('API name')),
                     "lender_api_name": custom_invoice_details.get('API name'),
                     "destination_info": custom_invoice_details.get('Provider Name'),
                     "total_transactions_count": int(custom_invoice_details.get('Successful hits'))
                                                 + int(custom_invoice_details.get('Failed hits')),
                     "successful_transactions_count": int(custom_invoice_details.get('Successful hits')),
                     "failed_transactions_count": int(custom_invoice_details.get('Failed hits')),
                     "invoice_number": custom_invoice_details.get('Invoice number')})
    return transaction_summary


def get_teal_mp_bhulekh_transaction_summary(invoices_for_month, teal_and_mp_bhulekh_invoice_data,
                                            organization_application,
                                            api_details_by_provider_and_api_name):
    custom_summary = []
    if teal_and_mp_bhulekh_invoice_data is not None and len(teal_and_mp_bhulekh_invoice_data) > 1:
        for custom_invoice_details in teal_and_mp_bhulekh_invoice_data:
            if custom_invoice_details.get('Month - Year') == invoices_for_month:
                custom_summary.append(
                    {"application_name": organization_application.get(custom_invoice_details.get('Bank name')),
                     "provider_api_name": api_details_by_provider_and_api_name.get(
                         custom_invoice_details.get('Provider Name') + custom_invoice_details.get('API name')),
                     "lender_api_name": custom_invoice_details.get('API name'),
                     "destination_info": custom_invoice_details.get('Provider Name'),
                     "total_transactions_count": int(custom_invoice_details.get('Successful hits'))
                                                 + int(custom_invoice_details.get('Failed hits')),
                     "successful_transactions_count": int(custom_invoice_details.get('Successful hits')),
                     "failed_transactions_count": int(custom_invoice_details.get('Failed hits')),
                     "document_type": custom_invoice_details.get('Failed hits'),
                     "unit_cost": float(custom_invoice_details.get('Unit Cost')),
                     "invoice_number": custom_invoice_details.get('Invoice number'),
                     "amount": custom_invoice_details.get('Amount'),
                     "use_amount_value": custom_invoice_details.get('Use Amount Value')
                     })
    return custom_summary


# Function to handle the button click
def on_button_click():
    # Get selected values from dropdowns
    selected_month = month_var.get()
    selected_year = year_var.get()
    invoices_for_month = f"{selected_month}-{selected_year}"
    # Get the selected date from the calendar
    selected_date = date_picker.get_date()
    # formatted_date = selected_date.strftime("%d-%m-%Y")

    # invoices_for_month = "July-2024"
    # Get Rate Card
    rate_card_data = get_api_rate_card_data()
    # Get API Details
    api_details = get_api_details()
    # Get organizations
    organizations = get_lenders()
    # Get application name associated with lender which is getting used in database to calculate total hits
    organization_application = {org['Bank Name']: org['Application name'] for org in organizations}
    # API details by provider name
    api_details_by_provider_and_api_name = {
        f"{api_detail['SP Name']}{api_detail['Lender API Name']}": api_detail['SP API Name'] for api_detail in
        api_details
    }
    # Get payment details
    payment_details = get_payment_details()
    # Get custom invoices data
    custom_invoice_data = get_custom_billing_data_for_sync_services()
    # Transaction summary of all invoices
    transaction_summary = get_transaction_summary(invoices_for_month,
                                                  custom_invoice_data,
                                                  organization_application,
                                                  api_details_by_provider_and_api_name)

    # Get Teal and MP Bhulekh data
    teal_and_mp_bhulekh_invoice_data = get_custom_billing_data_for_teal_and_mp_bhulekh_services()
    # Transaction summary of teal and MP Bhulekh
    teal_and_mp_bhulekh_summary = get_teal_mp_bhulekh_transaction_summary(invoices_for_month,
                                                                          teal_and_mp_bhulekh_invoice_data,
                                                                          organization_application,
                                                                          api_details_by_provider_and_api_name)

    invoice_summaries = get_invoice_summary(transaction_summary, organizations, rate_card_data, is_custom=False)
    invoice_summaries_teal_mp = get_invoice_summary(teal_and_mp_bhulekh_summary, organizations, rate_card_data,
                                                    is_custom=True)

    # Combine all transaction summaries
    invoice_summaries.extend(invoice_summaries_teal_mp)

    invoice_summaries = combine_invoice_summaries_and_add_billing_summary(invoice_summaries)
    generate_report(invoices_for_month, invoice_summaries, payment_details, selected_date, organization_application)


if __name__ == '__main__':
    # Create the main Tkinter window
    root = tk.Tk()
    root.title("RBiH Invoice Generator")

    # Variables to store the selected values
    month_var = tk.StringVar()
    year_var = tk.StringVar()

    # Month dropdown
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_label = tk.Label(root, text="Select Month:")
    month_label.pack(pady=5)
    month_dropdown = ttk.Combobox(root, textvariable=month_var, values=months, state="readonly")
    month_dropdown.pack(pady=5)
    month_dropdown.set("January")  # Default value

    # Year dropdown
    years = [str(year) for year in range(2025, 2051)]
    year_label = tk.Label(root, text="Select Year:")
    year_label.pack(pady=5)
    year_dropdown = ttk.Combobox(root, textvariable=year_var, values=years, state="readonly")
    year_dropdown.pack(pady=5)
    year_dropdown.set("2025")  # Default value

    # Date Picker using tkcalendar
    date_label = tk.Label(root, text="Select a Date:")
    date_label.pack(pady=5)
    date_picker = Calendar(root, date_pattern="dd-mm-yyyy")
    date_picker.pack(pady=5)

    # Button to trigger the selections
    select_button = tk.Button(root, text="Generate Invoice", command=on_button_click)
    select_button.pack(pady=10)

    # Run the Tkinter event loop
    root.mainloop()
    # invoices_for_month = "July-2024"
    # # Get Rate Card
    # rate_card_data = get_api_rate_card_data()
    # # Get API Details
    # api_details = get_api_details()
    # # Get organizations
    # organizations = get_lenders()
    # # Get application name associated with lender which is getting used in database to calculate total hits
    # organization_application = {org['Bank Name']: org['Application name'] for org in organizations}
    # # API details by provider name
    # api_details_by_provider_and_api_name = {
    #     f"{api_detail['SP Name']}{api_detail['Lender API Name']}": api_detail['SP API Name'] for api_detail in
    #     api_details
    # }
    # # Get payment details
    # payment_details = get_payment_details()
    # # Get custom invoices data
    # custom_invoice_data = get_custom_billing_data_for_sync_services()
    # # Transaction summary of all invoices
    # transaction_summary = get_transaction_summary(invoices_for_month,
    #                                               custom_invoice_data,
    #                                               organization_application,
    #                                               api_details_by_provider_and_api_name)
    #
    # # Get Teal and MP Bhulekh data
    # teal_and_mp_bhulekh_invoice_data = get_custom_billing_data_for_teal_and_mp_bhulekh_services()
    # # Transaction summary of teal and MP Bhulekh
    # teal_and_mp_bhulekh_summary = get_teal_mp_bhulekh_transaction_summary(invoices_for_month,
    #                                                                       teal_and_mp_bhulekh_invoice_data,
    #                                                                       organization_application,
    #                                                                       api_details_by_provider_and_api_name)
    #
    # invoice_summaries = get_invoice_summary(transaction_summary, organizations, rate_card_data, is_custom=False)
    # invoice_summaries_teal_mp = get_invoice_summary(teal_and_mp_bhulekh_summary, organizations, rate_card_data,
    #                                                 is_custom=True)
    #
    # # Combine all transaction summaries
    # invoice_summaries.extend(invoice_summaries_teal_mp)
    #
    # invoice_summaries = combine_invoice_summaries_and_add_billing_summary(invoice_summaries)
    # generate_report(invoices_for_month, invoice_summaries, payment_details, "28-11-2024", organization_application)
