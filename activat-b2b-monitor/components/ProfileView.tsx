import React, { useState } from 'react';
import { UserProfile, Event } from '../types';
import { Edit2, Save, Plus, X, Heart, MapPin, CheckCircle } from 'lucide-react';
import { t, getLanguageCode, Language } from '../utils/translations';

interface ProfileViewProps {
  profile: UserProfile;
  onUpdateProfile: (p: UserProfile) => void;
  savedEvents: Event[];
  onEventClick: (eventId: string) => void;
  language?: string;
}

export const ProfileView: React.FC<ProfileViewProps> = ({ profile, onUpdateProfile, savedEvents, onEventClick, language = 'English' }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState(profile);
  const [newTag, setNewTag] = useState('');
  const langCode = getLanguageCode(language);
  const translate = (key: string) => t(key, langCode);

  const handleSave = () => {
    onUpdateProfile(editForm);
    setIsEditing(false);
  };

  const addTag = () => {
    if (newTag && !editForm.interests.includes(newTag)) {
      setEditForm({ ...editForm, interests: [...editForm.interests, newTag] });
      setNewTag('');
    }
  };

  const removeTag = (tag: string) => {
    setEditForm({ ...editForm, interests: editForm.interests.filter(t => t !== tag) });
  };

  return (
    <div className="px-6 py-8 pb-32 max-w-lg mx-auto">
      {/* Profile Header Card */}
      <div className="bg-white rounded-2xl border border-borderLight shadow-soft p-6 mb-8 text-center relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-20 bg-gradient-to-r from-blue-600 to-activatBlue opacity-10"></div>
        <div className="relative z-10 flex flex-col items-center">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-activatBlue to-indigo-600 mb-4 flex items-center justify-center text-3xl font-bold text-white shadow-lg border-4 border-white">
            {profile.name.split(' ').map(n => n[0]).join('')}
          </div>
          
          {isEditing ? (
            <div className="w-full space-y-3 mt-2">
              <input 
                type="text" 
                value={editForm.name} 
                onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                className="w-full p-2 text-center font-bold text-lg border-b border-activatBlue outline-none bg-transparent"
                placeholder={translate('fullName')}
              />
              <input 
                type="text" 
                value={editForm.title} 
                onChange={(e) => setEditForm({...editForm, title: e.target.value})}
                className="w-full p-2 text-center text-sm border-b border-borderLight outline-none bg-transparent"
                placeholder={translate('jobTitle')}
              />
              <input 
                type="text" 
                value={editForm.company} 
                onChange={(e) => setEditForm({...editForm, company: e.target.value})}
                className="w-full p-2 text-center text-sm border-b border-borderLight outline-none bg-transparent"
                placeholder={translate('companyName')}
              />
            </div>
          ) : (
            <>
              <h2 className="text-xl font-bold text-textMain">{profile.name}</h2>
              <p className="text-activatBlue font-medium text-sm mt-1">{profile.title}</p>
              <p className="text-slateGrey text-xs mt-1">{profile.company}</p>
            </>
          )}

          <button 
            onClick={() => isEditing ? handleSave() : setIsEditing(true)}
            className={`mt-6 px-6 py-2 rounded-full text-xs font-semibold uppercase tracking-wide transition-all ${isEditing ? 'bg-green-500 text-white shadow-green-200 shadow-lg' : 'bg-slate-50 text-slateGrey hover:bg-slate-100'}`}
          >
            {isEditing ? <span className="flex items-center gap-2"><CheckCircle size={14}/> {translate('saveChanges')}</span> : <span className="flex items-center gap-2"><Edit2 size={14}/> {translate('editProfile')}</span>}
          </button>
        </div>
      </div>

      {/* Interests Section */}
      <section className="mb-8">
        <h3 className="text-sm font-bold text-textMain mb-3 flex items-center gap-2">
           {translate('interestsFocus')}
        </h3>
        <div className="flex flex-wrap gap-2">
          {(isEditing ? editForm.interests : profile.interests).map(tag => (
            <span key={tag} className="px-3 py-1.5 rounded-full bg-white border border-borderLight text-slateGrey text-xs font-medium flex items-center gap-1 shadow-sm">
              {tag}
              {isEditing && (
                <button onClick={() => removeTag(tag)} className="text-slate-400 hover:text-red-500"><X size={12}/></button>
              )}
            </span>
          ))}
          
          {isEditing && (
            <div className="flex items-center gap-2">
              <input 
                type="text" 
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder={translate('addTopic')}
                className="px-3 py-1.5 rounded-full bg-white border border-activatBlue text-xs outline-none w-24"
                onKeyPress={(e) => e.key === 'Enter' && addTag()}
              />
              <button onClick={addTag} className="p-1 bg-activatBlue text-white rounded-full"><Plus size={14}/></button>
            </div>
          )}
        </div>
      </section>

      {/* Saved Events Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-textMain">{translate('savedEvents')}</h3>
          <span className="text-xs font-medium px-2 py-0.5 bg-activatBlue/10 text-activatBlue rounded-full">{savedEvents.length}</span>
        </div>
        
        {savedEvents.length > 0 ? (
          <div className="space-y-3">
            {savedEvents.map(event => (
              <button
                key={event.id}
                onClick={() => onEventClick(event.id)}
                className="w-full flex gap-3 p-3 bg-white rounded-xl border border-borderLight shadow-sm hover:shadow-md hover:border-activatBlue/30 transition-all text-left"
              >
                <img src={event.imageUrl} className="w-16 h-16 rounded-lg object-cover bg-slate-100" />
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-textMain line-clamp-1">{event.title}</h4>
                  <p className="text-xs text-slateGrey mt-1 flex items-center gap-1"><MapPin size={10} /> {event.city}</p>
                  <p className="text-xs text-activatBlue mt-1 font-medium">{event.date}</p>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center border border-dashed border-slate-300 rounded-xl">
            <Heart className="mx-auto text-slate-300 mb-2" />
            <p className="text-sm text-slateGrey">{translate('noSavedEvents')}</p>
          </div>
        )}
      </section>
    </div>
  );
};