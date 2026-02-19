import { Event, Industry, City } from './types';

export const INDUSTRIES: Industry[] = ['All', 'IT/Digital', 'Agrosector', 'Energy', 'Retail', 'Mining', 'Construction', 'Transport', 'Other'];
export const CITIES: City[] = ['All', 'Almaty', 'Алматы', 'Astana', 'Астана', 'Shymkent', 'Атырау', 'Ереван', 'Ташкент'];

export const COUNTRY_CITIES: Record<string, string[]> = {
  "Казахстан": [
    "Алматы", "Астана", "Шымкент", "Атырау", "Актау", "Караганда", "Актобе",
    "Тараз", "Павлодар", "Усть-Каменогорск", "Семей", "Костанай", "Кызылорда",
    "Уральск", "Петропавловск", "Туркестан", "Кокшетау", "Талдыкорган",
  ],
  "Узбекистан": ["Ташкент", "Самарканд", "Наманган"],
  "Азербайджан": ["Баку", "Гянджа"],
  "Грузия": ["Тбилиси", "Батуми", "Кутаиси"],
  "Армения": ["Ереван", "Ванадзор"],
  "Кыргызстан": ["Бишкек", "Ош"],
  "Таджикистан": ["Душанбе", "Худжанд"],
  "Туркменистан": ["Ашхабад", "Мары", "Туркменабат"],
};

export const MOCK_EVENTS: Event[] = [
  {
    id: '1',
    title: 'Digital Bridge Forum 2024',
    date: '12.05.2024',
    city: 'Astana',
    description: 'The largest technology forum in Central Asia. Discussing AI, GovTech, and the future of venture capital in the region.',
    imageUrl: 'https://picsum.photos/800/450?random=1',
    industry: 'IT/Digital',
    likes: 124,
    dislikes: 2,
    userReaction: null
  },
  {
    id: '2',
    title: 'AgroWorld Kazakhstan',
    date: '15.05.2024',
    city: 'Almaty',
    description: 'International exhibition for agriculture. Key topics: Sustainable farming, export logistics, and agri-tech innovations.',
    imageUrl: 'https://picsum.photos/800/450?random=2',
    industry: 'Agrosector',
    likes: 45,
    dislikes: 0,
    userReaction: null
  },
  {
    id: '3',
    title: 'FinTech Revolution Summit',
    date: '22.05.2024',
    city: 'Almaty',
    description: 'Exploring the future of banking, blockchain integration, and regulatory landscapes in the CIS region.',
    imageUrl: 'https://picsum.photos/800/450?random=3',
    industry: 'FinTech',
    likes: 89,
    dislikes: 5,
    userReaction: null
  },
  {
    id: '4',
    title: 'Green Energy Expo',
    date: '01.06.2024',
    city: 'Astana',
    description: 'Renewable energy solutions exhibition. Focus on wind, solar, and hydro power potential in Kazakhstan.',
    imageUrl: 'https://picsum.photos/800/450?random=4',
    industry: 'Energy',
    likes: 32,
    dislikes: 1,
    userReaction: null
  },
  {
    id: '5',
    title: 'Retail Tech Conference',
    date: '10.06.2024',
    city: 'Shymkent',
    description: 'Modernizing retail through digitalization. E-commerce strategies and supply chain optimization.',
    imageUrl: 'https://picsum.photos/800/450?random=5',
    industry: 'Retail',
    likes: 28,
    dislikes: 3,
    userReaction: null
  }
];