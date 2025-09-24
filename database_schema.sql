-- ===========================================
-- SUPABASE DATABASE SCHEMA
-- Real Estate Leasing Bot
-- ===========================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- PROPERTIES TABLE
-- ===========================================
CREATE TABLE properties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    description TEXT,
    amenities TEXT[],
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===========================================
-- UNITS TABLE
-- ===========================================
CREATE TABLE units (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    unit_number VARCHAR(10) NOT NULL,
    rooms INTEGER NOT NULL,
    bathrooms DECIMAL(3,1) DEFAULT 1.0,
    area_sqm INTEGER,
    floor INTEGER,
    price DECIMAL(10,2) NOT NULL,
    deposit_months INTEGER DEFAULT 2,
    has_parking BOOLEAN DEFAULT FALSE,
    has_balcony BOOLEAN DEFAULT FALSE,
    has_elevator BOOLEAN DEFAULT FALSE,
    furnished BOOLEAN DEFAULT FALSE,
    pet_friendly BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'hold', 'rented')),
    available_from DATE,
    image_url TEXT,
    floorplan_url TEXT,
    features TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(property_id, unit_number)
);

-- ===========================================
-- LEADS TABLE
-- ===========================================
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    stage VARCHAR(50) NOT NULL DEFAULT 'new',
    
    -- Gate question responses
    has_payslips BOOLEAN,
    can_pay_deposit BOOLEAN,
    move_in_date TEXT,
    
    -- Profile information
    rooms INTEGER,
    budget DECIMAL(10,2),
    has_parking BOOLEAN,
    preferred_area TEXT,
    
    -- Additional preferences
    preferred_floor_min INTEGER,
    preferred_floor_max INTEGER,
    needs_furnished BOOLEAN,
    pet_owner BOOLEAN,
    
    -- Metadata
    source VARCHAR(100) DEFAULT 'whatsapp',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CHECK (stage IN (
        'new',
        'gate_question_payslips',
        'gate_question_deposit', 
        'gate_question_move_date',
        'collecting_profile',
        'qualified',
        'scheduling_in_progress',
        'tour_scheduled',
        'gate_failed',
        'no_fit',
        'future_fit'
    ))
);

-- ===========================================
-- APPOINTMENTS TABLE
-- ===========================================
CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL,
    calendly_event_id VARCHAR(255),
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    attendee_email VARCHAR(255),
    attendee_name VARCHAR(255),
    location TEXT,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'canceled', 'no_show')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===========================================
-- CONVERSATION LOG TABLE
-- ===========================================
CREATE TABLE conversation_log (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    message_type VARCHAR(10) NOT NULL CHECK (message_type IN ('user', 'bot')),
    content TEXT NOT NULL,
    message_id VARCHAR(255),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB
);

-- ===========================================
-- FOLLOWUPS TABLE
-- ===========================================
CREATE TABLE followups (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    send_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'canceled')),
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CHECK (message_type IN (
        'evening_before_reminder',
        'morning_of_reminder', 
        'three_hours_before_reminder',
        'abandoned_lead_nudge',
        'follow_up_after_tour',
        'no_show_follow_up'
    ))
);

-- ===========================================
-- DAILY METRICS TABLE
-- ===========================================
CREATE TABLE metrics_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_inquiries INTEGER DEFAULT 0,
    qualified_leads INTEGER DEFAULT 0,
    tours_scheduled INTEGER DEFAULT 0,
    tours_completed INTEGER DEFAULT 0,
    conversion_rate_qualified DECIMAL(5,2) DEFAULT 0.0,
    conversion_rate_tours DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ===========================================
-- INDEXES FOR PERFORMANCE
-- ===========================================

-- Lead indexes
CREATE INDEX idx_leads_phone ON leads(phone_number);
CREATE INDEX idx_leads_stage ON leads(stage);
CREATE INDEX idx_leads_last_interaction ON leads(last_interaction);
CREATE INDEX idx_leads_created_at ON leads(created_at);

-- Unit indexes
CREATE INDEX idx_units_status ON units(status);
CREATE INDEX idx_units_price ON units(price);
CREATE INDEX idx_units_rooms ON units(rooms);
CREATE INDEX idx_units_parking ON units(has_parking);
CREATE INDEX idx_units_property_id ON units(property_id);

-- Appointment indexes
CREATE INDEX idx_appointments_scheduled_time ON appointments(scheduled_time);
CREATE INDEX idx_appointments_lead_id ON appointments(lead_id);
CREATE INDEX idx_appointments_status ON appointments(status);
CREATE INDEX idx_appointments_calendly_id ON appointments(calendly_event_id);

-- Conversation log indexes
CREATE INDEX idx_conversation_lead_timestamp ON conversation_log(lead_id, timestamp);
CREATE INDEX idx_conversation_timestamp ON conversation_log(timestamp);

-- Followup indexes
CREATE INDEX idx_followups_send_at ON followups(send_at);
CREATE INDEX idx_followups_status ON followups(status);
CREATE INDEX idx_followups_lead_id ON followups(lead_id);

-- Metrics indexes
CREATE INDEX idx_metrics_date ON metrics_daily(date);

-- ===========================================
-- UPDATED_AT TRIGGERS
-- ===========================================

-- Function to update the updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
CREATE TRIGGER update_properties_updated_at 
    BEFORE UPDATE ON properties 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_units_updated_at 
    BEFORE UPDATE ON units 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_leads_updated_at 
    BEFORE UPDATE ON leads 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appointments_updated_at 
    BEFORE UPDATE ON appointments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- ROW LEVEL SECURITY (Optional)
