import math

class RouteOptimizerService:
    @staticmethod
    def estimate_distance_km(origin: str, dest: str) -> float:
        """Estimate geographical distance in kilometers between origin and destination."""
        orig_clean = origin.lower().strip()
        dest_clean = dest.lower().strip()

        # Same city or intra-region
        if orig_clean in dest_clean or dest_clean in orig_clean:
            return 25.0

        # Known regional Indian routes
        routes_km = {
            ("pune", "mumbai"): 150.0,
            ("mumbai", "pune"): 150.0,
            ("pune", "nashik"): 210.0,
            ("pune", "delhi"): 1420.0,
            ("pune", "bangalore"): 840.0,
            ("pune", "kolkata"): 1580.0,
            ("pune", "london"): 7200.0,
            ("pune", "new york"): 12500.0,
            ("mumbai", "london"): 7180.0,
            ("mumbai", "delhi"): 1400.0,
        }

        for (o, d), dist in routes_km.items():
            if o in orig_clean and d in dest_clean:
                return dist

        # Default fallbacks based on international check
        is_international = any(country in dest_clean for country in ["uk", "usa", "london", "dubai", "new york", "singapore", "international"])
        if is_international:
            return 6800.0
        return 450.0

    @staticmethod
    def calculate_routes(origin_city: str, destination_city: str, weight_kg: float, deadline_days: int, origin_weather: str = "", dest_weather: str = ""):
        # 100% Dynamic Multi-modal freight & fuel calculator
        origin = origin_city.strip() if origin_city else "Origin Regional Hub"
        dest = destination_city.strip() if destination_city else "Destination Terminal"
        weight = max(0.5, float(weight_kg))
        deadline = max(1, int(deadline_days))

        dist_km = RouteOptimizerService.estimate_distance_km(origin, dest)

        is_international = any(country in dest.lower() for country in ["uk", "usa", "london", "dubai", "new york", "singapore", "international"])
        is_same_city = origin.lower() in dest.lower() or dest.lower() in origin.lower() or dist_km <= 50.0

        # Check weather conditions for rain/storms
        combined_weather = (origin_weather + " " + dest_weather).lower()
        is_bad_weather = any(w in combined_weather for w in ["rain", "storm", "fog", "shower", "thunder"])

        # Weather multiplier for protective handling
        weather_factor = 1.15 if is_bad_weather else 1.0

        # ----------------------------------------------------
        # MODE 1: LOCAL / HIGHWAY ROAD FREIGHT (CONTAINER TRUCK)
        # ----------------------------------------------------
        if is_same_city:
            road_mode = "Local Waterproof Container Mini Truck (EV / Heavy Duty)"
            road_carrier = "City Express Local Fleet"
            road_days = 1
            # Fuel calculation: ~4L petrol/diesel @ ₹100/L = ₹400 fuel + ₹600 Driver & Vehicle Hire
            fuel_litres = round(max(2.0, dist_km / 8.0), 1)
            fuel_cost = round(fuel_litres * 100)
            handling_fee = 600
            road_shipping_cost = round((fuel_cost + handling_fee + (weight * 15)) * weather_factor)
        elif not is_international:
            road_mode = "Inter-State Highway Heavy Truck / Waterproof Express"
            road_carrier = "National Interstate Freight Express"
            road_days = 2 if dist_km <= 300 else (4 if dist_km <= 1000 else 6)
            fuel_litres = round(dist_km / 4.5, 1) # ~4.5 km/L truck mileage
            fuel_cost = round(fuel_litres * 100)
            highway_tolls_driver = round(dist_km * 3.5)
            road_shipping_cost = round((fuel_cost + highway_tolls_driver + (weight * 25)) * weather_factor)
        else:
            road_mode = "Cross-Border Combined Surface & Rail Freight"
            road_carrier = "Global Surface Cargo Link"
            road_days = 12
            fuel_litres = round(dist_km / 5.0, 1)
            road_shipping_cost = round((weight * 200 + 4000) * weather_factor)

        road_meets_deadline = (road_days) <= deadline

        # ----------------------------------------------------
        # MODE 2: AIR FREIGHT / CARGO EXPRESS
        # ----------------------------------------------------
        air_days = 1 if is_same_city else (4 if is_international else 2)
        air_cost_per_kg = 350 if is_international else 220
        air_base = 2500 if is_international else 1200
        air_shipping_cost = round((weight * air_cost_per_kg + air_base) * weather_factor)
        air_meets_deadline = (air_days) <= deadline

        fuel_details_road = f"{fuel_litres} Litres Diesel/Fuel @ ₹100/L = ₹{fuel_cost:,} + Tolls & Driver Fee" if not is_same_city else f"{fuel_litres} Litres Fuel @ ₹100/L = ₹{fuel_cost:,} + Base Hire Fee"

        routes = [
            {
                "id": "route-road-exp",
                "routeId": "route-road-exp",
                "mode": road_mode,
                "carrier": road_carrier,
                "originRegion": origin,
                "destination": dest,
                "estimatedDistanceKm": dist_km,
                "fuelLitres": fuel_litres if 'fuel_litres' in locals() else 0,
                "fuelExpensesInr": fuel_cost if 'fuel_cost' in locals() else 400,
                "fuelCalculationDetails": fuel_details_road if 'fuel_details_road' in locals() else "Standard Fuel & Base Hire Fee",
                "estimatedTransitDays": road_days,
                "totalDeliveryDays": road_days,
                "estimatedShippingCost": road_shipping_cost,
                "meetsDeadline": road_meets_deadline,
                "riskLevel": "LOW" if road_meets_deadline else "MEDIUM",
                "weatherAdapted": is_bad_weather
            },
            {
                "id": "route-air-exp",
                "routeId": "route-air-exp",
                "mode": "Air Freight Cargo Express",
                "carrier": "Air Cargo Priority",
                "originRegion": origin,
                "destination": dest,
                "estimatedDistanceKm": dist_km,
                "estimatedTransitDays": air_days,
                "totalDeliveryDays": air_days,
                "estimatedShippingCost": air_shipping_cost,
                "meetsDeadline": air_meets_deadline,
                "riskLevel": "LOW" if air_meets_deadline else "HIGH",
                "weatherAdapted": is_bad_weather
            }
        ]

        return routes
