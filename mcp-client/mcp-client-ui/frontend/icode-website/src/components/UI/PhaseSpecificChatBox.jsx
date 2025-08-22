import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import {
  Container,
  Header,
  Box,
  Button,
  SpaceBetween,
  Spinner,
  Alert
} from '@cloudscape-design/components';
import { sendPhaseMessageStreaming, formatChatMessage } from '../../services/chatService';
import MessageRenderer from './MessageRenderer';
import useAutoResize from '../../hooks/useAutoResize';
import './ChatBox.css';

const PhaseSpecificChatBox = forwardRef(({
  phase,
  projectName,
  onSpecificationUpdate,
  onConversationIdUpdate,
  onCodeGenerated,
  onJiraDataUpdated,
  onDiagramGenerated,
  onPdfGenerated
}, ref) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStage, setLoadingStage] = useState('');
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useAutoResize(inputValue);

  // Expose sendMessage method to parent components
  useImperativeHandle(ref, () => ({
    sendMessage: (message) => {
      if (message && typeof message === 'string' && message.trim()) {
        setInputValue(message.trim());
        // Use setTimeout to ensure the input value is set before sending
        setTimeout(() => {
          handleSendMessage();
        }, 0);
      }
    }
  }), []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversation history when phase changes
  useEffect(() => {
    loadPhaseConversation();
  }, [phase]);

  const loadPhaseConversation = async () => {
    // This will load existing conversation for the phase
    // For now, we'll reset the conversation when switching phases
    setMessages([]);
    setConversationId(null);
    setError(null);

    // Notify parent that conversation ID is cleared for this phase
    if (onConversationIdUpdate) {
      onConversationIdUpdate(phase, null);
    }

    // Add welcome message for the phase
    const welcomeMessage = getPhaseWelcomeMessage(phase);
    setMessages([{
      id: `welcome-${phase}`,
      content: welcomeMessage,
      sender: 'system',
      timestamp: new Date().toISOString()
    }]);
  };

  const getPhaseWelcomeMessage = (phase) => {
    const messages = {
      requirements: "Welcome to the Requirements phase! I'll help you gather and document comprehensive project requirements. Let's start by discussing your project's functional and non-functional requirements.",
      design: "Welcome to the Design phase! I'll assist you in creating system architecture and design documents. I can help with architectural patterns, system diagrams, and design decisions.",
      development: "Welcome to the Development phase! I'll guide you through coding standards, technology stack decisions, and implementation approaches for your project.",
      testing: "Welcome to the Testing phase! I'll help you develop testing strategies, create test plans, and establish quality assurance criteria for your project.",
      deployment: "Welcome to the Deployment phase! I'll assist with deployment planning, CI/CD setup, and release strategies for your project.",
      maintenance: "Welcome to the Maintenance phase! I'll help you establish maintenance procedures, monitoring requirements, and ongoing support processes."
    };

    return messages[phase] || `Welcome to the ${phase} phase! How can I assist you today?`;
  };

  const getInitialLoadingMessage = (phase) => {
    // Simple initial message while we wait for the backend to tell us what's happening
    return '🤖 Analyzing your request...';
  };





  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = formatChatMessage(inputValue.trim(), 'user');

    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    const messageContent = inputValue.trim();
    setInputValue('');
    setIsLoading(true);
    setStreamingContent('');
    setIsStreaming(false);

    setLoadingStage('🤖 Analyzing your request...');
    setError(null);

    try {
      // Use streaming response
      setIsStreaming(true);
      let fullResponse = '';
      let currentConversationId = conversationId;
      let toolsUsed = [];
      let toolStatus = null;

      // Add a placeholder message for streaming content
      const streamingMessageId = `streaming-${Date.now()}`;
      const streamingMessage = {
        id: streamingMessageId,
        content: '',
        sender: 'system',
        timestamp: new Date().toISOString(),
        isStreaming: true
      };
      setMessages(prev => [...prev, streamingMessage]);

      const response = await sendPhaseMessageStreaming(
        messageContent,
        phase,
        projectName,
        conversationId,
        (chunk) => {
          switch (chunk.type) {
            case 'metadata':
              currentConversationId = chunk.conversationId;
              setConversationId(chunk.conversationId);
              if (onConversationIdUpdate) {
                onConversationIdUpdate(phase, chunk.conversationId);
              }
              break;

            case 'content':
              fullResponse += chunk.content;
              setStreamingContent(fullResponse);
              // Update the streaming message in real-time
              setMessages(prev => prev.map(msg =>
                msg.id === streamingMessageId
                  ? { ...msg, content: fullResponse }
                  : msg
              ));
              break;

            case 'tools':
              toolsUsed = chunk.toolsUsed || [];
              toolStatus = chunk.toolStatus;
              if (chunk.toolStatus) {
                setLoadingStage(chunk.toolStatus === 'processing' ? '🔧 Using tools...' : '✅ Tools completed!');
              }
              break;

            case 'diagrams':
              if (chunk.diagrams && chunk.count > 0) {
                if (onDiagramGenerated) {
                  setTimeout(() => {
                    onDiagramGenerated(phase, currentConversationId);
                  }, 500);
                }
              }
              break;

            case 'code':
              if (chunk.codeFiles && chunk.count > 0) {
                if (onCodeGenerated) {
                  setTimeout(() => {
                    onCodeGenerated(phase, currentConversationId);
                  }, 500);
                }
              }
              break;

            case 'jira':
              if (chunk.jiraDataUpdated || chunk.jira_data_updated) {
                setLoadingStage('📋 Epics generated! Refreshing panel...');
                if (onJiraDataUpdated) {
                  setTimeout(() => {
                    onJiraDataUpdated(phase, currentConversationId);
                  }, 500);
                }
              }
              break;

            case 'complete':
              // Response completed
              setIsStreaming(false);
              setLoadingStage('✅ Response completed!');
              break;

            case 'error':
              setError(`Streaming error: ${chunk.error}`);
              setIsStreaming(false);
              break;
          }
        }
      );

      // Finalize the streaming message
      setMessages(prev => prev.map(msg =>
        msg.id === streamingMessageId
          ? { ...msg, content: fullResponse, isStreaming: false }
          : msg
      ));

      // Process the complete response for additional features
      const processedResponse = {
        ...response,
        message: fullResponse,
        tools_used: toolsUsed,
        tool_status: toolStatus
      };

      await handleResponseProcessing(processedResponse, currentConversationId);

    } catch (err) {
      setError(`Failed to send message to ${phase} endpoint. Please try again.`);
      console.error('Chat error:', err);
    } finally {
      // Show success message briefly before clearing
      setTimeout(() => {
        if (loadingStage.includes('✅') || loadingStage.includes('completed')) {
          setTimeout(() => {
            setIsLoading(false);
            setLoadingStage('');
            setIsStreaming(false);
          }, 2000);
        } else {
          setIsLoading(false);
          setLoadingStage('');
          setIsStreaming(false);
        }
      }, 100);
    }
  };

  const handleResponseProcessing = async (response, responseConversationId) => {
    // Debug: Log the full response to see what we're getting
    // Process response data

    // Update loading stage based on backend tool status - show completion status
    if (response.tool_status) {
      // Tool status received
      // Convert to completion status
      const completionStatus = response.tool_status.replace('...', ' completed! ✅');
      setLoadingStage(completionStatus);
    } else if (response.tools_used && response.tools_used.length > 0) {
      setLoadingStage('✅ Processing completed!');
    } else {
      // No tool status or tools_used in response
      setLoadingStage('✅ Request processed successfully!');
    }

    // Ensure message content is always a string
    let messageContent = response.message;
    if (typeof messageContent !== 'string') {
      console.warn('Received non-string message content:', messageContent);
      messageContent = JSON.stringify(messageContent);
    }

    // Streaming mode always adds messages during the streaming process
    // No need to add system message here as it's already handled in streaming

    // Update conversation ID if provided
    if (responseConversationId) {
      setConversationId(responseConversationId);
      // Notify parent component of the conversation ID
      if (onConversationIdUpdate) {
        onConversationIdUpdate(phase, responseConversationId);
      }
    }

    // Enhanced code generation detection
    const hasCodeGeneration = (
      (response.tools_used && response.tools_used.includes('generate_architecture_code')) ||
      (response.processed_outputs && response.processed_outputs.code_files && response.processed_outputs.code_files.length > 0) ||
      // Detect code blocks in the response content
      (messageContent && (
        messageContent.includes('```') ||
        messageContent.includes('terraform') ||
        messageContent.includes('cloudformation') ||
        messageContent.includes('dockerfile') ||
        /\.(py|js|ts|yaml|yml|json|tf)[\s\n]/.test(messageContent)
      ))
    );

    if (hasCodeGeneration) {
      if (onCodeGenerated) {
        setTimeout(() => {
          onCodeGenerated(phase, responseConversationId || conversationId);
        }, 1000);
      }
    }

    // Enhanced diagram generation detection
    const hasDiagramGeneration = (
      (response.tools_used && response.tools_used.includes('create_architecture_diagram')) ||
      (response.processed_outputs && response.processed_outputs.diagrams && response.processed_outputs.diagrams.length > 0) ||
      (response.diagrams && response.diagrams.length > 0) ||
      // Detect diagram URLs in the response content
      (messageContent && (
        (messageContent.includes('https://') && (
          messageContent.includes('.png') ||
          messageContent.includes('.jpg') ||
          messageContent.includes('.svg') ||
          messageContent.includes('diagram') ||
          messageContent.includes('architecture') ||
          messageContent.includes('s3.amazonaws.com')
        )) ||
        /(?:generated|created|uploaded|saved).*(?:diagram|architecture|visual)/i.test(messageContent) ||
        messageContent.includes('![') // Markdown image syntax
      ))
    );

    if (hasDiagramGeneration) {
      if (onDiagramGenerated) {
        setTimeout(() => {
          onDiagramGenerated(phase, responseConversationId || conversationId);
        }, 1000);
      }
    }

    // Enhanced PDF generation detection
    const hasPdfGeneration = (
      (response.tools_used && response.tools_used.includes('generate_documentation')) ||
      (response.processed_outputs && response.processed_outputs.pdfs && response.processed_outputs.pdfs.length > 0) ||
      // Detect PDF-related keywords in the response content
      (messageContent && (
        /(?:generated|created|uploaded|saved).*(?:pdf|document|specification)/i.test(messageContent) ||
        messageContent.includes('.pdf') ||
        messageContent.includes('PDF') ||
        messageContent.includes('documentation')
      ))
    );

    if (hasPdfGeneration) {
      if (onPdfGenerated) {
        setTimeout(() => {
          onPdfGenerated(phase, responseConversationId || conversationId);
        }, 1000);
      }
    }

    // Update loading stage with success message based on actual results
    if (response.tools_used && response.tools_used.length > 0) {
      const successMessages = {
        'createJiraIssue': '✅ Jira tickets created successfully!',
        'create_architecture_diagram': '✅ Architecture diagrams generated!',
        'generate_architecture_code': '✅ Code generation completed!',
        'domain_analysis': '✅ Domain analysis completed!',
        'analyze_architecture': '✅ Architecture analysis completed!',
        'estimate_architecture_cost': '✅ Cost estimation completed!',
        'query_aws_knowledge': '✅ AWS knowledge retrieved!',
        'generate_documentation': '✅ Documentation generated!',
        'mcp_amazon_q_business_retrieve': '✅ Information retrieved successfully!',
      };

      for (const tool of response.tools_used) {
        if (successMessages[tool]) {
          setLoadingStage(successMessages[tool]);
          break;
        }
      }

      if (!response.tools_used.some(tool => successMessages[tool])) {
        setLoadingStage('✅ Processing completed successfully!');
      }
    }

    // Handle Jira data updates detection

    const hasJiraUpdate = response.jira_data_updated || (
      (response.tools_used && response.tools_used.includes('createJiraIssue')) ||
      (response.processed_outputs && (
        (response.processed_outputs.jira_tickets && response.processed_outputs.jira_tickets.length > 0) ||
        (response.processed_outputs.epics && response.processed_outputs.epics.length > 0)
      )) ||
      (messageContent && messageContent.includes('api.atlassian.com/ex/jira'))
    );

    if (hasJiraUpdate) {
      if (onJiraDataUpdated) {
        onJiraDataUpdated(phase, responseConversationId || conversationId);
      }
    }

    // Handle automatic specification updates
    if (response.specification_updated && response.specification && onSpecificationUpdate) {
      let enhancedSpecification = { ...response.specification };
      if (response.diagrams && response.diagrams.length > 0) {
        enhancedSpecification.diagrams = response.diagrams;
      }

      onSpecificationUpdate(phase, enhancedSpecification);

      if (response.canvas_posted) {
        const specMessage = formatChatMessage(
          `📋 ${phase.charAt(0).toUpperCase() + phase.slice(1)} specification has been generated and is now available above.`,
          'system',
          new Date().toISOString()
        );
        setMessages(prev => [...prev, specMessage]);
      }

      if (response.diagrams && response.diagrams.length > 0) {
        const diagramMessage = formatChatMessage(
          `🖼️ Generated ${response.diagrams.length} diagram(s) for your ${phase} phase. Check the diagrams section above to view them.`,
          'system',
          new Date().toISOString()
        );
        setMessages(prev => [...prev, diagramMessage]);
      }

      if (response.architecture_analysis) {
        const analysisMessage = formatChatMessage(
          `🔍 Architecture analysis completed! The analysis has been included in my response above.`,
          'system',
          new Date().toISOString()
        );
        setMessages(prev => [...prev, analysisMessage]);
      }
    }

    // Handle processing status updates (final status)
    if (response.processing_status) {
      let statusContent = response.processing_status;
      if (typeof statusContent !== 'string') {
        console.warn('Received non-string processing status:', statusContent);
        statusContent = JSON.stringify(statusContent);
      }

      const statusMessage = formatChatMessage(
        statusContent,
        'status',
        new Date().toISOString()
      );
      setMessages(prev => [...prev, statusMessage]);
    }
  };

  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessage = (message) => {
    const getMessageStyle = (sender, isStreaming = false) => {
      const baseStyle = {
        position: 'relative'
      };

      switch (sender) {
        case 'user':
          return {
            ...baseStyle,
            backgroundColor: '#e3f2fd',
            borderLeft: '4px solid #2196f3'
          };
        case 'processing':
          return {
            ...baseStyle,
            backgroundColor: '#fff3e0',
            borderLeft: '4px solid #ff9800',
            fontStyle: 'italic',
            animation: 'pulse 2s infinite'
          };
        case 'status':
          return {
            ...baseStyle,
            backgroundColor: '#e8f5e8',
            borderLeft: '4px solid #4caf50',
            fontWeight: '500'
          };
        default:
          return {
            ...baseStyle,
            backgroundColor: isStreaming ? '#f0f8ff' : '#f5f5f5',
            borderLeft: isStreaming ? '4px solid #4CAF50' : '4px solid #9e9e9e',
            ...(isStreaming && {
              '::after': {
                content: '""',
                position: 'absolute',
                right: '10px',
                top: '50%',
                transform: 'translateY(-50%)',
                width: '8px',
                height: '8px',
                backgroundColor: '#4CAF50',
                borderRadius: '50%',
                animation: 'pulse 1s infinite'
              }
            })
          };
      }
    };

    const getSenderLabel = (sender, isStreaming = false) => {
      switch (sender) {
        case 'user':
          return 'You';
        case 'processing':
          return '🔄 Processing';
        case 'status':
          return '📋 System';
        default:
          return isStreaming ? '🤖 Assistant (streaming...)' : 'Assistant';
      }
    };

    return (
      <div
        key={message.id}
        style={{
          marginBottom: '12px',
          padding: '16px',
          borderRadius: '8px',
          border: '1px solid #e0e0e0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          ...getMessageStyle(message.sender, message.isStreaming)
        }}
      >
        <Box fontSize="body-s" color="text-label" margin={{ bottom: 'xs' }}>
          {getSenderLabel(message.sender, message.isStreaming)}
          {message.isStreaming && (
            <span style={{ marginLeft: '8px', color: '#4CAF50' }}>
              ●
            </span>
          )}
        </Box>
        <MessageRenderer content={message.content} sender={message.sender} />
        {message.isStreaming && !message.content && (
          <div style={{ fontStyle: 'italic', color: '#666', marginTop: '8px' }}>
            Waiting for response...
          </div>
        )}
      </div>
    );
  };

  const getPhaseDisplayName = (phase) => {
    return phase.charAt(0).toUpperCase() + phase.slice(1);
  };

  return (
    <>
      <style>
        {`
          @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
          }
          
          @keyframes slideIn {
            0% { 
              opacity: 0; 
              transform: translateY(-10px); 
            }
            100% { 
              opacity: 1; 
              transform: translateY(0); 
            }
          }
          
          @keyframes streamingPulse {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
          }
          
          .loading-stage-indicator {
            animation: slideIn 0.3s ease-out;
          }
          
          .loading-stage-success {
            background-color: #e8f5e8 !important;
            border-color: #4caf50 !important;
          }
          
          .streaming-indicator {
            animation: streamingPulse 1.5s infinite;
          }
          
          .streaming-message {
            background: linear-gradient(90deg, #f0f8ff 0%, #e3f2fd 50%, #f0f8ff 100%);
            background-size: 200% 100%;
            animation: streamingGradient 2s ease-in-out infinite;
          }
          
          @keyframes streamingGradient {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
        `}
      </style>
      <Container
        header={
          <Header variant="h3">
            {getPhaseDisplayName(phase)} Assistant
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="s">


          {/* Chat Messages */}
          <div
            className="chat-container"
            style={{
              height: 'calc(100vh - 500px)',
              minHeight: '600px',
              maxHeight: '100vh',
              overflowY: 'auto',
              border: '1px solid #e9ebed',
              borderRadius: '12px',
              backgroundColor: '#f8f9fa',
              padding: '16px'
            }}
          >
            {messages.length === 0 ? (
              <Box textAlign="center" color="text-label" padding="l">
                <Spinner size="large" />
                <Box margin={{ top: 's' }}>
                  Loading {phase} conversation...
                </Box>
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

          {/* Loading Stage Indicator */}
          {isLoading && loadingStage && (
            <Box
              padding="s"
              textAlign="center"
              className={`loading-stage-indicator ${loadingStage.includes('✅') ? 'loading-stage-success' : ''} ${isStreaming ? 'streaming-indicator' : ''}`}
              style={{
                backgroundColor: loadingStage.includes('✅') ? '#e8f5e8' : (isStreaming ? '#f0f8ff' : '#f0f8ff'),
                border: `1px solid ${loadingStage.includes('✅') ? '#4caf50' : (isStreaming ? '#4CAF50' : '#e3f2fd')}`,
                borderRadius: '8px',
                marginBottom: '12px'
              }}
            >
              <SpaceBetween direction="horizontal" size="xs" alignItems="center">
                {loadingStage.includes('✅') ? (
                  <Box fontSize="body-s" color="text-status-success">✅</Box>
                ) : isStreaming ? (
                  <Box fontSize="body-s" color="text-status-info" className="streaming-indicator">🌊</Box>
                ) : (
                  <Spinner size="small" />
                )}
                <Box
                  fontSize="body-s"
                  color={loadingStage.includes('✅') ? 'text-status-success' : (isStreaming ? 'text-status-info' : 'text-body-secondary')}
                  style={{ fontWeight: loadingStage.includes('✅') ? '500' : 'normal' }}
                >
                  {isStreaming && !loadingStage.includes('✅') ? `🌊 ${loadingStage}` : loadingStage}
                </Box>
              </SpaceBetween>
            </Box>
          )}

          {/* Input Area */}
          <div className="chat-input-container">
            <div className="chat-input-wrapper">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder={isLoading ? 'Processing your request...' : `Ask about ${phase}... (Press Enter to send, Shift+Enter for new line)`}
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
    </>
  );
});

PhaseSpecificChatBox.displayName = 'PhaseSpecificChatBox';

export default PhaseSpecificChatBox;