-- ===========================================

-- Enable RLS on all tables
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE units ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE followups ENABLE ROW LEVEL SECURITY;
ALTER TABLE metrics_daily ENABLE ROW LEVEL SECURITY;

-- Create policies (adjust based on your authentication needs)
-- For now, allow all operations for authenticated users

CREATE POLICY "Allow all operations for authenticated users" ON properties
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON units
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON leads
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON appointments
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON conversation_log
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON followups
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all operations for authenticated users" ON metrics_daily
    FOR ALL USING (auth.role() = 'authenticated');

-- ===========================================
-- SAMPLE DATA FOR TESTING
-- ===========================================

-- Insert sample property
INSERT INTO properties (name, address, description, latitude, longitude, contact_phone, contact_email)
VALUES (
    'בניין יוקרה בתל אביב',
    'רחוב דיזנגוף 100, תל אביב',
    'בניין יוקרתי במרכז תל אביב עם כל השירותים',
    32.0853,
    34.7818,
    '+972-50-1234567',
    'info@example.com'
);

-- Insert sample units
INSERT INTO units (property_id, unit_number, rooms, bathrooms, area_sqm, floor, price, has_parking, has_balcony, has_elevator, available_from, image_url)
VALUES 
    (1, 'A1', 3, 2.0, 85, 2, 7500.00, true, true, true, CURRENT_DATE, 'https://example.com/unit1.jpg'),
    (1, 'A2', 4, 2.5, 110, 3, 9200.00, true, true, true, CURRENT_DATE + INTERVAL '1 week', 'https://example.com/unit2.jpg'),
    (1, 'B1', 2, 1.5, 65, 1, 6200.00, false, false, true, CURRENT_DATE, 'https://example.com/unit3.jpg'),
    (1, 'B2', 3, 2.0, 90, 4, 8100.00, true, true, true, CURRENT_DATE + INTERVAL '2 weeks', 'https://example.com/unit4.jpg');

-- ===========================================
-- HELPFUL VIEWS
-- ===========================================

-- View for available units with property details
CREATE VIEW available_units_view AS
SELECT 
    u.id as unit_id,
    u.unit_number,
    u.rooms,
    u.bathrooms,
    u.area_sqm,
    u.floor,
    u.price,
    u.has_parking,
    u.has_balcony,
    u.available_from,
    u.image_url,
    u.floorplan_url,
    p.name as property_name,
    p.address as property_address,
    p.latitude,
    p.longitude
FROM units u
JOIN properties p ON u.property_id = p.id
WHERE u.status = 'available';

-- View for lead pipeline summary
CREATE VIEW lead_pipeline_view AS
SELECT 
    stage,
    COUNT(*) as count,
    AVG(EXTRACT(DAY FROM (NOW() - created_at))) as avg_days_in_stage
FROM leads 
WHERE stage NOT IN ('gate_failed', 'no_fit')
GROUP BY stage
ORDER BY 
    CASE stage
        WHEN 'new' THEN 1
        WHEN 'gate_question_payslips' THEN 2
        WHEN 'gate_question_deposit' THEN 3
        WHEN 'gate_question_move_date' THEN 4
        WHEN 'collecting_profile' THEN 5
        WHEN 'qualified' THEN 6
        WHEN 'scheduling_in_progress' THEN 7
        WHEN 'tour_scheduled' THEN 8
        ELSE 9
    END;

-- ===========================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ===========================================

-- Function to get leads by date range and stage
CREATE OR REPLACE FUNCTION count_leads_by_date_and_stage(
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    target_stage VARCHAR DEFAULT NULL
)
RETURNS INTEGER AS $$
BEGIN
    IF target_stage IS NULL THEN
        RETURN (
            SELECT COUNT(*)
            FROM leads
            WHERE created_at >= start_date AND created_at <= end_date
        );
    ELSE
        RETURN (
            SELECT COUNT(*)
            FROM leads
            WHERE created_at >= start_date 
                AND created_at <= end_date
                AND stage = target_stage
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to get appointments by date range and status
CREATE OR REPLACE FUNCTION count_appointments_by_date_and_status(
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    target_status VARCHAR DEFAULT NULL
)
RETURNS INTEGER AS $$
BEGIN
    IF target_status IS NULL THEN
        RETURN (
            SELECT COUNT(*)
            FROM appointments
            WHERE created_at >= start_date AND created_at <= end_date
        );
    ELSE
        RETURN (
            SELECT COUNT(*)
            FROM appointments
            WHERE created_at >= start_date 
                AND created_at <= end_date
                AND status = target_status
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ===========================================
-- COMPLETION MESSAGE
-- ===========================================

-- Print completion message
DO $$
BEGIN
    RAISE NOTICE 'Database schema created successfully!';
    RAISE NOTICE 'Tables created: properties, units, leads, appointments, conversation_log, followups, metrics_daily';
    RAISE NOTICE 'Sample data inserted for testing';
    RAISE NOTICE 'Indexes and triggers configured';
    RAISE NOTICE 'Views and functions created';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Update your .env file with Supabase credentials';
    RAISE NOTICE '2. Configure Calendly webhook URLs';
    RAISE NOTICE '3. Set up WhatsApp Business API';
    RAISE NOTICE '4. Start the application!';
END $$;
