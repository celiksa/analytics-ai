import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Database, Loader2, ChevronDown, BarChart } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid'; 

interface DatabaseInfo {
  name: string;
  schemas: string[];
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  visualization?: string;
  error?: boolean;
}

export default function Chat() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
    const [selectedDb, setSelectedDb] = useState<string>('');
    const [selectedSchema, setSelectedSchema] = useState<string>('');
    const [isConnected, setIsConnected] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const ws = useRef<WebSocket | null>(null);
    const [sessionId, setSessionId] = useState<string>('');

      // Initialize session ID and load history on mount
    useEffect(() => {
      // Try to get existing session ID from localStorage
      let existingSessionId = localStorage.getItem('chatSessionId');
      if (!existingSessionId) {
        existingSessionId = uuidv4();
        localStorage.setItem('chatSessionId', existingSessionId);
      }
      setSessionId(existingSessionId);
      
      // Load chat history for this session
      if (existingSessionId) {
        fetch(`http://localhost:8001/chat/history/${existingSessionId}`)
          .then(res => res.json())
          .then(historyMessages => {
            setMessages(historyMessages.map((msg: any) => ({
              role: msg.role,
              content: msg.content,
              visualization: msg.visualization
            })));
          })
          .catch(err => console.error('Failed to load chat history:', err));
      }
    }, []);

    useEffect(() => {
        fetch('http://localhost:8001/databases')
          .then(res => res.json())
          .then(data => setDatabases(data))
          .catch(err => console.error('Failed to fetch databases:', err));
      }, []);
    
      
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const connectWebSocket = () => {
    if (!selectedDb || !selectedSchema || !sessionId) return;
    ws.current = new WebSocket(
      `ws://localhost:8001/ws/chat?` + 
      `db=${selectedDb}&` +
      `schema=${selectedSchema}&` +
      `session_id=${sessionId}`
    );
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'message') {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.content }
        ]);
      } else if (data.type === 'visualization') {
        setMessages(prev => [
          ...prev.slice(0, -1),
          {
            ...prev[prev.length - 1],
            visualization: data.content
          }
        ]);
      } else if (data.type === 'error') {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: data.content, error: true }
        ]);
      } else if (data.type === 'end') {
        setIsLoading(false);
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected, attempting to reconnect...');
      setTimeout(connectWebSocket, 3000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  

  useEffect(() => {
    if (sessionId && selectedDb && selectedSchema) {
      connectWebSocket();
      setIsConnected(true);
    } else {
      setIsConnected(false);
    }
    return () => ws.current?.close();
  }, [sessionId, selectedDb, selectedSchema]);

  // Add Clear Chat History button to sidebar
  const clearHistory = async () => {
    if (confirm('Are you sure you want to clear the chat history?')) {
      setMessages([]);
      const newSessionId = uuidv4();
      localStorage.setItem('chatSessionId', newSessionId);
      setSessionId(newSessionId);
    }
  };

  const renderDatabaseSelection = () => (
    <div className="flex items-center space-x-4">
      <div className="relative">
        <select
          value={selectedDb}
          onChange={(e) => {
            setSelectedDb(e.target.value);
            setSelectedSchema(''); // Reset schema when database changes
          }}
          className="appearance-none pl-3 pr-8 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Select Database</option>
          {databases.map(db => (
            <option key={db.name} value={db.name}>{db.name}</option>
          ))}
        </select>
        <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
      </div>

      {selectedDb && (
        <div className="relative">
          <select
            value={selectedSchema}
            onChange={(e) => setSelectedSchema(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Select Schema</option>
            {databases
              .find(db => db.name === selectedDb)
              ?.schemas.map(schema => (
                <option key={schema} value={schema}>{schema}</option>
              ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
        </div>
      )}
    </div>
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    setIsLoading(true);
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(input);
    } else {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Connection error. Please try again.', 
        error: true 
      }]);
      setIsLoading(false);
    }
    
    setInput('');
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar */}
      <div className="w-64 bg-white border-r flex flex-col">
        {/* App Name */}
        <div className="p-4 border-b">
          <div className="flex items-center space-x-2">
            <BarChart className="w-6 h-6 text-blue-500" />
            <h1 className="text-xl font-semibold text-gray-800">Analytics AI</h1>
          </div>
        </div>

        {/* Database Selection */}
        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Database
            </label>
            <div className="relative">
              <select
                value={selectedDb}
                onChange={(e) => {
                  setSelectedDb(e.target.value);
                  setSelectedSchema('');
                }}
                className="w-full appearance-none pl-3 pr-8 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              >
                <option value="">Select Database</option>
                {databases.map(db => (
                  <option key={db.name} value={db.name}>{db.name}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            </div>
          </div>

          {selectedDb && (
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Schema
              </label>
              <div className="relative">
                <select
                  value={selectedSchema}
                  onChange={(e) => setSelectedSchema(e.target.value)}
                  className="w-full appearance-none pl-3 pr-8 py-2 border rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                >
                  <option value="">Select Schema</option>
                  {databases
                    .find(db => db.name === selectedDb)
                    ?.schemas.map(schema => (
                      <option key={schema} value={schema}>{schema}</option>
                    ))}
                </select>
                <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
              </div>
            </div>
          )}

          {/* Connection Status */}
          <div className="pt-2">
            <div className={`flex items-center space-x-2 text-sm ${isConnected ? 'text-green-600' : 'text-gray-500'}`}>
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-600' : 'bg-gray-500'}`}></div>
              <span>{isConnected ? 'Connected' : 'Not Connected'}</span>
            </div>
          </div>
        </div>
        {/* Add Clear History button */}
        <div className="p-4 mt-auto border-t">
          <button
            onClick={clearHistory}
            className="w-full px-4 py-2 text-sm text-red-600 hover:text-red-700 
                     border border-red-200 rounded-lg hover:bg-red-50 
                     transition-colors duration-200"
          >
            Clear Chat History
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 bg-white shadow-sm border-b">
          <div className="max-w-5xl mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-gray-500" />
              <span className="text-sm text-gray-600">
                {selectedDb ? `${selectedDb} / ${selectedSchema || 'Select Schema'}` : 'Select Database'}
              </span>
            </div>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto p-4 space-y-6">
            {messages.length === 0 && (
              <div className="text-center text-gray-500 mt-8">
                <Database className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p className="text-lg font-medium">Welcome to Analytics AI</p>
                <p className="text-sm mt-2">
                  {isConnected 
                    ? "Ask any question about your database" 
                    : "Please select a database and schema to start"}
                </p>
              </div>
            )}
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex items-start space-x-2 ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : 'flex-row'
                }`}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                  ${message.role === 'user' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-gray-200 text-gray-600'}`}
                >
                  {message.role === 'user' 
                    ? <User className="w-5 h-5" />
                    : <Database className="w-5 h-5" />}
                </div>

                <div className={`flex flex-col space-y-2 max-w-[85%]`}>
                  <div
                    className={`px-4 py-2 rounded-xl text-sm ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : message.error
                        ? 'bg-red-50 text-red-800 border border-red-200'
                        : 'bg-white text-gray-800 shadow-sm border'
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  </div>

                  {message.visualization && (
                    <div className="mt-2 bg-white p-2 rounded-lg shadow-sm border">
                      <img
                        src={`data:image/png;base64,${message.visualization}`}
                        alt="Data Visualization"
                        className="max-w-full h-auto max-h-[400px] object-contain rounded"
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex items-start space-x-2">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center">
                  <Database className="w-5 h-5" />
                </div>
                <div className="bg-white text-gray-500 px-4 py-2 rounded-xl shadow-sm border">
                  <Loader2 className="w-4 h-4 animate-spin" />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Input Form */}
        <div className="border-t bg-white p-4">
          <div className="max-w-5xl mx-auto">
            <form onSubmit={handleSubmit} className="flex space-x-4">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isConnected ? "Ask about your database..." : "Select database and schema to start..."}
                className="flex-1 p-3 border rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={!isConnected || isLoading}
              />
              <button
                type="submit"
                disabled={!isConnected || isLoading}
                className="px-4 py-2 bg-blue-500 text-white rounded-xl hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
              >
                <Send className="w-5 h-5" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
