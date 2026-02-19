import { supabaseGet, supabasePost, supabasePatch, supabaseDelete } from './supabase';

export interface DatabaseEvent {
  id: number;
  name: string | null;
  title: string;
  description: string | null;
  city: string | null;
  country: string | null;
  start_date: string | null;
  end_date: string | null;
  url: string;
  source: string | null;
  industry: string | null;
  place: string | null;
  image_url: string | null;
}

interface FeedbackRow {
  event_id: number;
  is_positive: boolean;
}

export interface EventFeedbackCounts {
  [eventId: number]: { likes: number; dislikes: number };
}

export async function loadEvents(): Promise<DatabaseEvent[]> {
  try {
    console.log('Loading events from Supabase...');
    const events = await supabaseGet<DatabaseEvent>(
      'events',
      'select=id,name,title,description,city,country,start_date,end_date,url,source,industry,place,image_url&order=start_date.desc.nullslast'
    );
    console.log(`Loaded ${events.length} events from Supabase`);
    return events;
  } catch (error) {
    console.error('Error loading events from Supabase:', error);
    throw error;
  }
}

export async function submitFeedback(eventId: number, userId: number, isPositive: boolean): Promise<void> {
  try {
    // Check if feedback already exists for this user and event
    const existingFeedback = await supabaseGet<{ id: number; is_positive: boolean }>(
      'feedbacks',
      `select=id,is_positive&user_id=eq.${userId}&event_id=eq.${eventId}`
    );

    if (existingFeedback.length > 0) {
      // Update existing feedback if it's different
      const existing = existingFeedback[0];
      if (existing.is_positive !== isPositive) {
        // Update the existing feedback
        await supabasePatch('feedbacks', {
          is_positive: isPositive,
          reason: null,
        }, `id=eq.${existing.id}`);
      }
      // If same, do nothing (already exists)
    } else {
      // Create new feedback
      await supabasePost('feedbacks', {
        user_id: userId,
        event_id: eventId,
        is_positive: isPositive,
        reason: null,
      });
    }
  } catch (error) {
    console.error('Error submitting feedback:', error);
    throw error;
  }
}

export async function deleteFeedback(eventId: number, userId: number): Promise<void> {
  try {
    await supabaseDelete('feedbacks', `user_id=eq.${userId}&event_id=eq.${eventId}`);
  } catch (error) {
    console.error('Error deleting feedback:', error);
    throw error;
  }
}

export async function loadFeedbackCounts(userId?: number): Promise<EventFeedbackCounts> {
  try {
    const rows = await supabaseGet<FeedbackRow>(
      'feedbacks',
      'select=event_id,is_positive'
    );
    const counts: EventFeedbackCounts = {};
    for (const row of rows) {
      if (!counts[row.event_id]) {
        counts[row.event_id] = { likes: 0, dislikes: 0 };
      }
      if (row.is_positive) {
        counts[row.event_id].likes++;
      } else {
        counts[row.event_id].dislikes++;
      }
    }
    return counts;
  } catch (error) {
    console.error('Error loading feedback counts:', error);
    return {};
  }
}

interface UserFeedbackRow {
  event_id: number;
  is_positive: boolean;
}

export async function loadUserReactions(userId: number): Promise<Record<number, 'like' | 'dislike'>> {
  try {
    const rows = await supabaseGet<UserFeedbackRow>(
      'feedbacks',
      `select=event_id,is_positive&user_id=eq.${userId}`
    );
    const reactions: Record<number, 'like' | 'dislike'> = {};
    for (const row of rows) {
      reactions[row.event_id] = row.is_positive ? 'like' : 'dislike';
    }
    return reactions;
  } catch (error) {
    console.error('Error loading user reactions:', error);
    return {};
  }
}
