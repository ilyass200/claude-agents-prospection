#!/usr/bin/env python3
"""Script pour mettre à jour le sheet après envoi d'un email."""
import json
import sys
import requests

# Args: token, spreadsheet_id, row, scheduled, subject, body, message_id
token = sys.argv[1]
spreadsheet_id = sys.argv[2]
row = sys.argv[3]
scheduled = sys.argv[4]
subject = sys.argv[5]
body = sys.argv[6]
message_id = sys.argv[7]

values = [['Email envoyé', scheduled, subject, body, message_id]]
payload = {'values': values}

r = requests.put(
    f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/leads_tracker!T{row}:X{row}?valueInputOption=USER_ENTERED',
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    json=payload
)
print(f'Row {row}: {r.status_code}')
if r.status_code not in [200, 201]:
    print(r.text[:200])
