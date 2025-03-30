<script>
    import { onMount, onDestroy } from 'svelte';
    import { afterUpdate } from 'svelte';

    
   // const baseEndpoint = import.meta.env.VITE_BACKEND_URL;
  
    // User info for both login and account creation
    let email = "";
    let password = "";
    let fullName = "";
    let age = "";
    let gender = "";
    let location = "";
    let bio = "";
    let insta_handle = "";

    let photo0 = ""
    let photo1 = "";
    let photo2 = "";
    let photo3 = "";

    let newPhoto = "";

    let interval;
    
    
    let message = "";
    
    let token = localStorage.getItem("token");
    let user_info = {}
    let recommended_profile_info =  {}

    // UI states
    let loggedin = false;
    let isLoading = false;
    let showMainPage = false;
    let showProfilePage = false;
    let showFriendsPage = false;
    let showChatScreen = false;
    let showAutoAdd = false;

    let newName = ""; ///when the user changes their name, we need to first pass the old name and then the new name so we can access their row in firebase and delete it

    let reciever_chat_email = "";
    let chat_message = "";
    let chatCont;

    let scroll = false
    let profileChanged = false
    let allMessages = [];

    let autoAddedFriends = [];
    let autoAddActivated = false;

    // Using the same backend endpoint 
    const baseEndpoint = "http://127.0.0.1:5000"; // change to  http://127.0.0.1:5000 for local or https://aodating.onrender.com for staging
    
  
    function handlePhoto0Upload(event) {
        photo0= event.target.files[0];
        console.log("test: ", photo0)

  }

  function handlePhoto1Upload(event) {
        photo1= event.target.files[0];
  }

  function handlePhoto2Upload(event) {
        photo2= event.target.files[0];
  }

  function handlePhoto3Upload(event) {
        photo3= event.target.files[0];
  }

  function removePhoto(url) {
    user_info["photo_url"] = user_info["photo_url"].filter(num => num !== url);
    console.log("removing url: ", url);
    console.log("new array: ", user_info["photo_url"]);
}

  function scrollToBottom() {
    setTimeout(() => {
      chatCont.scrollTop = chatCont.scrollHeight;
  }, 500);
}
  async function createAccount() {
  //create a FormData object so we can pass through image 

  let photo_array = [photo0, photo1, photo2, photo3]
  console.log("photo_array: ", photo_array)
  const formData = new FormData();
  formData.append("email", email);
  formData.append("password", password);
  formData.append("fullName", fullName);
  formData.append("age", age);
  formData.append("gender", gender);
  formData.append("location", location);
  formData.append("bio", bio);
  formData.append("handle", insta_handle);
  photo_array.forEach(photo => {
  formData.append("photo", photo);
});



  isLoading = true;
  try {
    const response = await fetch(`${baseEndpoint}/createAccount`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    message = data.message;
    if (response.status === 200) {
      getProfile();
    }
  } catch (error) {
    message = "Error creating account.";
  } finally {
    isLoading = false;
  }
}

async function updateProfile() {
  //create a FormData object so we can pass through image 

  const formData = new FormData();
  formData.append("email", email);
  formData.append("password", password);
  formData.append("newName", newName);
  formData.append("oldName", fullName)
  formData.append("age", age);
  formData.append("gender", gender);
  formData.append("location", location);
  formData.append("bio", bio);
  formData.append("friends", user_info["friends"]);
  formData.append("existingPhotos", JSON.stringify(user_info["photo_url"]));
  formData.append("newPhotos", photo0);

  isLoading = true;
  try {
    const response = await fetch(`${baseEndpoint}/updateProfile`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    message = data.message;
    if (response.status === 200) {
      console.log("Updated profile");
    }
  } catch (error) {
    message = "Error updating profile.";
  } finally {
    isLoading = false;
    getUserData()
  }
}
  
    async function login() {
      isLoading = true;
      try {
        const response = await fetch(`${baseEndpoint}/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const data = await response.json();
        message = data.message;
        console.log("data: ", data.user_info)
        user_info  = data.user_info
        fullName = data.user_info.name
        gender = data.user_info.gender
        age = data.user_info.age
        bio = data.user_info.bio
        location = data.user_info.country
        
        // user_info = data.user_info;
        // console.log("user_info: ", user_info)

        if (response.status === 200) {
          loggedin = true;
          getProfile()
        }
      } catch (error) {
        message = "Error logging in.";
      } finally {
        isLoading = false;
        showMainPage = true;
        console.log("")

      }
    }

    async function getProfile() {
        isLoading = true
        try {
            const response = await fetch(`${baseEndpoint}/getProfile`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({user_info}),
            })

            recommended_profile_info = await response.json();
            recommended_profile_info = recommended_profile_info.recommendedProfile
            isLoading = false
        } catch (error) {
        console.log("error: ", error)
        isLoading = false
    }

        }
    async function trainAgent(type) {
        let label = []
        if (type == "pos")  {
            label= [1]
        }else{
            label = [0]
        }

        console.log("training: ", label)

        email = email.toLowerCase();
        const data = {
            info: recommended_profile_info, 
            label: label,
            uid: fullName+ email, 
            email: email
        };

        try {
            const response = await fetch(`${baseEndpoint}/trainAgent`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            const result = await response.json(); 
            console.log(result);
            
        } catch (error) {
            console.error("Error training agent:", error);
        }
        getProfile(); 
    }

    async function getUserData() {  
        const data = {
          email: email
        }
        const response = await fetch(`${baseEndpoint}/getUserData`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        })
        const result = await response.json();

        user_info = result["user_info"]

        console.log("user info: ", user_info)

    }
    async function autoAdd() {
      
      isLoading = true
      const data =  {
        email:email
      }
      const response = await fetch (`${baseEndpoint}/autoAdd`, {
        method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
      })
      const result = await response.json();
      autoAddedFriends = result["friends"]
      if (response.status == 200)   {
        isLoading = false
        autoAddActivated= true
      } 
    }

    async function retrieveChats(scroll=false) {
      if (showChatScreen) { 
        const data = {
          reciever_email: reciever_chat_email,
          sender_email: email
        };

        const response = await fetch(`${baseEndpoint}/retrieveChats`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });

        const result = await response.json();

        if (!result){
          allMessages = []
        }
        else  {
          allMessages = result.messages;

        }

        if (response.status==200) {

          if (scroll){

            scrollToBottom()
          }
        }

      }}

      async function newChat() {
        const data = {
          sender_email: email,
          reciever_email: reciever_chat_email,
          message: chat_message,
        }
        const response = await fetch(`${baseEndpoint}/newChat`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(data),
        })
      }

      async function removeFriend() {
        const data =  {
          user_email: email,
          friend_email: reciever_chat_email,
        }

        const response = await fetch(`${baseEndpoint}/removeFriend`, {
          method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        })
        console.log("response: ", response.json())
        
      }

    
      onMount(()=>{
      //   if (token) {
      //   loggedin = true;
      //   showMainPage = true;
      //   showFriendsPage = false;
      // } 
        retrieveChats()

        interval = setInterval(retrieveChats, 1000)
        return () => clearInterval(interval);
      })

  </script>
  
  <main>

    {#if !loggedin}
      <div id="login">
        <h1 id="rainbow_header">Dating App</h1>
        <div class="auth-section">
          <h2>Create Account</h2>
          <label>
            Email:
            <input type="email" bind:value={email} />
          </label>
          <label>
            Password:
            <input type="password" bind:value={password} />
          </label>
          <label>
            Full Name:
            <input type="text" bind:value={fullName} placeholder="Your name" />
          </label>
          <label>
            Age:
            <input type="number" bind:value={age} min="18" placeholder="18" />
          </label>
          <label>
            Gender:
            <select bind:value={gender}>
              <option value="" disabled selected>Select Gender</option>
              <option>Male</option>
              <option>Female</option>
              <option>Non-binary</option>
              <option>Other</option>
            </select>
          </label>
          <label>
            Location:
            <input type="text" bind:value={location} placeholder="City, Country" />
          </label>
          <label>
            Bio:
            <textarea bind:value={bio} placeholder="Tell us about yourself"></textarea>
          </label>
          <label>
            Instagram Handle (So we can see what you like):
            <textarea bind:value={insta_handle} placeholder="handle"></textarea>
          </label>
          <button on:click={createAccount}>Create Account</button>
          <label>
            ADD Some Photos:
            <input type="file" accept="image/*" on:change={handlePhoto0Upload} />
            <input type="file" accept="image/*" on:change={handlePhoto1Upload} />
            <input type="file" accept="image/*" on:change={handlePhoto2Upload} />
            <input type="file" accept="image/*" on:change={handlePhoto3Upload} />
          </label>
        </div>
        <div class="auth-section">
          <h2>Login</h2>
          <label>
            Email:
            <input type="email" bind:value={email} />
          </label>
          <label>
            Password:
            <input type="password" bind:value={password} />
          </label>
          <button on:click={login}>Login</button>
        </div>
        {#if message}
          <p class="message">{message}</p>
        {/if}
        {#if isLoading}
          <p>Loading...</p>
        {/if}
      </div>
    {/if}

    {#if loggedin}
    <nav>
        <button on:click={() => {
          email = "";
          password = "";
          message = "";
          loggedin = false;
          isLoading = false;
          showMainPage = false;
          showProfilePage = false;
          showFriendsPage = false;
          showChatScreen = false;
          showAutoAdd = false;
        }}>
          Logout
        </button>
        <button on:click={() => {
          showProfilePage = true;
          showMainPage = false;
          showFriendsPage = false;
          showChatScreen = false;
          showAutoAdd = false;
          getUserData()
          profileChanged = true
        }}>
          Go to Profile
        </button>
        <button on:click={() => {
          
            showProfilePage = false;
            showMainPage = true;
            showFriendsPage = false;
            showChatScreen = false;
            showAutoAdd = false;
            getUserData()
 
          }}>
            Main
        </button>

        <button on:click={() => {
          showProfilePage = false;
          showMainPage = false;
          showFriendsPage = true;
          showChatScreen = false;
          showAutoAdd = false;
          getUserData();
        }}>
          Friends
          {#if user_info.newChat}
          {#if user_info.newChat.length > 0}
            <span class="new-chat-icon">({user_info.newChat.length})</span>
          {/if}
      {/if}
        </button>

        <button on:click={() => {
          showProfilePage = false;
          showMainPage = false;
          showFriendsPage = false;
          showChatScreen = false;
          showAutoAdd = true;
          autoAddActivated= false;
          autoAddedFriends = [];  // hide previously added
          getUserData();
        }}>
          Personal Agent

        </button>

      </nav>
    {/if}
  
    {#if showMainPage&&loggedin}
      <div id="home">
        <h1>Welcome, {fullName || email}!</h1>
        <p>
          Ready to find your match? Start browsing profiles and connect with interesting people!
        </p>

        <div class="recommended-profile">
          <h2>Recommended Profile:</h2>
          <p>Name: {recommended_profile_info.name}</p>
          <p>Gender: {recommended_profile_info.gender}</p>
          <p>Age: {recommended_profile_info.age}</p>
          <p>Bio: {recommended_profile_info.bio}</p>
          
          {#if recommended_profile_info && recommended_profile_info.photo_url}
            {#each recommended_profile_info.photo_url as url}
              <img id="profile_images" src={url} alt="Profile Photo" />
            {/each}
          {/if}
        </div>
        
        

        <button on:click={()=>
            trainAgent("pos")
            }>Add friend/ recommend</button>
        <button on:click={()=>
            trainAgent("neg")
            }>Recommend Less</button>
      </div>
    {/if}
    {#if showProfilePage && loggedin}
    <div class="profile-section">
      <h1>Your profile</h1>
      <label>Email:  {email}</label>
      <label>
        Full Name:
        <label>{fullName}<label>
      </label>
      <label>
        Age:
        <input type="number" bind:value={age} min="18" placeholder="18" />
      </label>
      <label>
        Gender:
        <select bind:value={gender}>
          <option value="" disabled selected>Select Gender</option>
          <option>Male</option>
          <option>Female</option>
          <option>Non-binary</option>
          <option>Other</option>
        </select>
      </label>
      <label>
        Location:
        <input type="text" bind:value={location} placeholder="City, Country" />
      </label>
      <label>
        Bio:
        <textarea bind:value={bio} placeholder="Tell us about yourself"></textarea>
      </label>

      <label>
        Photos:
        {#if user_info["photo_url"]}
          {#each user_info["photo_url"] as url}
          <img id="profile_images" src={url} alt="Profile Photo" />
          <button on:click={()=>
            removePhoto(url)}>Delete</button>
          {/each}
        {/if}

        Upload a new photo:
        {#if !user_info.photo_url || user_info.photo_url.length < 5}
        <input type="file" accept="image/*" on:change={handlePhoto0Upload} />
      {/if}
      

      </label>
      
      <button on:click={()=>{
      updateProfile()
      profileChanged = false}
      }>Update Profile</button>
    </div>
  {/if}
  
  
  {#if showFriendsPage}
  <div class="friends-container">
    <h1>Friends</h1>
    {#if user_info["friends"]}
      {#each user_info["friends"] as friend }
        <div class="friend-item">
          {#if user_info.newChat}
          {#if user_info.newChat.includes(friend)}
            <span class="new-label">New messages</span>
          {/if}
        {/if}
          <button
            class="friend-button"
            on:click={() => {
              showChatScreen = true;
              showFriendsPage = false;
              reciever_chat_email = friend;
              allMessages = [];
              scroll = true;
              retrieveChats(scroll);
            }}>
            {friend}
          </button>
        </div>
      {/each}
    {/if}
  </div>
{/if}
  {#if showChatScreen}
  <div class="chat-container">
    <h1>Chat with {reciever_chat_email}</h1>
    <button on:click={removeFriend}>Remove Friend</button>
    <div class="chat-messages" bind:this={chatCont}>
      {#each allMessages as message}
        <p
          class="chat-message"
          class:sent={message.sender === email.toLowerCase()}
          class:received={message.sender !== email.toLowerCase()}
        >
          {message.message}
        </p>
      {/each}
    </div>
    <label>
      Message:
      <input type="text" bind:value={chat_message} placeholder="Your chat"/>
    </label>
    <button on:click={newChat}>Send</button>
  </div>
{/if}


{#if showAutoAdd}
  <h1>Activate your personal Agent to find profile automatically</h1>
  <button on:click={autoAdd}>Engage </button>
  {#if autoAddActivated}
  {#if autoAddedFriends.length !== 0}
    <h1>We found these friends for you: </h1>
    {#each autoAddedFriends as newFriends}
      <li>{newFriends}</li>
    {/each}
    {:else}<h1>We couldn't find any new friends for you, please try again later</h1>
  {/if}
  {/if}
{/if}
    {#if isLoading}
    <div class="spinner-container">
        {#if isLoading&&showMainPage}
            <p> We're looking for the perfect profile!</p>
        {/if}

        <div class="spinner"></div>
    </div>
{/if}


  </main>
  
