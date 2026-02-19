import React from 'react';
import { Home, Settings, User } from 'lucide-react';
import { NavTab } from '../types';
import { t, getLanguageCode, Language } from '../utils/translations';

interface NavigationProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  language?: string;
}

export const Navigation: React.FC<NavigationProps> = ({ activeTab, onTabChange, language = 'English' }) => {
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);
  
  const navItems = [
    { id: 'feed', icon: Home, label: translate('feed') },
    { id: 'settings', icon: Settings, label: translate('settings') },
    { id: 'profile', icon: User, label: translate('profile') },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 h-20 pb-4 bg-surface/90 backdrop-blur-xl border-t border-borderLight shadow-[0_-4px_20px_-4px_rgba(0,0,0,0.05)]">
      <div className="flex justify-around items-center h-full px-6">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          const Icon = item.icon;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id as NavTab)}
              className="flex flex-col items-center justify-center w-16 gap-1 group"
            >
              <div 
                className={`
                  p-1.5 rounded-xl transition-all duration-300
                  ${isActive ? 'bg-activatBlue/10' : 'bg-transparent'}
                `}
              >
                <Icon 
                  size={24} 
                  strokeWidth={1.5}
                  className={`transition-colors duration-300 ${isActive ? 'text-activatBlue' : 'text-slateGrey group-hover:text-textMain'}`} 
                />
              </div>
              <span className={`text-[10px] font-medium transition-colors duration-300 ${isActive ? 'text-activatBlue' : 'text-slateGrey'}`}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};