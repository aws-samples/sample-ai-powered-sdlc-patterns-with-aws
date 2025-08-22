import React, { useEffect, useRef } from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import './SwaggerViewer.css';

const SwaggerViewer = ({ spec, title, version, onClose }) => {
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
      <div className="swagger-viewer-error">
        <h3>Error Loading API Specification</h3>
        <p>Failed to parse the OpenAPI specification. Please check the format.</p>
        <button onClick={onClose} className="close-button">Close</button>
      </div>
    );
  }

  return (
    <div className="swagger-viewer-container" ref={containerRef}>
      <div className="swagger-viewer-header">
        <div className="swagger-viewer-title">
          <h3>🔧 API Specification: {title}</h3>
          <span className="swagger-viewer-version">v{version}</span>
        </div>
        <button onClick={onClose} className="swagger-viewer-close">
          ✕
        </button>
      </div>
      
      <div className="swagger-viewer-content">
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

export default SwaggerViewer;