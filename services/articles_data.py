from typing import Dict, Any

ARTICLES_CATALOG: Dict[str, Dict[str, Any]] = {
    "what-is-ai-powered-procurement": {
        "slug": "what-is-ai-powered-procurement",
        "title": "What Is AI-Powered Artisan Procurement?",
        "category": "Procurement Technology",
        "summary": "An in-depth guide on how multi-agent AI workflows transform traditional Indian handicraft sourcing, supplier ranking, and inventory verification.",
        "author": "BharatLink Research Team",
        "date_published": "2026-01-15",
        "content_html": """
          <p>Traditional international B2B procurement of Indian artisan products has historically faced fragmentation, unverified middleman markups, unconfirmed stock levels, and opaque shipping timelines. AI-powered procurement replaces manual search with autonomous agentic workflows.</p>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">How Autonomous Agent Workflows Operate</h2>
          <p>Rather than relying on simple keyword matching, platforms like BharatLink Nexus AI employ specialized multi-agent architectures (built on LangGraph and Groq GPT-OSS-20B). Each agent executes a focused task:</p>
          <ul style="padding-left: 1.25rem; margin-bottom: 1.25rem;">
            <li><strong>Intent Parsing:</strong> Extracts target craft nouns, target quantity, destination city, and deadline requirements.</li>
            <li><strong>Catalog Discovery:</strong> Matches queries strictly against active database inventory with zero hallucination.</li>
            <li><strong>Supplier Evaluation:</strong> Ranks seller collectives based on stock availability, unit price, rating, and GI certification.</li>
            <li><strong>Logistics Optimization:</strong> Maps visual ASCII transit corridors from origin craft hubs to destination cities.</li>
            <li><strong>Live Weather Safety:</strong> Assesses climate risks at origin and destination hubs.</li>
          </ul>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">Benefits for Global Buyers</h2>
          <p>Institutional buyers gain transparent pricing breakdown, verified Geographical Indication provenance, and automated executive PDF sourcing recommendations in seconds.</p>
        """
    },
    "how-to-source-indian-handicrafts-internationally": {
        "slug": "how-to-source-indian-handicrafts-internationally",
        "title": "How to Source Authentic Indian Handicrafts Internationally",
        "category": "Export & Logistics",
        "summary": "Key steps, compliance standards, GI-tag verification, and shipping best practices for importing Indian artisan products.",
        "author": "BharatLink Logistics Architecture",
        "date_published": "2026-01-20",
        "content_html": """
          <p>Sourcing Indian artisan handicrafts for international export requires understanding Geographical Indication (GI) certification, artisan guild verification, and climate-safe transit corridor planning.</p>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">1. Verify Geographical Indication (GI) Tag Status</h2>
          <p>Geographical Indication tags guarantee that heritage items—such as Paithani Silk Sarees from Maharashtra, Kashmiri Pashmina shawls, or Jaipur Blue Pottery—possess authentic regional craftsmanship and material standards.</p>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">2. Evaluate Active Stock & MOQ Requirements</h2>
          <p>Direct artisan collectives operate with specific minimum order quantities (MOQ). AI procurement platforms verify active inventory in real time before finalizing sourcing plans.</p>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">3. Route Planning & Climate Protection</h2>
          <p>Delicate craft items (such as hand-painted Warli art or silk textiles) require climate-controlled packaging and live weather risk evaluation during transit.</p>
        """
    },
    "understanding-gi-certified-handlooms": {
        "slug": "understanding-gi-certified-handlooms",
        "title": "Understanding GI-Certified Handloom & Regional Indian Crafts",
        "category": "Heritage Crafts",
        "summary": "Explore India's rich handloom traditions including Paithani, Bandhani, Pashmina, and Solapur weaving clusters.",
        "author": "Handloom Heritage Guild",
        "date_published": "2026-02-01",
        "content_html": """
          <p>India represents over 95% of the global handwoven textile capacity. GI-certified handlooms protect traditional weaver communities from synthetic powerloom counterfeits.</p>

          <h2 style="color: var(--amber-gold); font-size: 1.4rem; margin-top: 1.5rem; margin-bottom: 0.75rem;">Famous Indian GI Handlooms</h2>
          <ul style="padding-left: 1.25rem; margin-bottom: 1.25rem;">
            <li><strong>Paithani Sarees (Maharashtra):</strong> 2,000-year-old weaving heritage characterized by oblique square borders and intricate peacock (mor) pallus woven with pure zari.</li>
            <li><strong>Kashmiri Pashmina (Jammar & Kashmir):</strong> Fine hand-combed Cashmere spun from Changthangi goats with fineness under 15 microns.</li>
            <li><strong>Bandhani Tie-Dye (Gujarat & Rajasthan):</strong> Ancient resist-dyeing technique producing intricate dot motifs on silk and cotton fabrics.</li>
          </ul>
        """
    }
}
