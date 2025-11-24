/**
 * Chat Component - Handles message rendering and interactions
 */

class ChatBubble {
    constructor(message) {
        this.message = message;
    }

    render() {
        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${this.message.role}`;
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Avatar
        const avatar = document.createElement('div');
        avatar.className = `message-avatar ${this.message.role}`;
        avatar.textContent = this.message.role === 'user' ? 'ME' : 'AI';
        
        // Bubble
        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        
        // Split content by newlines and create paragraphs
        const lines = this.message.content.split('\n');
        lines.forEach((line, index) => {
            const p = document.createElement('p');
            p.textContent = line;
            p.style.minHeight = '1.2em';
            p.style.marginBottom = index === lines.length - 1 ? '0' : '4px';
            bubble.appendChild(p);
        });
        
        // Timestamp
        const time = document.createElement('span');
        time.className = 'message-time';
        const timestamp = new Date(this.message.timestamp);
        time.textContent = timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        bubble.appendChild(time);
        
        content.appendChild(avatar);
        content.appendChild(bubble);
        wrapper.appendChild(content);
        
        // Debug Section (only for model messages with tool executions)
        if (this.message.role === 'model' && this.message.toolExecutions && this.message.toolExecutions.length > 0) {
            const debugSection = this.createDebugSection();
            wrapper.appendChild(debugSection);
        }
        
        return wrapper;
    }

    createDebugSection() {
        const section = document.createElement('div');
        section.className = 'debug-section';
        
        const toggle = document.createElement('button');
        toggle.className = 'debug-toggle';
        toggle.innerHTML = `
            <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
            </svg>
            <span>View Process (${this.message.toolExecutions.length} steps)</span>
        `;
        
        const content = document.createElement('div');
        content.className = 'debug-content';
        content.style.display = 'none';
        
        this.message.toolExecutions.forEach((tool, idx) => {
            const step = document.createElement('div');
            step.className = 'debug-step';
            
            const header = document.createElement('div');
            header.className = 'debug-step-header';
            
            const name = document.createElement('span');
            name.className = 'debug-step-name';
            name.textContent = `Step ${idx + 1}: ${tool.toolName}`;
            
            const time = document.createElement('span');
            time.className = 'debug-step-time';
            const toolTime = new Date(tool.timestamp);
            time.textContent = toolTime.toLocaleTimeString();
            
            header.appendChild(name);
            header.appendChild(time);
            
            const argsDiv = document.createElement('div');
            argsDiv.innerHTML = `<span class="debug-label">Inputs: </span><span>${JSON.stringify(tool.args)}</span>`;
            argsDiv.style.marginBottom = '4px';
            
            const resultDiv = document.createElement('div');
            resultDiv.className = 'debug-result';
            resultDiv.innerHTML = `<span class="debug-label" style="display: block; margin-bottom: 4px;">Result (Data Used):</span>`;
            
            const resultPre = document.createElement('div');
            resultPre.textContent = JSON.stringify(tool.result, null, 2);
            resultDiv.appendChild(resultPre);
            
            step.appendChild(header);
            step.appendChild(argsDiv);
            step.appendChild(resultDiv);
            content.appendChild(step);
        });
        
        toggle.addEventListener('click', () => {
            const isHidden = content.style.display === 'none';
            content.style.display = isHidden ? 'block' : 'none';
            toggle.querySelector('span').textContent = isHidden 
                ? `Hide Process & Data` 
                : `View Process (${this.message.toolExecutions.length} steps)`;
            toggle.querySelector('svg').style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)';
        });
        
        section.appendChild(toggle);
        section.appendChild(content);
        
        return section;
    }
}

class TypingIndicator {
    render() {
        const wrapper = document.createElement('div');
        wrapper.className = 'typing-indicator';
        wrapper.id = 'typingIndicator';
        
        const content = document.createElement('div');
        content.className = 'typing-content';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar model';
        avatar.textContent = 'AI';
        
        const bubble = document.createElement('div');
        bubble.className = 'typing-bubble';
        
        const dots = document.createElement('div');
        dots.className = 'typing-dots';
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            dots.appendChild(dot);
        }
        
        const text = document.createElement('span');
        text.className = 'typing-text';
        text.textContent = 'Querying Firestore tools...';
        
        bubble.appendChild(dots);
        bubble.appendChild(text);
        
        content.appendChild(avatar);
        content.appendChild(bubble);
        wrapper.appendChild(content);
        
        return wrapper;
    }
}

// Export for use in app.js
window.ChatBubble = ChatBubble;
window.TypingIndicator = TypingIndicator;