-- ====================================================================
-- CampusConnect — Operational & Analytical Sample SQL Queries
-- Demonstrating RDBMS concepts: Joins, Aggregations, Subqueries, & Window Functions
-- ====================================================================

-- 1. Identify Upcoming Events Near Maximum Capacity (> 85% Booked)
SELECT 
    e.title,
    e.event_date,
    c.name AS organizing_club,
    e.max_capacity,
    COUNT(er.id) AS confirmed_bookings,
    (e.max_capacity - COUNT(er.id)) AS seats_remaining,
    ROUND((COUNT(er.id) * 100.0 / e.max_capacity), 1) AS booking_percentage
FROM dbo.events e
INNER JOIN dbo.clubs c ON e.club_id = c.id
LEFT JOIN dbo.event_registrations er ON e.id = er.event_id AND er.status = 'confirmed'
WHERE e.event_date >= SYSUTCDATETIME() AND e.status = 'published'
GROUP BY e.id, e.title, e.event_date, c.name, e.max_capacity
HAVING (COUNT(er.id) * 100.0 / e.max_capacity) >= 85.0
ORDER BY booking_percentage DESC;

-- 2. Top 5 Most Active Students Across Campus
SELECT TOP 5
    u.student_id,
    u.name,
    u.department,
    COUNT(DISTINCT cm.club_id) AS clubs_joined,
    COUNT(DISTINCT er.id) AS events_registered,
    COUNT(DISTINCT a.id) AS events_attended
FROM dbo.users u
LEFT JOIN dbo.club_memberships cm ON u.id = cm.user_id
LEFT JOIN dbo.event_registrations er ON u.id = er.user_id AND er.status = 'confirmed'
LEFT JOIN dbo.attendance a ON u.id = a.user_id
WHERE u.role = 'student'
GROUP BY u.id, u.student_id, u.name, u.department
ORDER BY events_attended DESC, events_registered DESC;

-- 3. Monthly Registration Growth Trends
SELECT 
    DATEFROMPARTS(YEAR(er.registered_at), MONTH(er.registered_at), 1) AS [Month],
    e.category,
    COUNT(er.id) AS total_registrations
FROM dbo.event_registrations er
INNER JOIN dbo.events e ON er.event_id = e.id
WHERE er.status = 'confirmed'
GROUP BY YEAR(er.registered_at), MONTH(er.registered_at), e.category
ORDER BY [Month] ASC, total_registrations DESC;

-- 4. Check Unverified Attendees for Concluded Events
SELECT 
    e.title AS event_title,
    e.event_date,
    u.student_id,
    u.name AS student_name,
    u.email,
    er.registration_code
FROM dbo.event_registrations er
INNER JOIN dbo.events e ON er.event_id = e.id
INNER JOIN dbo.users u ON er.user_id = u.id
LEFT JOIN dbo.attendance a ON er.id = a.registration_id
WHERE e.event_date < SYSUTCDATETIME()
  AND er.status = 'confirmed'
  AND a.id IS NULL
ORDER BY e.event_date DESC;

-- 5. Audit Trail Inspection of Role Escalations or Suspicious Operations
SELECT 
    al.timestamp,
    al.action,
    al.entity_type,
    al.entity_id,
    initiator.name AS performed_by,
    initiator.role AS initiator_role,
    al.ip_address,
    al.details
FROM dbo.audit_logs al
LEFT JOIN dbo.users initiator ON al.user_id = initiator.id
WHERE al.action IN ('ROLE_CHANGE', 'USER_DEACTIVATED', 'ATTENDANCE_REMOVED')
ORDER BY al.timestamp DESC;
