import { useState, useRef, useEffect } from 'react';
import {
  Container,
  Header,
  Box,
  Button,
  SpaceBetween,
  Spinner,
  Alert
} from '@cloudscape-design/components';
import { sendChatMessage, formatChatMessage } from '../../services/chatService';
import MessageRenderer from './MessageRenderer';

import useAutoResize from '../../hooks/useAutoResize';
import './ChatBox.css';

const ChatBox = ({ projectName }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useAutoResize(inputValue);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = formatChatMessage(inputValue.trim(), 'user');

    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendChatMessage(userMessage.content, projectName);
      
      const systemMessage = formatChatMessage(
        response.message,
        'system',
        response.timestamp
      );

      setMessages(prev => [...prev, systemMessage]);
    } catch (err) {
      setError('Failed to send message. Please try again.');
      console.error('Chat error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessage = (message) => (
    <div
      key={message.id}
      style={{
        marginBottom: '12px',
        padding: '16px',
        backgroundColor: message.sender === 'user' ? '#e3f2fd' : '#ffffff',
        borderRadius: '8px',
        border: '1px solid #e0e0e0',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}
    >
      <Box fontSize="body-s" color="text-label" margin={{ bottom: 'xs' }}>
        {message.sender === 'user' ? '👤 You' : '🤖 Assistant'}
      </Box>
      <MessageRenderer content={message.content} sender={message.sender} />
    </div>
  );

  return (
    <Container
      header={
        <Header variant="h3">
          Chat Assistant
        </Header>
      }
    >
      <SpaceBetween direction="vertical" size="s">

        
        {/* Chat Messages */}
        <div
          className="chat-container"
          style={{
            height: '500px',
            overflowY: 'auto',
            border: '1px solid #e9ebed',
            borderRadius: '12px',
            backgroundColor: '#f8f9fa',
            padding: '16px'
          }}
        >
          {messages.length === 0 ? (
            <Box textAlign="center" color="text-label" padding="l">
              Start a conversation about your project
            </Box>
          ) : (
            <SpaceBetween direction="vertical" size="xs">
              {messages.map(renderMessage)}
              <div ref={messagesEndRef} />
            </SpaceBetween>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <Alert type="error" dismissible onDismiss={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Input Area */}
        <div className="chat-input-container">
          <div className="chat-input-wrapper">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
              disabled={isLoading}
              className="chat-input-textarea"
              rows={1}
            />
          </div>
          <Button
            variant="primary"
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            iconName={isLoading ? undefined : 'angle-right'}
            className="chat-send-button"
          >
            {isLoading ? <Spinner size="small" /> : 'Send'}
          </Button>
        </div>
      </SpaceBetween>
    </Container>
  );
};

export default ChatBox;