import React from 'react';
import { X, Calendar, MapPin, Share2, Globe, Heart, ExternalLink, Building2, Tag } from 'lucide-react';
import { Event } from '../types';
import { ShareModal } from './ShareModal';
import { t, getLanguageCode, translateCountryName, Language } from '../utils/translations';

interface EventDetailProps {
  event: Event;
  onClose: () => void;
  onSave: (id: string) => void;
  language?: string;
}

export const EventDetail: React.FC<EventDetailProps> = ({ event, onClose, onSave, language = 'English' }) => {
  const [imageError, setImageError] = React.useState(false);
  const [imageSrc, setImageSrc] = React.useState(event.imageUrl);
  const [isShareOpen, setIsShareOpen] = React.useState(false);
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);
  
  const handleImageError = () => {
    if (!imageError) {
      setImageError(true);
      // Fallback to Picsum Photos if the image fails to load
      setImageSrc(`https://picsum.photos/seed/${event.id}/800/450`);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] bg-surface flex flex-col animate-in slide-in-from-bottom-10 duration-200">
      {/* Detail Header with Image */}
      <div className="relative w-full h-64 flex-shrink-0">
        <img 
          src={imageSrc} 
          alt={event.title}
          className="w-full h-full object-cover"
          onError={handleImageError}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
        
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 p-2 bg-black/20 backdrop-blur-md rounded-full text-white hover:bg-black/40 transition-colors"
        >
          <X size={24} />
        </button>

        <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
           <span className="inline-block px-2 py-1 mb-2 text-xs font-bold bg-activatBlue rounded-md uppercase tracking-wider">
             {event.industry}
           </span>
           <h1 className="text-2xl font-bold leading-tight">{event.title}</h1>
        </div>
      </div>

      {/* Content Scrollable Area */}
      <div className="flex-1 overflow-y-auto bg-surface">
        <div className="p-6 space-y-6">
          
          {/* Key Info */}
          <div className="flex flex-col gap-4 p-5 bg-lightBg rounded-xl border border-borderLight shadow-sm">
            {/* Date & Time */}
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-white rounded-xl shadow-sm text-activatBlue flex-shrink-0">
                <Calendar size={20} />
              </div>
              <div className="flex-1">
                <p className="text-xs text-slateGrey uppercase font-semibold tracking-wider mb-1">{translate('dateTime')}</p>
                <p className="text-sm font-semibold text-textMain">
                  {event.startDate 
                    ? new Date(event.startDate).toLocaleDateString('en-US', { 
                        weekday: 'long',
                        month: 'long', 
                        day: 'numeric', 
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })
                    : event.date}
                </p>
                {event.endDate && event.endDate !== event.startDate && (
                  <p className="text-xs text-slateGrey mt-1">
                    {translate('until')} {new Date(event.endDate).toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric', 
                      year: 'numeric' 
                    })}
                  </p>
                )}
              </div>
            </div>
            
            <div className="h-[1px] bg-borderLight w-full" />

            {/* Location */}
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-white rounded-xl shadow-sm text-activatBlue flex-shrink-0">
                <MapPin size={20} />
              </div>
              <div className="flex-1">
                <p className="text-xs text-slateGrey uppercase font-semibold tracking-wider mb-1">{translate('location')}</p>
                <p className="text-sm font-semibold text-textMain">
                  {event.place || (event.city && event.city !== 'Unknown' ? event.city : '') || 'TBD'}
                  {event.city && event.city !== 'Unknown' && event.place && event.city !== event.place && `, ${event.city}`}
                  {event.country && `, ${translateCountryName(event.country, langCode)}`}
                </p>
              </div>
            </div>

            {/* Source */}
            {event.source && (
              <>
                <div className="h-[1px] bg-borderLight w-full" />
                <div className="flex items-start gap-3">
                  <div className="p-2.5 bg-white rounded-xl shadow-sm text-activatBlue flex-shrink-0">
                    <Tag size={20} />
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-slateGrey uppercase font-semibold tracking-wider mb-1">{translate('source')}</p>
                    <p className="text-sm font-semibold text-textMain">{event.source}</p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Description */}
          {event.description && (
            <div className="bg-white rounded-xl border border-borderLight p-5 shadow-sm">
              <h3 className="text-lg font-bold text-textMain mb-3 flex items-center gap-2">
                <div className="w-1 h-5 bg-activatBlue rounded-full"></div>
                {translate('aboutEvent')}
              </h3>
              <p className="text-textSec leading-relaxed text-sm whitespace-pre-wrap">
                {event.description}
              </p>
            </div>
          )}

          {/* Industry Badge */}
          {event.industry && (
            <div className="flex flex-wrap gap-2">
              <span className="px-4 py-2 rounded-full bg-activatBlue/10 text-activatBlue text-xs font-bold uppercase tracking-wider border border-activatBlue/20">
                {event.industry}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Action Bar */}
      <div className="p-4 border-t border-borderLight bg-surface/95 backdrop-blur-xl pb-8 flex items-center gap-3">
        <button 
          onClick={() => onSave(event.id)}
          className={`p-3 rounded-xl border flex items-center justify-center transition-all duration-200 ${event.saved ? 'bg-red-50 border-red-200 text-red-500 shadow-sm' : 'bg-white border-borderLight text-slateGrey hover:bg-slate-50'}`}
        >
          <Heart size={20} className={event.saved ? "fill-current" : ""} />
        </button>
        <button 
          onClick={() => setIsShareOpen(true)}
          className="p-3 rounded-xl border border-borderLight bg-white text-slateGrey flex items-center justify-center hover:bg-slate-50 transition-colors"
        >
          <Share2 size={20} />
        </button>
        {event.url ? (
          <a 
            href={event.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 bg-activatBlue text-white font-semibold py-3 px-6 rounded-xl hover:bg-blue-600 transition-all duration-200 flex items-center justify-center gap-2 shadow-md shadow-activatBlue/20 active:scale-[0.98]"
          >
            <Globe size={18} />
            {translate('visitEventPage')}
            <ExternalLink size={16} />
          </a>
        ) : (
          <button className="flex-1 bg-activatBlue text-white font-semibold py-3 px-6 rounded-xl hover:bg-blue-600 transition-colors flex items-center justify-center gap-2 shadow-md shadow-activatBlue/20">
            <Globe size={18} />
            {translate('registerNow')}
          </button>
        )}
      </div>

      {/* Share Modal */}
      <ShareModal
        isOpen={isShareOpen}
        onClose={() => setIsShareOpen(false)}
        eventUrl={event.url || ''}
        eventTitle={event.title}
      />
    </div>
  );
};