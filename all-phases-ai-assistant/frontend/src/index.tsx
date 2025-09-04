import { Amplify } from 'aws-amplify';
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { AMPLIFY_CONFIG } from './config/aws-config';
import './index.css';

// Configure AWS Amplify
Amplify.configure(AMPLIFY_CONFIG);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);