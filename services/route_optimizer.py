class RouteOptimizerService:
    @staticmethod
    def generate_text_map(origin_city: str, destination_city: str) -> str:
        """Generate a clean ASCII text route map from origin to destination."""
        origin = origin_city.strip() if origin_city else "Origin Hub"
        dest = destination_city.strip() if destination_city else "Destination Hub"

        orig_clean = origin.lower()
        dest_clean = dest.lower()

        if orig_clean in dest_clean or dest_clean in orig_clean:
            return f"[ 📍 Origin: {origin} ] ────── (Local Direct Dispatch) ──────► [ 🏁 Destination: {dest} ]"

        is_international = any(c in dest_clean for c in ["uk", "usa", "london", "dubai", "new york", "singapore", "germany", "france", "international"])

        if is_international:
            return f"[ 📍 Origin Hub: {origin} ] ────── (Air Freight Export Corridor) ──────► [ 🔄 International Gateway Hub: Mumbai/Delhi ] ────── (Global Transit Line) ──────► [ 🏁 Destination: {dest} ]"
        else:
            return f"[ 📍 Origin Hub: {origin} ] ────── (Interstate Logistics Corridor) ──────► [ 🔄 Central Dispatch Center ] ────── (Express Route) ──────► [ 🏁 Destination: {dest} ]"

    @staticmethod
    def calculate_routes(origin_city: str, destination_city: str, weight_kg: float = 1.0, deadline_days: int = 10, origin_weather: str = "", dest_weather: str = ""):
        origin = origin_city.strip() if origin_city else "Origin Hub"
        dest = destination_city.strip() if destination_city else "Destination Hub"
        deadline = max(1, int(deadline_days))

        is_same_city = (origin.lower() in dest.lower() or dest.lower() in origin.lower())
        is_intl = any(c in dest.lower() for c in ["uk", "usa", "london", "dubai", "new york", "singapore", "international"])

        lead_days = 1 if is_same_city else (3 if is_intl else 2)

        text_map = RouteOptimizerService.generate_text_map(origin, dest)

        return [
            {
                "id": "route-corridor-primary",
                "routeId": "route-corridor-primary",
                "mode": "Direct Logistics Corridor",
                "originRegion": origin,
                "destination": dest,
                "textMap": text_map,
                "totalDeliveryDays": lead_days,
                "meetsDeadline": lead_days <= deadline,
                "riskLevel": "LOW" if lead_days <= deadline else "MEDIUM"
            }
        ]
