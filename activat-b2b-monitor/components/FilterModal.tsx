import React, { useState } from 'react';
import { X, Filter } from 'lucide-react';
import { COUNTRY_CITIES } from '../constants';
import { t, getLanguageCode, translateCountryName, Language } from '../utils/translations';

interface FilterModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCountry: string | null;
  selectedCity: string | null;
  searchQuery: string;
  onCountryChange: (country: string | null) => void;
  onCityChange: (city: string | null) => void;
  onSearchChange: (query: string) => void;
  language?: string;
}

export const FilterModal: React.FC<FilterModalProps> = ({
  isOpen,
  onClose,
  selectedCountry,
  selectedCity,
  searchQuery,
  onCountryChange,
  onCityChange,
  onSearchChange,
  language = 'English',
}) => {
  const [localSearchQuery, setLocalSearchQuery] = useState(searchQuery);
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);

  if (!isOpen) return null;

  const handleSearchSubmit = () => {
    onSearchChange(localSearchQuery);
  };

  const handleReset = () => {
    onCountryChange(null);
    onCityChange(null);
    setLocalSearchQuery('');
    onSearchChange('');
  };

  return (
    <div className="fixed inset-0 z-[70] bg-black/50 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-borderLight">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-activatBlue/10 rounded-lg">
              <Filter size={20} className="text-activatBlue" />
            </div>
            <h2 className="text-xl font-bold text-textMain">{translate('filters')}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-100 transition-colors text-slateGrey"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Search */}
          <div>
            <label className="block text-sm font-semibold text-textMain mb-2">
              {translate('search')}
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={localSearchQuery}
                onChange={(e) => setLocalSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearchSubmit()}
                placeholder={translate('searchPlaceholder')}
                className="flex-1 px-4 py-2 border border-borderLight rounded-xl focus:outline-none focus:ring-2 focus:ring-activatBlue focus:border-transparent"
              />
              <button
                onClick={handleSearchSubmit}
                className="px-4 py-2 bg-activatBlue text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
              >
                {translate('search')}
              </button>
            </div>
          </div>

          {/* Country Selection */}
          <div>
            <label className="block text-sm font-semibold text-textMain mb-3">
              {translate('country')}
            </label>
            <div className="space-y-2">
              <button
                onClick={() => {
                  onCountryChange(null);
                  onCityChange(null);
                }}
                className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
                  selectedCountry === null
                    ? 'bg-activatBlue text-white border-activatBlue'
                    : 'bg-white border-borderLight hover:bg-slate-50'
                }`}
              >
                {translate('allCountries')}
              </button>
              {Object.keys(COUNTRY_CITIES).map((country) => (
                <button
                  key={country}
                  onClick={() => {
                    onCountryChange(country);
                    onCityChange(null);
                  }}
                  className={`w-full text-left px-4 py-3 rounded-xl border transition-all ${
                    selectedCountry === country
                      ? 'bg-activatBlue text-white border-activatBlue'
                      : 'bg-white border-borderLight hover:bg-slate-50'
                  }`}
                >
                  {translateCountryName(country, langCode)}
                </button>
              ))}
            </div>
          </div>

          {/* City Selection (only if country is selected) */}
          {selectedCountry && COUNTRY_CITIES[selectedCountry] && (
            <div>
              <label className="block text-sm font-semibold text-textMain mb-3">
                {translate('city')} ({translateCountryName(selectedCountry, langCode)})
              </label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                <button
                  onClick={() => onCityChange(null)}
                  className={`w-full text-left px-4 py-2 rounded-xl border transition-all ${
                    selectedCity === null
                      ? 'bg-activatBlue text-white border-activatBlue'
                      : 'bg-white border-borderLight hover:bg-slate-50'
                  }`}
                >
                  {translate('allCities')}
                </button>
                {COUNTRY_CITIES[selectedCountry].map((city) => (
                  <button
                    key={city}
                    onClick={() => onCityChange(city)}
                    className={`w-full text-left px-4 py-2 rounded-xl border transition-all ${
                      selectedCity === city
                        ? 'bg-activatBlue text-white border-activatBlue'
                        : 'bg-white border-borderLight hover:bg-slate-50'
                    }`}
                  >
                    {city}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-borderLight flex gap-3">
          <button
            onClick={handleReset}
            className="flex-1 px-4 py-3 border border-borderLight rounded-xl font-medium text-slateGrey hover:bg-slate-50 transition-colors"
          >
            {translate('reset')}
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-3 bg-activatBlue text-white rounded-xl font-medium hover:bg-blue-600 transition-colors"
          >
            {translate('apply')}
          </button>
        </div>
      </div>
    </div>
  );
};
