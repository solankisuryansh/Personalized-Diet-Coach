 async function sendMessage() {
    const input = document.getElementById("userInput");
    const message = input.value.trim();
    if (!message) return;
  
    const chatbox = document.getElementById("chatbox");
    chatbox.innerHTML += `<div class="message user">${message}</div>`;
    input.value = "";
  
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message })
    });
  
    const data = await response.json();
    chatbox.innerHTML += `<div class="message bot">${data.reply}</div>`;
    chatbox.scrollTop = chatbox.scrollHeight;
  }
  