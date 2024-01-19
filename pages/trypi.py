# Packages required:
import os
import requests 
import json 
import base64
from dotenv import load_dotenv

load_dotenv()

api_base = os.getenv("API_BASE") 
deployment_name = os.getenv("DEPLOYMENT_NAME")
API_KEY = os.getenv("AZURE_OPENAI_KEY_VISION")
base_url = f"{api_base}openai/deployments/{deployment_name}" 
headers = {   
    "Content-Type": "application/json",   
    "api-key": API_KEY
}

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

encoded_images = []

image_path = "/app/meeting_summary/image.jpg"

encoded_image = encode_image(image_path)


# Prepare endpoint, headers, and request body 
endpoint = f"{base_url}/chat/completions?api-version=2023-12-01-preview" 
data = { 
    "messages": [ 
        { "role": "system", "content": "You are a helpful assistant." }, 
        { "role": "user", "content": [  
            { 
                "type": "text", 
                "text": "Describe this picture:" 
            },
            { 
                "type": "image_url",
                "image_url": {
                    "url": "data:image/jpeg;base64," + encoded_image
                }
            }
        ] } 
    ],
    "max_tokens": 4096
}   

# Make the API call   
response = requests.post(endpoint, headers=headers, data=json.dumps(data), stream=True)   
# Check if the request was successful
if response.status_code == 200:
    # Process the response as it streams in
    for line in response.iter_lines():
        if line:
            # Decode each line and process it (e.g., print it)
            decoded_line = line.decode('utf-8')
            print(decoded_line)  # or handle the line as needed
else:
    print(f"Error: {response.status_code}")