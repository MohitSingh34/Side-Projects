import React from 'react';
import { SendIcon, ClipboardIcon } from './icons';

interface ChatControlsProps {
  userInput: string;
  setUserInput: (value: string) => void;
  onSendMessage: () => void;
  onPasteDeepseek: () => void;
  onPasteChatGPT: () => void;
  isLoading: boolean;
}

const ChatControls: React.FC<ChatControlsProps> = ({
  userInput,
  setUserInput,
  onSendMessage,
  onPasteDeepseek,
  onPasteChatGPT,
  isLoading,
}) => {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className="bg-chat-bg px-6 pb-6 border-t border-gray-700">
      <div className="flex justify-center items-center gap-4 mb-4">
        <button
          onClick={onPasteDeepseek}
          disabled={isLoading}
          className="flex items-center justify-center w-full px-4 py-2 bg-green-600 text-white font-semibold rounded-lg shadow-md hover:bg-green-700 transition duration-300 disabled:bg-gray-500 disabled:cursor-not-allowed"
        >
          <ClipboardIcon />
          Paste from Deepseek
        </button>
        <button
          onClick={onPasteChatGPT}
          disabled={isLoading}
          className="flex items-center justify-center w-full px-4 py-2 bg-purple-600 text-white font-semibold rounded-lg shadow-md hover:bg-purple-700 transition duration-300 disabled:bg-gray-500 disabled:cursor-not-allowed"
        >
          <ClipboardIcon />
          Paste from ChatGPT
        </button>
      </div>
      <div className="flex items-center bg-input-bg rounded-full p-2">
        <input
          type="text"
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className="w-full bg-transparent text-white placeholder-gray-400 focus:outline-none px-4"
        />
        <button
          onClick={onSendMessage}
          disabled={!userInput.trim()}
          className="bg-btn-primary text-white p-3 rounded-full hover:bg-btn-hover transition duration-300 disabled:bg-gray-500 disabled:cursor-not-allowed"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
};

export default ChatControls;