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

  const handlePaste = async (sender: Sender.Deepseek | Sender.ChatGPT) => {
    setIsLoading(true);
    setError(null);
    try {
      if (!navigator.clipboard?.readText || !navigator.permissions?.query) {
        throw new Error('Clipboard API not available. This feature requires a secure context (HTTPS) and user permission.');
      }

      const permissionStatus = await navigator.permissions.query({ name: 'clipboard-read' as PermissionName });

      if (permissionStatus.state === 'denied') {
        throw new Error('Clipboard permission denied. Please enable it in your browser settings to use this feature.');
      }

      const clipboardText = await navigator.clipboard.readText();

      // For debugging, log what we see on the clipboard.
      console.log("Read from clipboard:", clipboardText);

      const trimmedClipboard = clipboardText.trim();
      let expectedPrefix: string;
      let checkPrefix: string;
      let prefixLength: number;

      if (sender === Sender.Deepseek) {
          expectedPrefix = "Deepseek:";
          checkPrefix = "deepseek:";
          prefixLength = 9;
      } else { // ChatGPT
          expectedPrefix = "ChatGPT:";
          checkPrefix = "chatgpt:";
          prefixLength = 8;
      }

      if (trimmedClipboard.toLowerCase().startsWith(checkPrefix)) {
          const content = trimmedClipboard.substring(prefixLength).trim();
          if (content) {
            addMessage(content, sender);
          } else {
            throw new Error(`Found the prefix "${expectedPrefix}", but there was no content after it.`);
          }
      } else {
          throw new Error(`Could not find content starting with "${expectedPrefix}" on your clipboard. Make sure you've copied the entire AI response.`);
      }

    } catch (err) {
        if (err instanceof Error) {
            if (err.name === 'NotAllowedError') {
                setError('Clipboard permission was not granted. Please allow access to the clipboard.');
            } else {
                setError(err.message || 'Failed to read from clipboard.');
            }
        } else {
            setError('An unknown error occurred.');
        }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasteDeepseek = () => handlePaste(Sender.Deepseek);
  const handlePasteChatGPT = () => handlePaste(Sender.ChatGPT);

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
        onPasteDeepseek={handlePasteDeepseek}
        onPasteChatGPT={handlePasteChatGPT}
        isLoading={isLoading}
      />
    </div>
  );
};

export default App;
