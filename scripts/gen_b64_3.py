import base64  
with open(r'D:/ASTRA/jarvis-ai-assistant/scripts/storage_cleanup.py', 'rb') as f:  
    content = f.read()  
print(base64.b64encode(content).decode('ascii')) 
