import Icon from '../common/Icon';
import MessageList from './MessageList';
import SuggestionChips from './SuggestionChips';
import UploadZone from './UploadZone';
import type { UseChatResult } from '../../hooks/useChat';
import type { Suggestion, Translations } from '../../i18n/translations';
import type { Language } from '../../types';

interface ChatPanelProps {
  chat: UseChatResult;
  language: Language;
  t: Translations;
  suggestions: Suggestion[];
  suppliersCount: number;
  bidsCount: number;
}

export default function ChatPanel({ chat, language, t, suggestions, suppliersCount, bidsCount }: ChatPanelProps) {
  return (
    <div className="chat-panel">
      <MessageList
        messages={chat.messages}
        isLoading={chat.isLoading}
        suppliersCount={suppliersCount}
        bidsCount={bidsCount}
        chatRef={chat.chatRef}
        language={language}
        t={t}
      />

      <SuggestionChips suggestions={suggestions} onSelect={chat.handleSubmit} />

      <UploadZone
        uploadedFile={chat.uploadedFile}
        isDragging={chat.isDragging}
        fileInputRef={chat.fileInputRef}
        onDragOver={e => { e.preventDefault(); chat.setIsDragging(true); }}
        onDragLeave={() => chat.setIsDragging(false)}
        onDrop={chat.handleDrop}
        onZoneClick={() => chat.fileInputRef.current?.click()}
        onFileChange={chat.handleFileInputChange}
        onClearFile={() => chat.setUploadedFile(null)}
      />

      <div className="input-area">
        <div className="input-bar">
          <input
            className="chat-input"
            value={chat.inputValue}
            onChange={e => chat.setInputValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); chat.handleSubmit(); } }}
            placeholder={t.placeholder}
            disabled={chat.isLoading}
          />
          <button
            className={`send-btn ${chat.inputValue.trim() ? 'active' : ''}`}
            onClick={() => chat.handleSubmit()}
            disabled={chat.isLoading || !chat.inputValue.trim()}
          >
            <Icon name="send" size={14} color={chat.inputValue.trim() ? '#fff' : 'var(--text3)'} />
          </button>
        </div>
      </div>
    </div>
  );
}
