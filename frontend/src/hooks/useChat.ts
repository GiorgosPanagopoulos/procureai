import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, RefObject } from 'react';
import * as Sentry from '@sentry/react';
import { toast } from 'sonner';
import { checkHealth, sendChatMessage, uploadDocument } from '../api/chat';
import type { Message } from '../types';

export interface UseChatOptions {
  onMessageReceived?: () => void;
}

export interface UseChatResult {
  messages: Message[];
  inputValue: string;
  setInputValue: (value: string) => void;
  isLoading: boolean;
  isConnected: boolean;
  uploadedFile: File | null;
  setUploadedFile: (file: File | null) => void;
  isDragging: boolean;
  setIsDragging: (dragging: boolean) => void;
  chatRef: RefObject<HTMLDivElement>;
  fileInputRef: RefObject<HTMLInputElement>;
  handleSubmit: (text?: string) => Promise<void>;
  processFile: (file: File) => Promise<void>;
  handleDrop: (e: DragEvent<HTMLDivElement>) => void;
  handleFileInputChange: (e: ChangeEvent<HTMLInputElement>) => void;
  clearChat: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatResult {
  const { onMessageReceived } = options;
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    const check = async () => setIsConnected(await checkHealth());
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  const handleSubmit = async (text?: string) => {
    const txt = (text ?? inputValue).trim();
    if (!txt || isLoading) return;
    setInputValue('');

    const userMsg: Message = { id: Date.now().toString(), text: txt, sender: 'user', timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const data = await sendChatMessage(txt, conversationId);
      if (data.conversation_id) setConversationId(data.conversation_id);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: data.response?.trim() || 'No answer returned.',
        sender: 'agent',
        timestamp: new Date(),
        toolUsed: data.tool_used,
        trace: data.trace,
        usage: data.usage,
        conversationId: data.conversation_id,
      }]);
      onMessageReceived?.();
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'chat' }, extra: { query: txt } });
      const raw = err instanceof Error ? err.message : 'Unknown error';
      const isNetwork = raw === 'Load failed' || raw === 'Failed to fetch';
      const isTimeout = raw.includes('abort') || raw.includes('AbortError');
      const friendly = isNetwork
        ? 'Could not reach the backend. Make sure the server is running on port 8000.'
        : isTimeout
        ? 'The request timed out. The agent is taking too long — try a simpler query.'
        : `Error: ${raw}`;
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        text: friendly,
        sender: 'agent',
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const processFile = async (file: File) => {
    setIsLoading(true);
    try {
      const result = await uploadDocument(file);
      setUploadedFile(file);
      toast.success(`Uploaded "${file.name}" successfully`);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        text: `Successfully uploaded ${file.name}. ${result.message || 'Document processed and ready for queries.'}`,
        sender: 'agent',
        timestamp: new Date(),
      }]);
    } catch (err) {
      Sentry.captureException(err, { tags: { component: 'upload' }, extra: { filename: file.name } });
      toast.error(`Upload failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (file.type !== 'application/pdf') { toast.error('Please upload a PDF file'); return; }
    processFile(file);
  };

  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const clearChat = () => {
    setMessages([]);
    setConversationId(null);
  };

  return {
    messages, inputValue, setInputValue, isLoading, isConnected,
    uploadedFile, setUploadedFile, isDragging, setIsDragging,
    chatRef, fileInputRef,
    handleSubmit, processFile, handleDrop, handleFileInputChange, clearChat,
  };
}
