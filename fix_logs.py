import os

webhook_file = 'app/api/endpoints/webhook.py'
with open(webhook_file, 'r') as f:
    w_code = f.read()

w_code = w_code.replace(', flush=True) # FORCE LOG', ')')
w_code = w_code.replace(', flush=True)', ')')
w_code = w_code.replace('print(', 'logger.info(')

with open(webhook_file, 'w') as f:
    f.write(w_code)

whatsapp_file = 'app/core/whatsapp.py'
with open(whatsapp_file, 'r') as f:
    wa_code = f.read()

wa_code = wa_code.replace('print(', 'logger.error(')

with open(whatsapp_file, 'w') as f:
    f.write(wa_code)

print("Logs replaced.")
