from flask import Flask, request, jsonify, redirect, session, send_from_directory
from werkzeug.utils import secure_filename
import jwt
import datetime
from datetime import datetime
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

import random
from openai import OpenAI
import json

import ao_pyth as ao

from dotenv import load_dotenv
import embedding_bucketing.embedding_model_test as em

from flask_cors import CORS
import google.auth

from firebase_admin import credentials, auth, storage
import firebase_admin
from firebase_admin import firestore
import os
import requests
import base64


app = Flask(__name__)
app.secret_key = "super_secret_key"
CORS(app)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

# endpoint = "https://gift-recsys.onrender.com"  # change to https://gift-recsys.onrender.com for prod and http://127.0.0.1:5000 for local 
endpoint =  os.getenv("BACKEND_URL")
# frontend_url = "https://giftrec.aolabs.ai"   #change to http://localhost:5174 for local and  https://giftrec.aolabs.ai for prod
frontend_url = os.getenv("FRONTEND_URL")

ao_endpoint_url = "https://api.aolabs.ai/v0dev/kennel/agent"

openai_key = os.getenv("OPENAI_KEY")
rapid_key = os.getenv("RAPID_KEY")

firebase_sdk = json.loads(os.getenv("FIREBASE_SDK")) 
firebase_apikey = os.getenv("firebase_apikey")

JWT_SECRET_KEY = 'your_secret_key'
JWT_ALGORITHM = 'HS256'
#Set up google oauth
google_client = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

imgbb_api = os.getenv("IMGBB_API_KEY")


aolabs_key = os.getenv("AOLABS_API_KEY")
kennel_id = "aoDating4"


cred = credentials.Certificate(firebase_sdk)
firebase_admin.initialize_app(cred)



db = firestore.client()


