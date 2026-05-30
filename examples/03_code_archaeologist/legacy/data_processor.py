"""Legacy data processing module.

This file is an intentional example of older Python style — no type hints,
``%``-style string formatting, undocumented functions, and global mutable state.
It is used as a fixture by the Code Archaeologist demo to demonstrate analysis
and modernisation capabilities.
"""
import csv
import datetime
import os

# Global mutable state — intentional style issue.
PROCESSED_RECORDS = []
ERROR_LOG = []
TOTAL_AMOUNT = 0.0

DEFAULT_TAX_RATE = 0.08


def load_records(filepath):
    records = []
    f = open(filepath, 'r')
    reader = csv.DictReader(f)
    for row in reader:
        records.append(row)
    f.close()
    return records


def validate_record(record):
    if not record.get('id'):
        return False
    if not record.get('amount'):
        return False
    try:
        float(record['amount'])
    except ValueError:
        return False
    return True


def compute_tax(amount, rate=DEFAULT_TAX_RATE):
    return amount * rate


def process_record(record):
    global TOTAL_AMOUNT
    amount = float(record['amount'])
    tax = compute_tax(amount)
    total = amount + tax
    TOTAL_AMOUNT = TOTAL_AMOUNT + total
    result = {}
    result['id'] = record['id']
    result['name'] = record.get('name', 'Unknown')
    result['amount'] = amount
    result['tax'] = tax
    result['total'] = total
    result['processed_at'] = str(datetime.datetime.now())
    return result


def process_all(filepath):
    global PROCESSED_RECORDS, ERROR_LOG
    records = load_records(filepath)
    for r in records:
        if validate_record(r):
            processed = process_record(r)
            PROCESSED_RECORDS.append(processed)
        else:
            msg = 'Invalid record: %s' % str(r)
            ERROR_LOG.append(msg)
            print('ERROR: %s' % msg)


def format_summary():
    lines = []
    lines.append('=== Processing Summary ===')
    lines.append('Total records processed: %d' % len(PROCESSED_RECORDS))
    lines.append('Total errors: %d' % len(ERROR_LOG))
    lines.append('Total amount (with tax): %.2f' % TOTAL_AMOUNT)
    return '\n'.join(lines)


def save_results(output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    outfile = output_dir + '/results.csv'
    f = open(outfile, 'w')
    writer = csv.DictWriter(f, fieldnames=['id', 'name', 'amount', 'tax', 'total', 'processed_at'])
    writer.writeheader()
    for r in PROCESSED_RECORDS:
        writer.writerow(r)
    f.close()
    print('Results saved to: %s' % outfile)
    return outfile


if __name__ == '__main__':
    process_all('data/records.csv')
    print(format_summary())
    save_results('output')
