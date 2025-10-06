document.addEventListener('DOMContentLoaded', () => {
    const chatbox = document.querySelector('.chatbox');
    const chatInput = document.querySelector('.chat-input textarea');
    const sendChatBtn = document.querySelector('.chat-input span');

    let userMessage;

    const createChatLi = (message, className) => {
        const chatLi = document.createElement('li');
        chatLi.classList.add('chat', className);
        let chatContent = className === 'outgoing' ? `<p>${message}</p>` : `<span class="material-icons">smart_toy</span><p>${message}</p>`;
        chatLi.innerHTML = chatContent;
        return chatLi;
    }

    const generateResponse = (incomingChatLi) => {
        const API_URL = '/chat';
        const messageElement = incomingChatLi.querySelector('p');

        // Display loading animation
        messageElement.textContent = '...';

        fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: userMessage })
        }).then(res => res.json()).then(data => {
            messageElement.textContent = data.response;
        }).catch((error) => {
            messageElement.textContent = "Oops! Something went wrong. Please try again.";
        }).finally(() => chatbox.scrollTo(0, chatbox.scrollHeight));
    }

    const handleChat = () => {
        userMessage = chatInput.value.trim();
        if(!userMessage) return;
        chatInput.value = "";

        chatbox.appendChild(createChatLi(userMessage, "outgoing"));
        chatbox.scrollTo(0, chatbox.scrollHeight);

        setTimeout(() => {
            const incomingChatLi = createChatLi("Thinking...", "incoming");
            chatbox.appendChild(incomingChatLi);
            chatbox.scrollTo(0, chatbox.scrollHeight);
            generateResponse(incomingChatLi);
        }, 600);
    }

    sendChatBtn.addEventListener('click', handleChat);
    chatInput.addEventListener('keydown', (e) => {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleChat();
        }
    });
});
