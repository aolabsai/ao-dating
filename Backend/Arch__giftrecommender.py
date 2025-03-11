import requests

def upload_to_imgur(image_path):
    url = "https://api.imgur.com/3/image"
    headers = {"Authorization": f"Client-ID {client_id}"}

    with open(image_path, "rb") as image_file:
        response = requests.post(url, headers=headers, files={"image": image_file})
    
    print("Response Status Code:", response.status_code)
    print("Response Text:", response.text)  # This will show raw response

    try:
        return response.json()["data"]["link"]
    except requests.exceptions.JSONDecodeError:
        return "Error: Could not decode JSON response."

# Example usage
image_link = upload_to_imgur(r"uploads\WIN_20250228_15_31_25_Pro.jpg")
print("Public Link:", image_link)
