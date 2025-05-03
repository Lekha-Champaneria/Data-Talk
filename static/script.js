class ChatManager {
    constructor() {
        this.currentChatId = this.generateChatId();
        this.setupEventListeners();
        this.loadChatHistory();
    }

    generateChatId() {
        return `chat_${Date.now()}`;
    }

    setupEventListeners() {
        document.getElementById('chatForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        document.getElementById('newChat').addEventListener('click', () => {
            this.startNewChat();
        });

        document.getElementById('upload').addEventListener('change', (event) => {
            this.handleFileUpload(event);
        });

        document.getElementById('chatForm').querySelector('button[type="button"]').addEventListener('click', () => {
            this.startVoiceRecognition(); // Start voice recognition
        });
        

        document.addEventListener('DOMContentLoaded', () => {
            const chatManager = new ChatManager();
        });
    }

    setupSpeechRecognition() {
        // Check if the browser supports the Web Speech API
        if ('webkitSpeechRecognition' in window) {
            this.recognition = new webkitSpeechRecognition();
            this.recognition.continuous = false; // Stop after one utterance
            this.recognition.interimResults = false; // Do not show interim results
            this.recognition.lang = 'en-US'; // Default language

            // Handle transcription result
            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('userInput').value = transcript; // Populate input with transcribed text
            };

            // Handle errors
            this.recognition.onerror = (event) => {
                console.error("Speech recognition error:", event.error);
                alert("Error during speech recognition: " + event.error);
            };

            // Stop indicator when speech recognition ends
            this.recognition.onend = () => {
                console.log("Speech recognition ended.");
            };
        } else {
            alert("Your browser does not support speech recognition.");
        }
    }
    startVoiceRecognition() {
        if (this.recognition) {
            this.recognition.start(); // Start speech recognition
            console.log("Voice recognition started...");
        }
    }

    async loadChatHistory() {
        const historyPanel = document.getElementById('chatHistory');
        historyPanel.innerHTML = ''; // Clear previous history
    
        try {
            // Fetch chat history from the API
            const response = await fetch('/chats'); // Replace with the correct API URL if hosted remotely
            const chatList = await response.json();
    
            // Populate the chat history panel with data from the API
            chatList.forEach(chat => {
                console.log()
                const historyItem = document.createElement('div');
                historyItem.className = 'history-item';
    
                // Display the first message or a placeholder text
                historyItem.textContent = chat.content || 'New Chat';
    
                // Add a click listener to load the chat
                historyItem.addEventListener('click', () => this.loadChat(chat.chatId));
                
                historyPanel.appendChild(historyItem);
            });
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    async fetchChatFromAPI(chatId) {
        try {
            const response = await fetch(`/chat-history?chat_id=${chatId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch chat history: ${response.statusText}`);
            }
            const chatData = await response.json();
            return chatData; // Return the fetched data
        } catch (error) {
            console.error("Error fetching chat data:", error);
            return { messages: [] }; // Return an empty chat if the API call fails
        }
    }

    async loadChat(chatId) {
        this.currentChatId = chatId;
        const chat = await this.fetchChatFromAPI(chatId);
        // const chat = JSON.parse(localStorage.getItem(chatId));
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = '';

        chat.messages.forEach(msg => {
            this.displayMessage(msg.content, msg.type, msg.feedback);
        });
    }

    handleFileUpload(event) {
        console.log("Uploading file...");
        const file = event.target.files ? event.target.files[0] : null;
        
        if (file) {
            document.querySelector('.loading-indicator').classList.remove('hidden');
          // Prepare FormData
          const formData = new FormData();
          formData.append("file", file);
      
          // Send file to API
          fetch("/upload", {
            method: "POST",
            body: formData,
          })
          .then(response => {
            if (response.ok) {
              return response.json();
            } else {
              console.error("Error uploading file:", response.statusText);
              throw new Error("File upload failed");
            }
          })
          .then(data => {
            console.log("File uploaded successfully:", data);
            window.location.reload();
          })
          .catch(error => {
            console.error("Error uploading file:", error);
          })
          .finally(() => {
            document.querySelector('.loading-indicator').classList.add('hidden');
          });
        }
      }
      

    startNewChat() {
        this.currentChatId = this.generateChatId();
        document.getElementById('chatMessages').innerHTML = '';
        // localStorage.setItem(this.currentChatId, JSON.stringify({
        //     messages: []
        // }));
        this.loadChatHistory();
    }

    async sendMessage() {
        const input = document.getElementById('userInput');
        const message = input.value.trim();
        if (!message) return;

        // Display user message
        this.displayMessage(message, 'user');
        this.saveMessage(message, 'user');
        input.value = '';

        // Show loading indicator
        document.querySelector('.loading-indicator').classList.remove('hidden');

        console.log("currentChatId : ", this.currentChatId)

        try {
            const response = await fetch('/getresponse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message,
                    currentChatId: this.currentChatId })
            });

            const data = await response.json();
            // res.data.response

            // Parse the JSON response string to an object
            
            console.log("response data : ", data)
            this.displayMessage(data.response, 'bot');
            this.saveMessage(data.response, 'bot');
            document.querySelector('.loading-indicator').classList.add('hidden');
            
            // try {
            //     const parsedResponse = JSON.parse(data.response);
            
            //     // If parsing succeeds, handle the parsed response
            //     this.displayMessage(parsedResponse.response_message, 'bot');
            //     this.saveMessage(parsedResponse.response_message, 'bot');
            // } catch (error) {
            //     // If parsing fails, assume the response is plain text
            //     console.error('Error parsing JSON:', error);
            //     this.displayMessage(data.response, 'bot');
            //     this.saveMessage(data.response, 'bot');
            // } finally {
            //     // Hide loading indicator
            //     document.querySelector('.loading-indicator').classList.add('hidden');
            // }


        } catch (error) {
            console.error('Error:', error);
            document.querySelector('.loading-indicator').classList.add('hidden');
        }

        // try {
        //     const response = await fetch('/chat', {
        //         method: 'POST',
        //         headers: {
        //             'Content-Type': 'application/json'
        //         },
        //         body: JSON.stringify({ message })
        //     });

        //     const data = await response.json();
            
        //     // Hide loading indicator
        //     document.querySelector('.loading-indicator').classList.add('hidden');

        //     // Display bot response
        //     this.displayMessage(data.response, 'bot');
        //     this.saveMessage(data.response, 'bot');
        // } catch (error) {
        //     console.error('Error:', error);
        //     document.querySelector('.loading-indicator').classList.add('hidden');
        // }
    }

    displayMessage(content, type, feedback = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;
        messageDiv.textContent = content;
        messageDiv.innerHTML = content.replace(/\n/g, '<br>');

        if (type === 'bot') {
            const feedbackDiv = document.createElement('div');
            feedbackDiv.className = 'feedback';
        
            const buttons = [
                { text: '👍', value: 'positive' },
                { text: '👎', value: 'negative' }
            ];

            buttons.forEach(btn => {
                const button = document.createElement('button');
                button.textContent = btn.text;
                button.setAttribute('data-value', btn.value);
                if (feedback === btn.value) {
                    button.classList.add('active');
                }
                button.addEventListener('click', (e) => {
                    // Remove active class from all buttons in this feedback group
                    feedbackDiv.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                    // Add active class to clicked button
                    button.classList.add('active');
                    this.handleFeedback(content, btn.value);
                });
                feedbackDiv.appendChild(button);
            });

            messageDiv.appendChild(feedbackDiv);
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    

    async saveMessage(content, type, feedback = null) {
        // const chat = JSON.parse(localStorage.getItem(this.currentChatId) || '{"messages": []}');
        const chat = await this.fetchChatFromAPI(this.currentChatId);
        // chat.messages.push({ content, type, feedback });
        // localStorage.setItem(this.currentChatId, JSON.stringify(chat));
        this.loadChatHistory();
    }

    

    async handleFeedback(message, feedbackValue) {
        try {
            const response = await fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message,
                    feedback: feedbackValue
                })
            });

            if (response.ok) {
                // Update the message in local storage with feedback
                const chat = await this.fetchChatFromAPI(this.currentChatId);
                // const chat = JSON.parse(localStorage.getItem(this.currentChatId));
                const messageIndex = chat.messages.findIndex(msg => msg.content === message);
                if (messageIndex !== -1) {
                    chat.messages[messageIndex].feedback = feedbackValue;
                    // localStorage.setItem(this.currentChatId, JSON.stringify(chat));
                }
            } else {
                console.error('Failed to send feedback');
            }
        } catch (error) {
            console.error('Error sending feedback:', error);
        }
    }
}

// Initialize chat manager when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatManager();
});

