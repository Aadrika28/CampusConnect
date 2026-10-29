-- ====================================================================
-- CampusConnect — College Event & Club Management Platform
-- Relational Schema Definition compatible with Azure SQL Database & T-SQL
-- ====================================================================

-- 1. USERS TABLE
IF OBJECT_ID('dbo.audit_logs', 'U') IS NOT NULL DROP TABLE dbo.audit_logs;
IF OBJECT_ID('dbo.notifications', 'U') IS NOT NULL DROP TABLE dbo.notifications;
IF OBJECT_ID('dbo.announcements', 'U') IS NOT NULL DROP TABLE dbo.announcements;
IF OBJECT_ID('dbo.attendance', 'U') IS NOT NULL DROP TABLE dbo.attendance;
IF OBJECT_ID('dbo.event_registrations', 'U') IS NOT NULL DROP TABLE dbo.event_registrations;
IF OBJECT_ID('dbo.events', 'U') IS NOT NULL DROP TABLE dbo.events;
IF OBJECT_ID('dbo.club_memberships', 'U') IS NOT NULL DROP TABLE dbo.club_memberships;
IF OBJECT_ID('dbo.clubs', 'U') IS NOT NULL DROP TABLE dbo.clubs;
IF OBJECT_ID('dbo.users', 'U') IS NOT NULL DROP TABLE dbo.users;

CREATE TABLE dbo.users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    student_id NVARCHAR(50) NULL UNIQUE,
    name NVARCHAR(100) NOT NULL,
    email NVARCHAR(120) NOT NULL UNIQUE,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) NOT NULL DEFAULT 'student', -- student, club_leader, admin
    department NVARCHAR(100) NOT NULL DEFAULT 'Computer Science',
    batch_year INT NOT NULL DEFAULT 2025,
    phone NVARCHAR(20) NULL,
    avatar_url NVARCHAR(255) NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT chk_user_role CHECK (role IN ('student', 'club_leader', 'admin'))
);

CREATE NONCLUSTERED INDEX idx_users_email ON dbo.users(email);
CREATE NONCLUSTERED INDEX idx_users_student_id ON dbo.users(student_id);
CREATE NONCLUSTERED INDEX idx_users_role ON dbo.users(role);

-- 2. CLUBS TABLE
CREATE TABLE dbo.clubs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    slug NVARCHAR(100) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NOT NULL,
    category NVARCHAR(50) NOT NULL, -- Technical, Cultural, Sports, Literary, Social, Entrepreneurship
    logo_url NVARCHAR(255) NULL,
    banner_url NVARCHAR(255) NULL,
    faculty_coordinator NVARCHAR(100) NOT NULL,
    leader_id INT NULL,
    is_active BIT NOT NULL DEFAULT 1,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_clubs_leader FOREIGN KEY (leader_id) REFERENCES dbo.users(id) ON DELETE SET NULL
);

CREATE NONCLUSTERED INDEX idx_clubs_category ON dbo.clubs(category);
CREATE NONCLUSTERED INDEX idx_clubs_slug ON dbo.clubs(slug);

-- 3. CLUB MEMBERSHIPS TABLE
CREATE TABLE dbo.club_memberships (
    id INT IDENTITY(1,1) PRIMARY KEY,
    club_id INT NOT NULL,
    user_id INT NOT NULL,
    role NVARCHAR(30) NOT NULL DEFAULT 'member', -- member, core_team, leader
    joined_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_club_user UNIQUE (club_id, user_id),
    CONSTRAINT fk_cm_club FOREIGN KEY (club_id) REFERENCES dbo.clubs(id) ON DELETE CASCADE,
    CONSTRAINT fk_cm_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE
);

CREATE NONCLUSTERED INDEX idx_cm_user ON dbo.club_memberships(user_id);
CREATE NONCLUSTERED INDEX idx_cm_club ON dbo.club_memberships(club_id);

-- 4. EVENTS TABLE
CREATE TABLE dbo.events (
    id INT IDENTITY(1,1) PRIMARY KEY,
    club_id INT NOT NULL,
    title NVARCHAR(150) NOT NULL,
    slug NVARCHAR(150) NOT NULL UNIQUE,
    description NVARCHAR(MAX) NOT NULL,
    category NVARCHAR(50) NOT NULL, -- Hackathon, Workshop, Cultural Fest, Seminar, Sports Tournament, Competition
    venue NVARCHAR(150) NOT NULL,
    event_date DATETIME2 NOT NULL,
    end_date DATETIME2 NULL,
    registration_deadline DATETIME2 NOT NULL,
    max_capacity INT NOT NULL DEFAULT 100,
    banner_url NVARCHAR(255) NULL,
    status NVARCHAR(20) NOT NULL DEFAULT 'published', -- draft, published, cancelled, completed
    created_by_id INT NULL,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT chk_event_status CHECK (status IN ('draft', 'published', 'cancelled', 'completed')),
    CONSTRAINT chk_event_capacity CHECK (max_capacity > 0),
    CONSTRAINT fk_events_club FOREIGN KEY (club_id) REFERENCES dbo.clubs(id) ON DELETE CASCADE,
    CONSTRAINT fk_events_creator FOREIGN KEY (created_by_id) REFERENCES dbo.users(id) ON DELETE SET NULL
);

