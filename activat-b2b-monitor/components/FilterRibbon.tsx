import React from 'react';
import { Industry, City } from '../types';

interface FilterRibbonProps {
  items: (Industry | City)[];
  selectedItem: string;
  onSelect: (item: string) => void;
  className?: string;
}

export const FilterRibbon: React.FC<FilterRibbonProps> = ({ items, selectedItem, onSelect, className = '' }) => {
  return (
    <div className={`flex overflow-x-auto no-scrollbar gap-3 px-6 py-2 ${className}`}>
      {items.map((item) => {
        const isSelected = selectedItem === item;
        return (
          <button
            key={item}
            onClick={() => onSelect(item)}
            className={`
              flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 border
              ${isSelected 
                ? 'bg-activatBlue border-activatBlue text-white shadow-md shadow-activatBlue/20' 
                : 'bg-white border-borderLight text-slateGrey hover:border-slate-300 hover:text-textMain hover:bg-slate-50'}
            `}
          >
            {item}
          </button>
        );
      })}
    </div>
  );
};