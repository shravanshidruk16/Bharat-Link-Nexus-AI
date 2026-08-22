-- ============================================================
-- BHARATLINK NEXUS AI & SELLER CENTRAL — PRODUCTION SUPABASE SQL SCRIPT
-- Copy and run this entire script in your Supabase Dashboard SQL Editor
-- (100% Zero Dummy Data — Complete Schema with Product Updates & Order Status)
-- ============================================================

-- 1. PROFILES TABLE (Buyer Users & System Admins)
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  full_name TEXT NOT NULL,
  company_name TEXT,
  role TEXT DEFAULT 'buyer', -- 'buyer' or 'admin'
  country TEXT DEFAULT 'India',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. SELLER PROFILES TABLE (Artisan Sellers with Approval Flow & WhatsApp Contact)
CREATE TABLE IF NOT EXISTS public.seller_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  business_name TEXT NOT NULL,
  contact_person TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  phone TEXT NOT NULL,
  whatsapp_number TEXT NOT NULL,
  country TEXT DEFAULT 'India',
  state TEXT NOT NULL,
  city TEXT NOT NULL,
  address TEXT NOT NULL,
  postal_code TEXT,
  craft_category TEXT NOT NULL,
  years_active INT DEFAULT 5,
  description TEXT,
  export_history BOOLEAN DEFAULT TRUE,
  verification_status TEXT DEFAULT 'Pending Admin Approval',
  craft_certification TEXT DEFAULT 'GI Tag Certified',
  artisan_count INT DEFAULT 10,
  active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.seller_profiles ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE public.seller_profiles ADD COLUMN IF NOT EXISTS whatsapp_number TEXT;

-- 3. SELLER PRODUCTS TABLE (Catalog Items)
CREATE TABLE IF NOT EXISTS public.seller_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id UUID REFERENCES public.seller_profiles(id) ON DELETE CASCADE,
  seller_name TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT NOT NULL,
  subcategory TEXT,
  region TEXT NOT NULL,
  price NUMERIC NOT NULL CHECK (price > 0),
  currency TEXT DEFAULT 'INR',
  minimum_order_quantity INT DEFAULT 1 CHECK (minimum_order_quantity >= 1),
  available_stock INT DEFAULT 0 CHECK (available_stock >= 0),
  weight_kg NUMERIC NOT NULL CHECK (weight_kg > 0),
  authenticity_status TEXT DEFAULT 'GI Certified Authentic',
  image_url TEXT,
  image_urls JSONB DEFAULT '[]'::jsonb,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.seller_products ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE public.seller_products ADD COLUMN IF NOT EXISTS image_urls JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.seller_products ADD COLUMN IF NOT EXISTS active BOOLEAN DEFAULT TRUE;

-- 4. PROCUREMENT REQUESTS TABLE
CREATE TABLE IF NOT EXISTS public.procurement_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  raw_prompt TEXT NOT NULL,
  product_type TEXT,
  quantity INT,
  destination TEXT,
  deadline_days INT,
  budget_inr NUMERIC,
  status TEXT DEFAULT 'completed',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. PROCUREMENT RESULTS TABLE (Buyer Sourcing Orders)
CREATE TABLE IF NOT EXISTS public.procurement_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID REFERENCES public.procurement_requests(id) ON DELETE CASCADE,
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  supplier_name TEXT NOT NULL,
  product_name TEXT NOT NULL,
  quantity INT NOT NULL,
  product_cost NUMERIC NOT NULL,
  shipping_cost NUMERIC NOT NULL,
  total_cost NUMERIC NOT NULL,
  delivery_days INT NOT NULL,
  risk_level TEXT NOT NULL,
  carbon_kg NUMERIC,
  status TEXT DEFAULT 'Pending', -- 'Pending', 'Stock Delivered', 'Not Accepted'
  selected_route JSONB,
  reasons JSONB,
  alternatives JSONB,
  workflow_logs JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.procurement_results ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Pending';

-- 6. SAVED RECOMMENDATIONS TABLE
CREATE TABLE IF NOT EXISTS public.saved_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  result_id UUID REFERENCES public.procurement_results(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CREATE INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_seller_products_category ON public.seller_products(category);
CREATE INDEX IF NOT EXISTS idx_seller_products_region ON public.seller_products(region);
CREATE INDEX IF NOT EXISTS idx_seller_products_seller_id ON public.seller_products(seller_id);
CREATE INDEX IF NOT EXISTS idx_seller_profiles_active ON public.seller_profiles(active);

-- ENABLE ROW LEVEL SECURITY (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seller_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seller_products ENABLE ROW LEVEL SECURITY;

-- DROP OLD POLICIES IF THEY EXIST TO PREVENT CONFLICTS
DROP POLICY IF EXISTS "Allow All Profiles" ON public.profiles;
DROP POLICY IF EXISTS "Allow All Sellers" ON public.seller_profiles;
DROP POLICY IF EXISTS "Allow All Products" ON public.seller_products;
DROP POLICY IF EXISTS "Allow All Requests" ON public.procurement_requests;
DROP POLICY IF EXISTS "Allow All Results" ON public.procurement_results;
DROP POLICY IF EXISTS "Allow All Saved" ON public.saved_recommendations;

-- CREATE FULL RLS POLICIES FOR INSERT, SELECT, UPDATE, DELETE
CREATE POLICY "Allow All Profiles" ON public.profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Sellers" ON public.seller_profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Products" ON public.seller_products FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Requests" ON public.procurement_requests FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Results" ON public.procurement_results FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow All Saved" ON public.saved_recommendations FOR ALL USING (true) WITH CHECK (true);

-- SEED SYSTEM ADMIN ACCOUNT (Exact Hash Match)
-- Email: admin@bharatlink.com | Password: Admin@123
INSERT INTO public.profiles (email, password_hash, full_name, role)
VALUES (
  'admin@bharatlink.com',
  '85c9c34eb1eab3e32e08d7f6085d481ad9da4a713c2d6d038a560fc1d44ab7f8',
  'BharatLink Global Admin',
  'admin'
) ON CONFLICT (email) DO UPDATE SET password_hash = '85c9c34eb1eab3e32e08d7f6085d481ad9da4a713c2d6d038a560fc1d44ab7f8', role = 'admin';
