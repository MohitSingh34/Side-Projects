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
        text: 'Welcome to the AI Group Chat! The paste buttons now perform a copy-then-paste action chain.',
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

  const handleCopyAndPaste = async (sender: Sender.Deepseek | Sender.ChatGPT) => {
    setIsLoading(true);
    setError(null);
    try {
      // Step 1: Find and prepare the messages to copy.
      const otherSender = sender === Sender.Deepseek ? Sender.ChatGPT : Sender.Deepseek;

      const lastOtherMessageIndex = messages.map(m => m.sender).lastIndexOf(otherSender);

      if (lastOtherMessageIndex === -1) {
        throw new Error(`Could not find any messages from ${otherSender} to determine which new messages to copy.`);
      }

      const newMessagesToCopy = messages
        .slice(lastOtherMessageIndex + 1)
        .filter(m => m.sender === sender);

      if (newMessagesToCopy.length === 0) {
        throw new Error(`No new ${sender} messages found after the last message from ${otherSender}.`);
      }

      const combinedText = newMessagesToCopy.map(m => m.text).join('\n\n');

      // Step 2: Copy the combined text to the clipboard.
      const clipboardContent = `${sender}: ${combinedText}`;
      await navigator.clipboard.writeText(clipboardContent);

      addMessage(`Copied ${newMessagesToCopy.length} message(s) from ${sender}. Pasting now...`, Sender.System);

      // Step 3: Paste the content into the chat.
      addMessage(combinedText, sender);

    } catch (err) {
      if (err instanceof Error) {
        setError(err.message || `An error occurred during the ${sender} action.`);
      } else {
        setError('An unknown error occurred.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasteDeepseek = () => handleCopyAndPaste(Sender.Deepseek);
  const handlePasteChatGPT = () => handleCopyAndPaste(Sender.ChatGPT);

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
             <p className="ml-2 text-white text-sm">Performing action...</p>
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
