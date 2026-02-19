import React from 'react';
import { ThumbsUp, ThumbsDown, Calendar, MapPin, ChevronRight } from 'lucide-react';
import { Event } from '../types';
import { translateCountryName, getLanguageCode, Language } from '../utils/translations';

interface EventCardProps {
  event: Event;
  onFeedback: (e: React.MouseEvent, id: string, type: 'like' | 'dislike') => void;
  onClick: (event: Event) => void;
  language?: string;
}

export const EventCard: React.FC<EventCardProps> = ({ event, onFeedback, onClick, language = 'English' }) => {
  const [imageError, setImageError] = React.useState(false);
  const [imageSrc, setImageSrc] = React.useState(event.imageUrl);
  const langCode = getLanguageCode(language);
  
  const handleImageError = () => {
    if (!imageError) {
      setImageError(true);
      // Fallback to Picsum Photos if the image fails to load
      setImageSrc(`https://picsum.photos/seed/${event.id}/800/450`);
    }
  };

  return (
    <div 
      onClick={() => onClick(event)}
      className="w-full mb-6 group bg-white rounded-2xl border border-borderLight shadow-soft overflow-hidden hover:shadow-lg transition-all duration-300 active:scale-[0.99] cursor-pointer"
    >
      {/* Image Container */}
      <div className="relative w-full aspect-video overflow-hidden bg-slate-100">
        <img 
          src={imageSrc} 
          alt={event.title}
          className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
          loading="lazy"
          onError={handleImageError}
        />
        {/* Industry Badge overlay */}
        <div className="absolute top-3 left-3 px-2.5 py-1 bg-white/90 backdrop-blur-md rounded-lg shadow-sm text-[10px] font-bold text-textMain uppercase tracking-wider">
          {event.industry}
        </div>
      </div>

      {/* Content */}
      <div className="p-5 flex flex-col gap-4">
        {/* Title */}
        <h3 className="text-[18px] font-bold text-textMain leading-tight font-sans line-clamp-2">
          {event.title}
        </h3>

        {/* Description */}
        {event.description && (
          <p className="text-sm text-textSec line-clamp-2 leading-relaxed">
            {event.description}
          </p>
        )}

        <div className="flex-1" />

        {/* Footer: Location & Date */}
        <div className="flex items-center justify-between pt-3 border-t border-borderLight">
            <div className="flex items-center gap-2 text-slateGrey text-xs font-medium">
            <div className="flex items-center gap-1.5">
              <MapPin size={14} className="text-activatBlue" />
              <span className="font-semibold">{translateCountryName(event.country, langCode)}</span>
              {event.city && event.city !== 'Unknown' && <span className="text-slateGrey">• {event.city}</span>}
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar size={14} className="text-activatBlue ml-2" />
              <span>{event.date}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button 
              onClick={(e) => onFeedback(e, event.id, 'like')}
              className={`flex items-center gap-1.5 p-1.5 rounded-full transition-colors duration-200 hover:bg-slate-50 ${event.userReaction === 'like' ? 'text-activatBlue' : 'text-slateGrey'}`}
            >
              <ThumbsUp 
                size={18} 
                strokeWidth={1.5} 
                className={event.userReaction === 'like' ? 'fill-activatBlue/20' : ''}
              />
              <span className="text-xs font-medium">{event.likes}</span>
            </button>
            
            <button 
              onClick={(e) => onFeedback(e, event.id, 'dislike')}
              className={`flex items-center gap-1.5 p-1.5 rounded-full transition-colors duration-200 hover:bg-slate-50 ${event.userReaction === 'dislike' ? 'text-red-500' : 'text-slateGrey'}`}
            >
              <ThumbsDown 
                size={18} 
                strokeWidth={1.5} 
                className={event.userReaction === 'dislike' ? 'fill-red-500/20' : ''}
              />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};