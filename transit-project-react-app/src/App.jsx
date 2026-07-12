import { useState, useEffect } from 'react'
import './App.css'

const API_STATUS_URL = 'http://127.0.0.1:8000/api/status/'

function App() {
  const [connectionStatus, setConnectionStatus] = useState('checking')
  const [apiMessage, setApiMessage] = useState('')
  const [apiResponse, setApiResponse] = useState(null)

  // Verify connection to DRF backend
  const checkConnection = async () => {
    setConnectionStatus('checking')
    try {
      const res = await fetch(API_STATUS_URL)
      if (res.ok) {
        const data = await res.json()
        setConnectionStatus('online')
        setApiMessage(data.message || 'DRF connected successfully!')
        setApiResponse(data)
      } else {
        setConnectionStatus('offline')
        setApiMessage('Backend server returned an error response.')
      }
    } catch (err) {
      console.error(err)
      setConnectionStatus('offline')
      setApiMessage('Could not reach backend server at http://127.0.0.1:8000/')
    }
  }

  useEffect(() => {
    checkConnection()
  }, [])

  return (
    <div className="starter-container">
      <header className="starter-header">
        <div className="status-indicator">
          <span className={`status-dot ${connectionStatus}`}></span>
          <span className="status-text">
            {connectionStatus === 'online' ? 'Backend Connected' : 
             connectionStatus === 'offline' ? 'Backend Offline' : 'Connecting to API...'}
          </span>
        </div>
      </header>

      <main className="starter-main">
        <h1 className="starter-title">Django + React</h1>
        <p className="starter-subtitle">
          Your boilerplate setup is ready. Customize this project to build your application.
        </p>

        <div className="card-container">
          <div className="connection-card">
            <h3>API Connection Test</h3>
            <p className="connection-desc">
              Verifies if your React app is successfully talking to your Django REST API server via CORS.
            </p>
            
            <div className={`response-box status-${connectionStatus}`}>
              {connectionStatus === 'checking' && <p>Pinging backend...</p>}
              {connectionStatus === 'online' && (
                <div>
                  <p className="success-msg">✓ DRF Connection Online</p>
                  <p className="api-msg">"{apiMessage}"</p>
                  {apiResponse && (
                    <pre className="json-output">
                      {JSON.stringify(apiResponse, null, 2)}
                    </pre>
                  )}
                </div>
              )}
              {connectionStatus === 'offline' && (
                <div>
                  <p className="error-msg">✗ Connection Failed</p>
                  <p className="api-msg">{apiMessage}</p>
                  <p className="tip-msg">
                    💡 Check that your server is running with <code>python manage.py runserver</code>
                  </p>
                </div>
              )}
            </div>

            <button onClick={checkConnection} className="btn-test">
              Test Connection again
            </button>
          </div>
        </div>
      </main>

      <footer className="starter-footer">
        <p>Edit <code>src/App.jsx</code> to build your interface</p>
      </footer>
    </div>
  )
}

export default App
