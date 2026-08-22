-- Initialize Schema for BharatLink Nexus AI (Main Buyer Platform)

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  full_name TEXT,
  company_name TEXT,
  country TEXT DEFAULT 'United Kingdom',
  preferred_currency TEXT DEFAULT 'INR',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Procurement Requests Table
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

-- 3. Procurement Results Table
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
  selected_route JSONB,
  reasons JSONB,
  alternatives JSONB,
  workflow_logs JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Saved Recommendations Table
CREATE TABLE IF NOT EXISTS public.saved_recommendations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
  result_id UUID REFERENCES public.procurement_results(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procurement_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_recommendations ENABLE ROW LEVEL SECURITY;

-- Security Policies
CREATE POLICY "Users can view own profile" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "Users can update own profile" ON public.profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can view own requests" ON public.procurement_requests FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own requests" ON public.procurement_requests FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own results" ON public.procurement_results FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own results" ON public.procurement_results FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view saved" ON public.saved_recommendations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert saved" ON public.saved_recommendations FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can delete saved" ON public.saved_recommendations FOR DELETE USING (auth.uid() = user_id);
