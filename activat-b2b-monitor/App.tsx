import React, { useState, useMemo, useCallback, useEffect } from 'react';
import { Header } from './components/Header';
import { Navigation } from './components/Navigation';
import { FilterRibbon } from './components/FilterRibbon';
import { FilterModal } from './components/FilterModal';
import { EventCard } from './components/EventCard';
import { EventDetail } from './components/EventDetail';
import { SettingsView } from './components/SettingsView';
import { ProfileView } from './components/ProfileView';
import { LoginPage } from './components/LoginPage';
import { SignupPage } from './components/SignupPage';
import { INDUSTRIES } from './constants';
import { Event, Industry, NavTab, UserProfile, AppSettings, AuthUser } from './types';
import { loadEvents, DatabaseEvent } from './utils/database';
import { t, getLanguageCode } from './utils/translations';

// Generate image URL - use database image_url if available, otherwise use static placeholder
function getEventImageUrl(imageUrl: string | null | undefined, id: number): string {
  if (imageUrl && imageUrl.trim() !== '') {
    // Local parsed image (e.g. "parsed_images/abc123.jpg") → serve from public/
    if (imageUrl.startsWith('parsed_images/')) {
      return `/${imageUrl}`;
    }
    // Already a full URL
    if (imageUrl.startsWith('http://') || imageUrl.startsWith('https://')) {
      return imageUrl;
    }
    // Other relative paths
    return `/${imageUrl}`;
  }

  // Fallback placeholder
  return `https://picsum.photos/seed/${id}/800/450`;
}

// Session storage keys
const SESSION_STORAGE_KEY = 'activat_user_session';
const SETTINGS_STORAGE_KEY = 'activat_user_settings';

// Load user session from localStorage
function loadUserSession(): AuthUser | null {
  try {
    const sessionData = localStorage.getItem(SESSION_STORAGE_KEY);
    if (sessionData) {
      return JSON.parse(sessionData);
    }
  } catch (error) {
    console.error('Error loading user session:', error);
  }
  return null;
}

