import React, { useState, useRef, useEffect } from 'react';
import { X, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';

const ImagePreview = ({ src, onClose }) => {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });

  if (!src) return null;

  const handleZoomIn = (e) => {
    e.stopPropagation();
    setScale(prev => Math.min(prev + 0.5, 4));
  };

  const handleZoomOut = (e) => {
    e.stopPropagation();
    setScale(prev => Math.max(prev - 0.5, 0.5));
  };

  const handleRotate = (e) => {
    e.stopPropagation();
    setRotation(prev => (prev + 90) % 360);
  };

  const handleMouseDown = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
    dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    e.preventDefault();
    e.stopPropagation();
    const newX = e.clientX - dragStart.current.x;
    const newY = e.clientY - dragStart.current.y;
    setPosition({ x: newX, y: newY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // Reset position when scale is 1 or less to keep it centered
  useEffect(() => {
    if (scale <= 1) {
      setPosition({ x: 0, y: 0 });
    }
  }, [scale]);

  return (
    <div 
      className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center cursor-zoom-out animate-in fade-in duration-200 overflow-hidden"
      onClick={onClose}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Toolbar */}
      <div className="absolute top-4 right-4 flex space-x-2 z-10" onClick={(e) => e.stopPropagation()}>
        <button 
          onClick={handleZoomIn}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
          title="放大"
        >
          <ZoomIn size={24} />
        </button>
        <button 
          onClick={handleZoomOut}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
          title="缩小"
        >
          <ZoomOut size={24} />
        </button>
        <button 
          onClick={handleRotate}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
          title="旋转"
        >
          <RotateCw size={24} />
        </button>
        <button 
          onClick={onClose}
          className="p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors"
          title="关闭"
        >
          <X size={24} />
        </button>
      </div>

      {/* Image Container */}
      <div 
        className="relative"
        style={{ 
          transform: `translate(${position.x}px, ${position.y}px) rotate(${rotation}deg) scale(${scale})`,
          cursor: isDragging ? 'grabbing' : (scale > 1 ? 'grab' : 'default'),
          transition: isDragging ? 'none' : 'transform 0.2s ease-out'
        }}
        onClick={(e) => e.stopPropagation()}
        onMouseDown={handleMouseDown}
      >
        <img 
          src={src} 
          alt="Preview" 
          className="max-w-[90vw] max-h-[90vh] object-contain select-none shadow-2xl"
          draggable={false}
        />
      </div>
    </div>
  );
};

export default ImagePreview;
