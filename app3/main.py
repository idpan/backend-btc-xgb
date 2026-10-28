from flask import Flask, jsonify
from flask_cors import CORS
from engine import get_prediction,feature_engineering
app = Flask(__name__)
CORS(app)

@app.route('/')
def hello_world():
    return 'Halo, Dunia Flask di Ubuntu!'

@app.route('/api/predict/latest')
def get_latest():
    
    # get_prediction() sekarang mengembalikan dictionary, misalnya:
    # {'direction': 'up', 'confidence': 0.85, 'date': '2026-01-27'}
    prediction_result = get_prediction(feature_engineering())
    
    # Cek jika get_prediction mengembalikan None (jika ada error)
    if prediction_result is None:
        return {
            "message": "Error retrieving prediction",
            "data": None,
            "status": "error"
        }

    # Ambil nilai langsung dari dictionary menggunakan key string
    direction = prediction_result['direction']
    confidence = prediction_result['confidence']
    date = prediction_result['date']
    
    # Tidak perlu lagi konversi int(), round(), isoformat() karena sudah dilakukan di get_prediction()

    return {
        "message":"prediction retrieved successfully",
        "status": "success",
        "data":{
                "date": date,
                "direction": direction,
                "confidence_level": confidence
        }
    }

# Contoh penggunaan:
# print(get_latest()) 


if __name__ == '__main__':
    app.run(debug=True)
    