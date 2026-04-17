import logging
import requests
import json
from django.conf import settings

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    def __init__(self, space_id=None):
        # We manually build the prediction URL instead of relying on the library to fetch it
        self.space_id = space_id or getattr(settings, 'HF_SPACE_ID', 'Vishva1574/EnergyForecasting')
        # Subdomain based URL for HF Spaces
        self.api_url = f"https://{self.space_id.replace('/', '-').lower()}.hf.space/run/predict"

    def predict_next_hour(self, consumption_list, demand_list, temp_list):
        """
        Calls the HF Space via direct POST request.
        Bypasses metadata fetching to ensure stability on Render.
        """
        try:
            # Convert lists to comma-separated strings as expected by the Gradio app
            c_str = ", ".join(map(str, consumption_list))
            d_str = ", ".join(map(str, demand_list))
            t_str = ", ".join(map(str, temp_list))

            # Gradio API payload format
            payload = {
                "data": [c_str, d_str, t_str],
                "event_data": None,
                "fn_index": 0, # Assuming the first function is the predictor
                "trigger_id": None
            }

            logger.info(f"Direct API Call: {self.api_url}")
            response = requests.post(self.api_url, json=payload, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"HF Space Error ({response.status_code}): {response.text}")
                return None

            # Response structure: {"data": ["Result String"], "is_generating": false, ...}
            resp_data = response.json()
            prediction_text = resp_data["data"][0] if "data" in resp_data and len(resp_data["data"]) > 0 else ""

            logger.info(f"HF Response: {prediction_text}")

            # Extract number from "Predicted Consumption for Next Hour: 58.21 kWh"
            try:
                # Remove label and units
                value_str = prediction_text.split(":")[-1].replace("kWh", "").strip()
                return float(value_str)
            except (ValueError, IndexError):
                logger.error(f"Could not parse value from: {prediction_text}")
                return None

        except Exception as e:
            logger.error(f"Hugging Face direct call failed: {e}")
            return None
