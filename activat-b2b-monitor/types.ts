export interface Event {
  id: string;
  name: string;
  title: string;
  date: string;
  startDate?: string;
  endDate?: string;
  city: string;
  country: string;
  description: string;
  imageUrl: string;
  industry: string;
  url?: string;
  place?: string;
  source?: string;
  likes: number;
  dislikes: number;
  userReaction?: 'like' | 'dislike' | null;
  saved?: boolean;
}

export interface UserProfile {
  name: string;
  title: string;
  company: string;
  interests: string[];
}

export interface AppSettings {
  telegramNotifications: boolean;
  region: string;
  language: string;
}

export interface AuthUser {
  username: string;
  name: string;
  surname: string;
}

export type Industry = 'All' | 'IT/Digital' | 'Agrosector' | 'FinTech' | 'Energy' | 'Retail' | 'Mining' | 'Агросектор' | 'Ритейл/FMCG' | 'Строительство' | 'Транспорт' | 'Энергетика';
export type City = 'All' | 'Almaty' | 'Astana' | 'Shymkent' | 'Karaganda' | 'Алматы' | 'Астана' | 'Атырау' | 'Ереван' | 'Ташкент';

export type NavTab = 'feed' | 'settings' | 'profile';