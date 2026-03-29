import { useState, useEffect, useRef } from 'react';
import './App.css';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  toolUsed?: string;
}

interface AgentResponse {
  response: string;
  tool_used?: string;
}

interface Supplier {
  _id?: string;
  name: string;
  category: string;
  contact: string;
  rating: number;
}

interface Bid {
  _id?: string;
  supplier_id: string;
  items: Array<{ name: string; quantity: number; unit_price: number }>;
  total_price: number;
  delivery_days: number;
  terms: string;
  status: string;
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [bids, setBids] = useState<Bid[]>([]);
  const [isDarkMode, setIsDarkMode] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load dark mode preference from localStorage
    const saved = localStorage.getItem('darkMode');
    const isDark = saved ? JSON.parse(saved) : false;
    setIsDarkMode(isDark);
    
    // Apply dark class to document
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    localStorage.setItem('darkMode', JSON.stringify(newDarkMode));
    
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  const fetchWithTimeout = async (input: RequestInfo, init?: RequestInit, timeout = 15000) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const response = await fetch(input, { ...init, signal: controller.signal });
      return response;
    } finally {
      clearTimeout(id);
    }
  };

  // Check backend connection
  useEffect(() => {
    const checkConnection = async () => {
      try {
        const response = await fetch('http://localhost:8000/');
        setIsConnected(response.ok);
      } catch (error) {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputValue,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      setErrorMessage(null);
      const response = await fetchWithTimeout('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userMessage.text }),
      }, 20000);

      if (!response) {
        throw new Error('No response from server');
      }

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const errorMessage = errorPayload?.detail || response.statusText || 'Unknown error';
        throw new Error(`Agent request failed: ${errorMessage}`);
      }

      const data: AgentResponse = await response.json();
      const agentText = data.response?.trim() || 'Agent returned no answer. Please try again.';

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: agentText,
        sender: 'agent',
        timestamp: new Date(),
        toolUsed: data.tool_used,
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error occurred';
      setErrorMessage(message);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: `Error: ${message}`,
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchWithTimeout('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      }, 20000);

      if (!response) {
        throw new Error('No response from upload endpoint');
      }

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => null);
        const errorMessage = errorPayload?.detail || response.statusText || 'Upload failed';
        throw new Error(`Failed to upload file: ${errorMessage}`);
      }

      const result = await response.json();

      const uploadMessage: Message = {
        id: Date.now().toString(),
        text: `Successfully uploaded ${file.name}. ${result.message || 'Document processed and ready for queries.'}`,
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, uploadMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: Date.now().toString(),
        text: `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        sender: 'agent',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const suggestionChips = [
    "Compare bids for office equipment",
    "Find suppliers for IT hardware",
    "Generate procurement report",
    "What are payment terms in contracts?",
    "Show me medical equipment bids",
    "Find high-rated suppliers"
  ];

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
  };

  const handleLoadSuppliers = async () => {
    try {
      setErrorMessage(null);
      const response = await fetchWithTimeout('http://localhost:8000/suppliers', undefined, 15000);
      if (!response || !response.ok) {
        throw new Error('Failed to fetch suppliers');
      }
      const data = await response.json();
      setSuppliers(data);
      setErrorMessage(`Loaded ${data.length} suppliers`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load suppliers');
    }
  };

  const handleLoadBids = async () => {
    try {
      setErrorMessage(null);
      const response = await fetchWithTimeout('http://localhost:8000/bids', undefined, 15000);
      if (!response || !response.ok) {
        throw new Error('Failed to fetch bids');
      }
      const data = await response.json();
      setBids(data);
      setErrorMessage(`Loaded ${data.length} bids`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Failed to load bids');
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Top Bar */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">ProcureAI</h1>
          <div className="flex items-center space-x-4">
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 transition-colors"
              title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDarkMode ? (
                <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-gray-700 dark:text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                </svg>
              )}
            </button>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <label className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 text-white px-4 py-2 rounded-lg cursor-pointer transition-colors">
              <span>Upload PDF</span>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Chat */}
        <div className="w-full lg:w-1/2 flex flex-col border-r border-gray-200 dark:border-gray-700">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
                <p className="text-lg mb-2">Welcome to ProcureAI!</p>
                <p>Ask me anything about procurement, bids, suppliers, or contracts.</p>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    message.sender === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-900 dark:text-white'
                  }`}
                >
                  <p className="text-sm">{message.text}</p>
                  {message.toolUsed && (
                    <p className="text-xs mt-1 opacity-75">
                      Tool: {message.toolUsed}
                    </p>
                  )}
                  <p className="text-xs mt-1 opacity-50">
                    {message.timestamp.toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 px-4 py-2 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-300">Agent is thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-200 dark:border-gray-700 p-4">
            {/* Suggestion Chips */}
            <div className="flex flex-wrap gap-2 mb-4">
              {suggestionChips.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-3 py-1 rounded-full text-sm transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>

            {/* Message Input */}
            <form onSubmit={handleSubmit} className="flex space-x-2">
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="Ask about procurement, bids, suppliers..."
                className="flex-1 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading}
              />
              <button
                type="submit"
                disabled={isLoading || !inputValue.trim()}
                className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-700 dark:hover:bg-blue-600 disabled:bg-gray-400 dark:disabled:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
              >
                Send
              </button>
            </form>
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className="w-full lg:w-1/2 p-6 overflow-y-auto bg-gray-50 dark:bg-gray-900">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-4">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Data Inspector</h2>
            <div className="flex flex-wrap gap-2 mb-4">
              <button
                onClick={handleLoadSuppliers}
                className="bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded-lg text-sm"
              >
                Load Suppliers
              </button>
              <button
                onClick={handleLoadBids}
                className="bg-yellow-600 hover:bg-yellow-700 text-white px-3 py-2 rounded-lg text-sm"
              >
                Load Bids
              </button>
            </div>
            <div className="mb-3 text-sm text-gray-700 dark:text-gray-300">
              Suppliers loaded: {suppliers.length}, Bids loaded: {bids.length}
            </div>
            {(suppliers.length > 0 || bids.length > 0) && (
              <div className="space-y-3">
                {suppliers.length > 0 && (
                  <div>
                    <h3 className="font-medium text-gray-800 dark:text-gray-200">Suppliers ({suppliers.length})</h3>
                    <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 max-h-40 overflow-y-auto">
                      {suppliers.slice(0, 5).map((s, idx) => (
                        <li key={idx}>{s.name} ({s.category}, rating {s.rating})</li>
                      ))}
                    </ul>
                  </div>
                )}
                {bids.length > 0 && (
                  <div>
                    <h3 className="font-medium text-gray-800 dark:text-gray-200">Bids ({bids.length})</h3>
                    <ul className="list-disc list-inside text-sm text-gray-700 dark:text-gray-300 max-h-40 overflow-y-auto">
                      {bids.slice(0, 5).map((b, idx) => (
                        <li key={idx}>Bid from supplier {b.supplier_id}, total ${b.total_price}, status {b.status}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            {errorMessage && (
              <div className="mt-4 text-sm text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-3 rounded">
                {errorMessage}
              </div>
            )}
          </div>

          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Results</h2>

            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <p>Agent responses will appear here</p>
                <p className="text-sm mt-2">Try asking about bids, suppliers, or contracts</p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages
                  .filter(msg => msg.sender === 'agent')
                  .slice(-3) // Show last 3 agent responses
                  .map((message) => (
                    <div key={message.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-gray-900">Agent Response</h3>
                        {message.toolUsed && (
                          <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded">
                            {message.toolUsed}
                          </span>
                        )}
                      </div>
                      <p className="text-gray-700 whitespace-pre-wrap">{message.text}</p>
                      <p className="text-xs text-gray-500 mt-2">
                        {message.timestamp.toLocaleString()}
                      </p>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;