import re
from typing import List, Dict, Any


def clean_up_word(text: str) -> str:
    """Cleans text from extra whitespace, newlines, and tabs."""
    return re.sub(r'[\s\n\t]+', ' ', text).strip()


def extract_structured_events(
        entities: List[Dict[str, Any]]
) -> dict[str, list[Any]] | dict[str, list[Any]] | list[dict[str, str | list[Any] | Any]]:
    """
    Main function to extract and structure event details, including a detailed schedule,
    using adaptive logic based on the number of events found.
    """
    if not entities:
        return {"data": []}

    # 1. Group all entities by their type for efficient access
    grouped_entities = {}
    for entity in entities:
        # Standardize the text key to 'word'
        entity['word'] = entity.get('entity_text', '') or entity.get('word')
        group = entity.get('entity_group')
        if group and 'word' in entity:
            if group not in grouped_entities:
                grouped_entities[group] = []
            grouped_entities[group].append(entity)

    # Use 'EVTDATE' as the primary anchor for ordering events
    date_anchors = sorted(grouped_entities.get('EVTDATE', []), key=lambda x: x['start'])
    if not date_anchors:
        return {"data": []}

    # 2. Build the basic framework for each event
    events = []
    all_evts = sorted(grouped_entities.get('EVT', []), key=lambda x: x['start'])
    all_times = sorted(grouped_entities.get('EVTTIME', []), key=lambda x: x['start'])
    all_locs = sorted(grouped_entities.get('EVTLOC', []), key=lambda x: x['start'])

    for i, current_date in enumerate(date_anchors):
        start_boundary = date_anchors[i - 1]['start'] if i > 0 else -1
        end_boundary = current_date['start']

        evts_in_range = [e for e in all_evts if start_boundary < e['start'] < end_boundary]
        main_event = min(evts_in_range,
                         key=lambda e: abs(e['start'] - current_date['start'])) if evts_in_range else None

        if not main_event:
            continue

        main_time = min(all_times, key=lambda e: abs(e['start'] - main_event['start'])) if all_times else None
        main_loc = min(all_locs, key=lambda e: abs(e['start'] - main_event['start'])) if all_locs else None

        events.append({
            "eventName": clean_up_word(main_event['word']),
            "date": clean_up_word(current_date['word']),
            "time": clean_up_word(main_time['word']) if main_time else "",
            "location": clean_up_word(main_loc['word']) if main_loc else "",
            "organizers": [],
            "attendees": "",
            "equipment": [],
            "schedule": [],  # New field for the event agenda
            "_event_start_pos": main_event['start']
        })

    # 3. Allocate all other details to the correct event block

    # Organizers Allocation
    all_persons = sorted(grouped_entities.get('PER', []), key=lambda x: x['start'])
    all_phones = sorted(grouped_entities.get('PHONE', []), key=lambda x: x['start'])
    for person in all_persons:
        closest_event = None
        min_dist_event = float('inf')
        for event in events:
            if person['start'] > event['_event_start_pos']:
                dist = person['start'] - event['_event_start_pos']
                if dist < min_dist_event:
                    min_dist_event = dist
                    closest_event = event

        if closest_event:
            phone_candidates = [p for p in all_phones if p['start'] > person['end']]
            closest_phone = min(phone_candidates,
                                key=lambda p: p['start'] - person['end']) if phone_candidates else None

            organizer_data = {"name": clean_up_word(person['word']), "contact": ""}
            if closest_phone and (closest_phone['start'] - person['end']) < 50:
                organizer_data["contact"] = clean_up_word(closest_phone['word'])

            closest_event['organizers'].append(organizer_data)

    # Equipment Allocation
    all_items = sorted(grouped_entities.get('ITEM', []), key=lambda x: x['start'])
    all_item_qtys = sorted(grouped_entities.get('ITEMQTY', []), key=lambda x: x['start'])
    for item in all_items:
        closest_event = None
        min_dist_event = float('inf')
        for event in events:
            if item['start'] > event['_event_start_pos']:
                dist = item['start'] - event['_event_start_pos']
                if dist < min_dist_event:
                    min_dist_event = dist
                    closest_event = event

        if closest_event:
            qty_candidates = [q for q in all_item_qtys if q['start'] >= item['end']]
            closest_qty = min(qty_candidates, key=lambda q: q['start'] - item['end']) if qty_candidates else None

            quantity = "1"
            if closest_qty and (closest_qty['start'] - item['end']) < 10:
                quantity = clean_up_word(closest_qty['word'])

            closest_event['equipment'].append({"item": clean_up_word(item['word']), "quantity": quantity})

    # Attendee Description Allocation
    all_qty_peserta = sorted(grouped_entities.get('PEOQTY', []), key=lambda x: x['start'])
    for qty in all_qty_peserta:
        closest_event = None
        min_dist_event = float('inf')
        for event in events:
            if qty['start'] > event['_event_start_pos']:
                dist = qty['start'] - event['_event_start_pos']
                if dist < min_dist_event:
                    min_dist_event = dist
                    closest_event = event

        if closest_event and not closest_event['attendees']:
            closest_event['attendees'] = clean_up_word(qty['word'])

    # --- New Block: Schedule Allocation with Adaptive Logic ---
    all_schedule_items = sorted(grouped_entities.get('SCHEDULE_ITEM', []), key=lambda x: x['start'])
    all_schedule_times = sorted(grouped_entities.get('SCHEDULE_TIME', []), key=lambda x: x['start'])
    all_schedule_durations = sorted(grouped_entities.get('SCHEDULE_DURATION', []), key=lambda x: x['start'])

    is_single_event_document = len(events) == 1

    for item in all_schedule_items:
        parent_event = None
        if is_single_event_document:
            parent_event = events[0]
        else:
            # Multi-event logic: find the closest preceding event
            closest_event = None
            min_dist_event = float('inf')
            for event in events:
                if item['start'] > event['_event_start_pos']:
                    dist = item['start'] - event['_event_start_pos']
                    if dist < min_dist_event:
                        min_dist_event = dist
                        closest_event = event
            parent_event = closest_event

        if parent_event:
            # Find associated times and duration for this specific item
            # Look for 2 times and 1 duration that appear right before the item description
            time_candidates = [t for t in all_schedule_times if t['end'] <= item['start']]
            duration_candidates = [d for d in all_schedule_durations if d['end'] <= item['start']]

            # Get the closest duration
            closest_duration = min(duration_candidates,
                                   key=lambda d: item['start'] - d['end']) if duration_candidates else None

            # Get the two closest times
            time_candidates.sort(key=lambda t: item['start'] - t['end'])
            start_time_entity = time_candidates[0] if len(time_candidates) > 0 else None
            end_time_entity = time_candidates[1] if len(time_candidates) > 1 else None

            # Build schedule object, ensuring we don't cross over details from other items
            schedule_obj = {
                "description": clean_up_word(item['word']),
                "startTime": "",
                "endTime": "",
                "duration": ""
            }

            if start_time_entity and (item['start'] - start_time_entity['end'] < 50):
                schedule_obj["startTime"] = clean_up_word(start_time_entity['word'])
            if end_time_entity and start_time_entity and (start_time_entity['start'] - end_time_entity['end'] < 20):
                # Swap if endTime is before startTime
                schedule_obj["startTime"] = clean_up_word(end_time_entity['word'])
                schedule_obj["endTime"] = clean_up_word(start_time_entity['word'])

            if closest_duration and (item['start'] - closest_duration['end'] < 20):
                schedule_obj["duration"] = clean_up_word(closest_duration['word'])

            parent_event['schedule'].append(schedule_obj)

    # 4. Final cleanup and wrapping the response
    for event in events:
        del event['_event_start_pos']

    return events