flow = Flow.from_client_config(
    {
        "web": {
            "client_id": google_client,
            "client_secret": google_client_secret,
            "redirect_uris": [f"{endpoint}/callback"], 
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    },
    scopes=[
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ],
)
with open("google-countries.json") as f:
    country_data = json.load(f)

client = OpenAI(api_key=openai_key)
em.config(openai_key)

agent = None

# Configure upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 





def listTostring(s):
    return ''.join(map(str,s)) 

def stringTolist(s):
    return [int(i) for i in s]

def generate_token(user_email):
    payload = {
        'email': user_email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expires in 1 hour
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


    return token


def upload_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
    payload = {
        "key": imgbb_api,
        "image": encoded_image,
    }
    response = requests.post("https://api.imgbb.com/1/upload", data=payload)
    data = response.json()
    if data.get("success"):
        return data["data"]["url"]
    else:
        print("error uploading image")
        return data

def encode_input_to_binary(age, gender):

    age = int(age)
    age_binary = []
    if age<20:
        age_binary =[0,0,0]
    elif age<40:
        age_binary = [0,0,1]
    elif age<60:
        age_binary = [0,1,1]
    else:
        age_binary = [1,1,1]

    gender_binary = []
    if gender == "male":
        gender_binary = [0,0]
    elif gender == "female":
        gender_binary = [0,1]
    else:
        gender_binary = [1,1]


    input_to_agent = age_binary+gender_binary
    return input_to_agent

def agentResponse(Input, email, name_of_agent):
    arch = ao.Arch(arch_i="[3, 2]", arch_z="[1]", connector_function="full_conn", api_key = aolabs_key, kennel_id=kennel_id)
    email = email.lower()

    uid = name_of_agent+email
    Input = listTostring(Input)
    Agent = ao.Agent(Arch=arch, api_key=aolabs_key, uid=uid)
    response = Agent.next_state(Input)

    #dont even understand anything anymore about anything... dont ask, not sure why i cant just return response! 
    z = response
    print("agent response: ", response)
    return z


def create_local_cache():
    # Creates a temp json file when the user logs in, basically a copy of firebase database for users so we dont need to keep making calls 
    all_users = list(db.collection("Users").stream())
    all_users_list = []
    for user in all_users:
        all_users_list.append(user.to_dict())
    try:
        cache = open("cache.json", "r").read()
    except Exception as e:
        with open("cache.json", "w") as c:
            json.dump(all_users_list, c)

@app.route('/trainAgent', methods=["POST"])
def trainAgent():
    data = request.json
    recommended_profile_info = data["info"]
    label = data["label"]
    uid = data["uid"]
    user_email = data["email"]
    print("rec: ", recommended_profile_info)
    email = recommended_profile_info["email"]

    age = recommended_profile_info["age"]
    gender = recommended_profile_info["gender"]

    arch = ao.Arch(arch_i="[3, 2]", arch_z="[1]", connector_function="full_conn", api_key = aolabs_key, kennel_id=kennel_id)
    input_to_agent = encode_input_to_binary(int(age), gender)

    Agent = ao.Agent(Arch=arch, api_key=aolabs_key, uid=uid)
    if label == [1]:
        addFriend(user_email, email)

    print("training agent with label: ", label)


    Agent.next_state(INPUT=input_to_agent, LABEL=label)
    return jsonify({"message": "Training data saved successfully"}), 200


@app.route("/getUserData", methods=["POST"])
def getUserData():
    data = request.json
    email = data["email"].lower()
    print("email: ", email)

    ref = db.collection("Users")
    user_list =  list(ref.where("email", "==", email).stream())
    user_info = user_list[0].to_dict()
    print(user_info)

    return jsonify({"user_info": user_info})




def addFriend(user_email, add_email):

    user_docs = list(db.collection('Users').where('email', '==', user_email).stream())
    
    # Query for the friend document
    friend_docs = list(db.collection('Users').where('email', '==', add_email).stream())
    try:
        if not user_docs:
            return jsonify({"error": "User not found"}), 404    
        if not friend_docs:
            return jsonify({"error": "Friend not found"}), 404

        user_doc = user_docs[0]
        friend_doc = friend_docs[0]
        
        user_data = user_doc.to_dict()
        friend_data = friend_doc.to_dict()


        normalized_user_email = user_email.strip().lower()
        normalized_add_email = add_email.strip().lower()
        
        user_friends = [f.strip().lower() for f in user_data.get("friends", [])]
        friend_friends = [f.strip().lower() for f in friend_data.get("friends", [])]

        if normalized_user_email in friend_friends:
           print("friend already added")
           return jsonify({"error": "Friend already added"}), 400 
        #Check for duplicate relationship
        if normalized_add_email in user_friends:
           print("friend already added")
           return jsonify({"error": "Friend already added"}), 400
        
 
        
        user_friends.append(normalized_add_email)
        friend_friends.append(normalized_user_email)

        
        # Update the Firestore docs
        db.collection("Users").document(user_doc.id).update({"friends": user_friends})
        db.collection("Users").document(friend_doc.id).update({"friends": friend_friends})


        return jsonify({"message": "Friends added successfully"}), 200

    except Exception as e:
        print("Error adding friend:", e)
        return jsonify({"error": "An error occurred"}), 500




@app.route("/removeFriend", methods=["POST"])

def removeFriend():
    data = request.get_json()
    user_email = data["user_email"].lower()
    friend_email = data["friend_email"] 
    print(friend_email)

    user_docs = list(db.collection("Users").where("email", "==", user_email).stream())
    user_doc = user_docs[0]
    user = user_doc.to_dict()

    user_friends = user.get("friends", [])
    print(user_friends)

    user_friends.remove(friend_email)

    print(user_friends)

    db.collection("Users").document(user_doc.id).update({"friends": user_friends})

    return jsonify({"message": "success"}), 200

@app.route("/login_with_google", methods=['POST'])
def login_with_google():

    flow.redirect_uri = f"{endpoint}/callback"  # Adjust redirect URI
    auth_url, state = flow.authorization_url()
    
    # Store the state in the session for later validation
    session["oauth_state"] = state
    return jsonify({"url": auth_url})

from flask import url_for

@app.route("/callback", methods=['GET'])
def callback():
    state = session.get("oauth_state")
    
    # create a new Flow 
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": google_client,
                "client_secret": google_client_secret,
                "redirect_uris": [f"{endpoint}/callback"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        state=state
    )
    
    # Explicitly set the redirect URI to ensure it's included in the token request.
    flow.redirect_uri = f"{endpoint}/callback"
    
    # Fetch the token using the complete authorization response URL (with code, state, etc.)
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    # Verify the ID token from Google.
    idinfo = id_token.verify_oauth2_token(
        credentials.id_token, Request(), google_client
    )
    
    email = idinfo["email"]

    # Generate your JWT token (or process the user info as needed).
    payload = {
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    #redirect the user to the frontend with the token.
    return redirect(f"{frontend_url}/?token={token}")

#test
@app.route("/check_login", methods=['GET'])
def check_login():

    token = request.headers.get("Authorization")
    if token:
        token = token.replace("Bearer ", "") 
        
        try:
            # decode the secret key
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            email = payload.get('email')
            
            return jsonify({"status": "authenticated", "email": email})
        
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
    else:
        return jsonify({"status": "not_authenticated"}), 401

def verify_password(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={firebase_apikey}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        return response.json()  #return the user data
    else:
        return None  # auth failed... password incorrect

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email").lower()
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    # Verify email and password
    user_data = verify_password(email, password)

    if user_data:
        ref = db.collection("Users")
        user_list =  list(ref.where("email", "==", email).stream())
        user_info = user_list[0].to_dict()

    if user_data:
        create_local_cache()
        return jsonify({"message": f"Welcome {email}!", "user_info": user_info}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401
    

# Route to serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    
@app.route("/createAccount", methods=["POST"])
def createAccount():
    # Get text fields from the form data
    email = request.form.get("email").lower()
    country = request.form.get("location")
    age = request.form.get("age")
    gender = request.form.get("gender")
    name = request.form.get("fullName")
    bio = request.form.get("bio")

    # Get the uploaded file from the request.files
    photos = request.files.getlist("photo")
    
    print("recieved photos: ", photos)
    print("type photos: ", type(photos[0]))
    photo_array = []
    for photo in photos:
        photo_path = None
        if photo:
            filename = secure_filename(photo.filename)

            if not os.path.exists("uploads"):
                os.makedirs("uploads")
            photo_path = os.path.join("uploads", filename)
            
            photo.save(photo_path)
            photo_url = upload_image(photo_path)
        else:
            photo_url = ""

        photo_array.append(photo_url)

    User_info = {
        "email": email,
        "name": name,
        "country": country,
        "age": age,
        "gender": gender,
        "bio": bio,
        "photo_url": photo_array
    }
    
    check_agent = db.collection('Users').where('email', '==', email).where('name', '==', name).stream()

    if any(check_agent):
        return jsonify({"message": "User already exists"}), 400

    try:
        doc_ref = db.collection('Users').add(User_info)  # Ensure Firestore entry succeeds
    except Exception as e:
        print(e)
        return jsonify({"error": f"Firestore Error: {str(e)}"}), 500

    # Authentication logic
    password = request.form.get("password")
    try:
        user = auth.get_user_by_email(email)
        return jsonify({"message": "User already exists, try logging into your account", "uid": user.uid}), 200
    except auth.UserNotFoundError:
        user = auth.create_user(email=email, password=password)
        return jsonify({"message": "User created, you can now log in to your account", "uid": user.uid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    
@app.route("/getProfile", methods=["POST"])
def getProfile():
    data = request.get_json() 
    user_info = data.get("user_info", {})
    name = user_info["name"]
    email = user_info["email"]
    local = False

    if os.path.isfile("cache.json"): #if local cache
        print("using local")
        local = True
        with open("cache.json") as c:
            users = json.load(c)
        random.shuffle(users)
        random_user = users[0]
    else: # if no local cache
        print("no local")
        users = list(db.collection("Users").stream())
        random.shuffle(users)
        random_user = users[0].to_dict()

    age = random_user["age"]

    gender = random_user["gender"]


    input_to_agent = encode_input_to_binary(int(age), gender)  #Recommending only on age and gender at the moment

    response = agentResponse(input_to_agent, email, name)

    num_skipped_Users = 0
    while random_user["email"] == email or response == [0]:  
        random.shuffle(users)
        if local == False:
            random_user = users[0].to_dict()
        else:
            random_user = users[0]
        age = random_user["age"]
        gender = random_user["gender"]


        input_to_agent = encode_input_to_binary(int(age), gender)
        response = agentResponse(input_to_agent, email, name)
        num_skipped_Users += 1

        if num_skipped_Users >4 and random_user["email"] != email:
            print("forced recommendation")
            return jsonify({"recommendedProfile": random_user})

    return jsonify({"recommendedProfile": random_user})

@app.route("/updateProfile", methods=["POST"])
def updateProfile():
    print("updating profile")

    email = request.form.get("email").lower()
    country = request.form.get("location")
    age = request.form.get("age")
    gender = request.form.get("gender")
    newName = request.form.get("newName")
    oldName = request.form.get("oldName")
    bio = request.form.get("bio")
    friends = request.form.getlist("friends")

    print("adding friends: ", friends)
    
    existing_photos_str = request.form.get("existingPhotos")
    if existing_photos_str:
        try:
            existing_photos = json.loads(existing_photos_str)
        except Exception as e:
            print("Error parsing existingPhotos:", e)
            existing_photos = []
    else:
        existing_photos = []
    
    new_photos = request.files.getlist("newPhotos")
    new_photo_urls = []
    for photo in new_photos:
        if photo:
            filename = secure_filename(photo.filename)
            if not os.path.exists("uploads"):
                os.makedirs("uploads")
            photo_path = os.path.join("uploads", filename)
            photo.save(photo_path)
            uploaded_url = upload_image(photo_path)
            new_photo_urls.append(uploaded_url)
    
    # Combine existing photo URLs with new photo URLs
    photo_url = existing_photos + new_photo_urls
    

    Users = db.collection('Users').where('email', '==', email).where('name', '==', oldName).stream()
    for user in Users:
        update_data = {
            "name": newName,
            "country": country,
            "age": age,
            "gender": gender,
            "bio": bio,
            "photo_url": photo_url
        }
    
    user.reference.update(update_data)
    
    return jsonify({"message": "Profile updated!"})


@app.route("/newChat", methods=["POST"])
def newChat():
    data = request.get_json()
    reciever_email = data.get("reciever_email").lower()
    sender_email = data.get("sender_email").lower()
    message = data.get("message")

    print("sender: ", sender_email, "reciever: ",reciever_email, "message: ", message)

    # Fetch sender document
    sender_docs = list(db.collection("Users").where("email", "==", sender_email).stream())
    if not sender_docs:
        return jsonify({"error": "Sender not found"}), 404
    sender_doc = sender_docs[0]

    # Fetch receiver document
    receiver_docs = list(db.collection("Users").where("email", "==", reciever_email).stream())
    if not receiver_docs:
        return jsonify({"error": "Receiver not found"}), 404
    receiver_doc = receiver_docs[0]

    chat_id_sender = sender_email + reciever_email
    chat_id_receiver = reciever_email + sender_email

    new_message = {
        "sender": sender_email,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()  
    }

    # Update sender's chat document
    chat_ref_sender = sender_doc.reference.collection("Chats").document(chat_id_sender)
    chat_doc_sender = chat_ref_sender.get()
    if chat_doc_sender.exists:
        chat_ref_sender.update({
            "messages": firestore.ArrayUnion([new_message])
        })
    else:
        # Create a new chat document
        chat_ref_sender.set({
            "participants": [sender_email, reciever_email],
            "messages": [new_message]
        })

    # Update receiver's chat document 
    chat_ref_receiver = receiver_doc.reference.collection("Chats").document(chat_id_receiver)
    newChat = receiver_doc.to_dict().get("newChat", [])

    newChat.append(reciever_email)
    receiver_doc.reference.update({
        "newChat": firestore.ArrayUnion([sender_email])
    })
    chat_doc_receiver = chat_ref_receiver.get()
    if chat_doc_receiver.exists:
        chat_ref_receiver.update({
            "messages": firestore.ArrayUnion([new_message])
        })
    else:
        chat_ref_receiver.set({
            "participants": [sender_email, reciever_email],
            "messages": [new_message]
        })

    return jsonify({"status": "success"}), 200

@app.route("/retrieveChats", methods= ["POST"])
def retrieveChats():
    data = request.get_json()
    reciever_email = data.get("reciever_email").lower()
    sender_email = data.get("sender_email").lower()


    # Fetch sender document
    sender_docs = list(db.collection("Users").where("email", "==", sender_email).stream())
    if not sender_docs:
        return jsonify({"error": "Sender not found"}), 404
    sender_doc = sender_docs[0]

    # Fetch receiver document
    receiver_docs = list(db.collection("Users").where("email", "==", reciever_email).stream())
    if not receiver_docs:
        return jsonify({"error": "Receiver not found"}), 404
    receiver_doc = receiver_docs[0]

    chat_id = sender_email+reciever_email

    chat_ref = sender_doc.reference.collection("Chats").document(chat_id)

    sender_data = sender_doc.to_dict()
    newChat = sender_data.get("newChat", [])

    # Remove the receiver's email if it exists in the list
    if reciever_email in newChat:
        newChat.remove(reciever_email)
    else:
        pass

    # Now update the Firestore document with the modified list
    sender_doc.reference.update({"newChat": newChat})


    chat_doc = chat_ref.get()

    if not chat_ref.get():
            return jsonify({"error": "Chat not found"}), 404

    # Convert chat document to a dictionary and return it.
    chat_data = chat_doc.to_dict()
    print(chat_data)
    return jsonify(chat_data), 200


@app.route("/autoAdd", methods=["POST"])
def autoAdd():
    data = request.get_json()
    email = data["email"].lower()
    docs = list(db.collection("Users").where("email", "==", email).stream())
    if not docs:
        return jsonify({"error": "User not found"}), 404

    user_doc = docs[0]
    user_data = user_doc.to_dict()

    # Get current friend list (or initialize to empty list)
    friends = user_data.get("friends", [])
    age = user_data["age"]
    gender = user_data["gender"]
    input_binary = encode_input_to_binary(age, gender)

    # Get all users from the database
    all_users = list(db.collection("Users").stream())

    new_friends = []
    for user in all_users:
        other_data = user.to_dict()
        if other_data["email"].lower() == email:
            continue

        other_email = other_data["email"]
        other_name = other_data["name"]
        age2 = other_data["age"]
        gender2 = other_data["gender"]
        input2 = encode_input_to_binary(age2, gender=gender2)

        # Get a response based on the other user’s profile
        response1 = agentResponse(input2, email, user_data["name"])
        print("response 1", response1)
        if response1== [1]:
            
            response2 = agentResponse(input_binary, other_email, other_name)
            print("response 2", response2)
            if response2==[1]:
                print("match with: ", other_email)
                if other_email not in friends:
                    friends.append(other_email)
                    new_friends.append(other_email)
                else:
                    print("already friends")
                
                db.collection("Users").document(user.id).update({
                    "friends": firestore.ArrayUnion([email])
                })
            
  
                db.collection("Users").document(user_doc.id).update({"friends": friends})

    return jsonify({"message": "Auto friend addition complete", "friends": new_friends}), 200

@app.route('/')
def home():
    return "Testing"

if __name__ == '__main__':

    app.run(debug=True, port=5000)