// Save user session to localStorage
function saveUserSession(user: AuthUser | null): void {
  try {
    if (user) {
      localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch (error) {
    console.error('Error saving user session:', error);
  }
}

// Load settings from localStorage
function loadSettings(): AppSettings | null {
  try {
    const settingsData = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (settingsData) {
      return JSON.parse(settingsData);
    }
  } catch (error) {
    console.error('Error loading settings:', error);
  }
  return null;
}

// Save settings to localStorage
function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

function App() {
  // Authentication state - initialize from localStorage
  const [user, setUser] = useState<AuthUser | null>(() => loadUserSession());
  const [showSignup, setShowSignup] = useState(false);
  
  const [activeTab, setActiveTab] = useState<NavTab>('feed');
  const [selectedIndustry, setSelectedIndustry] = useState<Industry>('All');
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isFilterOpen, setIsFilterOpen] = useState<boolean>(false);

  // Load events from database
  useEffect(() => {
    const fetchEvents = async () => {
      try {
        setLoading(true);
        console.log('Loading events from database...');
        const dbEvents = await loadEvents();
        console.log(`Loaded ${dbEvents.length} events from database`);
        const convertedEvents: Event[] = dbEvents.map((dbEvent) => ({
          id: dbEvent.id.toString(),
          name: dbEvent.name || dbEvent.title,
          title: dbEvent.title,
          date: dbEvent.start_date 
            ? new Date(dbEvent.start_date).toLocaleDateString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric' 
              })
            : 'Date TBD',
          startDate: dbEvent.start_date || undefined,
          endDate: dbEvent.end_date || undefined,
          city: dbEvent.city || 'Unknown',
          country: dbEvent.country || 'Unknown',
          description: dbEvent.description || '',
          imageUrl: getEventImageUrl(dbEvent.image_url, dbEvent.id),
          industry: dbEvent.industry || 'General',
          url: dbEvent.url,
          place: dbEvent.place,
          source: dbEvent.source,
          likes: 0,
          dislikes: 0,
          userReaction: null,
          saved: false
        }));
        console.log(`Converted ${convertedEvents.length} events`);
        setEvents(convertedEvents);
      } catch (error) {
        console.error('Error loading events:', error);
        // Show error to user
        alert(`Failed to load events: ${error instanceof Error ? error.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

  // User Data State
  const [userProfile, setUserProfile] = useState<UserProfile>({
    name: user ? `${user.name} ${user.surname}` : 'Guest',
    title: 'Venture Partner',
    company: 'Activat VC',
    interests: ['FinTech', 'AI', 'Investment', 'SaaS']
  });

  // Initialize settings from localStorage or defaults
  const [settings, setSettings] = useState<AppSettings>(() => {
    const savedSettings = loadSettings();
    return savedSettings || {
      telegramNotifications: true,
      region: 'Казахстан',
      language: 'English'
    };
  });

  // Save settings to localStorage whenever they change
  useEffect(() => {
    saveSettings(settings);
  }, [settings]);

  // Update user profile when user changes
  useEffect(() => {
    if (user) {
      setUserProfile(prev => ({
        ...prev,
        name: `${user.name} ${user.surname}`
      }));
    }
  }, [user]);

  // Derived State
  const filteredEvents = useMemo(() => {
    const filtered = events.filter(event => {
      // Industry matching
      const industryMatch = selectedIndustry === 'All' || 
        event.industry === selectedIndustry ||
        (selectedIndustry === 'Agrosector' && (event.industry === 'Агросектор' || event.industry === 'Agrosector')) ||
        (selectedIndustry === 'Energy' && (event.industry === 'Энергетика' || event.industry === 'Energy')) ||
        (selectedIndustry === 'Retail' && (event.industry === 'Ритейл/FMCG' || event.industry === 'Retail')) ||
        (selectedIndustry === 'IT/Digital' && event.industry === 'IT/Digital');
      
      // Country matching
      const countryMatch = !selectedCountry || event.country === selectedCountry;
      
      // City matching (only if country is selected and city is selected)
      const cityMatch = !selectedCity || event.city === selectedCity;
      
      // Search matching - search in name, title, description, country
      const searchMatch = !searchQuery || 
        event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.country.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (event.name && event.name.toLowerCase().includes(searchQuery.toLowerCase()));
      
      return industryMatch && countryMatch && cityMatch && searchMatch;
    });

    // Sort events: primary region first, then others
    if (settings.region) {
      return filtered.sort((a, b) => {
        const aIsPrimaryRegion = a.country === settings.region;
        const bIsPrimaryRegion = b.country === settings.region;
        
        // Primary region events come first
        if (aIsPrimaryRegion && !bIsPrimaryRegion) return -1;
        if (!aIsPrimaryRegion && bIsPrimaryRegion) return 1;
        
        // Within same group, maintain original order (or sort by date if needed)
        return 0;
      });
    }
    
    return filtered;
  }, [events, selectedIndustry, selectedCountry, selectedCity, searchQuery, settings.region]);

  const selectedEvent = useMemo(() => 
    events.find(e => e.id === selectedEventId), 
  [events, selectedEventId]);

  const savedEvents = useMemo(() => 
    events.filter(e => e.saved), 
  [events]);

  // Handlers
  const handleFeedback = useCallback((e: React.MouseEvent, id: string, type: 'like' | 'dislike') => {
    e.stopPropagation(); // Prevent opening detail view
    setEvents(prevEvents => prevEvents.map(event => {
      if (event.id !== id) return event;
      
      const isRemoving = event.userReaction === type;
      const newReaction = isRemoving ? null : type;
      
      let newLikes = event.likes;
      let newDislikes = event.dislikes;

      // Reset counts based on old reaction
      if (event.userReaction === 'like') newLikes--;
      if (event.userReaction === 'dislike') newDislikes--;

      // Increment based on new reaction
      if (newReaction === 'like') newLikes++;
      if (newReaction === 'dislike') newDislikes++;

      return {
        ...event,
        userReaction: newReaction,
        likes: newLikes,
        dislikes: newDislikes
      };
    }));
  }, []);

  const toggleSave = useCallback((id: string) => {
    setEvents(prev => prev.map(e => e.id === id ? { ...e, saved: !e.saved } : e));
  }, []);

  const handleUpdateSettings = (key: keyof AppSettings, value: any) => {
    setSettings(prev => {
      const updated = { ...prev, [key]: value };
      saveSettings(updated);
      return updated;
    });
  };

  const handleLogin = (loggedInUser: AuthUser) => {
    setUser(loggedInUser);
    saveUserSession(loggedInUser);
    setShowSignup(false);
  };

  const handleSignup = (newUser: AuthUser) => {
    setUser(newUser);
    saveUserSession(newUser);
    setShowSignup(false);
  };

  const handleSignOut = () => {
    setUser(null);
    saveUserSession(null);
    setActiveTab('feed');
  };

  // Show login/signup if not authenticated
  if (!user) {
    return showSignup ? (
      <SignupPage onSignup={handleSignup} onSwitchToLogin={() => setShowSignup(false)} language={settings.language} />
    ) : (
      <LoginPage onLogin={handleLogin} onSwitchToSignup={() => setShowSignup(true)} language={settings.language} />
    );
  }

  return (
    <div className="min-h-screen bg-lightBg font-sans text-textMain">
      <Header searchQuery={searchQuery} onSearchChange={setSearchQuery} language={settings.language} />

      <main className="pt-16 min-h-screen relative">
        {/* Detail Overlay */}
        {selectedEvent && (
          <EventDetail 
            event={selectedEvent} 
            onClose={() => setSelectedEventId(null)} 
            onSave={toggleSave}
            language={settings.language}
          />
        )}

        {/* FEED TAB */}
        <div style={{ display: activeTab === 'feed' ? 'block' : 'none' }}>
           <div className="sticky top-16 z-40 bg-lightBg/95 backdrop-blur-md pt-3 pb-3 border-b border-borderLight shadow-sm">
              <div className="flex items-center justify-between px-6">
                <FilterRibbon 
                  items={INDUSTRIES} 
                  selectedItem={selectedIndustry} 
                  onSelect={(i) => setSelectedIndustry(i as Industry)} 
                />
                <button
                  onClick={() => setIsFilterOpen(true)}
                  className="flex-shrink-0 ml-4 p-2.5 rounded-xl bg-activatBlue text-white hover:bg-blue-600 transition-colors shadow-sm flex items-center justify-center"
                  aria-label="Open filters"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Filter Modal */}
            <FilterModal
              isOpen={isFilterOpen}
              onClose={() => setIsFilterOpen(false)}
              selectedCountry={selectedCountry}
              selectedCity={selectedCity}
              searchQuery={searchQuery}
              onCountryChange={setSelectedCountry}
              onCityChange={setSelectedCity}
              onSearchChange={setSearchQuery}
              language={settings.language}
            />

            <div className="px-6 py-6 pb-24 max-w-2xl mx-auto">
              {loading ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-activatBlue mb-4"></div>
                  <p className="text-slateGrey">{t('loadingEvents', getLanguageCode(settings.language))}</p>
                </div>
              ) : filteredEvents.length > 0 ? (
                <>
                  {process.env.NODE_ENV === 'development' && (
                    <div className="mb-4 p-2 bg-blue-50 text-blue-700 text-xs rounded">
                      {t('showingEvents', getLanguageCode(settings.language))
                        .replace('{count}', filteredEvents.length.toString())
                        .replace('{total}', events.length.toString())}
                    </div>
                  )}
                  {filteredEvents.map(event => (
                    <EventCard 
                      key={event.id} 
                      event={event} 
                      onFeedback={handleFeedback}
                      onClick={(e) => setSelectedEventId(e.id)}
                      language={settings.language}
                    />
                  ))}
                </>
              ) : events.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-slateGrey">
                  <p>{t('noEventsLoaded', getLanguageCode(settings.language))}</p>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-slateGrey">
                  <p>{t('noEventsFound', getLanguageCode(settings.language))}</p>
                  <p className="text-xs mt-2">{t('totalEvents', getLanguageCode(settings.language))} {events.length}</p>
                  <button 
                    onClick={() => {
                      setSelectedIndustry('All');
                      setSelectedCountry(null);
                      setSelectedCity(null);
                      setSearchQuery('');
                    }}
                    className="mt-4 text-activatBlue text-sm hover:underline font-medium"
                  >
                    {t('resetFilters', getLanguageCode(settings.language))}
                  </button>
                </div>
              )}
            </div>
        </div>

        {/* SETTINGS TAB */}
        {activeTab === 'settings' && (
          <SettingsView settings={settings} onUpdate={handleUpdateSettings} onSignOut={handleSignOut} />
        )}

        {/* PROFILE TAB */}
        {activeTab === 'profile' && (
          <ProfileView 
            profile={userProfile} 
            onUpdateProfile={setUserProfile} 
            savedEvents={savedEvents}
            onEventClick={setSelectedEventId}
            language={settings.language}
          />
        )}
      </main>

      <Navigation activeTab={activeTab} onTabChange={setActiveTab} language={settings.language} />
    </div>
  );
}

export default App;