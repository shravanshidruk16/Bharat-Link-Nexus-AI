import os
import json
from typing import Dict, Any, List, Optional

DEFAULT_DOMAIN = os.getenv("DOMAIN_URL", os.getenv("RENDER_EXTERNAL_URL", "https://bharat-link-nexus-ai.onrender.com")).rstrip("/")

class SEOService:
    @staticmethod
    def get_domain() -> str:
        return DEFAULT_DOMAIN

    @staticmethod
    def generate_meta_context(
        path: str,
        title: str,
        description: str,
        keywords: Optional[str] = None,
        og_image: Optional[str] = None,
        og_type: str = "website",
        noindex: bool = False,
        breadcrumbs: Optional[List[Dict[str, str]]] = None,
        schema_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        domain = SEOService.get_domain()
        canonical_url = f"{domain}{path}" if path.startswith("/") else f"{domain}/{path}"
        
        # Clean canonical URL of tracking parameters
        if "?" in canonical_url:
            canonical_url = canonical_url.split("?")[0]

        default_image = f"{domain}/static/images/logo.png"
        image_url = og_image if (og_image and (og_image.startswith("http://") or og_image.startswith("https://"))) else default_image

        # Base Organization Schema
        org_schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "BharatLink Nexus AI",
            "url": domain,
            "logo": f"{domain}/static/images/logo.png",
            "description": "AI-Powered Artisan Procurement & Intelligent Multi-Modal Logistics Platform for authentic Indian handicrafts.",
            "knowsAbout": ["Indian Handicrafts", "Artisan Sourcing", "GI Textiles", "Pottery", "B2B Procurement", "Multimodal Freight Logistics"]
        }

        # Base WebSite Schema with SearchAction
        website_schema = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "BharatLink Nexus AI",
            "url": domain,
            "potentialAction": {
                "@type": "SearchAction",
                "target": {
                    "@type": "EntryPoint",
                    "urlTemplate": f"{domain}/crafts?q={{search_term_string}}"
                },
                "query-input": "required name=search_term_string"
            }
        }

        # WebPage Schema
        webpage_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": canonical_url,
            "publisher": {
                "@type": "Organization",
                "name": "BharatLink Nexus AI"
            }
        }

        schemas = [org_schema, website_schema, webpage_schema]

        # Breadcrumb Schema if provided
        if breadcrumbs:
            item_list = []
            for idx, b in enumerate(breadcrumbs, 1):
                item_list.append({
                    "@type": "ListItem",
                    "position": idx,
                    "name": b["name"],
                    "item": f"{domain}{b['url']}" if b['url'].startswith('/') else b['url']
                })
            breadcrumb_schema = {
                "@context": "https://schema.org",
                "@type": "BreadcrumbList",
                "itemListElement": item_list
            }
            schemas.append(breadcrumb_schema)

        if schema_data:
            schemas.extend(schema_data)

        return {
            "title": title,
            "description": description,
            "keywords": keywords or "Indian artisan products, authentic Indian handicrafts, AI procurement, Indian handicraft wholesale, artisan logistics",
            "canonical_url": canonical_url,
            "noindex": noindex,
            "og_title": title,
            "og_description": description,
            "og_image": image_url,
            "og_type": og_type,
            "og_url": canonical_url,
            "twitter_title": title,
            "twitter_description": description,
            "twitter_image": image_url,
            "twitter_card": "summary_large_image",
            "breadcrumbs": breadcrumbs or [],
            "json_ld_scripts": [json.dumps(s, indent=2) for s in schemas]
        }

    @staticmethod
    def get_craft_catalog() -> Dict[str, Dict[str, Any]]:
        """Authentic Craft Taxonomy for programmatic SEO pages."""
        return {
            "paithani": {
                "slug": "paithani",
                "name": "Paithani Silk & Handloom Crafts",
                "category": "Textiles & Apparel",
                "region": "Maharashtra (Yeola & Paithan)",
                "description": "Discover authentic GI-tagged Paithani silk sarees and handloom stoles featuring traditional peacock motifs, pure zari borders, and handwoven heritage.",
                "history": "Paithani is a 2,000-year-old weaving tradition originating from the royal courts of the Satavahana dynasty in Maharashtra. Recognized globally for its distinctive kaleidoscope oblique square designs and peacock (mor) borders.",
                "sourcing_note": "BharatLink Nexus AI verifies GI-tag credentials and pure mulberry silk yarn standards directly from master weaving collectives in Yeola and Paithan."
            },
            "warli-art": {
                "slug": "warli-art",
                "name": "Warli Tribal Folk Paintings & Home Decor",
                "category": "Art & Paintings",
                "region": "Maharashtra (Palghar & Thane)",
                "description": "Source authentic Warli tribal paintings on eco-friendly canvas, wooden coaster sets, and wall art created by indigenous tribal artisans of Maharashtra.",
                "history": "Warli painting is a traditional indigenous art form dating back to 2500 BCE. Created using basic geometric shapes—circles, triangles, and squares—representing elements of nature and communal harvest celebrations.",
                "sourcing_note": "Directly connected with verified Warli artisan self-help groups in Palghar with natural rice-paste paint certification."
            },
            "pashmina": {
                "slug": "pashmina",
                "name": "Kashmiri Pure Pashmina & Cashmere Shawls",
                "category": "Textiles & Apparel",
                "region": "Kashmir",
                "description": "Source 100% authentic GI-certified hand-spun Kashmiri Pashmina shawls, stoles, and Kani weave wraps directly from Himalayan artisan guilds.",
                "history": "Hand-combed from the undercoat of Changthangi goats in Ladakh and hand-spun by Kashmiri master weavers in Srinagar, Kashmiri Pashmina represents the pinnacle of luxury handloom craftsmanship.",
                "sourcing_note": "Verified with Kashmir GI-tag authenticity codes testing fineness under 15 microns."
            },
            "bandhani": {
                "slug": "bandhani",
                "name": "Bandhani Tie-Dye Textiles & Sarees",
                "category": "Textiles & Apparel",
                "region": "Gujarat & Rajasthan",
                "description": "Procure handcrafted Bandhani (Bandhej) tie-dye dupattas, silk sarees, and dress fabrics sourced from traditional artisan families in Kutch and Jaipur.",
                "history": "Bandhani is an ancient art of resist dyeing practiced for over 5,000 years in western India, characterized by intricate hand-tied dot patterns (Ekdali, Trikunti, and Satdali).",
                "sourcing_note": "Sourced directly from verified Kutch and Jamnagar dyeing hubs with natural colorfast guarantees."
            },
            "blue-pottery": {
                "slug": "blue-pottery",
                "name": "Jaipur Blue Pottery & Ceramic Tableware",
                "category": "Pottery & Ceramics",
                "region": "Rajasthan (Jaipur)",
                "description": "Explore handcrafted Jaipur Blue Pottery ceramic vases, decorative plates, coasters, and tableware crafted without clay using quartz stone frit dough.",
                "history": "Jaipur Blue Pottery is a Turko-Persian craft introduced to Jaipur in the 19th century. Made using a unique blend of powdered quartz, glass, and natural oxides, giving it a vibrant turquoise glaze.",
                "sourcing_note": "Verified lead-free glazed ceramic tableware for global home decor and hospitality buyers."
            },
            "kolhapuri-crafts": {
                "slug": "kolhapuri-crafts",
                "name": "Kolhapuri Leather Chappals & Saaj Jewelry",
                "category": "Leather Craft & Goods",
                "region": "Maharashtra (Kolhapur)",
                "description": "Source authentic GI-certified vegetable-tanned Kolhapuri leather chappals, footwear, and traditional silver/gold Kolhapuri Saaj jewelry.",
                "history": "Crafted since the 12th century, Kolhapuri leather chappals are renowned for their hand-stitched durability, natural herbal tannage (using babool bark and myrobalan), and intricate braid work.",
                "sourcing_note": "Direct procurement connection with Kolhapur Artisan Leather Cooperatives ensuring eco-friendly tannage compliance."
            },
            "bidriware": {
                "slug": "bidriware",
                "name": "Bidriware Inlaid Metal Crafts & Decor",
                "category": "Metal Crafts",
                "region": "Karnataka (Bidar)",
                "description": "Source 14th-century GI-tagged Bidriware metal crafts featuring pure silver inlay on blackened zinc and copper alloys for luxury gifts and home decor.",
                "history": "Originating in Bidar, Karnataka during the Bahmani Sultanate, Bidriware involves casting a zinc-copper alloy, hand-carving intricate motifs, hammering fine pure silver wire, and oxidizing using special Bidar soil.",
                "sourcing_note": "Certified authentic silver purity inlay verified by Karnataka state handicraft registries."
            },
            "indian-handloom": {
                "slug": "indian-handloom",
                "name": "Authentic Indian Handloom & Artisan Textiles",
                "category": "Textiles & Apparel",
                "region": "Pan-India",
                "description": "Wholesale B2B procurement of certified Indian handloom fabrics, silk sarees, cotton linens, and khadi garments for global fashion brands and boutique stores.",
                "history": "India accounts for over 95% of the world's handwoven fabrics. BharatLink Nexus AI connects institutional procurement buyers directly with weaving clusters across India.",
                "sourcing_note": "Full Handloom Mark and Silk Mark verification provided across all textile procurement orders."
            }
        }

    @staticmethod
    def get_region_catalog() -> Dict[str, Dict[str, Any]]:
        """Regional Craft Clusters Catalog for local/regional SEO."""
        return {
            "maharashtra-artisans": {
                "slug": "maharashtra-artisans",
                "name": "Maharashtra Artisan Guilds & Craft Clusters",
                "state": "Maharashtra",
                "description": "Source authentic GI-tagged Paithani sarees, Warli paintings, Kolhapuri leatherware, and Solapur chaddars directly from verified Maharashtrian artisan collectives.",
                "highlights": ["Paithani Silk Weaving (Yeola/Paithan)", "Warli Tribal Art (Palghar)", "Kolhapuri Leather Chappals", "Konkan Bamboo Crafts", "Nagpur Cotton Handloom"]
            },
            "rajasthan-artisans": {
                "slug": "rajasthan-artisans",
                "name": "Rajasthan Handicraft & Ceramic Clusters",
                "state": "Rajasthan",
                "description": "Procure Jaipur Blue Pottery, Sanganeri block printed textiles, marble stone carvings, and brass metalware from Rajasthan's master craftsmen.",
                "highlights": ["Jaipur Blue Pottery", "Sanganeri & Bagru Block Prints", "Makrana Marble Crafts", "Jodhpur Wooden Furniture", "Thewa Art Jewelry"]
            },
            "gujarat-artisans": {
                "slug": "gujarat-artisans",
                "name": "Gujarat Handloom & Textile Artisan Clusters",
                "state": "Gujarat",
                "description": "Discover Patan Patola double ikat sarees, Kutch Ajrakh block prints, Bandhani tie-dye, and copper bell crafts from Gujarat's heritage artisan hubs.",
                "highlights": ["Patan Patola Silk Sarees", "Ajrakh Natural Block Printing", "Kutch Embroidery & Mirrorwork", "Sankheda Lacquered Furniture", "Jamnagar Bandhani"]
            },
            "kashmir-artisans": {
                "slug": "kashmir-artisans",
                "name": "Kashmir Pashmina & Woodcarving Guilds",
                "state": "Jammu & Kashmir",
                "description": "Source GI-certified Kashmiri Pashmina shawls, Walnut wood carvings, Papier-mâché decorative art, and Hand-knotted silk carpets from Srinagar artisans.",
                "history": "Kashmiri handicrafts boast a rich Persian heritage introduced by Mir Sayyid Ali Hamadani in the 14th century.",
                "highlights": ["GI Kashmiri Pashmina & Kani Shawls", "Walnut Wood Carvings", "Papier-mâché Artware", "Silk Hand-Knotted Carpets", "Kashmiri Saffron & Spices"]
            }
        }
