
import sys
sys.path.append('.')
from engine import get_prediction

def test_prediction():
    print("Testing prediction engine...")
    try:
        result = get_prediction()
        if result:
            print("Successfully retrieved prediction!")
            print(result)
        else:
            print("Prediction failed (returned None). Check engine.py output.")
    except Exception as e:
        print(f"Prediction crashed: {e}")

if __name__ == "__main__":
    test_prediction()
