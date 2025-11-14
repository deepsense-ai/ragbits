-- SQLBook: Code
SELECT name FROM sqlite_master WHERE type='table';

SELECT 
    h.name AS hotel_name,
    h.city,
    h.rating,
    r.number AS room_number,
    r.room_type,
    r.price_per_night,
    r.capacity
FROM hotels h
JOIN rooms r ON h.id = r.hotel_id
JOIN room_availability ra ON r.id = ra.room_id
WHERE h.city = 'Kraków'
  AND r.room_type = 'deluxe'
  AND ra.available_date >= '2025-03-15'
  AND ra.available_date <= '2025-03-17'
  AND ra.is_reserved = 0
GROUP BY h.id, r.id
ORDER BY h.name, r.room_type, r.price_per_night;


