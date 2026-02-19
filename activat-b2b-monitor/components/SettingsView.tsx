import React, { useState } from 'react';
import { Globe, Moon, FileText, HelpCircle, ChevronRight, LogOut, X } from 'lucide-react';
import { AppSettings } from '../types';
import { COUNTRY_CITIES } from '../constants';
import { t, getLanguageCode, LANGUAGE_NAMES, Language, translateCountryName } from '../utils/translations';

interface SettingsViewProps {
  settings: AppSettings;
  onUpdate: (key: keyof AppSettings, value: any) => void;
  onSignOut: () => void;
}

const SettingToggle: React.FC<{ label: string; checked: boolean; onChange: () => void }> = ({ label, checked, onChange }) => (
  <div className="flex items-center justify-between py-3">
    <span className="text-sm font-medium text-textMain">{label}</span>
    <button 
      onClick={onChange}
      className={`w-11 h-6 rounded-full transition-colors relative ${checked ? 'bg-activatBlue' : 'bg-slate-200'}`}
    >
      <div className={`absolute top-1 left-1 bg-white w-4 h-4 rounded-full shadow transition-transform ${checked ? 'translate-x-5' : 'translate-x-0'}`} />
    </button>
  </div>
);

const SettingLink: React.FC<{ icon: any; label: string; value?: string; onClick: () => void }> = ({ icon: Icon, label, value, onClick }) => (
  <button onClick={onClick} className="w-full flex items-center justify-between py-3 group">
    <div className="flex items-center gap-3">
      <div className="p-2 bg-slate-50 rounded-lg text-slateGrey group-hover:text-activatBlue group-hover:bg-blue-50 transition-colors">
        <Icon size={18} />
      </div>
      <span className="text-sm font-medium text-textMain">{label}</span>
    </div>
    <div className="flex items-center gap-2">
      {value && <span className="text-sm text-slateGrey">{value}</span>}
      <ChevronRight size={16} className="text-slate-300" />
    </div>
  </button>
);

const SelectionModal: React.FC<{ 
  title: string; 
  options: string[]; 
  currentValue: string; 
  onSelect: (value: string) => void; 
  onClose: () => void 
}> = ({ title, options, currentValue, onSelect, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onClose}>
    <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
      <div className="flex items-center justify-between p-4 border-b border-borderLight">
        <h3 className="text-lg font-bold text-textMain">{title}</h3>
        <button onClick={onClose} className="p-1 rounded-full hover:bg-slate-100 transition-colors">
          <X className="w-5 h-5 text-slateGrey" />
        </button>
      </div>
      <div className="p-2 overflow-y-auto">
        {options.map((option) => (
          <button
            key={option}
            onClick={() => {
              onSelect(option);
              onClose();
            }}
            className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
              currentValue === option
                ? 'bg-activatBlue/10 text-activatBlue font-medium'
                : 'text-textMain hover:bg-slate-50'
            }`}
          >
            {option}
            {currentValue === option && <span className="ml-2 text-activatBlue">✓</span>}
          </button>
        ))}
      </div>
    </div>
  </div>
);

export const SettingsView: React.FC<SettingsViewProps> = ({ settings, onUpdate, onSignOut }) => {
  const [showRegionModal, setShowRegionModal] = useState(false);
  const [showLanguageModal, setShowLanguageModal] = useState(false);

  // Get countries from COUNTRY_CITIES, prioritize primary region
  const countries = Object.keys(COUNTRY_CITIES);
  const regions = settings.region && countries.includes(settings.region) 
    ? [settings.region, ...countries.filter(c => c !== settings.region)]
    : countries;

  // Languages based on countries
  const languages = [
    'English',
    'Қазақша', // Kazakh
    'Русский', // Russian
    "O'zbekcha", // Uzbek
    'Azərbaycan', // Azerbaijani
    'ქართული', // Georgian
    'Հայերեն', // Armenian
    'Кыргызча', // Kyrgyz
    'Тоҷикӣ', // Tajik
    'Türkmen', // Turkmen
  ];

  const currentLang = getLanguageCode(settings.language);
  const translate = (key: string) => t(key, currentLang);

  const handleUserAgreement = () => {
    window.open('https://activat.vc/agreement', '_blank');
  };

  const handleHelp = () => {
    window.open('https://activat.vc/contacts', '_blank');
  };

  const handleSignOut = () => {
    if (window.confirm(translate('signOut') + '?')) {
      onSignOut();
    }
  };

  return (
    <>
      <div className="px-6 py-8 pb-32 max-w-lg mx-auto">
        <h1 className="text-2xl font-bold text-textMain mb-6">{translate('settings')}</h1>

        <section className="mb-8">
          <h2 className="text-xs font-bold text-slateGrey uppercase tracking-wider mb-3 pl-1">{translate('preferences')}</h2>
          <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-4 space-y-1">
            <SettingToggle 
              label={translate('telegramNotifications')} 
              checked={settings.telegramNotifications} 
              onChange={() => onUpdate('telegramNotifications', !settings.telegramNotifications)} 
            />
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-xs font-bold text-slateGrey uppercase tracking-wider mb-3 pl-1">{translate('regional')}</h2>
          <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-4 space-y-1">
            <SettingLink 
              icon={Globe} 
              label={translate('primaryRegion')} 
              value={translateCountryName(settings.region, currentLang)}
              onClick={() => setShowRegionModal(true)}
            />
            <div className="h-[1px] bg-slate-100 w-full" />
            <SettingLink 
              icon={Moon} 
              label={translate('language')} 
              value={settings.language}
              onClick={() => setShowLanguageModal(true)}
            />
          </div>
        </section>

        <section className="mb-8">
          <h2 className="text-xs font-bold text-slateGrey uppercase tracking-wider mb-3 pl-1">{translate('support')}</h2>
          <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-4 space-y-1">
            <SettingLink 
              icon={FileText} 
              label={translate('userAgreement')}
              onClick={handleUserAgreement}
            />
            <div className="h-[1px] bg-slate-100 w-full" />
            <SettingLink 
              icon={HelpCircle} 
              label={translate('help')}
              onClick={handleHelp}
            />
          </div>
        </section>

        <button 
          onClick={handleSignOut}
          className="w-full py-4 rounded-xl text-red-500 font-medium text-sm bg-red-50 hover:bg-red-100 transition-colors flex items-center justify-center gap-2"
        >
          <LogOut size={18} />
          {translate('signOut')}
        </button>
        
        <p className="text-center text-xs text-slate-300 mt-6">Version 2.0.4 (Build 492)</p>
      </div>

      {showRegionModal && (
        <SelectionModal
          title={translate('primaryRegion')}
          options={regions.map(region => translateCountryName(region, currentLang))}
          currentValue={translateCountryName(settings.region, currentLang)}
          onSelect={(value) => {
            // Find the original country name from the translated value
            const originalCountry = Object.keys(COUNTRY_CITIES).find(
              country => translateCountryName(country, currentLang) === value
            ) || value;
            onUpdate('region', originalCountry);
          }}
          onClose={() => setShowRegionModal(false)}
        />
      )}

      {showLanguageModal && (
        <SelectionModal
          title={translate('language')}
          options={languages}
          currentValue={settings.language}
          onSelect={(value) => onUpdate('language', value)}
          onClose={() => setShowLanguageModal(false)}
        />
      )}
    </>
  );
};
