import { getApiConfig } from '../config/apiConfig';
import { makeApiCall } from './api';

/**
 * Send a chat message to the chatbox endpoint
 * @param {string} message - The message content
 * @param {string} projectName - The project context (optional)
 * @returns {Promise<Object>} The chat response
 */
export const sendChatMessage = async (message, projectName = null) => {
  if (!message || typeof message !== 'string' || !message.trim()) {
    throw new Error('Message is required and must be a non-empty string');
  }

  const requestData = {
    message: message.trim(),
    ...(projectName && { project_name: projectName })
  };

  try {
    const config = getApiConfig();
    const response = await makeApiCall(
      config.endpoints.chatbox,
      {
        method: 'POST',
        body: JSON.stringify(requestData)
      }
    );

    return {
      message: response.response || response.message || 'Response received',
      timestamp: response.timestamp || new Date().toISOString()
    };
  } catch (error) {
    console.error('Chat service error:', error);
    throw new Error('Failed to send chat message');
  }
};

/**
 * Send a message to a specific SDLC phase endpoint with streaming support
 * @param {string} message - The message content
 * @param {string} phase - The SDLC phase (requirements, design, development, testing, deployment, maintenance)
 * @param {string} projectName - The project context (optional)
 * @param {string} conversationId - The conversation ID (optional)
 * @param {Function} onChunk - Callback function for streaming chunks (optional)
 * @returns {Promise<Object>} The complete chat response
 */
export const sendPhaseMessageStreaming = async (message, phase, projectName = null, conversationId = null, onChunk = null) => {
  if (!message || typeof message !== 'string' || !message.trim()) {
    throw new Error('Message is required and must be a non-empty string');
  }

  if (!phase || typeof phase !== 'string') {
    throw new Error('Phase is required and must be a valid SDLC phase');
  }

  const validPhases = ['requirements', 'design', 'development', 'testing', 'deployment', 'maintenance'];
  if (!validPhases.includes(phase)) {
    throw new Error(`Invalid phase. Must be one of: ${validPhases.join(', ')}`);
  }

  const requestData = {
    message: message.trim(),
    phase: phase,
    ...(projectName && { project_name: projectName }),
    ...(conversationId && { conversation_id: conversationId })
  };

  try {
    const config = getApiConfig();
    const streamEndpoint = `${config.endpoints.sdlc}/${phase}`;
    
    // Make streaming request with authentication headers
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache'
    };
    
    // Add authentication headers
    try {
      const authService = (await import('./authService')).default;
      
      // Add access token for general authentication
      const authHeader = await authService.getAuthHeader();
      if (authHeader) {
        headers.Authorization = authHeader;
      }
      
      // Add ID token for Amazon Q Business authentication
      const idToken = await authService.getIdToken();
      if (idToken) {
        headers['x-id-token'] = idToken;
      }
    } catch (error) {
      console.warn('Failed to get auth headers for streaming request:', error);
    }
    
    const response = await fetch(`${config.baseUrl}${streamEndpoint}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let fullResponse = '';
    let conversationId = null;
    let toolsUsed = [];
    let toolStatus = null;
    let timestamp = null;

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              // Process streaming chunk
              
              switch (data.type) {
                case 'metadata':
                  conversationId = data.conversation_id;
                  timestamp = data.timestamp;
                  if (onChunk) {
                    onChunk({
                      type: 'metadata',
                      conversationId: data.conversation_id,
                      phase: data.phase,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'content':
                  fullResponse += data.content;
                  if (onChunk) {
                    onChunk({
                      type: 'content',
                      content: data.content,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'tools':
                  toolsUsed = data.tools_used || [];
                  toolStatus = data.tool_status;
                  if (onChunk) {
                    onChunk({
                      type: 'tools',
                      toolsUsed: data.tools_used,
                      toolStatus: data.tool_status,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'diagrams':
                  if (onChunk) {
                    onChunk({
                      type: 'diagrams',
                      diagrams: data.diagrams,
                      count: data.count,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'code':
                  if (onChunk) {
                    onChunk({
                      type: 'code',
                      codeFiles: data.code_files,
                      count: data.count,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'jira':
                  if (onChunk) {
                    onChunk({
                      type: 'jira',
                      jiraDataUpdated: data.jira_data_updated,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'complete':
                  if (onChunk) {
                    onChunk({
                      type: 'complete',
                      conversationId: data.conversation_id,
                      phase: data.phase,
                      status: data.status,
                      toolsUsed: data.tools_used,
                      timestamp: data.timestamp
                    });
                  }
                  break;
                  
                case 'error':
                  throw new Error(data.error);
              }
            } catch (parseError) {
              console.warn('Failed to parse streaming data:', parseError);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }

    return {
      message: fullResponse,
      timestamp: timestamp || new Date().toISOString(),
      conversation_id: conversationId,
      tool_status: toolStatus,
      tools_used: toolsUsed,
      specification: null,
      specification_updated: false,
      canvas_posted: false,
      processing_indicator: null,
      processing_status: null,
      diagrams: null,
      diagram_generation_status: null,
      diagram_generation_error: null,
      architecture_analysis: null,
      jira_data_updated: false,
      processed_outputs: null
    };
  } catch (error) {
    console.error('Streaming phase chat service error:', error);
    throw new Error(`Failed to send streaming message to ${phase} phase`);
  }
};



/**
 * Format a chat message for display
 * @param {string} content - Message content
 * @param {string} sender - Message sender ('user' or 'system')
 * @param {string} timestamp - Message timestamp
 * @returns {Object} Formatted message object
 */
export const formatChatMessage = (content, sender, timestamp = null) => {
  // Ensure content is always a string
  let stringContent;
  
  if (typeof content === 'string') {
    stringContent = content;
  } else if (content === null || content === undefined) {
    stringContent = '[Empty message]';
  } else if (typeof content === 'object') {
    // Handle objects that might have text/onClick properties
    if (content.text && typeof content.text === 'string') {
      stringContent = content.text;
    } else {
      console.warn('formatChatMessage received object content:', content);
      stringContent = JSON.stringify(content, null, 2);
    }
  } else {
    // Handle other types (numbers, booleans, etc.)
    stringContent = String(content);
  }
  
  return {
    id: Date.now().toString() + Math.random().toString(36).substring(2, 11),
    content: stringContent.trim() || '[Empty message]',
    sender: sender,
    timestamp: timestamp || new Date().toISOString()
  };
};