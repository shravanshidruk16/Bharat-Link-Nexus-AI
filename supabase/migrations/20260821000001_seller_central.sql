-- Database Schema for BharatLink Nexus AI - Seller Central

-- 1. Seller Profiles Table
CREATE TABLE IF NOT EXISTS public.seller_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  business_name TEXT NOT NULL,
  contact_person TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT,
  country TEXT DEFAULT 'India',
  state TEXT NOT NULL,
  city TEXT NOT NULL,
  address TEXT NOT NULL,
  postal_code TEXT,
  craft_category TEXT NOT NULL,
  years_active INT DEFAULT 5,
  description TEXT,
  website_url TEXT,
  export_history BOOLEAN DEFAULT TRUE,
  verification_status TEXT DEFAULT 'Demo Verified', -- 'Pending', 'Demo Verified', 'Verified', 'Rejected'
  craft_certification TEXT, -- e.g. 'GI Tag Certified #MH-PAI-2018'
  artisan_count INT DEFAULT 10,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Seller Products Table
CREATE TABLE IF NOT EXISTS public.seller_products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  seller_id UUID REFERENCES public.seller_profiles(id) ON DELETE CASCADE,
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
  length_cm NUMERIC NOT NULL CHECK (length_cm > 0),
  width_cm NUMERIC NOT NULL CHECK (width_cm > 0),
  height_cm NUMERIC NOT NULL CHECK (height_cm > 0),
  authenticity_status TEXT DEFAULT 'GI Certified Authentic',
  quality_rating NUMERIC DEFAULT 4.8,
  tags JSONB DEFAULT '[]'::jsonb,
  image_urls JSONB DEFAULT '[]'::jsonb,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Seller Inventory Audit Logs
CREATE TABLE IF NOT EXISTS public.seller_inventory_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES public.seller_products(id) ON DELETE CASCADE,
  seller_id UUID REFERENCES public.seller_profiles(id) ON DELETE CASCADE,
  previous_stock INT NOT NULL,
  new_stock INT NOT NULL,
  reason TEXT DEFAULT 'Manual stock adjustment',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Transport Quotes & Logistics Cache
CREATE TABLE IF NOT EXISTS public.transport_quotes_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  origin_city TEXT NOT NULL,
  destination_city TEXT NOT NULL,
  weight_kg NUMERIC NOT NULL,
  volume_cm3 NUMERIC NOT NULL,
  mode TEXT NOT NULL,
  carrier TEXT NOT NULL,
  cost_inr NUMERIC NOT NULL,
  transit_days INT NOT NULL,
  risk_score NUMERIC DEFAULT 0.1,
  carbon_kg NUMERIC DEFAULT 0.0,
  data_source TEXT NOT NULL, -- 'Aviationstack', 'IndianRail', 'SeaRates', 'WeatherAPI', 'CachedEstimate'
  data_type TEXT DEFAULT 'ESTIMATE', -- 'LIVE', 'ESTIMATE', 'CACHED', 'SIMULATED'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for ultra-fast query performance
CREATE INDEX IF NOT EXISTS idx_seller_products_category ON public.seller_products(category);
CREATE INDEX IF NOT EXISTS idx_seller_products_region ON public.seller_products(region);
CREATE INDEX IF NOT EXISTS idx_seller_products_active ON public.seller_products(active);
CREATE INDEX IF NOT EXISTS idx_seller_products_seller_id ON public.seller_products(seller_id);
CREATE INDEX IF NOT EXISTS idx_seller_profiles_verification ON public.seller_profiles(verification_status);

-- Enable Row Level Security (RLS)
ALTER TABLE public.seller_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seller_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seller_inventory_logs ENABLE ROW LEVEL SECURITY;

-- Security Policies
CREATE POLICY "Sellers can view own profile" ON public.seller_profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Sellers can update own profile" ON public.seller_profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Public can view active products" ON public.seller_products FOR SELECT USING (active = true);
CREATE POLICY "Sellers can insert own products" ON public.seller_products FOR INSERT WITH CHECK (auth.uid() = seller_id);
CREATE POLICY "Sellers can update own products" ON public.seller_products FOR UPDATE USING (auth.uid() = seller_id);
CREATE POLICY "Sellers can delete own products" ON public.seller_products FOR DELETE USING (auth.uid() = seller_id);
