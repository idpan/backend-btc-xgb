from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import timedelta

from engine import get_prediction
from db_manager import DatabaseManager
from helpers.utils import load_json_file

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/api/predict/latest', methods=['GET'])
@jwt_required()
def get_latest():
    """Prediksi arah closing berikutnya (live, dari model)"""
    prediction_result = get_prediction()

    if prediction_result is None:
        return jsonify({"status": "error", "message": "Error retrieving prediction"}), 500

    direction = str(prediction_result['direction']).lower()
    confidence = float(prediction_result['confidence'])
    dataset_date = prediction_result['dataset_date']

    ref_date_str = dataset_date.strftime('%Y-%m-%d')
    ref_date_formatted = dataset_date.strftime('%d %b %Y')
    target_date_str = (dataset_date + timedelta(days=1)).strftime('%Y-%m-%d')

    # Upsert hasil prediksi ke database jika tersedia
    try:
        db = DatabaseManager()
        db.upsert_prediction_history(target_date_str, direction, confidence)
    except Exception as e:
        print(f"Upsert DB warning: {e}")

    prev_close = prediction_result.get('previous_close', 82605.23)

    return jsonify({
        "status": "success",
        "message": f"Data prediksi untuk tanggal {ref_date_str} berhasil diambil (Data Baru dari Yahoo Finance)",
        "data": {
            "id": f"pred-{dataset_date.strftime('%Y%m%d')}",
            "status": "pending",
            "tanggal": ref_date_str,
            "summary": {
                "prediction": direction,
                "reference_closing_date": ref_date_formatted,
                "reference_closing_price": prev_close,
                "next_closing_date": target_date_str,
                "next_closing_price": None,
                "result": "pending",
                "probability": confidence,
                "countdown_text": None
            },
            "calculation": prediction_result.get('calculation', {}),
            "features": prediction_result.get('features', []),
            "trees": prediction_result.get('trees', [])
        }
    }), 200


@prediction_bp.route('/api/prediction-history', methods=['GET'])
def get_history():
    """Riwayat prediksi harian"""
    history_data = load_json_file("prediction_history.json")
    if history_data is not None:
        return jsonify(history_data), 200

    # Fallback to DB
    try:
        db = DatabaseManager()
        predictions = db.get_prediction_history(limit=30)
        df_ohlcv = db.read_table_to_df('historical_data', index_col='date')
        df_ohlcv = df_ohlcv.sort_index()

        response_data = []
        for pred in predictions:
            pred_date = str(pred['date'])
            actual_direction = "pending"
            status = "pending"
            closing_price = 0.0
            next_closing_price = 0.0

            try:
                idx = df_ohlcv.index.get_loc(pred_date)
                if idx > 0:
                    next_closing_price = float(df_ohlcv.iloc[idx]['close'])
                    closing_price = float(df_ohlcv.iloc[idx-1]['close'])
                    actual_direction = "up" if next_closing_price > closing_price else "down"
                    status = "correct" if pred['direction'].lower() == actual_direction else "wrong"
                elif idx == 0:
                    next_closing_price = float(df_ohlcv.iloc[idx]['close'])
            except KeyError:
                pass

            formatted_date = pred_date
            if '-' in pred_date and len(pred_date.split('-')[0]) == 4:
                parts = pred_date.split('-')
                formatted_date = f"{parts[2]}-{parts[1]}-{parts[0]}"

            response_data.append({
                "date": formatted_date,
                "prediction_direction": pred['direction'].lower(),
                "actual_direction": actual_direction,
                "prediction_status": status,
                "closing_price": closing_price,
                "next_closing_price": next_closing_price
            })
        return jsonify(response_data), 200
    except Exception as e:
        print(f"Error reading prediction history: {e}")
        return jsonify([]), 200