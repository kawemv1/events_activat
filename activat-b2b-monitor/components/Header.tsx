import React, { useState } from 'react';
import { Search, X } from 'lucide-react';
import { t, getLanguageCode, Language } from '../utils/translations';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  language?: string;
}

export const Header: React.FC<HeaderProps> = ({ searchQuery, onSearchChange, language = 'English' }) => {
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);

  const handleSearchClick = () => {
    setIsSearchOpen(true);
  };

  const handleCloseSearch = () => {
    setIsSearchOpen(false);
    onSearchChange('');
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16 px-6 flex items-center justify-between bg-surface/80 backdrop-blur-xl border-b border-borderLight shadow-sm">
      <div className="flex items-center gap-2">
        <img 
          src="https://activat.vc/themes/activat-vc/assets/images/logo.svg" 
          alt="logo" 
          className="header_logo_img h-8"
        />
      </div>
      
      <div className="flex items-center gap-2">
        {isSearchOpen ? (
          <div className="flex items-center gap-2 bg-white rounded-full border border-borderLight px-3 py-2 shadow-sm">
            <Search className="w-4 h-4 text-slateGrey" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder={translate('searchEvents')}
              className="outline-none text-sm w-48 bg-transparent text-textMain placeholder-slateGrey"
              autoFocus
            />
            <button
              onClick={handleCloseSearch}
              className="p-1 rounded-full hover:bg-slate-100 transition-colors text-slateGrey"
              aria-label="Close search"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button 
            onClick={handleSearchClick}
            className="p-2 rounded-full hover:bg-slate-100 transition-colors active:scale-95 text-slateGrey hover:text-activatBlue"
            aria-label="Search"
          >
            <Search className="w-6 h-6" strokeWidth={1.5} />
          </button>
        )}
      </div>
    </header>
  );
};