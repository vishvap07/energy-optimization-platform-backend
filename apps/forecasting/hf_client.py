import logging
from gradio_client import Client
from django.conf import settings

logger = logging.getLogger(__name__)

class HuggingFaceClient:
    def __init__(self, space_id=None):
        self.space_id = space_id or settings.HF_SPACE_ID
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                # Use from_shared_uid is not needed, just Client(id) works for HF Spaces
                self._client = Client(self.space_id)
                logger.info(f"Hugging Face Client initialized for Space ID: {self.space_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Hugging Face client: {e}")
                raise
        return self._client

    def predict_next_hour(self, consumption_list, demand_list, temp_list):
        """
        Calls the HF Space API with 24-hour sequences.
        Each input list must have 24 floats.
        Returns the parsed predicted consumption (float).
        """
        try:
            # Convert lists to comma-separated strings as expected by the Gradio app
            c_str = ", ".join(map(str, consumption_list))
            d_str = ", ".join(map(str, demand_list))
            t_str = ", ".join(map(str, temp_list))

            logger.info(f"Calling HF Space at {self.space_id} endpoint /process_and_predict")
            
            result = self.client.predict(
                c_str=c_str,
                d_str=d_str,
                t_str=t_str,
                api_name="/process_and_predict"
            )

            # result is expected to be a dict or string based on the Label component
            # Format: "Predicted Consumption for Next Hour: 58.21 kWh"
            # Or if Gradio returns the dict: {'label': '...', 'confidences': [...]}
            
            prediction_text = ""
            if isinstance(result, dict):
                prediction_text = result.get('label', '')
            else:
                prediction_text = str(result)

            logger.info(f"HF Space Response: {prediction_text}")

            # Extract number from "Predicted Consumption for Next Hour: 58.21 kWh"
            # Split by ":" and "kWh"
            try:
                value_str = prediction_text.split(":")[-1].replace("kWh", "").strip()
                return float(value_str)
            except (ValueError, IndexError):
                logger.error(f"Could not parse prediction value from HF response: {prediction_text}")
                return None

        except Exception as e:
            logger.error(f"Hugging Face prediction failed: {e}")
            return None
