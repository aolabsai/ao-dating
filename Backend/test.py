from apify_client import ApifyClient
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENAI_KEY")

client = OpenAI(api_key=key)

aclient = ApifyClient("apify_api_BDuOGj01tnTh3Twbgx11WtOrwa8Zps0PT8rp")

def genTags(handle):
    run_input = {
        "directUrls": [f"https://www.instagram.com/{handle}/"],
        "resultsType": "posts",
        "resultsLimit": 5,
        "searchType": "hashtag",
        "searchLimit": 1,
        "addParentData": False,
    }

    run = aclient.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)

    caption_list = []
    try:
        for item in aclient.dataset(run["defaultDatasetId"]).iterate_items():
            caption_list.append(item["caption"])
    except Exception as e:
        print(e)
    return caption_list


def processTags(tags):
    messages = [
        {
            "role": "user",
            "content": f"Give 2 words that describe these captions from Instagram: {tags}"
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    

    text = response.choices[0].message.content
    print("Full response:", text)
    

    words = text.split()
    if len(words) >= 2:
        a, b = words[0], words[1]
        print("Parsed words:", a, b)
    else:
        print("Error: Expected at least two words in the response.")



    return a, b

list = genTags("rafayel_latif")
print(processTags(list))