CREATE NONCLUSTERED INDEX idx_events_date ON dbo.events(event_date);
CREATE NONCLUSTERED INDEX idx_events_category ON dbo.events(category);
CREATE NONCLUSTERED INDEX idx_events_club ON dbo.events(club_id);

-- 5. EVENT REGISTRATIONS TABLE
CREATE TABLE dbo.event_registrations (
    id INT IDENTITY(1,1) PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    registration_code NVARCHAR(64) NOT NULL UNIQUE,
    status NVARCHAR(20) NOT NULL DEFAULT 'confirmed', -- confirmed, cancelled
    registered_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    cancelled_at DATETIME2 NULL,
    CONSTRAINT uq_event_user UNIQUE (event_id, user_id),
    CONSTRAINT chk_reg_status CHECK (status IN ('confirmed', 'cancelled')),
    CONSTRAINT fk_er_event FOREIGN KEY (event_id) REFERENCES dbo.events(id) ON DELETE CASCADE,
    CONSTRAINT fk_er_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE
);

CREATE NONCLUSTERED INDEX idx_er_event ON dbo.event_registrations(event_id);
CREATE NONCLUSTERED INDEX idx_er_user ON dbo.event_registrations(user_id);
CREATE NONCLUSTERED INDEX idx_er_code ON dbo.event_registrations(registration_code);

-- 6. ATTENDANCE TABLE
CREATE TABLE dbo.attendance (
    id INT IDENTITY(1,1) PRIMARY KEY,
    registration_id INT NOT NULL UNIQUE,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    marked_by_id INT NULL,
    verification_method NVARCHAR(20) NOT NULL DEFAULT 'qr_scan', -- qr_scan, manual
    marked_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT uq_attendance_event_user UNIQUE (event_id, user_id),
    CONSTRAINT fk_att_reg FOREIGN KEY (registration_id) REFERENCES dbo.event_registrations(id) ON DELETE CASCADE,
    CONSTRAINT fk_att_event FOREIGN KEY (event_id) REFERENCES dbo.events(id) ON DELETE NO ACTION,
    CONSTRAINT fk_att_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE NO ACTION,
    CONSTRAINT fk_att_marker FOREIGN KEY (marked_by_id) REFERENCES dbo.users(id) ON DELETE SET NULL
);

CREATE NONCLUSTERED INDEX idx_att_event ON dbo.attendance(event_id);
CREATE NONCLUSTERED INDEX idx_att_user ON dbo.attendance(user_id);

-- 7. ANNOUNCEMENTS TABLE
CREATE TABLE dbo.announcements (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(200) NOT NULL,
    content NVARCHAR(MAX) NOT NULL,
    scope NVARCHAR(20) NOT NULL DEFAULT 'platform', -- platform, club, event
    club_id INT NULL,
    event_id INT NULL,
    author_id INT NULL,
    priority NVARCHAR(20) NOT NULL DEFAULT 'normal', -- low, normal, high, urgent
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT chk_ann_scope CHECK (scope IN ('platform', 'club', 'event')),
    CONSTRAINT chk_ann_priority CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    CONSTRAINT fk_ann_club FOREIGN KEY (club_id) REFERENCES dbo.clubs(id) ON DELETE CASCADE,
    CONSTRAINT fk_ann_event FOREIGN KEY (event_id) REFERENCES dbo.events(id) ON DELETE CASCADE,
    CONSTRAINT fk_ann_author FOREIGN KEY (author_id) REFERENCES dbo.users(id) ON DELETE SET NULL
);

-- 8. NOTIFICATIONS TABLE
CREATE TABLE dbo.notifications (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    title NVARCHAR(150) NOT NULL,
    message NVARCHAR(MAX) NOT NULL,
    link NVARCHAR(255) NULL,
    is_read BIT NOT NULL DEFAULT 0,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE CASCADE
);

CREATE NONCLUSTERED INDEX idx_notif_user_unread ON dbo.notifications(user_id, is_read);

-- 9. AUDIT LOGS TABLE
CREATE TABLE dbo.audit_logs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NULL,
    action NVARCHAR(50) NOT NULL,
    entity_type NVARCHAR(50) NOT NULL,
    entity_id NVARCHAR(50) NULL,
    details NVARCHAR(MAX) NULL,
    ip_address NVARCHAR(50) NULL,
    timestamp DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES dbo.users(id) ON DELETE SET NULL
);

CREATE NONCLUSTERED INDEX idx_audit_timestamp ON dbo.audit_logs(timestamp DESC);
