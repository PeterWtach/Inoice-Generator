# Get unit cost
from collections import defaultdict

import builder


def get_unit_cost(api_hits, sp_api_name, rate_card_data):
    # Iterate through the rate_card_data
    for rate_card in rate_card_data:
        # Check if SP API Name matches
        if rate_card['SP API Name'] == sp_api_name:
            # If Plan Type is 'flat', return the price directly
            if rate_card['Plan Type'] == 'flat':
                return float(rate_card['Price'])
            # If Plan Type is 'slab', check if the api_hits fall between Min and Max APIs Hits
            elif rate_card['Plan Type'] == 'slab':
                min_hits = int(rate_card['Min APIs Hits'])
                max_hits = int(rate_card['Max APIs Hits'])
                # Handle the case for slabs where max is 0, meaning "more than min hits"
                if min_hits <= api_hits and (max_hits == 0 or api_hits <= max_hits):
                    return float(rate_card['Price'])
    # If no matching slab or flat rate is found
    return 0.0


def get_invoice_summary(transaction_summary, organizations, rate_card_data, is_custom=False):
    invoice_summaries = []
    org_map = {
        org['Application name']: {
            "id": org['ID'],
            "name": org['Bank Name'],
            "name_description": org['Name Description'],
            "street": org['Street'],
            "location": org['Location'],
            "city": org['City'],
            "postal_code": org['Postal Code'],
            "state": org['State'],
            "country": org['Country'],
            "gstin": org['GST number'],
            "pan_number": org['PAN number'],
            "state_code": org['State code'],
            "address": f"{org['Street']}, {org['Location']}, {org['City']}, {org['Postal Code']}, {org['State']}, {org['Country']}"
        }
        for org in organizations
    }

    for tx in transaction_summary:
        invoice_summary = {}
        invoice_summary["application_name"] = tx.get("application_name")
        org_summary = org_map.get(tx.get('application_name'))
        invoice_summary["invoice_number"] = tx.get('invoice_number')
        invoice_summary["organization"] = org_summary
        if is_custom:
            unit_cost = tx.get("unit_cost")
        else:
            unit_cost = get_unit_cost(tx.get("successful_transactions_count"), tx.get("provider_api_name"),
                                      rate_card_data)

        # Creating a summary of the transaction and appending it to the user's transactions.
        invoice_summary["transaction_summary"] = {
            "application_name": tx.get("application_name"),
            "provider_api_name": tx.get("provider_api_name"),
            "provider_api_description": tx.get("provider_api_description"),
            "lender_api_name": tx.get("lender_api_name"),
            "lender_api_description": tx.get("lender_api_description"),
            "destination_info": tx.get("destination_info"),
            "total_transactions": tx.get("total_transactions_count"),
            "successful_transactions": tx.get("successful_transactions_count"),
            "failed_transactions": tx.get("failed_transactions_count"),
            "unit_cost": unit_cost,
            "amount": tx.get("amount"),
            "use_amount_value": tx.get("use_amount_value")
        }
        invoice_summaries.append(invoice_summary)
    return invoice_summaries


def combine_invoice_summaries_and_add_billing_summary(data):
    # To store the combined results
    combined_records = defaultdict(lambda: {
        'application_name': None,
        'invoice_number': None,
        'organization': None,
        'transaction_summary': {
            'application_name': None,
            'total_transactions': 0,
            'successful_transactions': 0,
            'failed_transactions': 0,
            'total_cost': 0.0,  # Initialize total cost
            'billing_summary': []
        }
    })

    for entry in data:
        print(entry)
        if entry['organization'] is not None:
            key = (entry['application_name'], entry['invoice_number'], entry['organization']['id'])
            transaction_summary = entry['transaction_summary']

            # Initialize the record with application_name, invoice_number, and organization only once
            if combined_records[key]['application_name'] is None:
                combined_records[key]['application_name'] = entry['application_name']
                combined_records[key]['invoice_number'] = entry['invoice_number']
                combined_records[key]['organization'] = entry['organization']
                combined_records[key]['transaction_summary']['application_name'] = transaction_summary['application_name']

            # Aggregate transaction counts
            combined_records[key]['transaction_summary']['total_transactions'] += transaction_summary['total_transactions']
            combined_records[key]['transaction_summary']['successful_transactions'] += transaction_summary[
                'successful_transactions']
            combined_records[key]['transaction_summary']['failed_transactions'] += transaction_summary[
                'failed_transactions']
            total_cost = 0
            use_unit_cost = True
            if transaction_summary.get('use_amount_value') == 'Y':
                total_cost = transaction_summary.get('amount')
                use_unit_cost = False
            else:
                # Add to billing_summary and calculate the total cost for this specific entry
                total_cost = str(transaction_summary['total_transactions'] * transaction_summary['unit_cost'])
            billing_entry = {
                "sr_no": len(combined_records[key]['transaction_summary']['billing_summary']) + 1,
                "service_name": transaction_summary['lender_api_name'],
                "provider": transaction_summary['destination_info'],
                "unit_cost": f"{transaction_summary['unit_cost']:.2f}" if use_unit_cost else "-",  # formatted as string for output
                "count": transaction_summary['total_transactions'],
                "total_cost": builder.report_builder.format_to_inr(total_cost)
            }

            # Add billing entry to billing_summary
            combined_records[key]['transaction_summary']['billing_summary'].append(billing_entry)

            if use_unit_cost:
                # Calculate total cost by summing up individual billing total costs
                combined_records[key]['transaction_summary']['total_cost'] += (
                        transaction_summary['total_transactions'] * transaction_summary['unit_cost'])
            else:
                combined_records[key]['transaction_summary']['total_cost'] += float(total_cost)

    # Convert the combined records dictionary to a list
    final_result = list(combined_records.values())
    return final_result
