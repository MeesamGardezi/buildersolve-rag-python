/**
 * Main Application - BuilderSolve Agent
 */

// Configuration
const WS_URL = 'ws://localhost:8000/ws/chat';
const API_BASE_URL = 'http://localhost:8000/api';

// State
let websocket = null;
let currentJob = null;
let messages = [];
let isConnected = false;

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const jobContext = document.getElementById('jobContext');
const jobVisualizer = document.getElementById('jobVisualizer');
const mobileJobBadge = document.getElementById('mobileJobBadge');

// Initialize app
function init() {
    console.log('🚀 Initializing BuilderSolve Agent...');
    
    // Setup event listeners
    chatForm.addEventListener('submit', handleSendMessage);
    
    // Connect to WebSocket
    connectWebSocket();
    
    // Keep connection alive
    setInterval(() => {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000); // Ping every 30 seconds
}

// WebSocket Connection
function connectWebSocket() {
    console.log('🔌 Connecting to WebSocket...');
    
    websocket = new WebSocket(WS_URL);
    
    websocket.onopen = () => {
        console.log('✅ WebSocket connected');
        isConnected = true;
        updateConnectionStatus(true);
    };
    
    websocket.onclose = () => {
        console.log('❌ WebSocket disconnected');
        isConnected = false;
        updateConnectionStatus(false);
        
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
            console.log('🔄 Attempting to reconnect...');
            connectWebSocket();
        }, 3000);
    };
    
    websocket.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
    };
    
    websocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    console.log('📨 Received:', data.type);
    
    switch (data.type) {
        case 'welcome':
            currentJob = data.job;
            updateJobUI();
            addMessage({
                id: 'welcome',
                role: 'model',
                content: data.message,
                timestamp: new Date()
            });
            break;
        
        case 'response':
            removeTypingIndicator();
            addMessage({
                id: Date.now().toString(),
                role: 'model',
                content: data.text,
                timestamp: new Date(),
                toolExecutions: data.toolExecutions || []
            });
            break;
        
        case 'job_update':
            currentJob = data.job;
            updateJobUI();
            break;
        
        case 'typing':
            if (data.isTyping) {
                showTypingIndicator();
            } else {
                removeTypingIndicator();
            }
            break;
        
        case 'error':
            removeTypingIndicator();
            addMessage({
                id: Date.now().toString(),
                role: 'model',
                content: data.message || 'An error occurred. Please try again.',
                timestamp: new Date()
            });
            break;
        
        case 'pong':
            // Connection keep-alive response
            break;
        
        default:
            console.warn('Unknown message type:', data.type);
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    if (connected) {
        sendButton.disabled = false;
        messageInput.disabled = false;
        messageInput.placeholder = "Ask about job costs, milestones, or switch jobs (e.g. 'Show me the Smith job')...";
    } else {
        sendButton.disabled = true;
        messageInput.disabled = true;
        messageInput.placeholder = "Connecting to server...";
    }
}

// Update Job UI
function updateJobUI() {
    if (!currentJob) return;
    
    const visualizer = new JobVisualizer(currentJob);
    
    // Update sidebar
    if (jobContext) {
        jobContext.innerHTML = visualizer.renderJobContext();
    }
    
    if (jobVisualizer) {
        jobVisualizer.innerHTML = visualizer.render();
    }
    
    // Update mobile badge
    if (mobileJobBadge) {
        mobileJobBadge.textContent = currentJob.jobPrefix || 'JOB';
    }
}

// Add message to chat
function addMessage(message) {
    messages.push(message);
    
    const bubble = new ChatBubble(message);
    chatMessages.appendChild(bubble.render());
    
    // Scroll to bottom
    scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
    // Remove existing indicator if any
    removeTypingIndicator();
    
    const indicator = new TypingIndicator();
    chatMessages.appendChild(indicator.render());
    
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const existing = document.getElementById('typingIndicator');
    if (existing) {
        existing.remove();
    }
}

// Scroll to bottom of chat
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Handle send message
function handleSendMessage(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message || !isConnected) return;
    
    // Add user message to UI
    addMessage({
        id: Date.now().toString(),
        role: 'user',
        content: message,
        timestamp: new Date()
    });
    
    // Clear input
    messageInput.value = '';
    
    // Prepare history for API (simplified - only send role and text)
    const history = messages
        .filter(m => m.role !== 'system')
        .map(m => ({
            role: m.role,
            parts: [{ text: m.content }]
        }));
    
    // Send to WebSocket
    websocket.send(JSON.stringify({
        type: 'message',
        message: message,
        history: history.slice(-10), // Send last 10 messages for context
        currentJobId: currentJob?.documentId
    }));
    
    // Show typing indicator
    showTypingIndicator();
}

// Fallback: REST API (if WebSocket is not available)
async function sendMessageViaREST(message, history) {
    try {
        const response = await fetch(`${API_BASE_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                history: history,
                currentJobId: currentJob?.documentId
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        removeTypingIndicator();
        
        addMessage({
            id: Date.now().toString(),
            role: 'model',
            content: data.text,
            timestamp: new Date(),
            toolExecutions: data.toolExecutions || []
        });
        
        if (data.switchedJobId && data.switchedJobId !== currentJob?.documentId) {
            // Fetch new job data
            const jobResponse = await fetch(`${API_BASE_URL}/job/${data.switchedJobId}`);
            if (jobResponse.ok) {
                currentJob = await jobResponse.json();
                updateJobUI();
            }
        }
        
    } catch (error) {
        console.error('❌ REST API Error:', error);
        removeTypingIndicator();
        addMessage({
            id: Date.now().toString(),
            role: 'model',
            content: 'I encountered an error connecting to the server. Please check your connection and try again.',
            timestamp: new Date()
        });
    }
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Export for debugging
window.app = {
    messages,
    currentJob,
    isConnected,
    sendMessageViaREST
};