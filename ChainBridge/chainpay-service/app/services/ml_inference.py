"""
ChainPay ML Inference API stubs for Token-Economic Modeling.
Exposes: predict_expected_reward, predict_expected_burn, predict_settlement_volatility
"""

from ml_engine.models.token_settlement_forecast_model import TokenSettlementForecastModel
from ml_engine.models.token_volatility_model import TokenVolatilityModel
import pandas as pd

# Example stub functions

def predict_expected_reward(input_dict):
    model = TokenSettlementForecastModel()
    # Assume model is loaded/trained
    df = pd.DataFrame([input_dict])
    return model.predict(df)

def predict_expected_burn(input_dict):
    model = TokenSettlementForecastModel()
    # Assume model is loaded/trained
    df = pd.DataFrame([input_dict])
    result = model.predict(df)
    return result["prediction"]["expected_burn"] if "prediction" in result else None

def predict_settlement_volatility(input_dict):
    model = TokenVolatilityModel()
    # Assume model is loaded/trained
    df = pd.DataFrame([input_dict])
    return model.predict(df)
