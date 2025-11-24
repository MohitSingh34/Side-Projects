
import React, { useState, useEffect } from 'react';
import type { Message } from './types';
import { Sender } from './types';
import ChatWindow from './components/ChatWindow';
import ChatControls from './components/ChatControls';

const App: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMessages([
      {
        id: Date.now(),
        text: 'Welcome to the AI Group Chat! Type a message or use the buttons to paste content from an AI.',
        sender: Sender.System,
      },
    ]);
  }, []);

  const addMessage = (text: string, sender: Sender) => {
    if (!text.trim()) return;
    const newMessage: Message = {
      id: Date.now(),
      text,
      sender,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const handleSendMessage = () => {
    addMessage(userInput, Sender.User);
    setUserInput('');
  };

  const handleAiAction = async (ai: Sender.Deepseek | Sender.ChatGPT) => {
    setIsLoading(true);
    setError(null);
    try {
      if (!navigator.clipboard?.readText) {
        throw new Error('Clipboard API not available. This feature requires a secure context (HTTPS) and user permission.');
      }
      const clipboardText = await navigator.clipboard.readText();
      
      const prefix = ai === Sender.Deepseek ? 'Deepseek:' : 'Chatgpt:';
      const regex = new RegExp(`^${prefix}\\s*(.*?)\\s*$`, 's');
      const match = clipboardText.match(regex);
      
      if (match && match[1]) {
        addMessage(match[1].trim(), ai);
      } else {
        throw new Error(`No content matching "${prefix} #content#" found on your clipboard. Please copy the text in the correct format.`);
      }

    } catch (err) {
        if (err instanceof Error) {
            setError(err.message || 'Failed to read from clipboard.');
        } else {
            setError('An unknown error occurred.');
        }
    } finally {
      setIsLoading(false);
    }
  };
  
  useEffect(() => {
    if (error) {
        const timer = setTimeout(() => setError(null), 5000);
        return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div className="flex flex-col h-screen bg-chat-bg font-sans">
      <header className="bg-gray-800 text-white text-center p-4 shadow-lg">
        <h1 className="text-2xl font-bold">AI Group Chat</h1>
      </header>
      
      <ChatWindow messages={messages} />
      
      {error && (
        <div className="px-6 pb-2">
            <div className="bg-red-500 text-white text-sm font-semibold px-4 py-2 rounded-md text-center">
                {error}
            </div>
        </div>
      )}
       {isLoading && (
        <div className="px-6 pb-2 flex justify-center items-center">
             <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
             <p className="ml-2 text-white text-sm">Accessing clipboard...</p>
        </div>
      )}

      <ChatControls
        userInput={userInput}
        setUserInput={setUserInput}
        onSendMessage={handleSendMessage}
        onAiAction={handleAiAction}
        isLoading={isLoading}
      />
    </div>
  );
};

export default App;
