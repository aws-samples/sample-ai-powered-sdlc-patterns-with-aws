import React, { useEffect, useRef } from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import './SimpleSwaggerViewer.css';

const SimpleSwaggerViewer = ({ spec, title, version, onClose }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    // Scroll to top when component mounts
    if (containerRef.current) {
      containerRef.current.scrollTop = 0;
    }
  }, [spec]);

  // Parse spec if it's a string
  let specObject;
  try {
    specObject = typeof spec === 'string' ? JSON.parse(spec) : spec;
  } catch (error) {
    console.error('Failed to parse OpenAPI spec:', error);
    return (
      <div className="simple-swagger-section" ref={containerRef}>
        <div className="simple-swagger-header">
          <div className="simple-swagger-title">
            <h3>❌ Error Loading API Specification</h3>
          </div>
          <button onClick={onClose} className="simple-swagger-close">
            ✕
          </button>
        </div>
        <div className="simple-swagger-content">
          <div style={{ padding: '20px', textAlign: 'center' }}>
            <p>Failed to parse the OpenAPI specification. Please check the format.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="simple-swagger-section" ref={containerRef}>
      <div className="simple-swagger-header">
        <div className="simple-swagger-title">
          <h3>🔧 API Specification: {title}</h3>
          <span className="simple-swagger-version">v{version}</span>
        </div>
        <button onClick={onClose} className="simple-swagger-close">
          ✕
        </button>
      </div>
      
      <div className="simple-swagger-content">
        <SwaggerUI
          spec={specObject}
          docExpansion="list"
          defaultModelsExpandDepth={1}
          defaultModelExpandDepth={1}
          displayOperationId={false}
          displayRequestDuration={true}
          filter={true}
          showExtensions={true}
          showCommonExtensions={true}
          tryItOutEnabled={true}
        />
      </div>
    </div>
  );
};

export default SimpleSwaggerViewer;