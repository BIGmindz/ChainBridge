#!/usr/bin/env python3
"""
Enhanced LightGBM Regime Detection Model
Comprehensive multiclass classifier for market regime detection with expanded features
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
from typing import Dict, List, Tuple, Optional
import warnings

try:
    from lightgbm import LGBMClassifier
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
except ImportError as e:
    print(f"Required dependency missing: {e}")
    print("Please install: pip install lightgbm scikit-learn")
    sys.exit(1)

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


class EnhancedRegimeModel:
    """
    Enhanced LightGBM multiclass classification model for regime detection
    Features: RSI, MACD, Bollinger Bands, volume ratio, price changes, volatility, trend measures
    """
    
    def __init__(self, model_dir: str = 'ml_models'):
        self.model_dir = model_dir
        self.model = None
        self.label_encoder = None
        self.feature_scaler = None
        self.feature_columns = None
        self.model_metadata = {}
        
        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)
    
    def generate_sample_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        Generate sample financial data with all requested features for training/testing
        
        Args:
            n_samples: Number of samples to generate
            
        Returns:
            DataFrame with financial features and regime labels
        """
        logger.info(f"🎲 Generating {n_samples} sample data points...")
        
        np.random.seed(42)  # For reproducible results
        data = []
        
        for i in range(n_samples):
            # Base price simulation with different regimes
            regime_type = np.random.choice(['bull', 'bear', 'sideways'], p=[0.4, 0.3, 0.3])
            
            # Generate features based on regime
            if regime_type == 'bull':
                base_trend = np.random.uniform(0.02, 0.08)  # Positive trend
                volatility = np.random.uniform(0.15, 0.25)
                volume_multiplier = np.random.uniform(1.2, 2.0)
            elif regime_type == 'bear':
                base_trend = np.random.uniform(-0.08, -0.02)  # Negative trend
                volatility = np.random.uniform(0.20, 0.35)
                volume_multiplier = np.random.uniform(1.5, 2.5)
            else:  # sideways
                base_trend = np.random.uniform(-0.01, 0.01)  # Neutral
                volatility = np.random.uniform(0.10, 0.20)
                volume_multiplier = np.random.uniform(0.8, 1.2)
            
            # RSI (14-period)
            if regime_type == 'bull':
                rsi_14 = np.random.uniform(55, 85)
            elif regime_type == 'bear':
                rsi_14 = np.random.uniform(15, 45)
            else:
                rsi_14 = np.random.uniform(35, 65)
            
            # MACD components
            macd = base_trend * np.random.uniform(0.8, 1.2)
            macd_signal = macd * np.random.uniform(0.7, 0.9)
            macd_hist = macd - macd_signal
            
            # Bollinger Bands
            bb_middle = 50000 + np.random.normal(0, 5000)  # Mid price around 50k
            bb_width = bb_middle * volatility * np.random.uniform(0.8, 1.2)
            bb_upper = bb_middle + bb_width / 2
            bb_lower = bb_middle - bb_width / 2
            bb_position = np.random.uniform(0.2, 0.8) if regime_type == 'sideways' else (
                np.random.uniform(0.6, 0.9) if regime_type == 'bull' else np.random.uniform(0.1, 0.4)
            )
            
            # Volume ratio
            volume_ratio = 1.0 * volume_multiplier * np.random.uniform(0.7, 1.3)
            
            # Price changes
            price_change_1h = base_trend / 24 + np.random.normal(0, volatility / 10)
            price_change_24h = base_trend + np.random.normal(0, volatility)
            
            # Volatility measures
            volatility_24h = volatility * np.random.uniform(0.8, 1.2)
            
            # Trend strength
            if regime_type == 'bull':
                trend_strength = np.random.uniform(0.6, 1.0)
            elif regime_type == 'bear':
                trend_strength = np.random.uniform(-1.0, -0.6)
            else:
                trend_strength = np.random.uniform(-0.3, 0.3)
            
            # Additional features for enhanced model
            momentum_rsi = rsi_14 + np.random.normal(0, 5)  # RSI with momentum
            price_momentum = price_change_24h / volatility_24h if volatility_24h > 0 else 0
            volume_price_trend = volume_ratio * price_change_24h
            bb_squeeze = 1 if bb_width < bb_middle * 0.15 else 0  # Bollinger squeeze indicator
            
            data.append({
                # Core technical indicators
                'rsi_14': max(0, min(100, rsi_14)),
                'macd': macd,
                'macd_signal': macd_signal,
                'macd_hist': macd_hist,
                
                # Bollinger Bands
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'bb_width': bb_width,
                'bb_position': max(0, min(1, bb_position)),
                
                # Volume and price metrics
                'volume_ratio': max(0.1, volume_ratio),
                'price_change_1h': price_change_1h,
                'price_change_24h': price_change_24h,
                
                # Volatility measures
                'volatility_24h': max(0.01, volatility_24h),
                
                # Trend measures
                'trend_strength': max(-1, min(1, trend_strength)),
                
                # Enhanced features
                'momentum_rsi': max(0, min(100, momentum_rsi)),
                'price_momentum': price_momentum,
                'volume_price_trend': volume_price_trend,
                'bb_squeeze': bb_squeeze,
                
                # Target regime
                'regime': regime_type
            })
        
        df = pd.DataFrame(data)
        logger.info(f"✅ Generated {len(df)} samples with {len(df.columns)-1} features")
        logger.info(f"📊 Regime distribution: {df['regime'].value_counts().to_dict()}")
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare features and target from DataFrame
        
        Args:
            df: Input DataFrame with features and regime column
            
        Returns:
            Tuple of (features DataFrame, target Series)
        """
        # Separate features and target
        feature_cols = [col for col in df.columns if col != 'regime']
        X = df[feature_cols].copy()
        y = df['regime'].copy()
        
        # Store feature columns for later use
        self.feature_columns = feature_cols
        
        # Handle any missing values
        X = X.fillna(X.median())
        
        return X, y
    
    def train_model(self, df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> Dict:
        """
        Train the enhanced LightGBM regime detection model
        
        Args:
            df: Training DataFrame with features and regime labels
            test_size: Proportion of data to use for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Training results dictionary
        """
        logger.info("🚀 Training Enhanced LightGBM Regime Detection Model...")
        
        # Prepare features and target
        X, y = self.prepare_features(df)
        
        # Initialize and fit label encoder
        self.label_encoder = LabelEncoder()
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split the data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=random_state, stratify=y_encoded
        )
        
        # Initialize feature scaler (for numerical stability)
        self.feature_scaler = StandardScaler()
        X_train_scaled = self.feature_scaler.fit_transform(X_train)
        X_test_scaled = self.feature_scaler.transform(X_test)
        
        # Configure LightGBM for multiclass classification
        self.model = LGBMClassifier(
            objective='multiclass',
            num_class=len(self.label_encoder.classes_),
            random_state=random_state,
            n_estimators=200,
            learning_rate=0.1,
            max_depth=8,
            num_leaves=31,
            feature_fraction=0.9,
            bagging_fraction=0.8,
            bagging_freq=5,
            verbose=-1  # Suppress LightGBM output
        )
        
        # Train the model
        logger.info("🔥 Training model...")
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate the model
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=5)
        cv_mean = cv_scores.mean()
        cv_std = cv_scores.std()
        
        # Predictions for detailed evaluation
        y_pred = self.model.predict(X_test_scaled)
        
        # Store model metadata
        self.model_metadata = {
            'training_date': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'n_features': X.shape[1],
            'n_samples': X.shape[0],
            'feature_columns': self.feature_columns,
            'regime_classes': self.label_encoder.classes_.tolist(),
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'cv_mean': cv_mean,
            'cv_std': cv_std
        }
        
        # Log results
        logger.info(f"✅ Training completed!")
        logger.info(f"📊 Train Accuracy: {train_score:.3f}")
        logger.info(f"📊 Test Accuracy: {test_score:.3f}")
        logger.info(f"📊 CV Score: {cv_mean:.3f} (+/- {cv_std:.3f})")
        logger.info(f"🎯 Regime Classes: {self.label_encoder.classes_}")
        
        # Classification report
        class_report = classification_report(
            y_test, y_pred, 
            target_names=self.label_encoder.classes_, 
            output_dict=True
        )
        
        return {
            'model': self.model,
            'train_accuracy': train_score,
            'test_accuracy': test_score,
            'cv_mean': cv_mean,
            'cv_std': cv_std,
            'classification_report': class_report,
            'metadata': self.model_metadata
        }
    
    def predict(self, features: pd.DataFrame) -> Tuple[List[str], np.ndarray]:
        """
        Make predictions using the trained model
        
        Args:
            features: DataFrame with features for prediction
            
        Returns:
            Tuple of (predicted regimes, prediction probabilities)
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        # Ensure feature order matches training
        if self.feature_columns:
            features = features[self.feature_columns]
        
        # Scale features
        features_scaled = self.feature_scaler.transform(features)
        
        # Make predictions
        pred_encoded = self.model.predict(features_scaled)
        pred_proba = self.model.predict_proba(features_scaled)
        
        # Decode predictions
        pred_regimes = self.label_encoder.inverse_transform(pred_encoded)
        
        return pred_regimes.tolist(), pred_proba
    
    def predict_single(self, feature_dict: Dict) -> Dict:
        """
        Make a single prediction from a feature dictionary
        
        Args:
            feature_dict: Dictionary with feature values
            
        Returns:
            Dictionary with prediction results
        """
        # Convert to DataFrame
        df = pd.DataFrame([feature_dict])
        
        # Make prediction
        regimes, probas = self.predict(df)
        
        # Get confidence (highest probability)
        regime = regimes[0]
        confidence = probas[0].max()
        
        # Get all regime probabilities
        regime_probs = dict(zip(self.label_encoder.classes_, probas[0]))
        
        return {
            'regime': regime,
            'confidence': confidence,
            'probabilities': regime_probs,
            'timestamp': datetime.now().isoformat()
        }
    
    def save_model(self, filepath: str = None) -> str:
        """
        Save the trained model and metadata
        
        Args:
            filepath: Optional filepath. If None, uses default location.
            
        Returns:
            Path where model was saved
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")
        
        if filepath is None:
            filepath = os.path.join(self.model_dir, 'enhanced_regime_model.pkl')
        
        # Prepare model data for saving
        model_data = {
            'model': self.model,
            'label_encoder': self.label_encoder,
            'feature_scaler': self.feature_scaler,
            'feature_columns': self.feature_columns,
            'metadata': self.model_metadata
        }
        
        # Save the model
        joblib.dump(model_data, filepath)
        logger.info(f"💾 Enhanced regime model saved: {filepath}")
        
        return filepath
    
    def load_model(self, filepath: str = None) -> bool:
        """
        Load a trained model
        
        Args:
            filepath: Path to the saved model file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        if filepath is None:
            filepath = os.path.join(self.model_dir, 'enhanced_regime_model.pkl')
        
        try:
            if not os.path.exists(filepath):
                logger.error(f"Model file not found: {filepath}")
                return False
            
            # Load model data
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            self.feature_scaler = model_data['feature_scaler']
            self.feature_columns = model_data['feature_columns']
            self.model_metadata = model_data.get('metadata', {})
            
            logger.info(f"✅ Enhanced regime model loaded: {filepath}")
            logger.info(f"🎯 Regime Classes: {self.label_encoder.classes_}")
            logger.info(f"📊 Features: {len(self.feature_columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores from the trained model
        
        Returns:
            Dictionary mapping feature names to importance scores
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train_model() first.")
        
        importance_scores = self.model.feature_importances_
        feature_importance = dict(zip(self.feature_columns, importance_scores))
        
        # Sort by importance
        feature_importance = dict(sorted(feature_importance.items(), 
                                      key=lambda x: x[1], reverse=True))
        
        return feature_importance
    
    def print_model_summary(self):
        """Print a comprehensive summary of the model"""
        if self.model is None:
            print("❌ No model trained yet")
            return
        
        print("\n" + "="*60)
        print("🤖 ENHANCED REGIME DETECTION MODEL SUMMARY")
        print("="*60)
        
        metadata = self.model_metadata
        print(f"📅 Training Date: {metadata.get('training_date', 'Unknown')}")
        print(f"📊 Training Samples: {metadata.get('n_samples', 'Unknown')}")
        print(f"🎯 Number of Features: {metadata.get('n_features', 'Unknown')}")
        print(f"🏷️  Regime Classes: {', '.join(metadata.get('regime_classes', []))}")
        print(f"🎯 Train Accuracy: {metadata.get('train_accuracy', 0):.3f}")
        print(f"🎯 Test Accuracy: {metadata.get('test_accuracy', 0):.3f}")
        print(f"🎯 CV Score: {metadata.get('cv_mean', 0):.3f} (+/- {metadata.get('cv_std', 0):.3f})")
        
        print(f"\n📈 TOP 10 MOST IMPORTANT FEATURES:")
        feature_importance = self.get_feature_importance()
        for i, (feature, importance) in enumerate(list(feature_importance.items())[:10]):
            print(f"  {i+1:2d}. {feature:<20} : {importance:.4f}")
        
        print("\n" + "="*60)


def main():
    """
    Demonstration of the Enhanced Regime Detection Model
    """
    print("🚀 Enhanced LightGBM Regime Detection Model Demo")
    print("="*55)
    
    # Initialize the model
    model = EnhancedRegimeModel()
    
    # Generate sample data
    sample_data = model.generate_sample_data(n_samples=2000)
    
    # Train the model
    results = model.train_model(sample_data)
    
    # Save the model
    model_path = model.save_model()
    
    # Print model summary
    model.print_model_summary()
    
    # Demonstrate single prediction
    print(f"\n🔮 SAMPLE PREDICTION:")
    sample_features = {
        'rsi_14': 65.0,
        'macd': 0.02,
        'macd_signal': 0.015,
        'macd_hist': 0.005,
        'bb_upper': 52000,
        'bb_middle': 50000,
        'bb_lower': 48000,
        'bb_width': 4000,
        'bb_position': 0.75,
        'volume_ratio': 1.5,
        'price_change_1h': 0.01,
        'price_change_24h': 0.03,
        'volatility_24h': 0.20,
        'trend_strength': 0.7,
        'momentum_rsi': 68.0,
        'price_momentum': 0.15,
        'volume_price_trend': 0.045,
        'bb_squeeze': 0
    }
    
    prediction = model.predict_single(sample_features)
    print(f"Predicted Regime: {prediction['regime']}")
    print(f"Confidence: {prediction['confidence']:.3f}")
    print(f"All Probabilities: {prediction['probabilities']}")
    
    print(f"\n✅ Model saved at: {model_path}")
    print("🎉 Demo completed successfully!")


if __name__ == "__main__":
    main()