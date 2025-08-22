import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Box } from '@cloudscape-design/components';

const MessageRenderer = ({ content, sender }) => {
  // Custom styles for different message types
  const getMessageStyles = () => {
    const baseStyles = {
      whiteSpace: 'pre-wrap',
      lineHeight: '1.6',
      fontSize: '14px'
    };

    if (sender === 'system') {
      return {
        ...baseStyles,
        color: '#232f3e'
      };
    }

    return baseStyles;
  };

  // Custom components for markdown rendering
  const markdownComponents = {
    // Headers
    h1: ({ children }) => (
      <h1 style={{ 
        fontSize: '24px', 
        fontWeight: 'bold', 
        margin: '16px 0 12px 0',
        color: '#232f3e',
        borderBottom: '2px solid #e9ebed',
        paddingBottom: '8px'
      }}>
        {children}
      </h1>
    ),
    h2: ({ children }) => (
      <h2 style={{ 
        fontSize: '20px', 
        fontWeight: 'bold', 
        margin: '14px 0 10px 0',
        color: '#232f3e'
      }}>
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3 style={{ 
        fontSize: '18px', 
        fontWeight: 'bold', 
        margin: '12px 0 8px 0',
        color: '#232f3e'
      }}>
        {children}
      </h3>
    ),
    
    // Bold text
    strong: ({ children }) => (
      <strong style={{ 
        fontWeight: 'bold',
        color: '#232f3e'
      }}>
        {children}
      </strong>
    ),
    
    // Code blocks
    code: ({ inline, children }) => {
      if (inline) {
        return (
          <code style={{
            backgroundColor: '#f1f3f3',
            padding: '2px 4px',
            borderRadius: '3px',
            fontSize: '13px',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace'
          }}>
            {children}
          </code>
        );
      }
      
      return (
        <pre style={{
          backgroundColor: '#f1f3f3',
          padding: '12px',
          borderRadius: '6px',
          overflow: 'auto',
          margin: '8px 0',
          border: '1px solid #e9ebed'
        }}>
          <code style={{
            fontSize: '13px',
            fontFamily: 'Monaco, Consolas, "Courier New", monospace'
          }}>
            {children}
          </code>
        </pre>
      );
    },
    
    // Lists
    ul: ({ children }) => (
      <ul style={{ 
        margin: '8px 0',
        paddingLeft: '20px'
      }}>
        {children}
      </ul>
    ),
    ol: ({ children }) => (
      <ol style={{ 
        margin: '8px 0',
        paddingLeft: '20px'
      }}>
        {children}
      </ol>
    ),
    li: ({ children }) => (
      <li style={{ 
        margin: '4px 0',
        lineHeight: '1.5'
      }}>
        {children}
      </li>
    ),
    
    // Links
    a: ({ href, children }) => (
      <a 
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        style={{
          color: '#0972d3',
          textDecoration: 'none'
        }}
        onMouseOver={(e) => e.target.style.textDecoration = 'underline'}
        onMouseOut={(e) => e.target.style.textDecoration = 'none'}
      >
        {children}
      </a>
    ),
    
    // Paragraphs
    p: ({ children }) => (
      <p style={{ 
        margin: '8px 0',
        lineHeight: '1.6'
      }}>
        {children}
      </p>
    ),
    
    // Blockquotes
    blockquote: ({ children }) => (
      <blockquote style={{
        borderLeft: '4px solid #0972d3',
        paddingLeft: '12px',
        margin: '8px 0',
        fontStyle: 'italic',
        backgroundColor: '#f8f9fa',
        padding: '8px 12px',
        borderRadius: '4px'
      }}>
        {children}
      </blockquote>
    ),
    
    // Horizontal rules
    hr: () => (
      <hr style={{
        border: 'none',
        borderTop: '1px solid #e9ebed',
        margin: '16px 0'
      }} />
    )
  };

  // Ensure content is a string
  const renderContent = () => {
    if (typeof content === 'string') {
      return (
        <ReactMarkdown components={markdownComponents}>
          {content}
        </ReactMarkdown>
      );
    } else if (content === null || content === undefined) {
      return <span style={{ color: '#687078', fontStyle: 'italic' }}>[Empty message]</span>;
    } else {
      return (
        <pre style={{
          backgroundColor: '#f1f3f3',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '12px',
          overflow: 'auto'
        }}>
          {JSON.stringify(content, null, 2)}
        </pre>
      );
    }
  };

  return (
    <div style={getMessageStyles()}>
      {renderContent()}
    </div>
  );
};

export default MessageRenderer;