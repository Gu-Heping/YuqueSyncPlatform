import React, { useState } from 'react';
import { X, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';

const ImagePreview = ({ src, onClose }) => {
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);

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

  return (
    <div 
      className="fixed inset-0 z-[60] bg-black/90 flex items-center justify-center cursor-zoom-out animate-in fade-in duration-200"
      onClick={onClose}
    >
      {/* Toolbar */}
      <div className="absolute top-4 right-4 flex space-x-2 z-10">
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

      {/* Image */}
      <div 
        className="relative transition-transform duration-200 ease-out"
        style={{ 
          transform: `scale(${scale}) rotate(${rotation}deg)`,
        }}
        onClick={(e) => e.stopPropagation()}
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
