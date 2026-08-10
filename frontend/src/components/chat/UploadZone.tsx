import type { ChangeEvent, DragEvent, RefObject } from 'react';
import Icon from '../common/Icon';

interface UploadZoneProps {
  uploadedFile: File | null;
  isDragging: boolean;
  fileInputRef: RefObject<HTMLInputElement>;
  onDragOver: (e: DragEvent<HTMLDivElement>) => void;
  onDragLeave: () => void;
  onDrop: (e: DragEvent<HTMLDivElement>) => void;
  onZoneClick: () => void;
  onFileChange: (e: ChangeEvent<HTMLInputElement>) => void;
  onClearFile: () => void;
}

export default function UploadZone({
  uploadedFile, isDragging, fileInputRef,
  onDragOver, onDragLeave, onDrop, onZoneClick, onFileChange, onClearFile,
}: UploadZoneProps) {
  return (
    <div className="upload-strip">
      {uploadedFile ? (
        <div className="upload-confirmed">
          <Icon name="bids" size={14} color="var(--cyan)" />
          <span className="upload-filename">{uploadedFile.name}</span>
          <button className="upload-clear" onClick={onClearFile}>
            <Icon name="close" size={12} color="var(--text3)" />
          </button>
        </div>
      ) : (
        <div
          className={`drop-zone ${isDragging ? 'dragover' : ''}`}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={onZoneClick}
        >
          <Icon name="upload" size={14} color={isDragging ? 'var(--accent2)' : 'var(--text3)'} />
          <span>
            Drag &amp; drop PDF, or{' '}
            <span className="upload-link">click to upload</span>
          </span>
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        style={{ display: 'none' }}
        onChange={onFileChange}
      />
    </div>
  );
}
