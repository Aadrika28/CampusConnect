-- ====================================================================
-- CampusConnect — Analytics & Reporting SQL Views
-- Designed for Power BI DirectQuery / Import & Institutional Reports
-- ====================================================================

-- 1. View: Event Registration and Attendance Performance
CREATE OR ALTER VIEW dbo.vw_EventPerformance AS
SELECT 
    e.id AS event_id,
    e.title AS event_title,
    e.category AS event_category,
    c.name AS club_name,
    e.venue,
    e.event_date,
    e.max_capacity,
    COUNT(DISTINCT er.id) AS total_registrations,
    COUNT(DISTINCT a.id) AS verified_attendance,
    (e.max_capacity - COUNT(DISTINCT er.id)) AS seats_remaining,
    CAST(
        CASE 
            WHEN COUNT(DISTINCT er.id) = 0 THEN 0.0
            ELSE (COUNT(DISTINCT a.id) * 100.0 / COUNT(DISTINCT er.id))
        END AS DECIMAL(5,2)
    ) AS attendance_rate_pct,
    CAST(
        (COUNT(DISTINCT er.id) * 100.0 / e.max_capacity) 
        AS DECIMAL(5,2)
    ) AS capacity_fill_rate_pct
FROM dbo.events e
INNER JOIN dbo.clubs c ON e.club_id = c.id
LEFT JOIN dbo.event_registrations er ON e.id = er.event_id AND er.status = 'confirmed'
LEFT JOIN dbo.attendance a ON e.id = a.event_id
GROUP BY e.id, e.title, e.category, c.name, e.venue, e.event_date, e.max_capacity;
GO

-- 2. View: Club Engagement & Member Growth
CREATE OR ALTER VIEW dbo.vw_ClubEngagement AS
SELECT 
    c.id AS club_id,
    c.name AS club_name,
    c.category AS club_category,
    c.faculty_coordinator,
    u.name AS leader_name,
    COUNT(DISTINCT cm.id) AS active_members_count,
    COUNT(DISTINCT e.id) AS total_events_hosted,
    COUNT(DISTINCT er.id) AS total_event_registrations,
    COUNT(DISTINCT a.id) AS total_event_attendances
FROM dbo.clubs c
LEFT JOIN dbo.users u ON c.leader_id = u.id
LEFT JOIN dbo.club_memberships cm ON c.id = cm.club_id
LEFT JOIN dbo.events e ON c.id = e.club_id
LEFT JOIN dbo.event_registrations er ON e.id = er.event_id AND er.status = 'confirmed'
LEFT JOIN dbo.attendance a ON e.id = a.event_id
WHERE c.is_active = 1
GROUP BY c.id, c.name, c.category, c.faculty_coordinator, u.name;
GO

-- 3. View: Student Participation Records
CREATE OR ALTER VIEW dbo.vw_StudentParticipationTranscript AS
SELECT 
    u.id AS student_user_id,
    u.student_id,
    u.name AS student_name,
    u.email AS student_email,
    u.department,
    u.batch_year,
    COUNT(DISTINCT cm.id) AS clubs_joined_count,
    COUNT(DISTINCT er.id) AS events_registered_count,
    COUNT(DISTINCT a.id) AS events_attended_count,
    CAST(
        CASE 
            WHEN COUNT(DISTINCT er.id) = 0 THEN 0.0
            ELSE (COUNT(DISTINCT a.id) * 100.0 / COUNT(DISTINCT er.id))
        END AS DECIMAL(5,2)
    ) AS student_attendance_pct
FROM dbo.users u
LEFT JOIN dbo.club_memberships cm ON u.id = cm.user_id
LEFT JOIN dbo.event_registrations er ON u.id = er.user_id AND er.status = 'confirmed'
LEFT JOIN dbo.attendance a ON u.id = a.user_id
WHERE u.role = 'student'
GROUP BY u.id, u.student_id, u.name, u.email, u.department, u.batch_year;
GO

-- 4. View: Department-wise Engagement Aggregates
CREATE OR ALTER VIEW dbo.vw_DepartmentEngagement AS
SELECT 
    u.department,
    COUNT(DISTINCT u.id) AS total_students_enrolled,
    COUNT(DISTINCT cm.id) AS total_club_affiliations,
    COUNT(DISTINCT er.id) AS total_event_signups,
    COUNT(DISTINCT a.id) AS verified_attendances,
    CAST(
        CASE 
            WHEN COUNT(DISTINCT er.id) = 0 THEN 0.0
            ELSE (COUNT(DISTINCT a.id) * 100.0 / COUNT(DISTINCT er.id))
        END AS DECIMAL(5,2)
    ) AS department_attendance_rate
FROM dbo.users u
LEFT JOIN dbo.club_memberships cm ON u.id = cm.user_id
LEFT JOIN dbo.event_registrations er ON u.id = er.user_id AND er.status = 'confirmed'
LEFT JOIN dbo.attendance a ON u.id = a.user_id
WHERE u.role = 'student'
GROUP BY u.department;
GO
