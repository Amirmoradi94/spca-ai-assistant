/**
 * SPCA Chat Widget
 * Embeddable chat widget for the SPCA website
 */

(function() {
    'use strict';

    // Default configuration
    const DEFAULT_CONFIG = {
        apiEndpoint: 'http://localhost:8000/api/v1/chat',
        theme: {
            primaryColor: '#0066cc',
            headerBg: '#0066cc',
        },
        position: 'bottom-right',
        language: 'auto', // 'auto', 'en', or 'fr'
        showGreeting: true,
        showSuggestions: true,
    };

    // I18n translations
    const translations = {
        en: null, // Will be loaded dynamically
        fr: null,
    };

    class SPCAChatWidget {
        constructor(config = {}) {
            this.config = { ...DEFAULT_CONFIG, ...config };
            this.sessionId = null;
            this.isOpen = false;
            this.messages = [];
            this.language = this.detectLanguage();
            this.isTyping = false;

            this.init();
        }

        detectLanguage() {
            // Auto-detect from config
            if (this.config.language !== 'auto') {
                return this.config.language;
            }

            // Detect from URL
            const path = window.location.pathname;
            if (path.includes('/fr/') || path.includes('/fr-')) {
                return 'fr';
            }

            // Detect from HTML lang attribute
            const htmlLang = document.documentElement.lang;
            if (htmlLang && htmlLang.startsWith('fr')) {
                return 'fr';
            }

            // Default to English
            return 'en';
        }

        async init() {
            await this.loadTranslations();
            this.createWidget();
            this.attachEventListeners();
            await this.createSession();

            if (this.config.showGreeting) {
                this.showGreeting();
            }
        }

        async loadTranslations() {
            // In production, these would be bundled or fetched
            // For now, we'll use inline translations
            translations.en = {
                widget: {
                    title: 'SPCA Assistant',
                    greeting: 'Hello! I can help you find information about SPCA services and animals for adoption. How can I assist you today?',
                    placeholder: 'Type your message...',
                    send: 'Send',
                    close: 'Close',
                    typing: 'Typing...',
                    error: 'Sorry, something went wrong. Please try again.',
                },
                suggestions: {
                    questions: [
                        'What dogs are available for adoption?',
                        'What are the adoption fees?',
                        'What are your opening hours?',
                    ],
                },
            };

            translations.fr = {
                widget: {
                    title: 'Assistant SPCA',
                    greeting: 'Bonjour! Je peux vous aider à trouver des informations sur les services de la SPCA et les animaux à adopter. Comment puis-je vous aider?',
                    placeholder: 'Tapez votre message...',
                    send: 'Envoyer',
                    close: 'Fermer',
                    typing: 'En train d\'écrire...',
                    error: 'Désolé, une erreur s\'est produite. Veuillez réessayer.',
                },
                suggestions: {
                    questions: [
                        'Quels chiens sont disponibles pour adoption?',
                        'Quels sont les frais d\'adoption?',
                        'Quelles sont vos heures d\'ouverture?',
                    ],
                },
            };
        }

        t(key) {
            const keys = key.split('.');
            let value = translations[this.language];
            for (const k of keys) {
                value = value?.[k];
            }
            return value || key;
        }

        createWidget() {
            // Create container
            const container = document.createElement('div');
            container.id = 'spca-chat-widget';
            container.innerHTML = `
                <button class="spca-chat-toggle" aria-label="${this.t('widget.title')}" role="button">
                    <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                    </svg>
                </button>
                <div class="spca-chat-window" hidden>
                    <div class="spca-chat-header">
                        <h3>${this.t('widget.title')}</h3>
                        <button class="spca-close-btn" aria-label="${this.t('widget.close')}">&times;</button>
                    </div>
                    <div class="spca-chat-messages"></div>
                    <div class="spca-chat-input">
                        <textarea
                            placeholder="${this.t('widget.placeholder')}"
                            rows="1"
                            aria-label="Message input"
                        ></textarea>
                        <button class="spca-send-btn" aria-label="${this.t('widget.send')}">
                            <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;

            document.body.appendChild(container);

            // Inject styles
            this.injectStyles();

            // Cache DOM elements
            this.elements = {
                toggle: container.querySelector('.spca-chat-toggle'),
                window: container.querySelector('.spca-chat-window'),
                messages: container.querySelector('.spca-chat-messages'),
                input: container.querySelector('textarea'),
                sendBtn: container.querySelector('.spca-send-btn'),
                closeBtn: container.querySelector('.spca-close-btn'),
            };
        }

        injectStyles() {
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = this.config.stylesUrl || 'widget-styles.css';
            document.head.appendChild(link);

            // Apply theme colors
            const style = document.createElement('style');
            style.textContent = `
                :root {
                    --spca-primary: ${this.config.theme.primaryColor};
                    --spca-primary-dark: ${this.darkenColor(this.config.theme.primaryColor)};
                }
            `;
            document.head.appendChild(style);
        }

        darkenColor(color) {
            // Simple color darkening
            const hex = color.replace('#', '');
            const r = Math.max(0, parseInt(hex.substr(0, 2), 16) - 30);
            const g = Math.max(0, parseInt(hex.substr(2, 2), 16) - 30);
            const b = Math.max(0, parseInt(hex.substr(4, 2), 16) - 30);
            return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
        }

        attachEventListeners() {
            this.elements.toggle.addEventListener('click', () => this.toggleChat());
            this.elements.closeBtn.addEventListener('click', () => this.closeChat());
            this.elements.sendBtn.addEventListener('click', () => this.sendMessage());

            this.elements.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            this.elements.input.addEventListener('input', () => {
                this.elements.input.style.height = 'auto';
                this.elements.input.style.height = this.elements.input.scrollHeight + 'px';
            });
        }

        toggleChat() {
            if (this.isOpen) {
                this.closeChat();
            } else {
                this.openChat();
            }
        }

        openChat() {
            this.isOpen = true;
            this.elements.window.hidden = false;
            this.elements.window.classList.add('opening');
            this.elements.toggle.classList.add('open');
            this.elements.input.focus();

            setTimeout(() => {
                this.elements.window.classList.remove('opening');
            }, 300);
        }

        closeChat() {
            this.isOpen = false;
            this.elements.window.classList.add('closing');
            this.elements.toggle.classList.remove('open');

            setTimeout(() => {
                this.elements.window.hidden = true;
                this.elements.window.classList.remove('closing');
            }, 300);
        }

        showGreeting() {
            const greeting = document.createElement('div');
            greeting.className = 'spca-greeting';
            greeting.innerHTML = `
                <p>${this.t('widget.greeting')}</p>
                ${this.config.showSuggestions ? this.renderSuggestions() : ''}
            `;
            this.elements.messages.appendChild(greeting);
        }

        renderSuggestions() {
            const questions = this.t('suggestions.questions') || [];
            const buttons = questions.map(q =>
                `<button class="spca-suggestion-btn" data-question="${this.escapeHtml(q)}">${this.escapeHtml(q)}</button>`
            ).join('');

            setTimeout(() => {
                document.querySelectorAll('.spca-suggestion-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        this.elements.input.value = btn.dataset.question;
                        this.sendMessage();
                    });
                });
            }, 100);

            return `<div class="spca-suggestions">${buttons}</div>`;
        }

        async createSession() {
            try {
                const response = await fetch(`${this.config.apiEndpoint}/session?language=${this.language}`, {
                    method: 'POST',
                });
                const data = await response.json();
                this.sessionId = data.session_id;
            } catch (error) {
                console.error('Failed to create session:', error);
            }
        }

        async sendMessage() {
            const message = this.elements.input.value.trim();
            if (!message || this.isTyping) return;

            // Add user message to UI
            this.addMessage('user', message);
            this.elements.input.value = '';
            this.elements.input.style.height = 'auto';

            // Show typing indicator
            this.showTyping();

            try {
                const response = await fetch(this.config.apiEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: this.sessionId,
                        language: this.language,
                    }),
                });

                const data = await response.json();

                this.hideTyping();

                if (data.response) {
                    this.addMessage('assistant', data.response);

                    // Update suggested questions if provided
                    if (data.suggested_questions && data.suggested_questions.length > 0) {
                        this.showSuggestedQuestions(data.suggested_questions);
                    }
                } else {
                    this.addMessage('assistant', this.t('widget.error'));
                }

            } catch (error) {
                console.error('Failed to send message:', error);
                this.hideTyping();
                this.addMessage('assistant', this.t('widget.error'));
            }
        }

        addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `spca-message ${role}`;
            messageDiv.innerHTML = `
                <div class="spca-message-bubble">${this.escapeHtml(content)}</div>
                <div class="spca-message-time">${this.formatTime(new Date())}</div>
            `;
            this.elements.messages.appendChild(messageDiv);
            this.scrollToBottom();

            this.messages.push({ role, content, timestamp: new Date() });
        }

        showTyping() {
            this.isTyping = true;
            const typingDiv = document.createElement('div');
            typingDiv.className = 'spca-message assistant';
            typingDiv.innerHTML = `
                <div class="spca-typing">
                    <div class="spca-typing-dot"></div>
                    <div class="spca-typing-dot"></div>
                    <div class="spca-typing-dot"></div>
                </div>
            `;
            typingDiv.id = 'spca-typing-indicator';
            this.elements.messages.appendChild(typingDiv);
            this.scrollToBottom();
        }

        hideTyping() {
            this.isTyping = false;
            const typingIndicator = document.getElementById('spca-typing-indicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        showSuggestedQuestions(questions) {
            const suggestionsDiv = document.createElement('div');
            suggestionsDiv.className = 'spca-suggestions';
            suggestionsDiv.innerHTML = questions.slice(0, 3).map(q =>
                `<button class="spca-suggestion-btn" data-question="${this.escapeHtml(q)}">${this.escapeHtml(q)}</button>`
            ).join('');
            this.elements.messages.appendChild(suggestionsDiv);

            suggestionsDiv.querySelectorAll('.spca-suggestion-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    this.elements.input.value = btn.dataset.question;
                    this.sendMessage();
                });
            });

            this.scrollToBottom();
        }

        scrollToBottom() {
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }

        formatTime(date) {
            return date.toLocaleTimeString(this.language === 'fr' ? 'fr-CA' : 'en-US', {
                hour: '2-digit',
                minute: '2-digit'
            });
        }

        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    }

    // Auto-initialize or expose for manual init
    window.SPCAChatWidget = SPCAChatWidget;

    // Auto-init if script has data-auto-init
    const script = document.currentScript;
    if (script && script.dataset.autoInit === 'true') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                new SPCAChatWidget(window.SPCA_CHAT_CONFIG || {});
            });
        } else {
            new SPCAChatWidget(window.SPCA_CHAT_CONFIG || {});
        }
    }
})();
