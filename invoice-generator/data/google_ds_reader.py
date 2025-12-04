import os
import sys

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


def get_data_from_google_sheet(data_range):
    current_dir = os.getcwd()
    creds_template_path = os.path.join(os.path.join(current_dir, 'creds'), 'invoice-generation-443205-60eafd4715eb.json')

    # Provide the path to your service account credentials JSON file
    creds = Credentials.from_service_account_file(creds_template_path,
                                                  scopes=['https://www.googleapis.com/auth/spreadsheets'])
    # Build the service object
    service = build('sheets', 'v4', credentials=creds)
    # Call the Sheets API
    sheet = service.spreadsheets()
    # Mahesh RBIH Spread Sheet
    return sheet.values().get(spreadsheetId='1UOw_RzlRyXt5iSDM-VrjENxRJ9nLvmuJheG_vrRRLx4', range=data_range).execute()
    # Mahesh Spread Sheet
    # return sheet.values().get(spreadsheetId='18tjuL9goTKgTFe4Kpux9OXeWdR-D4spjZgWKZud6mdQ', range=data_range).execute()


def get_lenders():
    lenders_data = []
    data = get_data_from_google_sheet('Lender Information!A:M')
    values = data.get('values', [])
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            org = values[count]
            lenders_data.append({'ID': org[0], 'Bank Name': org[1],
                                 'Name Description': org[2], 'PAN number': org[3],
                                 'GST number': org[4], 'Street': org[5], 'Location': org[6],
                                 'City': org[7], 'Postal Code': org[8], 'State': org[9],
                                 'Country': org[10], 'State code': org[11], 'Application name': org[12]})
        return lenders_data


def get_api_details():
    apis_details_data = []
    data = get_data_from_google_sheet('API Details!A:C')
    values = data.get('values', [])
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            api_details = values[count]
            apis_details_data.append({'SP Name': api_details[0], 'Lender API Name': api_details[1],
                                      'SP API Name': api_details[2]})
        return apis_details_data


def get_payment_details():
    result_payment_details = {}
    data = get_data_from_google_sheet('Payment Details!A:F')
    values = data.get('values', [])
    print(values)
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            value = values[count]
            result_payment_details[f"{value[0]}-{value[1]}"] = {'Month - Year': value[0], 'Bank name': value[1],
                                                                'Previous Balance': value[2],
                                                                'Payment Received': value[3], 'Adjustments': value[4],
                                                                'PO Number': value[5]}
        return result_payment_details


def get_custom_billing_data_for_teal_and_mp_bhulekh_services():
    result_custom_billing_data = []
    data = get_data_from_google_sheet('Teal and MP Bhulekh!A:K')
    values = data.get('values', [])
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            value = values[count]
            result_custom_billing_data.append(
                {'Month - Year': value[0], 'Bank name': value[1], 'API name': value[2],
                 'Provider Name': value[3], 'Document Type': value[4], 'Successful hits': value[5],
                 'Failed hits': value[6], 'Unit Cost': value[7], 'Invoice number': value[8], 'Amount': value[9],
                 'Use Amount Value': value[10]})
        return result_custom_billing_data


def get_custom_billing_data_for_sync_services():
    result_custom_billing_data = []
    data = get_data_from_google_sheet('SP Invoices!A:G')
    values = data.get('values', [])
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            value = values[count]
            result_custom_billing_data.append(
                {'Month - Year': value[0], 'Bank name': value[1], 'Successful hits': value[2],
                 'Failed hits': value[3], 'API name': value[4], 'Provider Name': value[5],
                 'Invoice number': value[6]})
        return result_custom_billing_data


def get_api_rate_card_data():
    rate_card_data = []
    data = get_data_from_google_sheet('Rate Card!A:G')
    values = data.get('values', [])
    if not values:
        print('No data found.')
        sys.exit(0)
    else:
        for count in range(1, len(values)):
            value = values[count]
            rate_card_data.append({'SP Name': value[0], 'Lender API Name': value[1], 'SP API Name': value[2],
                                   'Plan Type': value[3], 'Min APIs Hits': value[4], 'Max APIs Hits': value[5],
                                   'Price': value[6]})
        return rate_card_data
