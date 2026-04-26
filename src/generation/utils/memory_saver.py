import requests
from typing import Optional  # Used for type hinting for better code clarity


# --- Function 1: Unload LM Studio Model ---

def unload_lmstudio_model(instance_id: str, base_url: str = "http://169.254.83.107:1234/api/v1/models/unload") -> \
Optional[bool]:
    """
    Unloads a specific model from LM Studio using its Instance ID.

    Args:
        instance_id (str): The unique ID of the model to unload (e.g., google/gemma-4-e4b).
        base_url (str): The base URL for the LM Studio API. Defaults to standard address.

    Returns:
        Optional[bool]: True if successful, False if failure due to API response,
                         None if connection error occurs.
    """
    payload = {
        "instance_id": instance_id
    }

    print(f"\n--- Starting LM Studio Model Unloading for: {instance_id} ---")
    try:
        response = requests.post(base_url, json=payload)

        if response.status_code == 200:
            print("✅ Memory released successfully! Model unloaded.")
            return True
        else:
            print(f"❌ Unloading failed (Status Code: {response.status_code}).")
            print(f"   Response details: {response.text}")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"🚨 Connection Error: Could not connect to LM Studio API ({base_url}). Please check if the service is running.")
        print(f"   Details: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return None


# --- Function 2: Free ComfyUI Memory ---

def free_comfyui_memory(url: str = "http://192.168.0.210:8188/free", payload: dict = None) -> bool:
    """
    Sends a command to the ComfyUI API to unload models and clear VRAM.

    Args:
        url (str): The API endpoint URL for ComfyUI. Defaults to specified address.
        payload (dict, optional): Data structure to send.
                                    Defaults to standard memory free payload if None.

    Returns:
        bool: True if successful (status code 200), False otherwise.
    """
    if payload is None:
        # Standard Memory Free Payload
        payload = {
            "unload_models": True,
            "free_memory": True
        }

    print("\n--- Starting ComfyUI VRAM Cleanup ---")
    try:
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            # Note: /free endpoint usually doesn't return useful content; success is the goal.
            print("✅ ComfyUI successfully received memory cleanup instruction (Status Code: 200).")
            return True
        else:
            print(f"❌ Memory clearing failed: {response.text}")
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"🚨 Connection Error: Could not connect to ComfyUI API ({url}). Please ensure ComfyUI is running.")
        print(f"   Details: {e}")
        return False
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
        return False


# =======================================================================
# 📝 Usage Example (Main Execution Block)
# =======================================================================

if __name__ == "__main__":
    # Model ID you want to unload
    #target_model_id = "google/gemma-4-e4b"
    target_model_id = "gemma-4-26b-a4b-it@iq3_xxs"

    # --- Execute LM Studio Unload ---
    lm_success = unload_lmstudio_model(instance_id=target_model_id)

    print("\n" + "=" * 50)

    # --- Execute ComfyUI Memory Free ---
    comfy_success = free_comfyui_memory()

    print("=" * 50)
    if lm_success and comfy_success:
        print("🎉 All resource cleanup processes completed!")
